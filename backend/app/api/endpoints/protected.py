from fastapi import APIRouter, Depends

from backend.app.core.security import get_current_user

router = APIRouter()


@router.get("/me", summary="Get current user info")
async def read_current_user(current_user: dict = Depends(get_current_user)):
    return current_user
