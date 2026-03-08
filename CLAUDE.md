# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

### Critical Rules - DO NOT VIOLATE

- **NEVER create mock data or simplified components** unless explicitly told to do so

- **NEVER replace existing complex components with simplified versions** - always fix the actual problem

- **ALWAYS work with the existing codebase** - do not create new simplified alternatives

- **ALWAYS find and fix the root cause** of issues instead of creating workarounds

- When debugging issues, focus on fixing the existing implementation, not replacing it

- When something doesn't work, debug and fix it - don't start over with a simple version

- **ALWAYS check DOCS before making changes**

## Project Overview

ETL Explorer Hub — a data architecture command center for discovering, understanding, and utilizing ETL pipelines. Dark-themed "bento-box" UI with master-detail layout, pipeline lineage visualization, schema browsing, join intelligence, and an AI architect terminal.

## Technology Stack

- **Backend:** Python, FastAPI, SQLAlchemy, uv (package manager)
- **Frontend:** TypeScript, React, Vite, pnpm, shadcn/ui, Zustand (state), TanStack Query (data fetching), Lucide icons
- **Containerization:** Docker
- **Integrations:** Airflow (pipeline health), Hue, PySpark, Git (code reading via cloned repos), OpenAPI-compatible AI endpoint
- **Do NOT use:** Redux

## Architecture

- Backend serves a REST API; frontend consumes it via TanStack Query
- ETL catalog is sourced from an Iceberg catalog under `catalog.iceberg.dagger` — only ETLs under the `Dagger` folder are displayed
- Pipeline lineage is derived by parsing ETL source code from a configurable git repository (cloned and pulled hourly): extract section reveals upstream dependencies, class `__init__` reveals target table
- `get_etl_dags(etl_name)` — Python function that returns the list of networks/DAGs an ETL is scheduled on
- AI Architect terminal uses an OpenAPI-compatible LLM endpoint with full catalog context

## Key UI Sections

1. **Pipeline Registry** — searchable master list (search by name, description, or field name) with Airflow status indicators
2. **Bento Workspace** — detail view with: pipeline topology/lineage, volume & schedule metrics, schema structure viewer, 1-click consume snippets, dual join intelligence (schema matches + AI insights), DAG network schedule
3. **Global Schema Matrix** — cross-pipeline field frequency and entity mapping
4. **AI Architect Terminal** — goal-oriented natural language queries against the catalog

## Commands

### Development (Docker Compose Watch - auto-updates on file changes)
```bash
docker compose up              # Start all services (backend, frontend, db, airflow, git-seed)
docker compose watch           # Start with file-watching auto-sync
docker compose down            # Stop all services
docker compose down -v         # Stop and remove volumes (reset DB)
```

### Backend (local, without Docker)
```bash
cd backend
uv sync                        # Install dependencies
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
uv run alembic upgrade head    # Run migrations
uv run alembic revision --autogenerate -m "description"  # Create migration
```

### Frontend (local, without Docker)
```bash
cd frontend
pnpm install                   # Install dependencies
pnpm dev                       # Start dev server at :5173
pnpm build                     # Production build
pnpm dlx shadcn@latest add <component>  # Add shadcn/ui component
```

### Production
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

## Backend Architecture

Three-layer pattern: **Router** (HTTP) -> **Service** (business logic) -> **Repository** (data access)
- `backend/app/routers/` — FastAPI route handlers, all under `/api/`
- `backend/app/services/` — orchestrates repos and integration clients
- `backend/app/repositories/` — async SQLAlchemy queries
- `backend/app/integrations/` — external system clients (Airflow, Git, Iceberg, LLM)
- `backend/app/parsers/` — ETL code AST parser and Iceberg catalog navigator
- `backend/app/tasks/` — APScheduler background tasks (git pull, airflow poll, catalog sync)
- `backend/app/models/` — SQLAlchemy ORM models
- `backend/app/schemas/` — Pydantic request/response DTOs
- Dependency injection via FastAPI `Depends`

## Frontend Architecture

- `frontend/src/components/` — React components organized by feature (layout, pipeline-registry, bento-workspace, schema-matrix, ai-terminal, shared)
- `frontend/src/hooks/` — TanStack Query hooks wrapping API calls (server state)
- `frontend/src/stores/` — Zustand stores for client-only UI state (active tab, selected pipeline, chat history)
- `frontend/src/api/` — Axios client layer with API functions per domain
- `frontend/src/types/` — TypeScript interfaces mirroring Pydantic schemas
- Always-dark theme: `#09090b` (background), `#18181b` (cards), indigo-500 (accent)

## Configuration

All integrations configured via `.env` (dev defaults) or `.env.prod` (external APIs). See `.env.example` for all variables organized by section: Database, Airflow, Git, Iceberg, LLM, App.

## Design Reference

`design_idea.ts` contains a React component mockup showing the target UI design, layout structure, and component hierarchy. Use it as a visual reference, not as production code.
