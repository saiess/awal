import copy
import logging
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from uuid import uuid4

from .audio import write_raw
from .projects import file_hash, now

log = logging.getLogger(__name__)


class BusyError(Exception):
    pass


class Jobs:
    def __init__(self, store, engine):
        self.store, self.engine = store, engine
        self.gate = threading.Lock()
        self.state_lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="narration")
        self.stop = threading.Event()
        self.records = {}
        self.active_id = None

    @contextmanager
    def idle(self):
        if self.stop.is_set() or not self.gate.acquire(blocking=False):
            raise BusyError("Another operation is running. Please wait for it to finish.")
        try:
            yield
        finally:
            self.gate.release()

    def active(self):
        with self.state_lock:
            return copy.deepcopy(self.records.get(self.active_id))

    def read(self, job_id):
        with self.state_lock:
            if job_id not in self.records:
                raise KeyError("Job not found. Reopen the saved project after a restart.")
            return copy.deepcopy(self.records[job_id])

    def update(self, job_id, **values):
        with self.state_lock:
            self.records[job_id].update(values)

    def start(self, project_id, segment_id=None, only_missing=True):
        if self.stop.is_set() or not self.gate.acquire(blocking=False):
            raise BusyError("Generation or export is already running.")
        try:
            p = self.store.read(project_id)
            targets = ([self.store.segment(p, segment_id)] if segment_id else
                       [s for s in p["segments"] if not only_missing or s["status"] != "ready" or s["stale"]])
            if not targets:
                raise ValueError("All sections are already up to date.")
            job_id = str(uuid4())
            record = {"id": job_id, "project_id": p["id"], "status": "queued", "created_at": now(),
                      "done_segments": 0, "failed_segments": 0, "total_segments": len(targets),
                      "active_segment_id": None, "error": None}
            with self.state_lock:
                self.records[job_id] = record
                self.active_id = job_id
            self.executor.submit(self.run, job_id, p, [s["id"] for s in targets])
            return copy.deepcopy(record)
        except Exception:
            self.gate.release()
            raise

    def run(self, job_id, project, target_ids):
        failures = 0
        try:
            self.update(job_id, status="generating")
            reference = self.store.path(project["narrator"]["reference_audio_relative_path"])
            if file_hash(reference) != project["narrator"]["reference_sha256"]:
                raise ValueError("Saved narrator recording checksum changed. Restore its original file.")
            self.engine.load()
            for segment_id in target_ids:
                if self.stop.is_set():
                    self.update(job_id, status="interrupted", error="Stopped between sections. Generate remaining sections to resume.")
                    return
                self.update(job_id, active_segment_id=segment_id)
                def begin(p):
                    s = self.store.segment(p, segment_id)
                    base_seed = project["narrator"]["engine_parameters"].get("seed", 1234)
                    previous_seed = s.get("last_attempt_seed", (s.get("generation_parameters") or {}).get("seed", base_seed))
                    attempted = "last_attempt_seed" in s or s["version"] > 0 or s["status"] == "failed"
                    # Keep the initial baseline; every retry differs from the previous attempt,
                    # including failures. Persist before inference so restarts retain the seed.
                    seed = (previous_seed + 1 + secrets.randbelow(2**32 - 1)) % 2**32 if attempted else base_seed
                    s.update(status="generating", stale=True, error=None, last_attempt_seed=seed)
                current = self.store.change(project["id"], begin)
                segment = self.store.segment(current, segment_id)
                try:
                    parameters = copy.deepcopy(project["narrator"]["engine_parameters"])
                    parameters["seed"] = segment["last_attempt_seed"]
                    result = self.engine.synthesize(segment["text"], reference, parameters)
                    version = segment["version"] + 1
                    folder = self.store.project_dir(project["id"]) / "segments" / segment_id
                    while (folder / f"v{version:04}_raw.wav").exists():
                        version += 1
                    target = folder / f"v{version:04}_raw.wav"
                    info = write_raw(target, result.samples, result.sample_rate)
                    def commit(p):
                        s = self.store.segment(p, segment_id)
                        s.update(status="ready", stale=False, error=None, version=version,
                                 audio_path=target.relative_to(self.store.root).as_posix(),
                                 duration_seconds=info["duration_seconds"], sample_rate=result.sample_rate,
                                 sha256=info["sha256"], generated_at=now(), metrics=result.metrics,
                                 generated_text=segment["text"],
                                 generation_parameters=parameters)
                    self.store.change(project["id"], commit)
                except Exception:
                    log.exception("Section generation failed: project=%s section=%s", project["id"], segment_id)
                    failures += 1
                    error = "Generation failed. Previous audio is preserved. See data/logs/app.log, then retry this section."
                    def fail(p):
                        self.store.segment(p, segment_id).update(status="failed", stale=True, error=error)
                    self.store.change(project["id"], fail)
                    self.update(job_id, failed_segments=failures, error=error)
                self.update(job_id, done_segments=self.read(job_id)["done_segments"] + 1)
            self.update(job_id, status="failed" if failures else "ready")
        except Exception as e:
            log.exception("Generation initialization failed")
            self.update(job_id, status="failed", error=str(e) if isinstance(e, (ValueError, RuntimeError)) else
                        "Model initialization failed. Check CUDA, pinned model cache, and data/logs/app.log.")
        finally:
            self.update(job_id, active_segment_id=None, finished_at=now())
            with self.state_lock:
                self.active_id = None
            self.gate.release()

    def close(self):
        self.stop.set()
        self.executor.shutdown(wait=True)
