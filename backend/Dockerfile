# ── Stage 1: Builder — install dependencies only ──
FROM python:3.12-slim AS builder

# Install Java (needed for PySpark/Iceberg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre-headless && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies (cached layer — only rebuilds when lock changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# ── Stage 2: Runtime — copy app code + dependencies ──
FROM python:3.12-slim AS runtime

# Install Java runtime (needed for PySpark at runtime)
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre-headless && \
    rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# Install uv (needed for running commands)
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/uv.lock ./

# Copy app code
COPY . .
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

CMD ["sh", "-c", "uv run alembic upgrade head && exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
