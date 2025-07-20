import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from starlette.middleware.sessions import SessionMiddleware

from backend.app.api.router import router as api_router
from backend.app.core.config import settings
from backend.app.core.db import engine, init_db
from backend.app.core.telemetry import get_logger, instrument_fastapi

# Initialize logger first
logger = get_logger(__name__)
logger.info("Starting FastAPI application...")

# FastAPI app instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
)

# Instrument FastAPI after OTel setup
instrument_fastapi(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
)

# Register API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# DB instrumentation and initialization
SQLAlchemyInstrumentor().instrument(engine=engine)
init_db()

logger.info("Application initialized successfully.")

# Entrypoint
if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
