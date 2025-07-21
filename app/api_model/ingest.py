from pydantic import BaseModel, HttpUrl


class IngestRequest(BaseModel):
    """Request model for initiating an ingestion process.
    Attributes:
        repo_url (HttpUrl): URL of the repository to be ingested.
    """

    repo_url: HttpUrl


class IngestResponse(BaseModel):
    """Response model for ingestion status.
    This model is used to return the status of an ingestion process.
    Attributes:
        repo_id (str): Unique identifier for the repository.
        status (str): Current status of the ingestion process.
    """

    repo_id: str
    status: str


class IngestStatusResponse(BaseModel):
    """Response model for checking the status of an ingestion process.
    Attributes:
        repo_id (str): Unique identifier for the repository.
        status (str): Current status of the ingestion process.
        error (str | None): Error message if the ingestion failed, otherwise None.
    """

    repo_id: str
    status: str
    error: str | None = None
