from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


def test_protected_me_no_token():
    res = client.get(f"{settings.API_V1_STR}/protected/me")
    assert res.status_code == 401


def test_protected_me_with_token():
    token = create_access_token(subject="xyz", scopes=[])
    res = client.get(
        f"{settings.API_V1_STR}/protected/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["username"] == "xyz"
