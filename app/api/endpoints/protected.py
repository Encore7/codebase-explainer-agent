from typing import Annotated

from fastapi import APIRouter, Depends

from app.api_model.user import UserOut
from app.core.security import get_current_user
from app.core.telemetry import get_logger
from app.models.user import User
from app.utils.trace import _trace_attrs

router = APIRouter()
logger = get_logger(__name__)


@router.get("/me", response_model=UserOut, summary="Get current user info")
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserOut:
    """Fetch the current user's information.
    This endpoint retrieves the details of the user currently authenticated.
    Args:
        current_user (User): The currently authenticated user.
    Returns:
        UserOut: A model containing the user's information.
    Raises:
        RuntimeError: If there is an error fetching the user info.
    """
    try:
        logger.info(
            "Fetched current user",
            extra={"user": current_user.username, **_trace_attrs()},
        )
        return UserOut.from_orm(current_user)
    except Exception as exc:
        logger.exception("Failed to fetch current user info", extra=_trace_attrs())
        raise RuntimeError("Protected route failure") from exc
