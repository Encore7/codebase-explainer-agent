from fastapi import APIRouter, Depends

from backend.app.api.endpoints.health import router as health_router

router = APIRouter()

# Public
router.include_router(health_router, prefix="/health", tags=["Health"])
