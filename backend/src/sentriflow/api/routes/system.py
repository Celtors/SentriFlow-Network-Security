import asyncio
import subprocess

from fastapi import APIRouter, HTTPException, Request

from sentriflow.api.schemas import Consent, ProxyCommand
from sentriflow.os_adapters.windows.cert_store import certificate_status, manage_ca

router = APIRouter()


@router.get("/system/status")
async def status(request: Request):
    return request.app.state.runtime.system_status()


@router.post("/system/proxy")
async def proxy(body: ProxyCommand, request: Request):
    runtime = request.app.state.runtime
    if body.enabled and not runtime.proxy_running:
        raise HTTPException(409, "Interception proxy is not running")
    try:
        if body.enabled:
            runtime.system_proxy.enable()
        else:
            runtime.system_proxy.restore()
    except (RuntimeError, OSError) as exc:
        raise HTTPException(409, str(exc)) from exc
    runtime.events.publish("system.status", runtime.system_status())
    return runtime.system_status()


@router.get("/system/ca")
async def ca_status(request: Request):
    return certificate_status(request.app.state.runtime.config.data_dir / "ca")


@router.post("/system/ca")
async def install_ca(body: Consent, request: Request):
    if not body.consent:
        raise HTTPException(422, "Explicit consent is required to trust the local HTTPS CA")
    try:
        await asyncio.to_thread(manage_ca, request.app.state.runtime.config.data_dir / "ca", True)
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(
            409, "CA install failed; inspect doctor output and permissions"
        ) from exc
    return ca_status_response(request)


@router.delete("/system/ca")
async def remove_ca(request: Request):
    try:
        await asyncio.to_thread(manage_ca, request.app.state.runtime.config.data_dir / "ca", False)
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(409, "CA removal failed; certificate files were preserved") from exc
    return ca_status_response(request)


def ca_status_response(request: Request):
    return certificate_status(request.app.state.runtime.config.data_dir / "ca")
