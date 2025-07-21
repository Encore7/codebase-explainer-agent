from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Request, status

from app.api_model.token import RefreshTokenRequest, TokenResponse
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    oauth,
    revoke_refresh_token,
)
from app.core.telemetry import get_logger
from app.utils.trace import _trace_attrs

logger = get_logger(__name__)
router = APIRouter()


@router.get("/login", summary="User login")
async def login(request: Request) -> dict:
    """Initiate GitHub OAuth login flow.
    This endpoint redirects the user to GitHub for authentication.
    Args:
        request (Request): The incoming HTTP request.
    Returns:
        dict: A dictionary containing the redirect URL for GitHub OAuth.
    Raises:
        HTTPException: If there is an error initiating the OAuth flow.
    """
    redirect_uri = request.url_for("auth_callback")
    logger.info(
        "Initiating GitHub OAuth login",
        extra={"redirect_uri": str(redirect_uri), **_trace_attrs()},
    )
    return await oauth.github.authorize_redirect(request, str(redirect_uri))


@router.get(
    "/callback",
    name="auth_callback",
    summary="GitHub OAuth callback",
    response_model=TokenResponse,
)
async def auth_callback(request: Request) -> TokenResponse:
    """Handle GitHub OAuth callback and generate access token.
    This endpoint processes the OAuth callback from GitHub, retrieves user information,
    and generates an access token for the user.
    Args:
        request (Request): The incoming HTTP request containing the OAuth callback.
    Returns:
        TokenResponse: A model containing the access and refresh tokens.
    Raises:
        HTTPException: If there is an error during the OAuth process or token generation.
    """
    try:
        token = await oauth.github.authorize_access_token(request)
        response = await oauth.github.get("user", token=token)
        user = response.json()
    except Exception as exc:
        logger.error("GitHub OAuth failed", extra={"error": str(exc), **_trace_attrs()})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth failure"
        ) from exc

    username = user.get("login")
    if not username:
        logger.error(
            "GitHub response missing username",
            extra={"response": str(user), **_trace_attrs()},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub auth failed"
        )

    logger.info(
        "GitHub login successful",
        extra={"username": username, **_trace_attrs()},
    )
    try:
        access = create_access_token(subject=username, scopes=["chat", "ingest"])
        refresh = await create_refresh_token(subject=username)
        return TokenResponse(access_token=access, refresh_token=refresh)
    except Exception as exc:
        logger.exception(
            "Token generation failed", extra={"username": username, **_trace_attrs()}
        )
        raise HTTPException(status_code=500, detail="Token creation failed") from exc


@router.post("/refresh", summary="Refresh access token", response_model=TokenResponse)
async def refresh(body: Annotated[RefreshTokenRequest, Body()]) -> TokenResponse:
    """Refresh access token using a valid refresh token.
    This endpoint allows users to obtain a new access token using their refresh token.
    Args:
        body (RefreshTokenRequest): The request body containing the refresh token.
    Returns:
        TokenResponse: A model containing the new access token.
    Raises:
        HTTPException: If the refresh token is invalid or expired.
    """
    token = body.refresh_token
    logger.info("Token refresh requested", extra=_trace_attrs())

    try:
        data = await decode_token(token, "refresh")
        access = create_access_token(subject=data["sub"], scopes=data.get("scopes"))
        return TokenResponse(access_token=access)
    except Exception as exc:
        logger.warning("Refresh failed", extra={"error": str(exc), **_trace_attrs()})
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc


@router.post("/logout", summary="Revoke refresh token")
async def logout(body: Annotated[RefreshTokenRequest, Body()]) -> dict[str, str]:
    """Revoke the provided refresh token.
    This endpoint allows users to log out by revoking their refresh token.
    Args:
        body (RefreshTokenRequest): The request body containing the refresh token to be revoked.
    Returns:
        dict: A dictionary indicating the logout status.
    Raises:
        HTTPException: If the revocation fails.
    """
    token = body.refresh_token
    if token:
        try:
            await revoke_refresh_token(token)
            logger.info("Refresh token revoked", extra=_trace_attrs())
        except Exception as exc:
            logger.exception("Failed to revoke refresh token", extra=_trace_attrs())
            raise HTTPException(status_code=500, detail="Logout failed") from exc
    return {"detail": "logged out"}
