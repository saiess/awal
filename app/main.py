import logging
from contextlib import asynccontextmanager

from filelock import FileLock, Timeout

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api import routes
from .config import ROOT, Settings
from .jobs import BusyError, Jobs
from .projects import Store
from .tts.engine import TurboEngine


def create_app(settings=None, engine=None):
    settings = settings or Settings()
    store = Store(settings)
    engine = engine or TurboEngine(settings)
    jobs = Jobs(store, engine)

    @asynccontextmanager
    async def lifespan(app):
        logdir = store.path("logs")
        logdir.mkdir(exist_ok=True)
        handler = logging.FileHandler(logdir / "app.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger = logging.getLogger("app")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        lock = FileLock(store.path(".app.lock"))
        try:
            try:
                lock.acquire(timeout=0)
            except Timeout as e:
                raise RuntimeError("Another application instance is already using this data folder. Close it first.") from e
            if hasattr(engine, "prepare_runtime"):
                # Startup occurs on the server thread before requests; weights remain unloaded.
                engine.prepare_runtime()
            await run_in_threadpool(store.recover)
            yield
        finally:
            await run_in_threadpool(jobs.close)
            lock.release()
            logger.removeHandler(handler)
            handler.close()

    app = FastAPI(title="Local Narration", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.store, app.state.jobs, app.state.engine = store, jobs, engine
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    @app.middleware("http")
    async def local_requests(request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if (origin and origin.rstrip("/") != f"{request.url.scheme}://{request.url.netloc}") or request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "Cross-origin writes are not allowed."}, status_code=403)
            length = request.headers.get("content-length", "0")
            if not length.isdigit() or int(length) > settings.max_upload_bytes + 1024*1024:
                return JSONResponse({"detail": "Request is too large."}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(BusyError)
    async def busy(request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    @app.exception_handler(KeyError)
    async def missing(request, error):
        return JSONResponse({"detail": str(error.args[0])}, status_code=404)

    @app.exception_handler(ValueError)
    async def invalid(request, error):
        return JSONResponse({"detail": str(error)}, status_code=422)

    @app.exception_handler(Exception)
    async def failed(request, error):
        logging.getLogger("app").error("Request failed", exc_info=error)
        return JSONResponse({"detail": "Operation failed. Existing files are preserved; see data/logs/app.log."}, status_code=500)

    app.include_router(routes(store, jobs, engine, settings))
    app.mount("/static", StaticFiles(directory=ROOT / "app/static"), name="static")

    @app.get("/docs", include_in_schema=False, response_class=HTMLResponse)
    def docs():
        return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Local Narration API</title>
        <link rel="icon" href="/static/favicon.svg"><link rel="stylesheet" href="/static/vendor/swagger/swagger-ui.css">
        <script defer src="/static/vendor/swagger/swagger-ui-bundle.js"></script><script defer src="/static/docs.js"></script>
        </head><body><div id="swagger-ui"></div></body></html>'''

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(ROOT / "app/static/index.html")

    return app


app = create_app()
