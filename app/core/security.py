import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated, Any, List

import redis.asyncio as aioredis
from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.exc import SQLAlchemyError

from app.api_model.user import UserOut
from app.core.config import settings
from app.core.db import get_db
from app.core.telemetry import get_logger
from app.crud.user import get_or_create_user
from app.utils.trace import _trace_attrs

logger = get_logger(__name__)

# GitHub OAuth
oauth = OAuth()
oauth.register(
    name="github",
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_CLIENT_SECRET,
    authorize_url=str(settings.GITHUB_AUTHORIZE_URL),
    access_token_url=str(settings.GITHUB_ACCESS_TOKEN_URL),
    api_base_url=str(settings.GITHUB_API_BASE_URL),
    client_kwargs={"scope": "read:user"},
)

oauth2_scheme: Annotated[str, Depends] = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token"
)


def _now() -> datetime:
    return datetime.now(UTC)


@lru_cache
def _get_redis():
    return aioredis.from_url(
        str(settings.REDIS_URL),
        encoding="utf-8",
        decode_responses=True,
    )


def create_access_token(
    subject: Annotated[str, "User identifier"],
    scopes: Annotated[List[str], "Token scopes"] = [],
    expires_delta: Annotated[timedelta | None, "Lifespan override"] = None,
) -> str:
    """Create a JWT access token for the user.
    Args:
        subject (str): User identifier (e.g., username or user ID).
        scopes (List[str]): List of scopes granted to the token.
        expires_delta (timedelta | None): Custom expiration time, if any.
    Returns:
        str: Encoded JWT access token.
    """
    payload = {
        "sub": subject,
        "type": "access",
        "scopes": scopes,
        "exp": _now()
        + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    logger.info(
        "Access token created",
        extra={
            "user": subject,
            "scopes": scopes,
            "exp": payload["exp"],
            **_trace_attrs(),
        },
    )
    return token


async def create_refresh_token(subject: Annotated[str, "User ID"]) -> str:
    """Create a JWT refresh token for the user.
    Args:
        subject (str): User identifier (e.g., username or user ID).
    Returns:
        str: Encoded JWT refresh token.
    """
    jti = secrets.token_urlsafe(16)
    payload = {
        "sub": subject,
        "type": "refresh",
        "jti": jti,
        "exp": _now() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    try:
        await _get_redis().set(
            f"refresh_jti:{jti}",
            subject,
            ex=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        )
        logger.info(
            "Refresh token created",
            extra={
                "user": subject,
                "jti": jti,
                "exp": payload["exp"],
                **_trace_attrs(),
            },
        )
    except Exception as exc:
        logger.exception(
            "Failed to store refresh token in Redis",
            extra={"user": subject, "jti": jti, **_trace_attrs()},
        )
        raise RuntimeError("Redis error while storing refresh token") from exc
    return token


async def revoke_refresh_token(token: Annotated[str, "JWT Refresh Token"]) -> None:
    """Revoke a JWT refresh token by removing its JTI from Redis.
    Args:
        token (str): JWT refresh token to revoke.
    Raises:
        HTTPException: If the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        jti = payload.get("jti")
        if jti:
            await _get_redis().delete(f"refresh_jti:{jti}")
            logger.info("Refresh token revoked", extra={"jti": jti, **_trace_attrs()})

    except JWTError as exc:
        logger.warning(
            "Refresh token revocation failed",
            extra={"reason": "Invalid or expired", **_trace_attrs()},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected error during token revocation", extra=_trace_attrs()
        )
        raise HTTPException(
            status_code=500, detail="Internal error during revocation"
        ) from exc


async def decode_token(
    token: Annotated[str, "JWT Access or Refresh Token"],
    expected_type: Annotated[str, "Expected token type"] = "access",
) -> dict:
    """Decode and validate a JWT token.
    Args:
        token (str): JWT token to decode.
        expected_type (str): Expected token type ("access" or "refresh").
    Returns:
        dict: Decoded token payload.
    Raises:
        HTTPException: If the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        if expected_type == "refresh":
            jti = payload.get("jti")
            if not jti or not await _get_redis().exists(f"refresh_jti:{jti}"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token",
                )

        return payload

    except JWTError as exc:
        logger.warning(
            "Token validation failed",
            extra={"expected_type": expected_type, **_trace_attrs()},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Any, Depends(get_db)],
) -> UserOut:
    """Retrieve the current authenticated user from the access token.
    Args:
        token (str): JWT access token.
        db (Session): Database session dependency.
    Returns:
        UserOut: User data including ID, username, and scopes.
    Raises:
        HTTPException: If the token is invalid, expired, or user resolution fails.
    """
    payload = await decode_token(token, expected_type="access")
    username = payload["sub"]
    scopes = payload.get("scopes", [])
    try:
        user = get_or_create_user(db, username=username, github_id=username)
        logger.info(
            "User authenticated",
            extra={"user": username, "scopes": scopes, **_trace_attrs()},
        )
        return UserOut(id=user.id, username=user.username, scopes=scopes)
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to retrieve or create user",
            extra={"user": username, **_trace_attrs()},
        )
        raise HTTPException(status_code=500, detail="User resolution failed") from exc


def require_scopes(required: Annotated[List[str], "Required scopes"]):
    """Decorator to enforce required scopes for a route.
    Args:
        required (List[str]): List of scopes required for access.
    Returns:
        Callable: Dependency function that checks user scopes.
    """

    async def _checker(current: Annotated[UserOut, Depends(get_current_user)]):
        """Dependency function to check if the current user has required scopes.
        Args:
            current (UserOut): Current authenticated user.
        Raises:
            HTTPException: If the user lacks required scopes.
        """
        for scope in required:
            if scope not in current.scopes:
                logger.warning(
                    "Missing required scope",
                    extra={
                        "required_scope": scope,
                        "user": current.username,
                        **_trace_attrs(),
                    },
                )
                raise HTTPException(status_code=403, detail=f"Missing scope: {scope}")

    return _checker
