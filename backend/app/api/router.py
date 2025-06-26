from fastapi import APIRouter

from backend.app.api.endpoints.auth import router as auth_router
from backend.app.api.endpoints.health import router as health_router

router = APIRouter()

# Public
router.include_router(health_router, prefix="/health", tags=["Health"])
router.include_router(auth_router, prefix="/auth", tags=["Auth"])
