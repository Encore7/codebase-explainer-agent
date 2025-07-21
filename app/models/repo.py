import enum
from datetime import UTC, datetime
from typing import Annotated, Optional

from sqlmodel import Field, SQLModel


class IngestStatus(str, enum.Enum):
    """Enumeration for the status of a repository ingestion task.
    Attributes:
        scheduled: The task is scheduled for ingestion.
        in_progress: The task is currently being processed.
        done: The task has been completed successfully.
        failed: The task has failed during processing.
    """

    scheduled = "scheduled"
    in_progress = "in_progress"
    done = "done"
    failed = "failed"


class RepoTask(SQLModel, table=True):
    """Model representing a repository ingestion task.
    Attributes:
        id (int): The unique identifier for the task.
        repo_id (str): The unique identifier for the repository.
        repo_url (str): The URL of the repository to be ingested.
        status (IngestStatus): The current status of the ingestion task.
        user_id (int): The ID of the user who created the task.
        error (Optional[str]): An error message if the task failed.
        created_at (datetime): The timestamp when the task was created.
        updated_at (datetime): The timestamp when the task was last updated.
    """

    id: Annotated[Optional[int], Field(default=None, primary_key=True)]
    repo_id: Annotated[str, Field(index=True, unique=True, nullable=False)]
    repo_url: Annotated[str, Field(nullable=False)]
    status: Annotated[
        IngestStatus, Field(default=IngestStatus.scheduled, nullable=False)
    ]
    user_id: Annotated[int, Field(foreign_key="user.id", nullable=False)]
    error: Annotated[Optional[str], Field(default=None)]
    created_at: Annotated[
        datetime, Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    ]
    updated_at: Annotated[
        datetime, Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    ]

    def __repr__(self) -> str:
        """Return a string representation of the RepoTask instance."""
        return f"<RepoTask id={self.id} repo_id={self.repo_id} status={self.status}>"
