from fastapi import APIRouter

from app.core.telemetry import get_logger
from app.utils.trace import _trace_attrs

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", summary="Health check")
async def health_check():
    """Perform a health check to ensure the service is running.
    This endpoint is used to verify that the service is operational.
    Returns:
        dict: A dictionary indicating the service status.
    Raises:
        RuntimeError: If the health check fails.
    """
    try:
        logger.info("Health check passed", extra=_trace_attrs())
        return {"status": "ok"}
    except Exception as exc:
        logger.exception("Health check failed", extra=_trace_attrs())
        raise RuntimeError("Health check error") from exc
