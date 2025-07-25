from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_docs_ui():
    res = client.get(f"{settings.API_V1_STR}/docs")
    assert res.status_code == 200
    assert "Swagger UI" in res.text


def test_openapi_json():
    res = client.get(f"{settings.API_V1_STR}/openapi.json")
    assert res.status_code == 200
    assert "openapi" in res.json()
