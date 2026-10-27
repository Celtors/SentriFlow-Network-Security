from typing import Annotated, Any

from fastapi import APIRouter, Depends

from sentriflow.api.dependencies import runtime
from sentriflow.application import Runtime

router = APIRouter()


@router.get("/health")
async def health(rt: Annotated[Runtime, Depends(runtime)]) -> dict[str, Any]:
    return {
        "status": "ok",
        "proxy_running": rt.proxy_running,
        "system_proxy_enabled": bool(rt.system_proxy and rt.system_proxy.enabled),
        "ca_generated": (rt.config.ca_dir / "mitmproxy-ca-cert.pem").exists(),
        "pending_halts": len(rt.halts.pending()),
    }
