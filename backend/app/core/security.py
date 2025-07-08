from datetime import datetime, timedelta
from typing import Annotated, Dict, Optional

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from backend.app.core.config import settings

# OAuth configuration for GitHub integration
oauth = OAuth()
oauth.register(
    name="github",
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_CLIENT_SECRET,
    authorize_url=settings.GITHUB_AUTHORIZE_URL,
    access_token_url=settings.GITHUB_ACCESS_TOKEN_URL,
    api_base_url=settings.GITHUB_API_BASE_URL,
    client_kwargs={"scope": "read:user"},
)

# JWT creation and validation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


def create_access_token(
    data: Annotated[Dict[str, str], ""],
    expires_delta: Annotated[Optional[timedelta], ""] = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(datetime.UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def get_current_user(
    token: Annotated[str, ""] = Depends(oauth2_scheme),
) -> Dict[str, str]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return {"username": username}
