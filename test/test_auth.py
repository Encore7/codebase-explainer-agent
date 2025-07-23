import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


def test_login_redirect():
    res = client.get(f"{settings.API_V1_STR}/auth/login", allow_redirects=False)
    assert res.status_code in (302, 303, 307)
    assert "github.com/login/oauth/authorize" in res.headers["location"]


def test_callback_no_code():
    res = client.get(f"{settings.API_V1_STR}/auth/callback")
    assert res.status_code == 400


@pytest.mark.parametrize(
    "scopes,expected_status",
    [
        ([], 200),
        (["chat"], 200),
    ],
)
def test_token_roundtrip(scopes, expected_status):
    # We can't fully simulate the callback without GitHub,
    # but we can test our JWT creation/validation
    token = create_access_token(subject="alice", scopes=scopes)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert payload["sub"] == "alice"
    assert payload.get("scopes", []) == scopes
