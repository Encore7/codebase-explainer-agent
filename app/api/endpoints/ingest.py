from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session

from app.api_model.ingest import IngestRequest, IngestResponse, IngestStatusResponse
from app.core.db import get_db
from app.core.ingest import ingest_repo_task
from app.core.security import get_current_user
from app.core.telemetry import get_logger
from app.crud.repo import create_repo_task, get_repo_task
from app.utils.trace import _trace_attrs

router = APIRouter()

logger = get_logger(__name__)


@router.post(
    "/ingest", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED
)
async def ingest_repo(
    req: IngestRequest,
    bg: BackgroundTasks,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Endpoint to start repository ingestion.
    Args:
        req (IngestRequest): The request containing the repository URL.
        bg (BackgroundTasks): Background tasks manager to handle async tasks.
        current: Current authenticated user.
        db (Session): Database session dependency.
    Returns:
        IngestResponse: Response containing the repository ID and status.
    Raises:
        HTTPException: If the ingestion fails to start.
    """
    try:
        task = create_repo_task(db, user_id=current.id, repo_url=str(req.repo_url))
        logger.info(
            "Scheduled ingestion task",
            extra={"repo_id": task.repo_id, "user_id": current.id, **_trace_attrs()},
        )
        bg.add_task(ingest_repo_task, task.repo_id, task.repo_url)
        return IngestResponse(repo_id=task.repo_id, status=task.status.value)
    except Exception as exc:
        logger.exception(
            "Failed to schedule ingestion",
            extra={
                "user_id": current.id,
                "repo_url": str(req.repo_url),
                **_trace_attrs(),
            },
        )
        raise HTTPException(
            status_code=500, detail="Failed to start ingestion"
        ) from exc


@router.get("/{repo_id}/status", response_model=IngestStatusResponse)
async def ingest_status(
    repo_id: str,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Endpoint to check the status of a repository ingestion.
    Args:
        repo_id (str): The ID of the repository to check.
        current: Current authenticated user.
        db (Session): Database session dependency.
    Returns:
        IngestStatusResponse: Response containing the ingestion status.
    Raises:
        HTTPException: If the repo is not found or access is unauthorized.
    """
    try:
        task = get_repo_task(db, repo_id)
        if not task or task.user_id != current.id:
            logger.warning(
                "Unauthorized or missing repo access",
                extra={"repo_id": repo_id, "user_id": current.id, **_trace_attrs()},
            )
            raise HTTPException(status_code=404, detail="Repo not found")

        logger.info(
            "Repo status queried",
            extra={
                "repo_id": repo_id,
                "user_id": current.id,
                "status": task.status.value,
                **_trace_attrs(),
            },
        )
        return IngestStatusResponse(
            repo_id=task.repo_id,
            status=task.status.value,
            error=task.error,
        )
    except Exception as exc:
        logger.exception(
            "Failed to fetch repo status", extra={"repo_id": repo_id, **_trace_attrs()}
        )
        raise HTTPException(
            status_code=500, detail="Internal error fetching status"
        ) from exc
