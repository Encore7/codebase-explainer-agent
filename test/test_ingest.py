import pytest
from fastapi.testclient import TestClient

import app.services.ingest as ingest_mod
from app.core.config import settings
from app.core.db import get_db, init_db
from app.core.security import create_access_token
from app.crud.repo import create_repo_task, update_repo_status
from app.main import app
from app.models.repo import IngestStatus

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield


def test_ingest_schedules(monkeypatch):
    # stub out the heavy task
    monkeypatch.setattr(ingest_mod, "ingest_repo_task", lambda repo_id, repo_url: None)

    token = create_access_token(subject="charlie", scopes=["ingest"])
    res = client.post(
        f"{settings.API_V1_STR}/repos",
        headers={"Authorization": f"Bearer {token}"},
        json={"repo_url": "https://github.com/org/repo"},
    )
    assert res.status_code == 202
    body = res.json()
    assert "repo_id" in body and body["status"] == "scheduled"


def test_ingest_status():
    db = next(get_db())
    task = create_repo_task(db, user_id=1, repo_url="https://github.com/org/repo")
    update_repo_status(db, task.repo_id, IngestStatus.done)

    token = create_access_token(subject="charlie", scopes=["ingest"])
    res = client.get(
        f"{settings.API_V1_STR}/repos/{task.repo_id}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "done"
    assert body["repo_id"] == task.repo_id


def test_ingest_status_404():
    token = create_access_token(subject="charlie", scopes=["ingest"])
    res = client.get(
        f"{settings.API_V1_STR}/repos/invalid_id/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
