"""Subprocess harness for real browser/GPU checks; not an application endpoint."""
import sys
import threading
import faulthandler
import time
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uvicorn

faulthandler.dump_traceback_later(30, repeat=True)
print("Loading application for browser integration", flush=True)
from app.main import app
app.state.engine.prepare_runtime()

@app.get("/__integration_id", include_in_schema=False)
def integration_id():
    return {"token": os.environ.get("TTS_TEST_TOKEN")}

server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="info", http="h11"))
thread = threading.Thread(target=server.run)
thread.start()
while not server.started and thread.is_alive():
    time.sleep(.1)
faulthandler.cancel_dump_traceback_later()
try:
    sys.stdin.readline()
finally:
    server.should_exit = True
    thread.join()
    faulthandler.cancel_dump_traceback_later()
