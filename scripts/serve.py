"""Foreground local server; a single process owns the model and generation worker."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == "__main__":
    import uvicorn
    server = uvicorn.Server(uvicorn.Config("app.main:app", host="127.0.0.1", port=8000,
                                        workers=1, http="h11", ws="none", timeout_graceful_shutdown=120))
    if "--stop-on-stdin" in sys.argv:
        import threading
        # Load native libraries before starting any helper thread on Windows.
        from app.main import app
        app.state.engine.prepare_runtime()

        def stop_on_input():
            sys.stdin.readline()
            server.should_exit = True

        threading.Thread(target=stop_on_input, daemon=True).start()
    server.run()
