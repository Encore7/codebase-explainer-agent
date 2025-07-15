import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.core.security import get_current_user

router = APIRouter()
logger = structlog.get_logger()


class UserOut(BaseModel):
    id: int
    username: str
    scopes: list[str]


@router.get("/me", response_model=UserOut, summary="Get current user info")
async def read_current_user(current_user: dict = Depends(get_current_user)):
    logger.info("Fetched current user", user=current_user["username"])
    return current_user
