import logging
from typing import Annotated

from sqlalchemy.orm import Session

from backend.app.models.user import User

logger = logging.getLogger(__name__)


def get_user_by_username(
    db: Annotated[Session, "DB session"], username: str
) -> User | None:
    return db.query(User).filter(User.username == username).first()


def create_user(
    db: Annotated[Session, "DB session"], username: str, github_id: str
) -> User:
    user = User(username=username, github_id=github_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(
        "Created new user", extra={"username": username, "github_id": github_id}
    )
    return user


def get_or_create_user(
    db: Annotated[Session, "DB session"], username: str, github_id: str
) -> User:
    user = get_user_by_username(db, username)
    if user:
        logger.info("Existing user returned", extra={"username": username})
        return user
    return create_user(db, username, github_id)
