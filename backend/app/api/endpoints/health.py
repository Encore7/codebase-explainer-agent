import structlog
from fastapi import APIRouter

router = APIRouter()
logger = structlog.get_logger()


@router.get("/", summary="Health check")
async def health_check():
    logger.info("Health check passed")
    return {"status": "ok"}
