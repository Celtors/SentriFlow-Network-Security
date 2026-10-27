from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from sentriflow.api import ws
from sentriflow.api.routes import (
    alerts,
    blocklist,
    flows,
    geo,
    halts,
    health,
    patterns,
    processes,
    rules,
    score,
    settings,
    system,
)
from sentriflow.api.security import valid_host, valid_origin, valid_token
from sentriflow.application import Runtime


def create_app(runtime: Runtime | None = None, token: str | None = None) -> FastAPI:
    rt = runtime or Runtime()
    if token is not None:
        rt.token = token

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        owns_runtime = not rt.started
        if owns_runtime:
            await rt.open()
        try:
            yield
        finally:
            if owns_runtime:
                await rt.close()

    app = FastAPI(
        title="SentriFlow", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None
    )
    app.state.runtime = rt

    @app.middleware("http")
    async def local_session(request: Request, call_next):
        if not valid_host(request.headers, rt.config) or not valid_origin(
            request.headers, rt.config
        ):
            return JSONResponse({"detail": "Untrusted host or origin"}, status_code=403)
        if request.url.path.startswith("/api") and not valid_token(request.headers, rt.token):
            return JSONResponse({"detail": "Session token required"}, status_code=401)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; connect-src 'self' ws://127.0.0.1:* ws://localhost:*; "
            "img-src 'self' data:; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"
        )
        return response

    for module in (
        health,
        flows,
        processes,
        halts,
        rules,
        patterns,
        alerts,
        blocklist,
        score,
        geo,
        settings,
        system,
    ):
        app.include_router(module.router, prefix="/api")
    app.include_router(ws.router)
    web = rt.config.frontend_dir
    if (web / "index.html").is_file():

        @app.get("/")
        async def dashboard() -> FileResponse:
            return FileResponse(web / "index.html")

        app.mount("/", StaticFiles(directory=web, html=True), name="dashboard")
    else:

        @app.get("/")
        async def index() -> dict[str, str]:
            return {"service": "SentriFlow", "dashboard": "Frontend build is not installed"}

    return app
