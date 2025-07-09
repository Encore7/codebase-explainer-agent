from fastapi import APIRouter, Depends

from backend.app.api.endpoints.auth import router as auth_router
from backend.app.api.endpoints.health import router as health_router
from backend.app.api.endpoints.protected import router as protected_router
from backend.app.core.security import get_current_user

router = APIRouter()

# Public endpoints
router.include_router(health_router, prefix="/health", tags=["Health"])
router.include_router(auth_router, prefix="/auth", tags=["Auth"])

# Protected endpoints
protected = APIRouter(
    prefix="/protected", tags=["Protected"], dependencies=[Depends(get_current_user)]
)
protected.include_router(protected_router, prefix="", tags=["Protected"])
router.include_router(protected)
