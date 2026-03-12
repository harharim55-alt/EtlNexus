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

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (async), PostgreSQL 16, Alembic, uv (package manager)
- **Frontend:** TypeScript, React 19, Vite, pnpm, shadcn/ui (base-ui), Zustand (state), TanStack Query (data fetching), Lucide icons, Tailwind CSS v4
- **Auth:** Keycloak (OIDC/SSO), PyJWT, oidc-client-ts + react-oidc-context
- **Containerization:** Docker, Docker Compose
- **Integrations:** Airflow (pipeline discovery, health, topology), Iceberg REST catalog, PySpark, OpenAPI-compatible AI endpoint
- **Do NOT use:** Redux

## Architecture

- Backend serves a REST API; frontend consumes it via TanStack Query
- All pipeline metadata is sourced from Airflow — **no git cloning**. `AirflowSyncService` reads `rendered_fields.op_kwargs` from task instances for pipeline discovery, lineage, and metadata
- Lineage `reads_from` edges derived from `needs` task_ids in op_kwargs; `writes_to` edges parsed from task logs (`ETL_WRITES_TO:` markers)
- ETL catalog is sourced from an Iceberg catalog — schemas synced every 2 hours
- AI Architect terminal uses an OpenAPI-compatible LLM endpoint with full catalog context
- **SSO/RBAC:** Keycloak OIDC with JIT user provisioning, team-based RBAC, visibility grants for cross-team access, admin panel for grant management

## Key UI Sections

1. **Pipeline Registry** — searchable master list (search by name, description, or field name) with Airflow status indicators, team badges, and visibility filtering
2. **Bento Workspace** — detail view with: pipeline topology/lineage, volume & schedule metrics, schema structure viewer, 1-click consume snippets, dual join intelligence (schema matches + AI insights), DAG network schedule, resource performance, execution plan tree, documentation editor
3. **Global Schema Matrix** — cross-pipeline field frequency and entity mapping
4. **AI Architect Terminal** — goal-oriented natural language queries against the catalog
5. **Admin Panel** — user management, team overview, visibility grant management (admin-only)

## Commands

### Development (Docker Compose Watch - auto-updates on file changes)
```bash
docker compose up              # Start all services (backend, frontend, db, airflow, keycloak, iceberg)
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
pnpm tsc --noEmit              # TypeScript type check
pnpm dlx shadcn@latest add <component>  # Add shadcn/ui component
```

### Production
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

## Backend Architecture

Three-layer pattern: **Router** (HTTP) -> **Service** (business logic) -> **Repository** (data access)
- `backend/app/routers/` — FastAPI route handlers, all under `/api/`. All endpoints require authentication via `get_current_user` (except health check and `/api/auth/config`)
- `backend/app/services/` — orchestrates repos and integration clients
- `backend/app/repositories/` — async SQLAlchemy queries
- `backend/app/integrations/` — external system clients (Airflow, Iceberg, LLM, OIDC)
- `backend/app/parsers/` — Iceberg catalog navigator
- `backend/app/tasks/` — APScheduler background tasks (airflow sync, airflow poll, catalog sync)
- `backend/app/models/` — SQLAlchemy ORM models (pipelines, users, teams, visibility_grants, etc.)
- `backend/app/schemas/` — Pydantic request/response DTOs
- `backend/app/auth.py` — JWT validation, JIT user provisioning, role/team authorization dependencies
- Dependency injection via FastAPI `Depends`

## Authentication & Authorization

- **SSO:** Keycloak OIDC via `oidc_client.py`. Dual-issuer support (internal Docker DNS + public URL). `sso_enabled` toggle in settings (default: off for local dev, on in docker-compose)
- **JIT Provisioning:** Users and teams created/synced on first SSO login from JWT claims
- **RBAC:** Three roles: `admin`, `member`, `viewer`. Enforced at DB level with CHECK constraint
- **Visibility:** Non-admin users see: own team's pipelines + unassigned pipelines + pipelines/teams granted via `visibility_grants`
- **Grants:** Two types — per-pipeline or per-source-team, with `viewer` or `editor` level. Admin-only management via `/api/visibility/grants`
- **Default user:** When SSO disabled, a stable `default-admin` user is returned (no credential check)
- **5 Teams:** Dagger, Vault, Prism, Relay, Oasis — each owning specific DAGs

## Frontend Architecture

- `frontend/src/components/` — React components organized by feature (layout, pipeline-registry, bento-workspace, schema-matrix, ai-terminal, admin, shared)
- `frontend/src/hooks/` — TanStack Query hooks wrapping API calls (server state)
- `frontend/src/stores/` — Zustand stores for client-only UI state (active tab, selected pipeline, chat history)
- `frontend/src/api/` — Axios client layer with API functions per domain
- `frontend/src/types/` — TypeScript interfaces mirroring Pydantic schemas
- Always-dark theme: `#09090b` (background), `#18181b` (cards), indigo-500 (accent). No dark mode toggle needed
- shadcn/ui uses base-ui (React 19): `delay` not `delayDuration`, no `asChild` on TooltipTrigger

## Background Tasks (APScheduler)

- **Airflow pipeline sync:** every 20 min — discovers pipelines, lineage, team assignment from op_kwargs
- **Airflow status poll:** every 20 min — task run statuses, resource usage from logs, execution plans
- **Catalog sync:** every 2 hours — Iceberg schemas synced to pipeline fields

## Configuration

All integrations configured via `.env` (dev defaults) or `.env.prod` (external APIs). See `.env.example` for all variables organized by section: Database, Airflow, Iceberg, LLM, SSO/Keycloak, App.

## Design Reference

`design_idea.ts` contains a React component mockup showing the target UI design, layout structure, and component hierarchy. Use it as a visual reference, not as production code.
