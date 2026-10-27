import asyncio
import subprocess
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from sentriflow.api.dependencies import runtime
from sentriflow.api.schemas import ConsentInput, ProxyInput
from sentriflow.application import Runtime
from sentriflow.os_adapters.windows.cert_store import ca_status, install_ca, remove_ca

router = APIRouter()
RT = Annotated[Runtime, Depends(runtime)]


@router.post("/system/proxy")
async def proxy(body: ProxyInput, rt: RT) -> dict[str, bool]:
    if not rt.system_proxy:
        raise HTTPException(501, "System proxy routing requires Windows")
    if body.enabled and not rt.proxy_running:
        raise HTTPException(409, "Start the local proxy before enabling system routing")
    try:
        async with rt.system_lock:
            await asyncio.to_thread(
                rt.system_proxy.enable if body.enabled else rt.system_proxy.restore
            )
    except OSError as error:
        raise HTTPException(409, str(error)) from error
    rt.bus.publish("system.status", {"system_proxy_enabled": rt.system_proxy.enabled})
    return {"enabled": rt.system_proxy.enabled}


@router.get("/system/ca")
async def ca(rt: RT) -> dict[str, Any]:
    return await asyncio.to_thread(ca_status, rt.config.ca_dir)


@router.post("/system/ca")
async def install(body: ConsentInput, rt: RT) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(install_ca, rt.config.ca_dir, confirmed=body.confirmed)
    except (OSError, subprocess.SubprocessError) as error:
        raise HTTPException(
            409, "CA installation failed; inspect the current-user store"
        ) from error


@router.delete("/system/ca")
async def remove(rt: RT) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(remove_ca, rt.config.ca_dir)
    except (OSError, subprocess.SubprocessError) as error:
        raise HTTPException(409, "CA removal failed; inspect the current-user store") from error
