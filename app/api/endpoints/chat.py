from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, status
from fastapi.websockets import WebSocketDisconnect
from sqlmodel import Session

from app.core.db import get_db
from app.core.security import get_current_user, require_scopes
from app.core.telemetry import get_logger
from app.crud.repo import get_repo_task
from app.models.repo import IngestStatus
from app.services.agent import get_agent_for_repo
from app.utils.trace import _trace_attrs

router = APIRouter()

logger = get_logger(__name__)


@router.websocket("/{repo_id}")
async def chat_ws(
    ws: WebSocket,
    repo_id: str,
    current: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    WebSocket endpoint for real-time chat with the agent.
    This endpoint allows users to ask questions about a specific repository
    and receive answers in real-time.
    Args:
        ws (WebSocket): The WebSocket connection.
        repo_id (str): The ID of the repository to chat about.
        current (dict): The current user information.
        db (Session): The database session.
    Raises:
        WebSocketDisconnect: If the WebSocket connection is closed.
        Exception: For any internal errors during the chat session.
    """
    await ws.accept()

    task = get_repo_task(db, repo_id)
    if not task or task.user_id != current["id"] or task.status != IngestStatus.done:
        logger.warning(
            "Repo not ready for chat",
            extra={"repo_id": repo_id, "user_id": current["id"], **_trace_attrs()},
        )
        await ws.send_json({"error": "Repo not ready – check /repos/{repo_id}/status"})
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    logger.debug(
        "Chat session started",
        extra={"repo_id": repo_id, "user_id": current["id"], **_trace_attrs()},
    )
    agent = get_agent_for_repo(repo_id)

    try:
        while True:
            data = await ws.receive_json()
            question = data.get("q", "").strip()
            if not question:
                continue

            state = await agent.run({"question": question, "repo_id": repo_id})
            stream = state["stream"]

            async for delta in stream:
                token = delta.get("content", "")
                await ws.send_json({"token": token, "is_final": False})

            await ws.send_json({"token": "", "is_final": True})

    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected",
            extra={"repo_id": repo_id, "user_id": current["id"], **_trace_attrs()},
        )
        return

    except Exception as exc:
        logger.exception(
            "Internal error during chat session",
            extra={
                "repo_id": repo_id,
                "user_id": current["id"],
                "error": exc,
                **_trace_attrs(),
            },
        )
        await ws.send_json({"error": "Internal error during chat"})
        await ws.close(code=status.WS_1011_INTERNAL_ERROR)
