FROM python:3.12-slim AS base

# Install git (needed for git integration) and Java (needed for PySpark/Iceberg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git default-jre-headless && \
    rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# Copy app code
COPY . .
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

CMD ["sh", "-c", "uv run alembic upgrade head && exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
