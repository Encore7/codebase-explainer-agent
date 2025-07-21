import hashlib
from datetime import UTC, datetime
from typing import Annotated

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.telemetry import get_logger
from app.models.repo import IngestStatus, RepoTask
from app.utils.trace import _trace_attrs

logger = get_logger(__name__)


def _make_repo_id(repo_url: str) -> str:
    """Generate a unique repository ID based on the repository URL.
        This uses a SHA-1 hash of the URL, truncated to 8 characters.
    Args:
        repo_url (str): The URL of the repository.
    Returns:
        str: A unique identifier for the repository, derived from its URL.
    """
    return hashlib.sha1(repo_url.encode()).hexdigest()[:8]


def create_repo_task(
    db: Annotated[Session, "DB session"],
    user_id: int,
    repo_url: str,
) -> RepoTask:
    """Create a new repository task in the database.
    Args:
        db (Session): The database session.
        user_id (int): The ID of the user creating the task.
        repo_url (str): The URL of the repository to be ingested.
    Returns:
        RepoTask: The created repository task.
    Raises:
        RuntimeError: If there is a database error while creating the task.
    """
    repo_id = _make_repo_id(repo_url)
    try:
        task = RepoTask(
            repo_id=repo_id,
            repo_url=repo_url,
            user_id=user_id,
            status=IngestStatus.scheduled,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.info(
            "Created new repo task",
            extra={"repo_id": repo_id, "user_id": user_id, **_trace_attrs()},
        )
        return task
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception(
            "Failed to create repo task",
            extra={
                "repo_id": repo_id,
                "user_id": user_id,
                "repo_url": repo_url,
                **_trace_attrs(),
            },
        )
        raise RuntimeError("Database error while creating repo task") from exc


def get_repo_task(
    db: Annotated[Session, "DB session"],
    repo_id: str,
) -> RepoTask | None:
    """Fetch a repository task by its ID.
    Args:
        db (Session): The database session.
        repo_id (str): The unique identifier of the repository task.
    Returns:
        RepoTask | None: The repository task if found, otherwise None.
    Raises:
        RuntimeError: If there is a database error while fetching the task.
    """
    try:
        task = db.query(RepoTask).filter(RepoTask.repo_id == repo_id).first()
        if task:
            logger.info(
                "Fetched repo task", extra={"repo_id": repo_id, **_trace_attrs()}
            )
        else:
            logger.warning(
                "Repo task not found", extra={"repo_id": repo_id, **_trace_attrs()}
            )
        return task
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to fetch repo task", extra={"repo_id": repo_id, **_trace_attrs()}
        )
        raise RuntimeError("Database error while fetching repo task") from exc


def update_repo_status(
    db: Annotated[Session, "DB session"],
    repo_id: str,
    status: IngestStatus,
    error: str | None = None,
) -> None:
    """Update the status of a repository task.
    Args:
        db (Session): The database session.
        repo_id (str): The unique identifier of the repository task.
        status (IngestStatus): The new status of the repository task.
        error (str | None): An optional error message if the status is failed.
    Raises:
        RuntimeError: If there is a database error while updating the task status.
    """
    try:
        task = get_repo_task(db, repo_id)
        if not task:
            logger.warning(
                "Repo task not found for update",
                extra={"repo_id": repo_id, **_trace_attrs()},
            )
            return

        task.status = status
        task.error = error
        task.updated_at = datetime.now(UTC)
        db.add(task)
        db.commit()
        logger.info(
            "Updated repo task status",
            extra={
                "repo_id": repo_id,
                "status": status,
                "error": error,
                **_trace_attrs(),
            },
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception(
            "Failed to update repo task status",
            extra={
                "repo_id": repo_id,
                "status": status,
                "error": error,
                **_trace_attrs(),
            },
        )
        raise RuntimeError("Database error while updating repo task") from exc
