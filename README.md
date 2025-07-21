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

| Endpoint                    | Description                         | Auth Scope     |
|-----------------------------|-------------------------------------|----------------|
| `GET /api/v1/health`        | Health check                        | ❌ Public       |
| `POST /api/v1/auth/login`   | GitHub OAuth login                  | ❌ Public       |
| `POST /api/v1/auth/logout`  | Revoke refresh token                | ✅ Auth         |
| `GET /api/v1/protected/me`  | Get current user info               | ✅ Auth         |
| `POST /api/v1/repos/`       | Ingest a Git repo                   | ✅ `ingest`     |
| `GET /api/v1/repos/{id}/status` | Check ingest status              | ✅ `ingest`     |
| `GET /api/v1/rate_limited`  | Rate-limited test endpoint          | ✅ `rate_limited` |
| `WS  /api/v1/chat/{repo_id}`| Ask questions about ingested repo   | ✅ `chat`       |

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

## 🚀 Running Locally

### 1. Clone the Repo

```bash
git clone https://github.com/your-username/repo-lens.git
cd repo-lens