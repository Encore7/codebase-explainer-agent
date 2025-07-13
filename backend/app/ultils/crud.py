from sqlalchemy.orm import Session

from backend.app.models.user import User


def get_user_by_username(db: Session, username: str) -> User | None:
    """
    Return a User by their username, or None if not found.
    """
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, username: str, github_id: str) -> User:
    """
    Create (and persist) a new User.
    """
    user = User(username=username, github_id=github_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_user(db: Session, username: str, github_id: str) -> User:
    """
    Fetch an existing user or create one if absent.
    """
    user = get_user_by_username(db, username)
    if user:
        return user
    return create_user(db, username, github_id)
