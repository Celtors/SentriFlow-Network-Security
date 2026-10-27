from fastapi import APIRouter

router = APIRouter()


@router.get("/geo/destinations")
async def destinations() -> dict[str, object]:
    return {"available": False, "destinations": [], "reason": "Offline GeoIP is not configured"}
