import logging
import re
import subprocess
import tempfile
from pathlib import Path
from uuid import UUID

import soundfile as sf
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from . import audio
from .models import ExportInput, GenerateInput, ProjectInput, ScriptInput, SegmentInput
from .projects import now
from .segmentation import segment_text

log = logging.getLogger(__name__)


def routes(store, jobs, engine, settings):
    router = APIRouter(prefix="/api")

    @router.get("/health")
    def health():
        return {"status": "ok", "engine_loaded": engine.loaded, "gpu_available": engine.gpu_available,
                "busy": jobs.gate.locked(), "active_job": jobs.active(),
                "engine_id": "chatterbox-turbo", "default_export_speed": settings.default_speed}

    @router.get("/narrators")
    def narrators():
        profile = store.narrator()
        return [profile] if profile else []

    @router.get("/narrators/{narrator_id}/reference")
    def reference(narrator_id: UUID):
        profile = store.narrator(narrator_id)
        return FileResponse(store.path(profile["reference_audio_relative_path"]), media_type="audio/wav")

    @router.post("/narrators", status_code=201)
    async def upload_narrator(label: str = Form(..., min_length=1, max_length=120),
                              rights_confirmed: bool = Form(...), reference_audio: UploadFile = File(...)):
        if not rights_confirmed:
            raise HTTPException(403, "Confirm permission to clone and publish this voice commercially.")
        if not label.strip():
            raise HTTPException(422, "Give the narrator a nonempty label.")
        allowed_types = {"audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave", "audio/ogg", "application/ogg",
                         "audio/opus", "audio/flac", "audio/x-flac", "audio/mpeg", "audio/mp3", "audio/mp4", "audio/x-m4a"}
        if reference_audio.content_type not in allowed_types:
            raise HTTPException(415, "Upload a WAV, OGG, FLAC, MP3, or M4A audio recording.")
        filename = reference_audio.filename or ""
        demuxers = {".wav": "wav", ".ogg": "ogg", ".opus": "ogg", ".flac": "flac", ".mp3": "mp3", ".m4a": "mov"}
        ext = Path(filename).suffix.lower()
        if ext not in demuxers or any(c in filename for c in ("/", "\\", ":")) or len(filename) > 180:
            raise HTTPException(422, "Unsupported or invalid audio filename.")
        content = await reference_audio.read(settings.max_upload_bytes + 1)
        await reference_audio.close()
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(413, "Reference recordings must be 15 MB or smaller.")
        def decode_and_save():
            with jobs.idle(), tempfile.TemporaryDirectory(prefix="reference-", dir=store.root) as tmp:
                source = Path(tmp) / "source.audio"
                source.write_bytes(content)
                converted = Path(tmp) / "reference.wav"
                cmd = [audio.ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                       "-protocol_whitelist", "file,pipe", "-f", demuxers[ext], "-i", str(source),
                       "-t", "31", "-map", "0:a:0", "-vn", "-ar", "24000", "-ac", "1", "-c:a", "pcm_f32le", str(converted)]
                p = subprocess.run(cmd, capture_output=True, timeout=60)
                if p.returncode:
                    raise ValueError("The recording could not be decoded. Upload a valid audio file.")
                samples, sr = sf.read(converted, dtype="float32")
                audio.validate_audio(samples, sr)
                if not 10 <= len(samples)/sr <= 30:
                    raise ValueError("Use a clear 10–30-second reference recording.")
                return store.add_narrator(label.strip(), converted,
                                          {"rights_confirmed": True, "confirmed_at": now(),
                                           "statement": "User confirmed rights to clone and publish commercially."}, source)
        return await run_in_threadpool(decode_and_save)

    @router.post("/segment")
    def preview(body: ScriptInput):
        return {"segments": segment_text(body.script, settings.segment_chars)}

    @router.get("/projects")
    def list_projects():
        return store.list_projects()

    @router.post("/projects", status_code=201)
    def create_project(body: ProjectInput):
        with jobs.idle():
            return store.create(body.title, body.script, body.narrator_id)

    @router.get("/projects/{project_id}")
    def project(project_id: UUID):
        return store.read(project_id)

    @router.patch("/projects/{project_id}/segments/{segment_id}")
    def edit(project_id: UUID, segment_id: UUID, body: SegmentInput):
        with jobs.idle():
            return store.edit(project_id, segment_id, body.text)

    @router.post("/projects/{project_id}/generate", status_code=202)
    def generate(project_id: UUID, body: GenerateInput):
        return jobs.start(project_id, only_missing=body.only_missing_or_stale)

    @router.post("/projects/{project_id}/segments/{segment_id}/regenerate", status_code=202)
    def regenerate(project_id: UUID, segment_id: UUID):
        return jobs.start(project_id, segment_id=segment_id)

    @router.get("/jobs/{job_id}")
    def job(job_id: UUID):
        return jobs.read(str(job_id))

    @router.get("/projects/{project_id}/segments/{segment_id}/audio")
    def section_audio(project_id: UUID, segment_id: UUID):
        s = store.segment(store.read(project_id), segment_id)
        if not s["audio_path"]:
            raise KeyError("This section has not been generated yet.")
        return FileResponse(store.project_file(project_id, s["audio_path"]), media_type="audio/wav")

    @router.post("/projects/{project_id}/exports", status_code=201)
    def export(project_id: UUID, body: ExportInput):
        with jobs.idle():
            # Missing/stale sections are a state conflict, not a malformed format request.
            p = store.read(project_id)
            selected = [store.segment(p, s) for s in body.segment_ids] if body.segment_ids else p["segments"]
            if any(s["status"] != "ready" or s["stale"] for s in selected):
                raise HTTPException(409, "Generate the selected sections before exporting; some are missing, failed, or stale.")
            return audio.export_project(store, project_id, body)

    @router.get("/projects/{project_id}/exports/{export_id}/download")
    def download(project_id: UUID, export_id: UUID, download: bool = False, audio_only: bool = False):
        p = store.read(project_id)
        record = next((e for e in p["exports"] if e["id"] == str(export_id)), None)
        if record is None:
            raise KeyError("Export not found.")
        file = store.project_file(project_id, record["audio_path"] if audio_only else record["download_path"])
        title = re.sub(r"[^\w -]", "", p["title"]).strip()[:80] or "narration"
        types = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".zip": "application/zip"}
        return FileResponse(file, filename=title + file.suffix, media_type=types[file.suffix],
                            content_disposition_type="attachment" if download else "inline")

    return router
