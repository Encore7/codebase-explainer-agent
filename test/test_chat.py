import pytest
from fastapi.testclient import TestClient, WebSocketDisconnect

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


def test_chat_not_ready():
    token = create_access_token(subject="dana", scopes=["chat"])
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"{settings.API_V1_STR}/chat/not_ready",
            headers={"Authorization": f"Bearer {token}"},
        ):
            pass


def test_chat_ready(monkeypatch):
    # Set up a done task
    db = next(get_db())
    task = create_repo_task(db, user_id=1, repo_url="https://github.com/org/repo")
    update_repo_status(db, task.repo_id, IngestStatus.done)

    # Stub out agent.run to return a fake stream
    class FakeAgent:
        async def run(self, state):
            async def gen():
                yield {"content": "Hello"}
                yield {"content": ""}

            return {"stream": gen()}

    monkeypatch.setattr(
        "app.services.agent.get_agent_for_repo", lambda repo_id: FakeAgent()
    )

    token = create_access_token(subject="dana", scopes=["chat"])
    with client.websocket_connect(
        f"{settings.API_V1_STR}/chat/{task.repo_id}",
        headers={"Authorization": f"Bearer {token}"},
    ) as ws:
        ws.send_json({"q": "Hi"})
        msg1 = ws.receive_json(timeout=5)
        assert msg1["token"] == "Hello"
        msg2 = ws.receive_json(timeout=5)
        assert msg2["is_final"] is True
