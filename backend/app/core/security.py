import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, List

import redis.asyncio as aioredis
from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from opentelemetry.trace import get_current_span

from backend.app.api_model.user import UserOut
from backend.app.core.config import settings
from backend.app.core.crud import get_or_create_user
from backend.app.core.db import get_db
from backend.app.core.telemetry import get_logger
from backend.app.utils.trace import _trace_attrs

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


def _get_redis():
    return aioredis.from_url(
        str(settings.REDIS_URL), encoding="utf-8", decode_responses=True
    )


def create_access_token(
    subject: Annotated[str, "User identifier"],
    scopes: Annotated[List[str], "Token scopes"] = [],
    expires_delta: Annotated[timedelta | None, "Lifespan override"] = None,
) -> str:
    payload = {"sub": subject, "type": "access", "scopes": scopes}
    payload["exp"] = _now() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    logger.info(
        "Access token created",
        extra={"user": subject, "scopes": scopes, **_trace_attrs()},
    )
    return token


async def create_refresh_token(subject: Annotated[str, "User ID"]) -> str:
    jti = secrets.token_urlsafe(16)
    payload = {
        "sub": subject,
        "type": "refresh",
        "jti": jti,
        "exp": _now() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    await _get_redis().set(
        f"refresh_jti:{jti}", subject, ex=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
    )
    logger.info(
        "Refresh token created", extra={"user": subject, "jti": jti, **_trace_attrs()}
    )
    return token


async def revoke_refresh_token(token: Annotated[str, "JWT Refresh Token"]) -> None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        jti = payload.get("jti")
        if jti:
            await _get_redis().delete(f"refresh_jti:{jti}")
            logger.info("Refresh token revoked", extra={"jti": jti, **_trace_attrs()})
    except JWTError:
        logger.warning(
            "Refresh token revocation failed",
            extra={"reason": "Invalid or expired", **_trace_attrs()},
        )


async def decode_token(
    token: Annotated[str, "JWT Access or Refresh Token"],
    expected_type: Annotated[str, "Expected token type"] = "access",
) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
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
    except JWTError:
        logger.warning(
            "Token validation failed",
            extra={"expected_type": expected_type, **_trace_attrs()},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Any, Depends(get_db)],
) -> UserOut:
    payload = await decode_token(token, expected_type="access")
    username = payload["sub"]
    scopes = payload.get("scopes", [])

    user = get_or_create_user(db, username=username, github_id=username)
    logger.info(
        "User authenticated",
        extra={"user": username, "scopes": scopes, **_trace_attrs()},
    )

    return UserOut(id=user.id, username=user.username, scopes=scopes)


def require_scopes(required: Annotated[List[str], "Required scopes"]):
    async def _checker(current: Annotated[UserOut, Depends(get_current_user)]):
        for scope in required:
            if scope not in current.scopes:
                logger.warning(
                    "Missing scope",
                    extra={
                        "required_scope": scope,
                        "user": current.username,
                        **_trace_attrs(),
                    },
                )
                raise HTTPException(status_code=403, detail=f"Missing scope: {scope}")

    return _checker
