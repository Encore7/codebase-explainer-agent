from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Health check")
async def health_check():
    """
    Simple endpoint to verify the service is up.
    """
    return {"status": "ok"}
