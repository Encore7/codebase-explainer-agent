import chromadb
from openai import OpenAI
from pydriller import Repository
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.core.telemetry import get_logger
from app.crud.repo import update_repo_status
from app.models.repo import IngestStatus
from app.utils.trace import _trace_attrs

logger = get_logger(__name__)


def ingest_repo_task(repo_id: str, repo_url: str):
    """Ingest a repository's commit history into the vector database.
    This function retrieves commit data from the specified repository,
    processes the modified files, generates embeddings using OpenAI,
    and stores the results in a ChromaDB collection.
    Args:
        repo_id (str): Unique identifier for the repository.
        repo_url (str): URL of the repository to be ingested.
    """
    db = Session(engine)
    try:
        logger.info(
            "Ingestion started",
            extra={"repo_id": repo_id, "repo_url": repo_url, **_trace_attrs()},
        )
        update_repo_status(db, repo_id, IngestStatus.in_progress)

        client = chromadb.Client()
        embedder = OpenAI(api_key=settings.OPENAI_API_KEY)
        collection = client.get_collection(name=repo_id)

        for commit in Repository(repo_url).traverse_commits():
            for mf in commit.modified_files:
                text = f"{commit.msg}\n{mf.diff}"
                try:
                    emb = embedder.embeddings.create(input=text)["data"][0]["embedding"]
                    collection.add(
                        documents=[text],
                        embeddings=[emb],
                        metadatas=[
                            {
                                "commit": commit.hash,
                                "path": mf.new_path,
                                "date": commit.author_date.isoformat(),
                                "author": commit.author.name,
                            }
                        ],
                        ids=[f"{commit.hash}:{mf.new_path}"],
                    )
                except Exception as embed_exc:
                    logger.warning(
                        "Embedding or storage failed for file",
                        extra={
                            "repo_id": repo_id,
                            "commit": commit.hash,
                            "path": mf.new_path,
                            "error": str(embed_exc),
                            **_trace_attrs(),
                        },
                    )
                    continue

        update_repo_status(db, repo_id, IngestStatus.done)
        logger.info("Ingestion completed", extra={"repo_id": repo_id, **_trace_attrs()})

    except Exception as exc:
        logger.exception(
            "Ingestion failed",
            extra={"repo_id": repo_id, "error": str(exc), **_trace_attrs()},
        )
        update_repo_status(db, repo_id, IngestStatus.failed, error=str(exc))
        raise

    finally:
        db.close()
        logger.debug(
            "DB session closed after ingestion",
            extra={"repo_id": repo_id, **_trace_attrs()},
        )
