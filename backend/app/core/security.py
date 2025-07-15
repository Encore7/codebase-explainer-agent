import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Dict, List, Optional

import redis.asyncio as aioredis
import structlog
from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from backend.app.core.config import settings
from backend.app.core.db import get_db
from backend.app.ultils.crud import get_or_create_user

logger = structlog.get_logger()

#  GitHub OAuth
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


#  Internal Helpers
def _now() -> datetime:
    return datetime.now(UTC)


def _get_redis():
    return aioredis.from_url(
        str(settings.REDIS_URL), encoding="utf-8", decode_responses=True
    )


#  Token Creation
def create_access_token(
    subject: Annotated[str, "User identifier"],
    scopes: Annotated[Optional[List[str]], "Protected API scope of token"] = None,
    expires_delta: Annotated[Optional[timedelta], "Token lifespan"] = None,
) -> str:
    to_encode: Dict[str, Any] = {"sub": subject, "type": "access"}
    if scopes:
        to_encode["scopes"] = scopes
    expire = _now() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    logger.info("Access token created", user=subject, scopes=scopes)
    return token


async def create_refresh_token(subject: Annotated[str, "User ID"]) -> str:
    jti = secrets.token_urlsafe(16)
    to_encode = {"sub": subject, "type": "refresh", "jti": jti}
    expire = _now() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    await _get_redis().set(
        f"refresh_jti:{jti}", subject, ex=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
    )
    logger.info("Refresh token created", user=subject, jti=jti)
    return token


#  Token Revocation
async def revoke_refresh_token(token: Annotated[str, "JWT Refresh Token"]):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        jti = payload.get("jti")
        if jti:
            await _get_redis().delete(f"refresh_jti:{jti}")
            logger.info("Refresh token revoked", jti=jti)
    except JWTError:
        logger.warning("Refresh token revocation failed", reason="Invalid/expired")


#  Token Validation
async def decode_token(
    token: Annotated[str, "JWT Access or Refresh Token"],
    expected_type: Annotated[str, "Expected token type"] = "access",
) -> Dict[str, Any]:
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != expected_type:
            raise creds_exc

        if expected_type == "refresh":
            jti = payload.get("jti")
            if not jti or not await _get_redis().exists(f"refresh_jti:{jti}"):
                raise creds_exc

        return payload
    except JWTError:
        logger.warning("JWT validation failed", expected_type=expected_type)
        raise creds_exc


#  Authenticated User Dependency
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Any, Depends(get_db)],
) -> Dict[str, Any]:
    payload = await decode_token(token, expected_type="access")
    username = payload["sub"]
    scopes = payload.get("scopes", [])

    user = get_or_create_user(db, username=username, github_id=username)
    logger.info("User authenticated", user=username, scopes=scopes)

    return {"id": user.id, "username": user.username, "scopes": scopes}


#  Scope Checker
def require_scopes(required: Annotated[List[str], "Required scopes"]):
    async def _checker(current=Depends(get_current_user)):
        for scope in required:
            if scope not in current["scopes"]:
                logger.warning(
                    "Missing scope", required=scope, user=current["username"]
                )
                raise HTTPException(status_code=403, detail=f"Missing scope: {scope}")

    return _checker
