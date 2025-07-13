from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """
    Represents a user of the system, backed by a SQL table.
    Inherits both ORM mapping and Pydantic validation.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, nullable=False)
    github_id: str = Field(unique=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
