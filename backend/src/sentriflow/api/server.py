from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
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
from sentriflow.api.security import Security
from sentriflow.runtime import Runtime


def create_app(runtime: Runtime, token: str) -> FastAPI:
    app = FastAPI(title="SentriFlow", docs_url=None, redoc_url=None, openapi_url=None)
    security = Security(runtime.config.api_port, token)
    app.state.runtime, app.state.security = runtime, security

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        if not security.boundary(request):
            return JSONResponse({"detail": "Local peer, Host or Origin rejected"}, status_code=403)
        if request.url.path.startswith("/api"):
            authorization = request.headers.get("authorization", "")
            if not authorization.startswith("Bearer ") or not security.valid_token(
                authorization[7:]
            ):
                return JSONResponse({"detail": "Session token required"}, status_code=401)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'self'"
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
    if runtime.config.frontend_dir.is_dir():
        app.mount("/", StaticFiles(directory=runtime.config.frontend_dir, html=True), name="web")
    else:

        @app.get("/")
        async def missing_build():
            raise HTTPException(503, "Build the frontend with scripts/build.ps1 first")

    return app
