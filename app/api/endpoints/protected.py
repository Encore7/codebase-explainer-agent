from typing import Annotated

from fastapi import APIRouter, Depends
from opentelemetry.trace import get_current_span

from app.api_model.user import UserOut
from app.core.security import get_current_user
from app.core.telemetry import get_logger
from app.models.user import User

router = APIRouter()


logger = get_logger(__name__)


@router.get("/me", response_model=UserOut, summary="Get current user info")
async def read_current_user(current_user: Annotated[User, Depends(get_current_user)]):
    span = get_current_span()
    ctx = span.get_span_context()
    logger.info(
        "Fetched current user",
        extra={
            "user": current_user.username,
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
        },
    )
    return UserOut.from_orm(current_user)
