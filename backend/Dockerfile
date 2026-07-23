# ── Stage 1: Builder — install dependencies only ──
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies (cached layer — only rebuilds when lock changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# ── Stage 2: Runtime — copy app code + dependencies ──
FROM python:3.12-slim AS runtime

# uv is NOT installed at runtime: the app runs the venv's uvicorn directly, so no
# uv cache is written at start (avoids '/.cache/uv Permission denied' when the
# platform runs the container as an arbitrary/non-root UID, e.g. on Kubernetes/Argo).
ENV PYTHONPATH=/app
# Put the venv on PATH so "uvicorn" and the venv's Python resolve without uv.
ENV PATH=/app/.venv/bin:$PATH
# Don't try to write .pyc files (the code dir may be read-only for an arbitrary UID).
ENV PYTHONDONTWRITEBYTECODE=1
# A writable HOME for the non-root/arbitrary UID (OpenShift runs a random UID in group 0).
ENV HOME=/home/appuser

# Create a non-root user (used by local docker; OpenShift overrides it with a random UID).
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/uv.lock ./

# Copy app code
COPY . .
# OpenShift arbitrary-UID support: own by group root (GID 0) with group perms = owner,
# so the random non-root UID (always in group 0) can read/write /app and $HOME.
RUN chown -R appuser:0 /app /home/appuser && chmod -R g=u /app /home/appuser

USER appuser
EXPOSE 8000

# The app bootstraps itself on startup: it ensures the database + its own tables
# exist (idempotent) before serving — no separate migration step.
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
