# ---------- Stage 1: Builder ----------
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Optional dev tools in builder
RUN pip install ruff grype

COPY ./app ./app

# Lint & scan inside image to enforce check
RUN ruff ./app
RUN grype /app --fail-on=high || (echo "❌ Vulns found!" && exit 1)

# ---------- Stage 2: Runtime ----------
FROM python:3.11-slim

RUN useradd -m -u 1000 fastapiuser
WORKDIR /app

COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

USER fastapiuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
