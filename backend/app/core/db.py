from sqlalchemy.ext.asyncio import create_async_engine  # Optional
from sqlmodel import Session, SQLModel, create_engine

from backend.app.core.config import settings

# Sync engine (PostgreSQL via psycopg2)
engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
)


# Session factory (used via Depends)
def get_db():
    with Session(engine) as session:
        yield session
