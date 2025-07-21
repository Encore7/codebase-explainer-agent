# Codebase Explainer Agent

FastAPI-Powered Git Repository Ingestion & QA Agent

Codebase Explainer Agent is a FastAPI application for ingesting Git repositories, embedding commit diffs using OpenAI, and enabling question answering over the ingested data using LangGraph agents and ChromaDB.

## ✨ Features

- **🔐 OAuth2 Login via GitHub**  
  Secure authentication with access/refresh tokens and scoped route protection.

- **📦 Repository Ingestion Pipeline**  
  - Commit history parsed using `PyDriller`  
  - Diffs embedded via OpenAI embeddings  
  - Stored in `ChromaDB` as vector documents  

- **🤖 LangGraph Agent**  
  - `retrieve → summarise → compose` agent flow  
  - Answer user questions on repo logic  
  - Streamed WebSocket output  

- **📈 Unified Observability**  
  - OpenTelemetry traces (Tempo)  
  - Structured logs (Loki)  
  - Metrics (Prometheus)

- **⚖️ Rate Limiting with SlowAPI**  
  - Per-IP or per-user throttling  
  - 429 responses with custom logging

## 🗂️ API Overview

| Endpoint                    | Description                         | Auth Scope   |
|-----------------------------|-------------------------------------|--------------|
| `GET /api/v1/health`        | Health check                        | Public       |
| `POST /api/v1/auth/login`   | GitHub OAuth login                  | Public       |
| `POST /api/v1/auth/logout`  | Revoke refresh token                | Auth         |
| `GET /api/v1/protected/me`  | Get current user info               | Auth         |
| `POST /api/v1/repos/`       | Ingest a Git repo                   | `ingest`     |
| `GET /api/v1/repos/{id}/status` | Check ingest status             | `ingest`     |
| `GET /api/v1/rate_limited`  | Rate-limited test endpoint          | `rate_limited` |
| `WS  /api/v1/chat/{repo_id}`| Ask questions about ingested repo   | `chat`       |

## ⚙️ Tech Stack

| Layer            | Tools |
|------------------|-------|
| **Framework**    | FastAPI, SQLModel |
| **Auth**         | GitHub OAuth2, JWT (access/refresh + scopes) |
| **Vector Store** | ChromaDB |
| **Embedding**    | OpenAI API |
| **Agent**        | LangGraph |
| **Observability**| OpenTelemetry, Tempo, Loki, Prometheus |
| **Rate Limiting**| SlowAPI |
| **Background Tasks** | FastAPI BackgroundTasks (async ingestion) |

## Running Locally

### 1. Clone the Repo

```bash
git clone git@github.com:Encore7/codebase-explainer-agent.git
cd codebase-explainer-agent
```

### 2. Set Environment Variables

Set the environment variables from .env.example file

### 3. Run with Docker Compose

```bash
docker-compose up --build
```

### 4. Access Docs
- Swagger: http://localhost:8000/api/v1/docs
- Redoc: http://localhost:8000/api/v1/redoc

## 🧪 Example Chat Flow

1. **Login via GitHub**
   - Visit `/api/v1/auth/login` to authenticate using your GitHub account.
   - The system will redirect back with an `access_token` and `refresh_token`.

2. **Ingest a Git Repository**
   - `POST /api/v1/repos/`
   - Request body:
     ```json
     {
       "repo_url": "https://github.com/your-org/your-repo"
     }
     ```
   - Response:
     ```json
     {
       "repo_id": "your-repo-name",
       "status": "queued"
     }
     ```

3. **Check Ingestion Status**
   - `GET /api/v1/repos/{repo_id}/status`
   - Status will be `queued`, then `in_progress`, and finally `done`.

4. **Open Chat WebSocket**
   - Connect to: `ws://localhost:8000/api/v1/chat/{repo_id}`
   - Use the `access_token` for authentication.

5. **Send a Question**
   - Example payload:
     ```json
     {
       "q": "What changes were made to the authentication system?"
     }
     ```

6. **Receive Streaming Response**
   - Tokens will be streamed back as:
     ```json
     { "token": "Some", "is_final": false }
     { "token": " update", "is_final": false }
     ...
     { "token": "", "is_final": true }
     ```

---

## 📊 Monitoring Stack

- **Traces** → OpenTelemetry → Tempo
- **Logs** → Structured logs with trace context via Loki
- **Metrics** → Prometheus metrics at `/metrics`

All logs and spans include trace ID and span ID for correlation.

---

## 🛡️ Scopes & Route Security

| Scope         | Grants Access To                         |
|---------------|------------------------------------------|
| `ingest`      | Repository ingestion APIs                |
| `chat`        | Chat/agent WebSocket                     |
| `rate_limited`| Rate-limited demo endpoint               |

JWT tokens are issued with scopes:

```json
{
  "sub": "your_github_username",
  "type": "access",
  "scopes": ["ingest", "chat"],
  "exp": 1753020000
}
```

Use these scopes to control access to each feature of the app.

---

## 🧱 Folder Structure

```
app/
├── api/              # Route definitions (auth, ingest, chat, etc.)
├── api_model/        # Pydantic request/response models
├── core/             # App settings, security, db, telemetry
├── crud/             # Database queries (SQLModel)
├── models/           # SQLModel DB schema
├── services/         # Business logic: ingestion, agent, etc.
├── utils/            # Tracing, logging, helpers
└── main.py           # FastAPI entrypoint
```

---

## 📌 Future Enhancements

- [ ] GitHub webhook trigger for automatic ingestion  
- [ ] Switch to Celery for scalable async tasks  
- [ ] RAG-enhanced agent with retrieval fallback  
- [ ] Granular rate limits per user/token  

---

## 👥 Contributing

Open to contributions via pull requests, discussions, or issues.

---

## 🪪 License

MIT License © 2025
