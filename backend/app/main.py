import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from starlette.middleware.sessions import SessionMiddleware

from backend.app.api.router import router as api_router
from backend.app.core.config import settings
from backend.app.core.db import engine, init_db
from backend.app.core.telemetry import setup_otel

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
)

# Initialize OpenTelemetry (traces, logs, metrics)
setup_otel(service_name=settings.PROJECT_NAME)

# Instrument FastAPI (AFTER OTel init)
FastAPIInstrumentor.instrument_app(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
)

# Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Database Initialization
SQLAlchemyInstrumentor().instrument(engine=engine)
init_db()

# Entrypoint
if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
