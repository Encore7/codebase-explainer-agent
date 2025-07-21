from typing import Generator

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.core.telemetry import get_logger
from app.utils.trace import _trace_attrs

logger = get_logger(__name__)

# Sync engine (PostgreSQL via psycopg2)
engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
)


def init_db() -> None:
    """Initialize the database schema.
    Raises:
        RuntimeError: If database initialization fails.
    """
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database schema created successfully.", extra=_trace_attrs())
    except SQLAlchemyError as exc:
        logger.exception("Failed to initialize database schema.", extra=_trace_attrs())
        raise RuntimeError("Database initialization failed") from exc


def get_db() -> Generator[Session, None, None]:
    """Get a database session.
    Raises:
        RuntimeError: _description_

    Yields:
        Generator[Session, None, None]: _description_
    """
    session = Session(engine)
    try:
        logger.debug("Opened new DB session.", extra=_trace_attrs())
        yield session
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        logger.exception("Session rollback due to exception.", extra=_trace_attrs())
        raise RuntimeError("Database session failed") from exc
    finally:
        session.close()
        logger.debug("Closed DB session.", extra=_trace_attrs())
