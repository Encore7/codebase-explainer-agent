import logging

from fastapi import APIRouter
from opentelemetry.trace import get_current_span

from backend.app.core.telemetry import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", summary="Health check")
async def health_check():
    span = get_current_span()
    ctx = span.get_span_context()
    logger.info(
        "Health check passed",
        extra={
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
        },
    )
    return {"status": "ok"}
