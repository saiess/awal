"""Process control for the current isolated Chrome/CUDA smoke test."""

import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx

ROOT=Path(__file__).resolve().parents[1]
BASE="http://127.0.0.1:8001"


def stop(process):
    if process and process.poll() is None:
        process.stdin.write("stop\n")
        process.stdin.flush()
        try:
            process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            if os.name=="nt":
                subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],capture_output=True,check=True)
            else:
                process.kill()
            process.wait(timeout=20)


def start(log):
    token=uuid4().hex
    env=dict(os.environ,HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",TTS_TEST_TOKEN=token)
    process=subprocess.Popen([str(ROOT / ".venv-qwen3/Scripts/python.exe"),str(ROOT / "tests/live_server.py")],cwd=ROOT,env=env,
        stdin=subprocess.PIPE,stdout=log,stderr=log,text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        if process.poll() is not None:
            raise RuntimeError("Isolated test server exited; inspect its server.log.")
        try:
            identity=httpx.get(BASE+"/__integration_id",timeout=2)
            if identity.status_code==200 and identity.json().get("token")==token:
                health=httpx.get(BASE+"/api/health",timeout=5)
                health.raise_for_status()
                return process,health.json()
        except httpx.HTTPError:
            pass
        time.sleep(.3)
    stop(process)
    raise RuntimeError("Isolated test server startup timed out.")
