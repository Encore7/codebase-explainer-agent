import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.sessions import SessionMiddleware

from backend.app.api.router import router as api_router
from backend.app.core.config import settings
from backend.app.core.logging import configure_logging
from backend.app.core.tracing import setup_tracer

# Setup Logging & Logger
configure_logging()
logger = structlog.get_logger()

# FastAPI App Initialization
try:
    logger.info("FastAPI app initializing...", env=settings.ENVIRONMENT)

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
    )

    # Tracing
    setup_tracer(app)
    logger.info("Tracing initialized", otlp_endpoint="http://localhost:4318")

    # Metrics Instrumentation
    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(app, include_in_schema=False)
    logger.info("Prometheus metrics enabled", metrics_path="/metrics")

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.FRONTEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware registered", origins=settings.FRONTEND_CORS_ORIGINS)

    # OAuth Session Middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        session_cookie="session",
    )
    logger.info("Session middleware configured")

    # API Routers
    app.include_router(api_router, prefix=settings.API_V1_STR)
    logger.info("API routers registered", prefix=settings.API_V1_STR)

except Exception as e:
    logger.error("FastAPI app startup failed", error=str(e))
    raise

# Entrypoint
if __name__ == "__main__":
    logger.info("Uvicorn starting...", host="0.0.0.0", port=8000)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
