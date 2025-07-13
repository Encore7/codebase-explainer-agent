from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    oauth,
    revoke_refresh_token,
)

router = APIRouter()


@router.get("/login", summary="User login")
async def login(request: Annotated[Request, "Request object"]):
    """
    Endpoint to handle user login.
    """
    redirect_uri = request.url_for("auth_callback")
    return await oauth.github.authorize_redirect(request, str(redirect_uri))


@router.get("/callback", name="auth_callback", summary="GitHub OAuth callback")
async def auth_callback(request: Annotated[Request, "Request object"]):
    """
    Endpoint to handle the OAuth callback from GitHub.
    """
    token = await oauth.github.authorize_access_token(request)
    response = await oauth.github.get("user", token=token)
    user = response.json()
    if "login" not in user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub auth failed"
        )
    username = user["login"]
    access = create_access_token(subject=username, scopes=["chat", "ingest"])
    refresh = await create_refresh_token(subject=username)
    return JSONResponse(
        {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}
    )


@router.post("/refresh", summary="Refresh access token")
async def refresh(body: Annotated[dict, "Request body with refresh token"]):
    """Endpoint to refresh access token using refresh token."""
    token = body.get("refresh_token")
    if not token:
        raise HTTPException(status_code=400, detail="refresh_token required")
    data = await decode_token(token, "refresh")
    access = create_access_token(subject=data["sub"], scopes=data.get("scopes"))
    return {"access_token": access, "token_type": "bearer"}


@router.post("/logout", summary="Revoke refresh token")
async def logout(body: Annotated[dict, "Request body with refresh token"]):
    """Endpoint to log out user by revoking the refresh token."""
    token = body.get("refresh_token")
    if token:
        await revoke_refresh_token(token)
    return {"detail": "logged out"}
