from typing import Annotated

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.telemetry import get_logger
from app.models.user import User
from app.utils.trace import _trace_attrs

logger = get_logger(__name__)


def get_user_by_username(
    db: Annotated[Session, "DB session"],
    username: str,
) -> User | None:
    """Fetch a user by their username.
    If the user does not exist, return None.
    If an error occurs, log it and raise a RuntimeError.
    Args:
        db (Session): The database session.
        username (str): The username to search for.
    Returns:
        User | None: The user object if found, otherwise None.
    Raises:
        RuntimeError: If there is a database error while fetching the user.
    """
    try:
        user = db.query(User).filter(User.username == username).first()
        if user:
            logger.info(
                "Fetched existing user", extra={"username": username, **_trace_attrs()}
            )
        else:
            logger.warning(
                "User not found", extra={"username": username, **_trace_attrs()}
            )
        return user
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to query user by username",
            extra={"username": username, **_trace_attrs()},
        )
        raise RuntimeError("Database error while fetching user") from exc


def create_user(
    db: Annotated[Session, "DB session"],
    username: str,
    github_id: str,
) -> User:
    """Create a new user in the database.
    Args:
        db (Session): The database session.
        username (str): The username of the new user.
        github_id (str): The GitHub ID of the new user.
    Returns:
        User: The newly created user object.
    Raises:
        RuntimeError: If there is a database error while creating the user.
    """
    user = User(username=username, github_id=github_id)
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(
            "Created new user",
            extra={"username": username, "github_id": github_id, **_trace_attrs()},
        )
        return user
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception(
            "Failed to create user",
            extra={"username": username, "github_id": github_id, **_trace_attrs()},
        )
        raise RuntimeError("Database error while creating user") from exc


def get_or_create_user(
    db: Annotated[Session, "DB session"],
    username: str,
    github_id: str,
) -> User:
    """Get an existing user by username or create a new user if not found.
    Args:
        db (Session): The database session.
        username (str): The username of the user.
        github_id (str): The GitHub ID of the user.
    Returns:
        User: The existing or newly created user object.
    Raises:
        RuntimeError: If there is a database error while getting or creating the user.
    """
    try:
        user = get_user_by_username(db, username)
        if user:
            logger.info(
                "Returning existing user",
                extra={"username": username, **_trace_attrs()},
            )
            return user
        return create_user(db, username, github_id)
    except SQLAlchemyError as exc:
        logger.exception(
            "get_or_create_user failed",
            extra={"username": username, "github_id": github_id, **_trace_attrs()},
        )
        raise RuntimeError("Database error in get_or_create_user") from exc
