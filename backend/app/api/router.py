import logging

from fastapi import APIRouter, Depends

from backend.app.api.endpoints.auth import router as auth_router
from backend.app.api.endpoints.health import router as health_router
from backend.app.api.endpoints.protected import router as protected_router
from backend.app.core.security import get_current_user

logger = logging.getLogger(__name__)

# Root API router
router = APIRouter()

# Public Routes
router.include_router(health_router, prefix="/health", tags=["Health"])
router.include_router(auth_router, prefix="/auth", tags=["Auth"])
logger.info("Public routers registered", extra={"prefixes": ["/health", "/auth"]})

# Protected Routes (with auth dependency)
protected_router_wrapper = APIRouter(
    prefix="/protected",
    tags=["Protected"],
    dependencies=[Depends(get_current_user)],
)
protected_router_wrapper.include_router(protected_router)
router.include_router(protected_router_wrapper)
logger.info("Protected routers registered", extra={"prefix": "/protected"})
