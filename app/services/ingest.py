from typing import Annotated, List, Tuple

import chromadb
from chromadb.api.models import Collection
from openai import OpenAI
from pydriller import Repository
from sqlmodel import Session
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.core.config import settings
from app.core.db import engine
from app.core.telemetry import get_logger
from app.crud.repo import update_repo_status
from app.models.repo import IngestStatus
from app.utils.trace import _trace_attrs

logger = get_logger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(Exception),
)
def get_embedding(
    embedder: Annotated[OpenAI, "OpenAI Embedder"],
    text: Annotated[str, "Text to embed"],
) -> List[float]:
    """Retrieve embedding for the given text using OpenAI API.
    Args:
        embedder: OpenAI client instance.
        text: Text to embed.
    Returns:
        List of floats representing the embedding.
    """
    return embedder.embeddings.create(input=text)["data"][0]["embedding"]


def ingest_repo_task(
    repo_id: Annotated[str, "Repository ID"], repo_url: Annotated[str, "Repository URL"]
):
    """Ingest a repository by traversing its commits and adding modified files to ChromaDB.
    Args:
        repo_id: Unique identifier for the repository.
        repo_url: URL of the repository to ingest.
    """
    db = Session(engine)
    try:
        logger.info("Ingestion started", extra={"repo_id": repo_id, **_trace_attrs()})
        update_repo_status(db, repo_id, IngestStatus.in_progress)

        client: Annotated[chromadb.Client, "ChromaDB Client"] = chromadb.Client()
        try:
            collection = client.get_collection(name=repo_id)
        except ValueError:
            collection = client.create_collection(name=repo_id)

        embedder: Annotated[OpenAI, "OpenAI Embedder"] = OpenAI(
            api_key=settings.OPENAI_API_KEY
        )
        batch: List[Tuple[str, dict, str]] = []

        for commit in Repository(repo_url).traverse_commits():
            for mf in commit.modified_files:
                text = f"{commit.msg}\n{mf.diff or ''}"
                metadata = {
                    "commit": commit.hash,
                    "path": mf.new_path,
                    "date": commit.author_date.isoformat(),
                    "author": commit.author.name,
                }
                doc_id = f"{commit.hash}:{mf.new_path}"
                batch.append((text, metadata, doc_id))

                if len(batch) >= 20:
                    _process_batch(batch, collection, embedder, repo_id)
                    batch.clear()

        if batch:
            _process_batch(batch, collection, embedder, repo_id)

        update_repo_status(db, repo_id, IngestStatus.done)
        logger.info("Ingestion completed", extra={"repo_id": repo_id, **_trace_attrs()})

    except Exception as exc:
        logger.exception(
            "Ingestion failed", extra={"repo_id": repo_id, **_trace_attrs()}
        )
        update_repo_status(db, repo_id, IngestStatus.failed, error=str(exc))
        raise RuntimeError("Ingestion process crashed") from exc

    finally:
        db.close()
        logger.debug(
            "DB session closed after ingestion",
            extra={"repo_id": repo_id, **_trace_attrs()},
        )


def _process_batch(
    batch: Annotated[List[Tuple[str, dict, str]], "Batch of (text, metadata, id)"],
    collection: Annotated[Collection, "ChromaDB Collection"],
    embedder: Annotated[OpenAI, "OpenAI Embedder"],
    repo_id: Annotated[str, "Repository ID"],
):
    """Process a batch of documents, embedding and adding them to the ChromaDB collection.
    Args:
        batch: List of tuples containing (text, metadata, id).
        collection: ChromaDB collection to add documents to.
        embedder: OpenAI client for generating embeddings.
        repo_id: Repository ID for logging and tracking.
    """
    texts, metadatas, ids = zip(*batch)
    embeddings: List[List[float]] = []

    for text in texts:
        try:
            emb = get_embedding(embedder, text)
        except Exception as exc:
            logger.warning(
                "Failed to embed document",
                extra={"repo_id": repo_id, "error": str(exc), **_trace_attrs()},
            )
            emb = None
        embeddings.append(emb)

    docs, embs, metas, doc_ids = [], [], [], []
    for text, emb, meta, did in zip(texts, embeddings, metadatas, ids):
        if emb is not None:
            docs.append(text)
            embs.append(emb)
            metas.append(meta)
            doc_ids.append(did)

    if docs:
        try:
            collection.add(
                documents=docs,
                embeddings=embs,
                metadatas=metas,
                ids=doc_ids,
            )
            logger.debug(
                "Batch added to ChromaDB",
                extra={"count": len(docs), "repo_id": repo_id, **_trace_attrs()},
            )
        except Exception as exc:
            logger.error(
                "ChromaDB batch insert failed",
                extra={"repo_id": repo_id, "error": str(exc), **_trace_attrs()},
            )
