"""Authenticated live metadata only; no endpoint fetches supplied websites."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from sentriflow.api.dependencies import runtime
from sentriflow.application import Runtime

router = APIRouter()


@router.get("/websites")
async def websites(rt: Annotated[Runtime, Depends(runtime)]) -> dict:
    return rt.websites.snapshot()


@router.get("/websites/{website_id}")
async def website(website_id: str, rt: Annotated[Runtime, Depends(runtime)]) -> dict:
    site = rt.websites.sites.get(website_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Live website no longer available")
    return site


@router.get("/model/status")
async def model_status(rt: Annotated[Runtime, Depends(runtime)]) -> dict:
    return rt.websites.status()
