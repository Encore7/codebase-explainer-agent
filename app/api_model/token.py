from typing import Optional

from pydantic import BaseModel


class RefreshTokenRequest(BaseModel):
    """Request model for refreshing access tokens.
    Attributes:
        refresh_token (str): The refresh token to use for obtaining a new access token.
    """

    refresh_token: str


class TokenResponse(BaseModel):
    """Response model for access and refresh tokens.
    Attributes:
        access_token (str): The newly issued access token.
        refresh_token (Optional[str]): The refresh token, if applicable.
        token_type (str): The type of the token, typically "bearer".
    """

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
