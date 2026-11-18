"""Subprocess harness for real browser/GPU checks; not an application endpoint."""
import sys
import threading
import faulthandler
import time
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uvicorn
import socket
original_connect = socket.socket.connect
def local_only(sock, address):
    if sock.family in (socket.AF_INET,socket.AF_INET6) and address[0] not in ('127.0.0.1','::1','localhost'):
        raise RuntimeError('External network blocked during application integration verification')
    return original_connect(sock,address)
socket.socket.connect=local_only

faulthandler.dump_traceback_later(30, repeat=True)
print("Loading application for browser integration", flush=True)
from app.main import app
app.state.engine.prepare_runtime()

@app.get("/__integration_id", include_in_schema=False)
def integration_id():
    return {"token": os.environ.get("TTS_TEST_TOKEN")}

server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="info", http="h11",
                                      timeout_graceful_shutdown=30))
faulthandler.cancel_dump_traceback_later()
def stop_on_input():
    sys.stdin.readline()
    server.should_exit = True
threading.Thread(target=stop_on_input,daemon=True).start()
server.run()
