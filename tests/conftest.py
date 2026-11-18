import io
import threading
import time
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.tts.engine import AudioResult


class FakeEngine:
    loaded = False
    gpu_available = True
    fail = False
    malformed = None
    calls = 0
    entered = None
    release = None

    def load(self):
        self.loaded = True

    def synthesize(self, text, reference, options):
        self.calls += 1
        if self.entered:
            self.entered.set()
            assert self.release.wait(10)
        if self.fail:
            raise RuntimeError("deliberate inference failure")
        samples = np.sin(2*np.pi*(220+len(text))*np.arange(24000)/24000).astype(np.float32)*.12
        if self.malformed == "nan": samples[3] = np.nan
        if self.malformed == "silent": samples[:] = 0
        return AudioResult(samples, 16000 if self.malformed == "rate" else 24000, {"generation_seconds": .01})


def reference_bytes(seconds=12):
    buffer = io.BytesIO()
    sf.write(buffer, .1*np.sin(2*np.pi*180*np.arange(24000*seconds)/24000), 24000, format="WAV", subtype="FLOAT")
    return buffer.getvalue()


@pytest.fixture
def setup(tmp_path):
    settings = Settings(data_root=tmp_path / "data")
    engine = FakeEngine()
    app = create_app(settings, engine=engine)
    source = tmp_path / "reference.wav"
    source.write_bytes(reference_bytes())
    narrator = app.state.store.add_narrator("Test narrator", source, {"rights_confirmed": True}, transcript="The exact reference words.")
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield client, app, engine, narrator


def create_project(client, narrator, script="First section.\n\nSecond section.\n\nThird section."):
    response = client.post("/api/projects", json={"title": "Test narration", "script": script, "narrator_id": narrator["id"]})
    assert response.status_code == 201, response.text
    return response.json()


def finish(client, response):
    assert response.status_code == 202, response.text
    job = response.json()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        job = client.get("/api/jobs/" + job["id"]).json()
        if job["status"] in ("ready", "failed", "interrupted"):
            return job
        time.sleep(.01)
    raise AssertionError("Job timed out")
