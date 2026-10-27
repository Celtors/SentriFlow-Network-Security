from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/blocklist/status")
async def status(request: Request):
    return {
        "sources": request.app.state.runtime.blocklist.status(),
        "note": "Bundled list is a small demo seed; import a reviewed local file via CLI",
    }
