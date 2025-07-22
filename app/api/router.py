from fastapi import APIRouter, Depends

from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.chat import router as chat_router
from app.api.endpoints.health import router as health_router
from app.api.endpoints.ingest import router as ingest_router
from app.api.endpoints.protected import router as protected_router
from app.api.endpoints.rate_limited import router as rate_limited_router
from app.core.config import settings
from app.core.security import require_scopes
from app.core.telemetry import get_logger
from app.utils.trace import _trace_attrs

logger = get_logger(__name__)

# Root API router
router = APIRouter()

# Public Routes
try:
    router.include_router(health_router, prefix="/health", tags=["Health"])
    router.include_router(auth_router, prefix="/auth", tags=["Auth"])
    logger.info(
        "Public routers registered",
        extra={"prefixes": ["/health", "/auth"], **_trace_attrs()},
    )
except Exception as exc:
    logger.exception("Failed to register public routers", extra=_trace_attrs())
    raise RuntimeError("Router registration failed: /health or /auth") from exc

# Protected Routes
try:
    protected = APIRouter(prefix=settings.API_V1_STR)

    # Ingestion (requires "ingest" scope)
    protected.include_router(
        ingest_router,
        prefix="/repos",
        tags=["Ingest"],
        dependencies=[Depends(require_scopes(["ingest"]))],
    )

    # Chat (requires "chat" scope)
    protected.include_router(
        chat_router,
        prefix="/chat",
        tags=["Chat"],
        dependencies=[Depends(require_scopes(["chat"]))],
    )

    # protected
    protected.include_router(protected_router, prefix="/protected", tags=["Protected"])

    # Rate-limited endpoints
    protected.include_router(
        rate_limited_router,
        prefix="/rate_limited",
        tags=["Rate Limited"],
        dependencies=[Depends(require_scopes(["rate_limited"]))],
    )

    router.include_router(protected)

    logger.info(
        "Protected routers registered",
        extra={"prefix": settings.API_V1_STR, **_trace_attrs()},
    )
except Exception as exc:
    logger.exception("Failed to register protected routers", extra=_trace_attrs())
    raise RuntimeError(f"Router registration failed: {settings.API_V1_STR}") from exc
