import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.sessions import SessionMiddleware

from backend.app.api.router import router as api_router
from backend.app.core.config import settings
from backend.app.core.logging import configure_logging

configure_logging()
logger = structlog.get_logger()
logger.info("FastAPI app initializing...", env=str(settings.ENVIRONMENT))

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
)

# Prometheus Instrumentation
instrumentator = Instrumentator().instrument(app)
instrumentator.expose(app, include_in_schema=False)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session Middleware (for OAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
)

app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
