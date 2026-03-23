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

# Pre-download Iceberg Spark JAR so no Maven access is needed at runtime
RUN apt-get update && apt-get install -y --no-install-recommends wget && \
    mkdir -p /app/jars && \
    wget -q -O /app/jars/iceberg-spark-runtime.jar \
      "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.7.1/iceberg-spark-runtime-3.5_2.12-1.7.1.jar" && \
    rm -rf /var/lib/apt/lists/*

# ── Stage 2: Runtime — copy app code + dependencies ──
FROM python:3.12-slim AS runtime

# Install Java runtime (needed for PySpark at runtime)
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre-headless && \
    rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/default-java

# Install uv (needed for running commands)
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy installed dependencies and pre-downloaded JARs from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/jars /app/jars
COPY --from=builder /app/pyproject.toml /app/uv.lock ./

# Copy app code
COPY . .
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

CMD ["sh", "-c", "uv run alembic upgrade head && exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
