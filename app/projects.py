import copy
import hashlib
import json
import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from .config import ENGINE_ID, MODEL_REVISION, PARAMETERS
from .segmentation import segment_text


def now():
    return datetime.now(timezone.utc).isoformat()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_path(root, relative):
    root = Path(root).resolve()
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Invalid relative path.")
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError("Path is outside the data directory.")
    return target


def identifier(value):
    return str(UUID(str(value)))


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        with temp.open("w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


class Store:
    def __init__(self, settings):
        self.settings = settings
        self.root = settings.data_root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def path(self, relative):
        return safe_path(self.root, relative)

    def project_dir(self, project_id):
        return self.path(f"projects/{identifier(project_id)}")

    def project_file(self, project_id, relative):
        target = self.path(relative)
        if not target.is_relative_to(self.project_dir(project_id)):
            raise ValueError("File does not belong to this project.")
        if not target.is_file():
            raise KeyError("Audio file not found.")
        return target

    def read(self, project_id):
        with self.lock:
            path = self.project_dir(project_id) / "project.json"
            if not path.is_file():
                raise KeyError("Project not found.")
            return json.loads(path.read_text(encoding="utf-8"))

    def save(self, project):
        with self.lock:
            project["updated_at"] = now()
            atomic_json(self.project_dir(project["id"]) / "project.json", project)

    def change(self, project_id, update):
        with self.lock:
            project = self.read(project_id)
            update(project)
            self.save(project)
            return project

    def list_projects(self):
        with self.lock:
            rows = []
            for path in (self.root / "projects").glob("*/project.json"):
                p = json.loads(path.read_text(encoding="utf-8"))
                rows.append({"id": p["id"], "title": p["title"], "updated_at": p["updated_at"],
                             "segment_count": len(p["segments"]),
                             "ready_count": sum(s["status"] == "ready" and not s["stale"] for s in p["segments"])})
            return sorted(rows, key=lambda r: r["updated_at"], reverse=True)

    def narrator(self, narrator_id=None):
        if narrator_id is None:
            pointer = self.path("narrators/current.json")
            if not pointer.exists():
                return None
            narrator_id = json.loads(pointer.read_text())["id"]
        path = self.path(f"narrators/{identifier(narrator_id)}/profile.json")
        if not path.exists():
            raise KeyError("Narrator not found.")
        return json.loads(path.read_text(encoding="utf-8"))

    def add_narrator(self, label, reference, consent, source=None):
        narrator_id = str(uuid4())
        folder = self.path(f"narrators/{narrator_id}")
        folder.mkdir(parents=True)
        try:
            target = folder / "reference.wav"
            shutil.copyfile(reference, target)
            if source:
                shutil.copyfile(source, folder / "original.audio")
            profile = {"id": narrator_id, "label": label, "mode": "reference", "language": "en",
                       "reference_audio_relative_path": target.relative_to(self.root).as_posix(),
                       "reference_sha256": file_hash(target), "engine_id": ENGINE_ID,
                       "engine_revision": MODEL_REVISION, "engine_parameters": copy.deepcopy(PARAMETERS),
                       "created_at": now(), "consent": consent}
            atomic_json(folder / "profile.json", profile)
            atomic_json(self.path("narrators/current.json"), {"id": narrator_id})
            return profile
        except Exception:
            # Leave no active pointer to a partially created profile; files can be inspected locally.
            raise

    def create(self, title, script, narrator_id):
        if len(script) > self.settings.max_script_chars:
            raise ValueError("Script is too long.")
        narrator = self.narrator(narrator_id)
        project = {"schema_version": 1, "id": str(uuid4()), "title": title, "language": "en",
                   "narrator_id": narrator["id"], "narrator": copy.deepcopy(narrator),
                   "engine_id": ENGINE_ID, "engine_revision": MODEL_REVISION,
                   "created_at": now(), "script": script,
                   "export_settings": {"speed": self.settings.default_speed, "processed": True,
                                       "enhance": False, "gap_seconds": .12}, "exports": [], "segments": []}
        for i, text in enumerate(segment_text(script, self.settings.segment_chars)):
            project["segments"].append({"id": str(uuid4()), "order": i, "text": text, "status": "pending",
                                        "stale": True, "audio_path": None, "version": 0, "duration_seconds": None,
                                        "error": None, "generation_parameters": None, "generated_at": None})
        self.save(project)
        return project

    @staticmethod
    def segment(project, segment_id):
        segment_id = identifier(segment_id)
        for segment in project["segments"]:
            if segment["id"] == segment_id:
                return segment
        raise KeyError("Section not found.")

    def edit(self, project_id, segment_id, text):
        def update(p):
            segment = self.segment(p, segment_id)
            if segment["text"] != text:
                segment.update(text=text, stale=True, status="pending", error=None)
        return self.change(project_id, update)

    def recover(self):
        for row in self.list_projects():
            p = self.read(row["id"])
            changed = False
            for s in p["segments"]:
                if s["status"] == "generating":
                    s.update(status="pending", stale=True,
                             error="Generation was interrupted. Previous audio, if any, is preserved; retry this section.")
                    changed = True
            if changed:
                self.save(p)
