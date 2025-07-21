from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """User model for the application.
    Represents a user with a unique username and GitHub ID.
    Attributes:
        id (int): Unique identifier for the user.
        username (str): Unique username for the user.
        github_id (str): Unique GitHub ID for the user.
        created_at (datetime): Timestamp when the user was created.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, nullable=False)
    github_id: str = Field(unique=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"
