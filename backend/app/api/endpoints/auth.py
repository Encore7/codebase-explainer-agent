from fastapi import APIRouter

router = APIRouter()

@router.get("/login", summary="User login")
async def login():
    