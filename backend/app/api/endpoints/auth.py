from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    oauth,
    revoke_refresh_token,
)

logger = structlog.get_logger()
router = APIRouter()


# Request Models
class RefreshTokenRequest(BaseModel):
    refresh_token: str


# OAuth Login
@router.get("/login", summary="User login")
async def login(request: Annotated[Request, "Request object"]):
    redirect_uri = request.url_for("auth_callback")
    logger.info("Initiating GitHub OAuth login", redirect_uri=redirect_uri)
    return await oauth.github.authorize_redirect(request, str(redirect_uri))


# OAuth Callback
@router.get("/callback", name="auth_callback", summary="GitHub OAuth callback")
async def auth_callback(request: Annotated[Request, "Request object"]):
    try:
        token = await oauth.github.authorize_access_token(request)
        response = await oauth.github.get("user", token=token)
        user = response.json()
    except Exception as e:
        logger.error("GitHub OAuth failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth failure"
        )

    username = user.get("login")
    if not username:
        logger.error("GitHub response missing username", response=user)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub auth failed"
        )

    logger.info("GitHub login successful", username=username)
    access = create_access_token(subject=username, scopes=["chat", "ingest"])
    refresh = await create_refresh_token(subject=username)
    return JSONResponse(
        {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}
    )


# Refresh Token Endpoint
@router.post("/refresh", summary="Refresh access token")
async def refresh(body: RefreshTokenRequest):
    token = body.refresh_token
    logger.info("Token refresh requested")

    try:
        data = await decode_token(token, "refresh")
        access = create_access_token(subject=data["sub"], scopes=data.get("scopes"))
        return {"access_token": access, "token_type": "bearer"}
    except Exception as e:
        logger.warning("Refresh failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# Logout & Revoke Token
@router.post("/logout", summary="Revoke refresh token")
async def logout(body: RefreshTokenRequest):
    token = body.refresh_token
    if token:
        await revoke_refresh_token(token)
        logger.info("Refresh token revoked")
    return {"detail": "logged out"}
