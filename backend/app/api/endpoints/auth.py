from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from backend.app.core.security import create_access_token, oauth

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
    # Issue JWT
    jwt_token = create_access_token({"sub": user["login"]})
    return JSONResponse({"access_token": jwt_token, "token_type": "bearer"})
