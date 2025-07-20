from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# Sync engine (PostgreSQL via psycopg2)
engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
)


def init_db():
    SQLModel.metadata.create_all(engine)


# Session factory (used via Depends)
def get_db():
    with Session(engine) as session:
        yield session
