from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.telemetry import get_logger
from app.utils.trace import _trace_attrs

logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.get("/", summary="Rate limited endpoint")
@limiter.limit("5/minute")
async def rate_limited(request: Request):
    """A rate-limited endpoint that allows 5 requests per minute.
    If the limit is exceeded, it will log a warning and return a message.
    Returns:
        dict: A message indicating the rate limit has been exceeded.
    """
    logger.warning("Rate limit exceeded", extra={**_trace_attrs()})
    return {"message": "This is a rate-limited endpoint"}
