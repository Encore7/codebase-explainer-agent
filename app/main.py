import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.router import router as api_router
from app.core.config import settings
from app.core.db import engine, init_db
from app.core.telemetry import get_logger, instrument_fastapi
from app.utils.rate_limiter import limiter
from app.utils.trace import _trace_attrs

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

# Middleware: CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware: Session
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
)

# Middleware: Rate Limiter (SlowAPI)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


# Exception Handler: Rate Limiting
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(
        "Rate limit exceeded",
        extra={"path": str(request.url.path), **_trace_attrs()},
    )
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


# Register API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Instrument DB
SQLAlchemyInstrumentor().instrument(engine=engine)

# Init DB
init_db()

logger.info("Application initialized successfully.")

# Entrypoint
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
