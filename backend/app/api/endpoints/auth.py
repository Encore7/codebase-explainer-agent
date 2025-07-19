import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from opentelemetry.trace import get_current_span

from backend.app.api_model.token import RefreshTokenRequest, TokenResponse
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    oauth,
    revoke_refresh_token,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def get_trace_attrs() -> dict[str, str]:
    """Helper to inject trace_id and span_id into logs."""
    span = get_current_span()
    ctx = span.get_span_context()
    return {
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
    }


@router.get("/login", summary="User login")
async def login(request: Annotated[Request, Depends()]) -> Any:
    redirect_uri = request.url_for("auth_callback")
    logger.info(
        "Initiating GitHub OAuth login",
        extra={"redirect_uri": str(redirect_uri), **get_trace_attrs()},
    )
    return await oauth.github.authorize_redirect(request, str(redirect_uri))


@router.get(
    "/callback",
    name="auth_callback",
    summary="GitHub OAuth callback",
    response_model=TokenResponse,
)
async def auth_callback(request: Annotated[Request, Depends()]) -> TokenResponse:
    try:
        token = await oauth.github.authorize_access_token(request)
        response = await oauth.github.get("user", token=token)
        user = response.json()
    except Exception as e:
        logger.error(
            "GitHub OAuth failed", extra={"error": str(e), **get_trace_attrs()}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth failure"
        )

    username = user.get("login")
    if not username:
        logger.error(
            "GitHub response missing username",
            extra={"response": str(user), **get_trace_attrs()},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub auth failed"
        )

    logger.info(
        "GitHub login successful", extra={"username": username, **get_trace_attrs()}
    )
    access = create_access_token(subject=username, scopes=["chat", "ingest"])
    refresh = await create_refresh_token(subject=username)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", summary="Refresh access token", response_model=TokenResponse)
async def refresh(body: Annotated[RefreshTokenRequest, Depends()]) -> TokenResponse:
    token = body.refresh_token
    logger.info("Token refresh requested", extra=get_trace_attrs())

    try:
        data = await decode_token(token, "refresh")
        access = create_access_token(subject=data["sub"], scopes=data.get("scopes"))
        return TokenResponse(access_token=access)
    except Exception as e:
        logger.warning("Refresh failed", extra={"error": str(e), **get_trace_attrs()})
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/logout", summary="Revoke refresh token")
async def logout(body: Annotated[RefreshTokenRequest, Depends()]) -> dict[str, str]:
    token = body.refresh_token
    if token:
        await revoke_refresh_token(token)
        logger.info("Refresh token revoked", extra=get_trace_attrs())
    return {"detail": "logged out"}
