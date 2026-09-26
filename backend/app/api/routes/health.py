from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health():
    return {"status": "ok"}


@router.get("/live")
async def live():
    return {"status": "alive"}


@router.get("/ready")
async def ready():
    # In a real app, check DB and storage here
    return {"status": "ready"}
