# EtlNexus Developer Guide

**ETL Explorer Hub** — data architecture command center for discovering, understanding, and utilizing ETL pipelines.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Prerequisites and Environment Setup](#2-prerequisites-and-environment-setup)
3. [Quick Start](#3-quick-start)
4. [Project Structure](#4-project-structure)
5. [Backend Architecture](#5-backend-architecture)
6. [Frontend Architecture](#6-frontend-architecture)
7. [Data Model](#7-data-model)
8. [Authentication and RBAC](#8-authentication-and-rbac)
9. [External Integrations](#9-external-integrations)
10. [Background Tasks and Scheduling](#10-background-tasks-and-scheduling)
11. [How to Add a New Backend Endpoint](#11-how-to-add-a-new-backend-endpoint)
12. [How to Add a New Frontend Feature](#12-how-to-add-a-new-frontend-feature)
13. [How to Add a Database Migration](#13-how-to-add-a-database-migration)
14. [Naming Conventions](#14-naming-conventions)
15. [Configuration Reference](#15-configuration-reference)
16. [Testing Strategy](#16-testing-strategy)
17. [Deployment Guide](#17-deployment-guide)
18. [Troubleshooting](#18-troubleshooting)

---

## 1. Project Overview

EtlNexus is a dark-themed, bento-box-style data catalog and pipeline intelligence UI. The product serves data engineers and architects who need to understand what ETL pipelines exist, what data they read and write, how they perform, and how teams own them.

### Key Capabilities

- **Pipeline Registry** — searchable catalog of all ETL pipelines discovered from Airflow, with Airflow health status and team ownership badges.
- **Bento Workspace** — detail panel for a selected pipeline: lineage topology, schema viewer, Spark resource/performance metrics, execution plan tree, join intelligence, consume snippets, and inline documentation editing.
- **Global Schema Matrix** — cross-pipeline field frequency heatmap that identifies shared entities.
- **DAG Summary** — per-DAG view of task schedules, resource allocations, and run history.
- **Sensors View** — data-ingestion root tasks with downstream topology explorer.
- **AI Architect Terminal** — natural language queries against the full pipeline catalog using a configurable LLM endpoint.
- **Admin Panel** — visibility grant management for cross-team pipeline access (admin-only).

### Theme and Design Language

- Always-dark: background `#09090b`, card surfaces `#18181b`, accent `indigo-500`.
- No dark-mode toggle is ever needed or implemented.
- Computer-networking domain: DAG IDs such as `backbone_core`, `perimeter_defense`, pipeline names are PascalCase.

---

## 2. Prerequisites and Environment Setup

### Required Tools

| Tool | Minimum Version | Purpose |
|------|----------------|---------|
| Docker | 24+ | Container runtime |
| Docker Compose | 2.20+ | Orchestration |
| Node.js | 20+ | Frontend local development |
| pnpm | 9+ | Frontend package manager |
| Python | 3.12 | Backend local development |
| uv | 0.6+ | Backend package manager |

### Installing Frontend Tools

```bash
# Install Node.js via nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20
nvm use 20

# Enable pnpm via corepack
corepack enable
corepack prepare pnpm@latest --activate
```

### Installing Backend Tools

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Environment Files

Copy the example env file and fill in values for your target deployment:

```bash
cp .env.example .env
```

For local Docker Compose development, the defaults in `.env.example` work out of the box. The most important variables to review are the SSO settings and the LLM endpoint. See [Section 15](#15-configuration-reference) for the full variable reference.

---

## 3. Quick Start

### Option A: Full Docker Compose Stack (Recommended)

This starts all services: backend, frontend, PostgreSQL, Airflow (webserver + scheduler + init), Keycloak, Iceberg REST, and the data seed containers.

```bash
# Start all services
docker compose up

# Start with live file-sync (auto-reloads on code changes without full rebuild)
docker compose watch

# Stop all services
docker compose down

# Stop and wipe all persistent volumes (full reset)
docker compose down -v
```

Service endpoints after startup:

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | See dev users below |
| Backend API | http://localhost:8000/api | — |
| API Docs (Swagger) | http://localhost:8000/docs | — |
| Airflow | http://localhost:8080 | admin / admin |
| Keycloak | http://localhost:8090 | admin / admin |
| Iceberg REST | http://localhost:8181 | — |
| PostgreSQL | localhost:5432 | etlnexus / etlnexus |

### Dev Test Users (Keycloak)

When `SSO_ENABLED=true` (default in the Docker Compose stack), these users are pre-seeded in the `etlnexus` Keycloak realm:

| Username | Password | Role | Teams |
|----------|----------|------|-------|
| alice | password | admin | Dagger |
| bob | password | member | Vault, Prism |
| charlie | password | member | Relay |
| diana | password | member | Oasis |

### Option B: Local Backend Development

Run the backend locally against a Dockerized database and Airflow:

```bash
# Start only the infrastructure services
docker compose up db airflow-db airflow-init airflow-webserver airflow-scheduler keycloak iceberg-rest iceberg-seed iceberg-data-seed

cd backend

# Install dependencies
uv sync

# Apply migrations
uv run alembic upgrade head

# Start the API server with auto-reload
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option C: Local Frontend Development

Run the frontend dev server against either the local or Dockerized backend:

```bash
cd frontend

# Install dependencies
pnpm install

# Start the Vite dev server at :5173
pnpm dev

# Type-check without emitting (run before committing)
pnpm tsc --noEmit

# Production build
pnpm build
```

The frontend proxies `/api` requests to the backend. In local dev mode, the `VITE_API_BASE_URL` environment variable controls where requests go. By default it falls back to `/api`, which Vite's dev server proxies to `http://localhost:8000/api`.

---

## 4. Project Structure

```
EtlNexus/
├── backend/                        # FastAPI application
│   ├── alembic/
│   │   ├── env.py                  # Async Alembic environment
│   │   └── versions/               # 019 migration files (001–019)
│   ├── app/
│   │   ├── main.py                 # FastAPI app factory, lifespan hooks, router registration
│   │   ├── config.py               # Pydantic Settings (reads .env)
│   │   ├── database.py             # Async engine, session factory, Base
│   │   ├── auth.py                 # JWT validation, JIT provisioning, auth dependencies
│   │   ├── cache.py                # Module-level TTL caches (pipeline list, topology, etc.)
│   │   ├── dependencies.py         # FastAPI Depends factories for all repos and services
│   │   ├── routers/                # HTTP route handlers (one file per domain)
│   │   │   ├── pipelines.py
│   │   │   ├── lineage.py
│   │   │   ├── topology.py
│   │   │   ├── airflow.py
│   │   │   ├── resources.py
│   │   │   ├── dag_summary.py
│   │   │   ├── sensors.py
│   │   │   ├── schema_matrix.py
│   │   │   ├── usage.py
│   │   │   ├── consumers.py
│   │   │   ├── ai.py
│   │   │   ├── auth.py
│   │   │   ├── teams.py
│   │   │   ├── users.py
│   │   │   ├── visibility.py
│   │   │   └── health.py
│   │   ├── services/               # Business logic (one class per domain)
│   │   │   ├── pipeline_service.py
│   │   │   ├── airflow_service.py
│   │   │   ├── airflow_sync_service.py
│   │   │   ├── catalog_sync_service.py
│   │   │   ├── consumer_service.py
│   │   │   ├── dag_summary_service.py
│   │   │   ├── resource_service.py
│   │   │   ├── schema_matrix_service.py
│   │   │   ├── sensor_service.py
│   │   │   ├── team_service.py
│   │   │   ├── usage_service.py
│   │   │   └── visibility_service.py
│   │   ├── repositories/           # Async SQLAlchemy data access
│   │   │   ├── pipeline_repo.py
│   │   │   ├── lineage_repo.py
│   │   │   ├── airflow_repo.py
│   │   │   ├── dag_task_repo.py
│   │   │   ├── field_frequency_repo.py
│   │   │   ├── resource_repo.py
│   │   │   ├── sensor_repo.py
│   │   │   ├── team_repo.py
│   │   │   ├── usage_repo.py
│   │   │   ├── user_repo.py
│   │   │   └── visibility_grant_repo.py
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── __init__.py         # Re-exports all models (Alembic autogenerate needs this)
│   │   │   ├── pipeline.py         # Pipeline + PipelineField
│   │   │   ├── lineage.py          # LineageEdge
│   │   │   ├── airflow_status.py   # AirflowRunStatus
│   │   │   ├── run_history.py      # PipelineRunHistory (sparkMeasure metrics + plan)
│   │   │   ├── resource_config.py  # PipelineResourceConfig
│   │   │   ├── dag_task.py         # DagTask
│   │   │   ├── sensor.py           # Sensor
│   │   │   ├── pipeline_usage.py   # PipelineUsage
│   │   │   ├── team.py             # Team
│   │   │   ├── user.py             # User
│   │   │   ├── user_team.py        # UserTeam (many-to-many)
│   │   │   └── visibility_grant.py # VisibilityGrant
│   │   ├── schemas/                # Pydantic request/response DTOs
│   │   │   ├── pipeline.py
│   │   │   ├── lineage.py
│   │   │   ├── topology.py
│   │   │   ├── airflow.py
│   │   │   ├── resources.py
│   │   │   ├── execution_plan.py
│   │   │   ├── dag_summary.py
│   │   │   ├── sensor.py
│   │   │   ├── schema_matrix.py
│   │   │   ├── usage.py
│   │   │   ├── consumer.py
│   │   │   ├── ai.py
│   │   │   ├── auth.py
│   │   │   ├── team.py
│   │   │   ├── visibility.py
│   │   │   └── common.py
│   │   ├── integrations/           # External system clients
│   │   │   ├── airflow_client.py   # httpx client for Airflow REST API
│   │   │   ├── iceberg_client.py   # PySpark/Iceberg catalog client
│   │   │   ├── llm_client.py       # OpenAPI-compatible LLM client
│   │   │   └── oidc_client.py      # JWKS-caching OIDC JWT validator
│   │   ├── tasks/                  # APScheduler background jobs
│   │   │   ├── scheduler.py        # Job registration and lock guards
│   │   │   ├── airflow_sync_task.py
│   │   │   ├── airflow_poll_task.py
│   │   │   ├── catalog_sync_task.py
│   │   │   └── seed_usage_data.py
│   │   └── parsers/
│   │       └── dagger_catalog.py   # Iceberg namespace filter
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/                       # React application
│   ├── src/
│   │   ├── main.tsx                # React DOM entry point
│   │   ├── App.tsx                 # Root component, tab routing, lazy loading
│   │   ├── index.css               # Tailwind base + custom scrollbar styles
│   │   ├── api/                    # Axios API function modules
│   │   │   ├── client.ts           # Axios instance, Bearer token interceptor, 401 handler
│   │   │   ├── pipelines.ts
│   │   │   ├── lineage.ts
│   │   │   ├── topology.ts
│   │   │   ├── airflow.ts
│   │   │   ├── resources.ts
│   │   │   ├── execution-plan.ts
│   │   │   ├── dag-summary.ts
│   │   │   ├── sensors.ts
│   │   │   ├── schema-matrix.ts
│   │   │   ├── usage.ts
│   │   │   ├── consumers.ts
│   │   │   ├── ai.ts
│   │   │   ├── auth.ts
│   │   │   └── admin.ts
│   │   ├── hooks/                  # TanStack Query hooks (server state)
│   │   │   ├── use-pipelines.ts
│   │   │   ├── use-pipeline-detail.ts
│   │   │   ├── use-update-pipeline.ts
│   │   │   ├── use-sync-pipeline.ts
│   │   │   ├── use-lineage.ts
│   │   │   ├── use-topology.ts
│   │   │   ├── use-upstream-topology.ts
│   │   │   ├── use-airflow-status.ts
│   │   │   ├── use-resource-metrics.ts
│   │   │   ├── use-execution-plan.ts
│   │   │   ├── use-dag-summary.ts
│   │   │   ├── use-sensors.ts
│   │   │   ├── use-schema-matrix.ts
│   │   │   ├── use-pipeline-usage.ts
│   │   │   ├── use-pipeline-consumers.ts
│   │   │   ├── use-join-suggestions.ts
│   │   │   ├── use-ai-chat.ts
│   │   │   ├── use-auth.ts
│   │   │   └── use-admin.ts
│   │   ├── stores/                 # Zustand stores (client UI state)
│   │   │   ├── navigation-store.ts # activeTab
│   │   │   ├── pipeline-store.ts   # selectedPipelineId, searchQuery, filters
│   │   │   ├── auth-store.ts       # user, token, ssoEnabled
│   │   │   ├── ai-store.ts         # chat history
│   │   │   └── sensor-store.ts     # selectedSensor
│   │   ├── types/                  # TypeScript interfaces mirroring Pydantic schemas
│   │   │   ├── pipeline.ts
│   │   │   ├── lineage.ts
│   │   │   ├── topology.ts
│   │   │   ├── airflow.ts
│   │   │   ├── resources.ts
│   │   │   ├── execution-plan.ts
│   │   │   ├── dag-summary.ts
│   │   │   ├── sensor.ts
│   │   │   ├── schema-matrix.ts
│   │   │   ├── usage.ts
│   │   │   ├── consumer.ts
│   │   │   ├── ai.ts
│   │   │   └── auth.ts
│   │   ├── components/             # React components by feature
│   │   │   ├── auth/               # AuthBootstrap, AuthGuard
│   │   │   ├── layout/             # AppShell, Sidebar
│   │   │   ├── pipeline-registry/  # PipelineRegistry, PipelineListItem, PipelineSearch, PipelineFilters
│   │   │   ├── bento-workspace/    # BentoWorkspace and all bento cards
│   │   │   ├── dag-summary/        # DagSummaryView
│   │   │   ├── sensors/            # SensorsView
│   │   │   ├── schema-matrix/      # SchemaMatrixView
│   │   │   ├── ai-terminal/        # AIArchitectView
│   │   │   ├── admin/              # AdminView (visibility grants)
│   │   │   ├── shared/             # ErrorState, EmptyState, shared UI helpers
│   │   │   └── ui/                 # shadcn/ui generated components
│   │   └── lib/
│   │       ├── constants.ts        # TABS constant and TabType union
│   │       ├── permissions.ts      # isAdmin(), canEditPipeline() helpers
│   │       └── utils.ts            # cn() Tailwind class merger
│   ├── Dockerfile                  # Multi-stage: dev → build → nginx production
│   ├── nginx.conf                  # SPA routing + /api reverse proxy
│   └── package.json
│
├── dev/
│   ├── airflow/
│   │   └── Dockerfile              # Custom Airflow image with Java 17, PySpark, sparkmeasure
│   ├── dags/                       # Airflow DAG definitions (bind-mounted)
│   │   └── daily/                  # Daily DAG files + resources/ subdirectory
│   ├── keycloak/
│   │   └── etlnexus-realm.json     # Pre-configured Keycloak realm with users and groups
│   └── seeds/
│       ├── seed_iceberg.py         # Creates Iceberg namespaces and tables
│       ├── seed_iceberg_data.py    # Populates Iceberg tables with sample data
│       └── etl_code/               # PySpark ETL source files (dagger/ subfolder)
│
├── docker-compose.yml              # Full development stack
├── docker-compose.prod.yml         # Minimal production stack (no Airflow/Keycloak)
├── .env.example                    # Template for all environment variables
└── CLAUDE.md                       # AI assistant instructions for this codebase
```

---

## 5. Backend Architecture

### Three-Layer Pattern

Every HTTP endpoint follows the same layered flow:

```
HTTP Request
    └── Router (app/routers/)
            Validates path/query params, selects HTTP method
            Injects dependencies via FastAPI Depends
            Returns JSON response
        └── Service (app/services/)
                Orchestrates business logic
                Coordinates multiple repositories
                May apply caching
            └── Repository (app/repositories/)
                    Executes async SQLAlchemy queries
                    Returns ORM model instances
                    Never contains business logic
```

This separation ensures:
- Routers contain no SQL and no business logic — only HTTP glue.
- Services are unit-testable without an HTTP layer.
- Repositories are the single point of DB access and can be swapped in tests.

### Application Lifecycle (main.py)

The `lifespan` async context manager in `backend/app/main.py` runs at startup and shutdown:

**Startup sequence:**
1. Initialize the OIDC client (fetches `.well-known/openid-configuration` and JWKS if SSO is enabled).
2. Fire-and-forget background task: `sync_pipelines_from_airflow()` → `seed_usage_data()` → `sync_from_catalog()` → `poll_airflow_statuses()`. This does not block the app from accepting requests; the app serves empty/stale data until the first sync completes.
3. Start the APScheduler instance.

**Shutdown sequence:**
1. Shut down APScheduler.
2. Close the httpx clients for Airflow and OIDC.
3. Stop the PySpark session used by the Iceberg client.

### Dependency Injection (dependencies.py)

`backend/app/dependencies.py` contains FastAPI Depends factories for every repository and service. Each factory creates a new instance per request, injecting the async database session.

```python
# Pattern: factory function injected with get_db_session
def get_pipeline_service(
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
    lineage_repo: LineageRepository = Depends(get_lineage_repo),
) -> PipelineService:
    return PipelineService(pipeline_repo, lineage_repo)
```

When adding a new service, always:
1. Add a `get_<thing>_repo` function to `dependencies.py`.
2. Add a `get_<thing>_service` function that wires up the repo.
3. Inject the service into the router via `Depends(get_<thing>_service)`.

### Caching Strategy (cache.py)

The application uses module-level TTL caches backed by plain dicts. Pipeline data changes only at each 20-minute sync cycle, so reads between syncs can skip DB queries entirely.

Defined caches and their TTLs:

| Cache | TTL | Cleared by |
|-------|-----|-----------|
| `pipeline_list_cache` | 30 s | After sync/poll |
| `schema_matrix_cache` | 60 s | After sync/poll |
| `topology_cache` | 30 s | After sync/poll |
| `dag_summary_cache` | 60 s | After sync/poll |
| `sensor_cache` | 60 s | After sync/poll |
| `sensor_topology_cache` | 30 s | After sync/poll |

All caches are cleared via `clear_all()` in `backend/app/cache.py` after every sync/poll cycle.

Important: when a `PATCH /api/pipelines/{id}` mutation succeeds, `pipeline_list_cache.clear()` is called manually so stale data is not served.

### Structured Logging

The logging configuration in `main.py` produces `%(asctime)s [%(levelname)s] %(name)s: %(message)s` formatted output. All modules get loggers via `logging.getLogger(__name__)`. Log level is `DEBUG` when `settings.debug=True`, otherwise `INFO`.

SQLAlchemy engine logging is suppressed at `WARNING` level to avoid flooding logs with every query. Set `echo=True` on the engine temporarily when debugging queries.

---

## 6. Frontend Architecture

### Application Shell

The app renders inside `AppShell` (a fixed-height flex container with `Sidebar` on the left and a scrollable `main` on the right). Tab routing is managed entirely in memory by `useNavigationStore`; there is no URL router.

`App.tsx` uses React `lazy()` + `Suspense` for all tab views except the `PipelineRegistry` (which is always mounted). This keeps the initial bundle small.

### State Management Rules

There are two categories of state, and they must not be mixed:

| Category | Tool | Examples |
|----------|------|---------|
| Server state (data from the API) | TanStack Query | Pipeline list, pipeline detail, DAG summary |
| Client UI state (user interaction) | Zustand | Selected pipeline ID, active tab, search query, filter sets |

**Never** put API data in Zustand. **Never** put UI state (e.g., a modal's open/closed status) in TanStack Query. **Never** use Redux.

### Zustand Stores

| Store | State |
|-------|-------|
| `navigation-store` | `activeTab` (`catalog` \| `matrix` \| `dags` \| `sensors` \| `ai` \| `admin`) |
| `pipeline-store` | `selectedPipelineId`, `selectedDagId`, `searchQuery`, `filtersOpen`, `teamFilters`, `dagFilters`, `statusFilters` |
| `auth-store` | `user`, `token`, `isAuthenticated`, `ssoEnabled` |
| `ai-store` | Chat message history |
| `sensor-store` | Selected sensor name |

### TanStack Query Hooks Pattern

Every hook lives in `frontend/src/hooks/` and follows this structure:

```typescript
// Query (read-only)
export function usePipelines(searchQuery: string) {
  return useQuery({
    queryKey: ["pipelines", searchQuery],      // cache key — must include all parameters
    queryFn: () => fetchPipelines(searchQuery || undefined),
    staleTime: 5 * 60_000,                    // 5 minutes before background refetch
    refetchInterval: 5 * 60_000,              // poll every 5 minutes
    placeholderData: keepPreviousData,         // prevents flicker during re-fetch
  });
}

// Mutation (write)
export function useUpdatePipeline(pipelineId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PipelineUpdateRequest) => updatePipeline(pipelineId, body),
    onSuccess: () => {
      // Always invalidate affected queries
      queryClient.invalidateQueries({ queryKey: ["pipeline", pipelineId] });
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
    },
  });
}
```

Query keys must be unique and hierarchical. Use `["resource"]` for lists and `["resource", id]` for individual items.

### Axios API Client (api/client.ts)

A single Axios instance is exported from `frontend/src/api/client.ts`. It:
- Sets `baseURL` to `VITE_API_BASE_URL` or `/api` as a fallback.
- Attaches the Bearer token from `useAuthStore` on every outbound request via a request interceptor.
- Handles `401` responses by clearing auth state when SSO is enabled (triggering a redirect to the login page).
- Logs a warning on `503` responses without rethrowing.

All API functions import this client:

```typescript
import apiClient from "./client";

export async function fetchPipelines(query?: string): Promise<PipelineListItem[]> {
  const params = query ? { q: query } : {};
  const { data } = await apiClient.get<PipelineListItem[]>("/pipelines", { params });
  return data;
}
```

### shadcn/ui with base-ui (React 19)

This project uses `@base-ui/react` (the React 19 variant of shadcn's component library). Two important differences from the standard shadcn/ui docs:

1. Tooltip delay prop is `delay`, not `delayDuration`.
2. `asChild` is not available on `TooltipTrigger` — wrap the trigger element directly.

To add a new shadcn component:

```bash
cd frontend
pnpm dlx shadcn@latest add <component-name>
```

Generated files land in `frontend/src/components/ui/`. Do not modify generated files directly unless necessary; instead wrap them in feature-specific components.

### Theme Constants

| Token | Value | Usage |
|-------|-------|-------|
| Background | `#09090b` | `bg-[#09090b]` |
| Card surface | `#18181b` | `bg-[#18181b]` |
| Accent | `indigo-500` | Borders, highlights |
| Text primary | `slate-300` | Body text |
| Text muted | `slate-500` / `slate-600` | Labels, placeholders |

---

## 7. Data Model

### Tables Overview

| Table | Purpose |
|-------|---------|
| `pipelines` | Core pipeline registry — one row per ETL task discovered from Airflow |
| `pipeline_fields` | Iceberg schema columns belonging to a pipeline |
| `lineage_edges` | Directed edges representing reads_from / writes_to relationships |
| `airflow_run_statuses` | Latest Airflow run status per pipeline (one-to-one) |
| `pipeline_run_history` | Per-run duration, resource metrics, sparkMeasure data, execution plan |
| `pipeline_resource_configs` | Allocated Spark resources per pipeline per DAG |
| `dag_tasks` | Airflow task graph snapshot (task_id, downstream_task_ids, dag_id) |
| `sensors` | Data ingestion root tasks discovered from Airflow |
| `pipeline_usages` | Enrichment data for consumer relationships (access counts, descriptions) |
| `teams` | Organizational teams (sourced from SSO groups or manual creation) |
| `users` | Authenticated users (JIT-provisioned from JWT on first login) |
| `user_teams` | Many-to-many join: user team memberships |
| `visibility_grants` | Cross-team pipeline access grants (admin-managed) |

### Key Relationships

```
pipelines (1) ──── (1) airflow_run_statuses
pipelines (1) ──── (N) pipeline_fields
pipelines (1) ──── (N) lineage_edges [as source or target]
pipelines (1) ──── (N) pipeline_run_history
pipelines (1) ──── (N) pipeline_resource_configs
pipelines (N) ──── (1) teams [via team_id FK]

users (N) ──── (N) teams [via user_teams]
visibility_grants → (pipeline_id XOR source_team_id) and (grantee_team_id XOR grantee_user_id)
```

### Pipeline Discovery Flow

Pipelines are not created manually. They are discovered automatically from Airflow:

1. `AirflowSyncService.sync_pipelines_from_airflow()` calls `GET /dags` to list all DAGs, then `GET /dags/{id}/tasks` for task definitions and `GET /dags/{id}/dagRuns/{runId}/taskInstances` for rendered `op_kwargs`.
2. Each Airflow task with `etl_name` in its `op_kwargs` becomes a row in `pipelines`.
3. Tasks with `sensor_name` in `op_kwargs` become rows in `sensors`.
4. `needs` keys in `op_kwargs` create `reads_from` lineage edges.
5. `ETL_WRITES_TO:` log markers create `writes_to` lineage edges.
6. Team assignment is derived by matching the task's `task_group` against known team names.
7. Schema fields are synced separately by `CatalogSyncService` from the Iceberg REST catalog.

### VisibilityGrant Constraints

The `visibility_grants` table has two `CHECK` constraints enforced at the database level:

- **Target constraint**: exactly one of `pipeline_id` or `source_team_id` must be non-null (a grant targets either a specific pipeline or all pipelines owned by a team).
- **Grantee constraint**: exactly one of `grantee_team_id` or `grantee_user_id` must be non-null.

The `grant_level` column is either `"viewer"` (can see the pipeline) or `"editor"` (can also edit description and documentation).

---

## 8. Authentication and RBAC

### Two Modes

**SSO disabled (`SSO_ENABLED=false`):**
Every request is treated as a stable default admin user with `sub="default-admin"`. No token is required. The frontend sets `token="no-sso"` in the auth store and never attaches an `Authorization` header.

**SSO enabled (`SSO_ENABLED=true`):**
Every protected endpoint requires a Bearer JWT issued by the configured Keycloak realm. The OIDC client validates the token against JWKS, checks `exp`/`iss`/`aud` claims, and accepts both internal Docker and public-facing issuer URLs.

### JWT Validation Flow

1. `HTTPBearer(auto_error=False)` extracts the token from the `Authorization` header.
2. `oidc_client.validate_token(token)` decodes and verifies the JWT using the cached JWKS (RS256). On `kid` cache miss, the JWKS is refreshed once.
3. `_upsert_user_from_claims(session, claims)` JIT-provisions the user row if it does not exist, refreshes `email`, `display_name`, `role`, and `last_login`, and reconciles team memberships with the SSO groups in the token.

### Dependency Hierarchy

Three auth dependency variants are available for use in routers:

| Dependency | Behaviour |
|-----------|-----------|
| `get_current_user` | Requires valid token (or returns default admin when SSO disabled). Raises HTTP 401 on failure. |
| `get_current_user_optional` | Returns `None` instead of raising when credentials are absent. |
| `require_role("admin")` | Factory returning a dependency that raises HTTP 403 unless `user.role` is in the given set. |
| `require_team_membership("pipeline_id")` | Factory that checks the caller belongs to the owning team. Admins bypass. |
| `require_team_membership_or_editor_grant("pipeline_id")` | Same as above but also allows users with an `"editor"` visibility grant. |

Usage example:

```python
# Require admin role
@router.get("/grants", dependencies=[Depends(require_role("admin"))])

# Require team membership or editor grant to mutate
@router.patch(
    "/{pipeline_id}",
    dependencies=[Depends(require_team_membership_or_editor_grant("pipeline_id"))],
)
```

### Team-Based Visibility

The `PipelineRepository.list_visible()` method builds a query that applies visibility rules:

- Admins see all pipelines.
- Members see pipelines where: the pipeline has no team, OR they belong to the owning team, OR they have a visibility grant (either targeting the specific pipeline or all pipelines of the owning team, either directly to them or to one of their teams).

### Frontend Auth Flow

1. On app load, `AuthBootstrap` calls `GET /api/auth/config` to determine whether SSO is enabled.
2. If SSO is disabled: a synthetic default user is placed in `auth-store` and the app renders normally.
3. If SSO is enabled: `react-oidc-context` wraps the app with the OIDC provider. `AuthGuard` checks `isAuthenticated` and redirects to the Keycloak login page if the user is not authenticated. After login, the OIDC callback populates `auth-store` with the user's profile and token.
4. `api/client.ts` reads the token from `auth-store` on every request via the request interceptor.

### Frontend Permission Helpers (lib/permissions.ts)

```typescript
isAdmin(user)                           // true if user.role === "admin"
canEditPipeline(user, pipelineTeam)     // true if admin, or unassigned pipeline, or user is in the team
```

The `can_edit` field is also set server-side on `PipelineDetail` responses, which is the authoritative value for showing edit controls.

---

## 9. External Integrations

### Airflow Client (integrations/airflow_client.py)

A singleton `airflow_client` instance wraps Airflow's REST API v1. It uses a persistent `httpx.AsyncClient` with connection pooling (10 max connections, 5 keepalive).

Key methods:

| Method | Purpose |
|--------|---------|
| `get_all_dags()` | Paginated DAG list, 5-minute TTL cache |
| `get_dag_tasks(dag_id)` | Task definitions with downstream IDs, 5-minute TTL cache |
| `get_task_instances(dag_id, run_id)` | Task instances for a specific run (includes `rendered_fields`) |
| `get_task_log(dag_id, run_id, task_id)` | Raw task log text (used to parse `ETL_WRITES_TO:`, `ETL_DESCRIPTION:`, `ETL_RESOURCE_ACTUAL:`, `ETL_EXECUTION_PLAN:` markers) |
| `get_dag_source(dag_id)` | DAG Python source via dagSources API |
| `get_task_group_map(dag_id)` | Parses DAG source to build `task_id → TaskGroup` mapping |

All requests retry once before marking `_connected = False` and returning `None`. Callers must handle `None` gracefully.

### Iceberg Client (integrations/iceberg_client.py)

The `iceberg_client` singleton uses a lazily-created PySpark session to read table schemas from the Iceberg REST catalog. PySpark is loaded only when the catalog sync task runs.

The session is configured with:
- `iceberg-spark-runtime-3.5_2.12:1.7.1` JAR for Iceberg support.
- `spark.sql.catalog.iceberg` pointing to the REST catalog URI.
- `spark.driver.memory=512m` to minimize memory footprint.
- Spark UI disabled.

The `stop()` method is called during application shutdown to release JVM resources.

### OIDC Client (integrations/oidc_client.py)

The `oidc_client` singleton validates JWTs using JWKS cached for 6 hours. Two public methods are useful when extending auth logic:

- `extract_groups(claims)` — reads the claim path defined by `SSO_GROUPS_CLAIM`, strips leading `/` from Keycloak path strings.
- `extract_role(claims)` — walks a dot-separated `SSO_ROLE_CLAIM` path, returns `"admin"` if `SSO_ADMIN_ROLE` appears in the roles list, otherwise `"member"`.

### LLM Client (integrations/llm_client.py)

An OpenAPI-compatible endpoint configured via `LLM_API_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. The `AIService` in `services/ai_service.py` builds a system prompt that injects the full pipeline catalog context before each request. Timeout is 30 seconds.

---

## 10. Background Tasks and Scheduling

### Scheduler Setup (tasks/scheduler.py)

The APScheduler `AsyncIOScheduler` is configured in `setup_scheduler()` and started in the lifespan handler. An `asyncio.Lock` (`_sync_lock`) prevents concurrent executions of sync and poll jobs, which would cause race conditions on shared tables.

### Jobs

| Job ID | Schedule | Description |
|--------|----------|-------------|
| `airflow_pipeline_sync` | Every 20 minutes | Discovers pipelines + lineage from Airflow, then polls statuses |
| `airflow_catchup_sync` | Once, 5 minutes after startup | One-shot catch-up in case Airflow wasn't ready at boot |
| `catalog_sync` | Every 2 hours (first run at +1 hour) | Reads Iceberg table schemas and upserts `pipeline_fields` |

The initial sync at startup (in `main.py`) runs immediately as a background task and is not subject to the scheduler. Jobs added to the scheduler start after their first interval to avoid duplicate work.

### Adding a New Background Task

1. Create `backend/app/tasks/my_task.py` with an async function:

```python
import logging
from app.database import async_session_factory

logger = logging.getLogger(__name__)

async def run_my_task() -> None:
    logger.info("Starting my task")
    try:
        async with async_session_factory() as session:
            # do work
            pass
    except Exception:
        logger.exception("My task failed")
```

2. Register the job in `setup_scheduler()` in `backend/app/tasks/scheduler.py`:

```python
from app.tasks.my_task import run_my_task

scheduler.add_job(
    run_my_task,
    "interval",
    hours=1,
    id="my_task",
    name="My Scheduled Task",
    replace_existing=True,
    next_run_time=now + timedelta(hours=1),
)
```

Always use a `try/except Exception` block in the task function; exceptions propagate to the scheduler and can suppress future runs if unhandled.

---

## 11. How to Add a New Backend Endpoint

This section walks through a complete example: adding `GET /api/pipelines/{pipeline_id}/tags` to return custom tags for a pipeline.

### Step 1: Add the Database Model (if new table needed)

Add a model in `backend/app/models/tags.py`:

```python
import uuid
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class PipelineTag(Base):
    __tablename__ = "pipeline_tags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), index=True
    )
    tag: Mapped[str] = mapped_column(String(100), index=True)
```

Register the model in `backend/app/models/__init__.py`:

```python
from app.models.tags import PipelineTag  # noqa: F401
```

### Step 2: Create a Migration

```bash
cd backend
uv run alembic revision --autogenerate -m "add_pipeline_tags"
# Review the generated file in alembic/versions/
uv run alembic upgrade head
```

See [Section 13](#13-how-to-add-a-database-migration) for migration conventions.

### Step 3: Create the Pydantic Schema

Add to `backend/app/schemas/` (or a new file `tags.py`):

```python
from pydantic import BaseModel

class TagResponse(BaseModel):
    id: str
    tag: str

class TagsResponse(BaseModel):
    pipeline_id: str
    tags: list[TagResponse]
```

### Step 4: Create the Repository

Create `backend/app/repositories/tag_repo.py`:

```python
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tags import PipelineTag

class TagRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_pipeline_id(self, pipeline_id: uuid.UUID) -> list[PipelineTag]:
        stmt = select(PipelineTag).where(PipelineTag.pipeline_id == pipeline_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

### Step 5: Create the Service

Create `backend/app/services/tag_service.py`:

```python
import uuid
from app.repositories.tag_repo import TagRepository
from app.schemas.tags import TagResponse, TagsResponse

class TagService:
    def __init__(self, tag_repo: TagRepository):
        self.tag_repo = tag_repo

    async def get_pipeline_tags(self, pipeline_id: uuid.UUID) -> TagsResponse:
        tags = await self.tag_repo.get_by_pipeline_id(pipeline_id)
        return TagsResponse(
            pipeline_id=str(pipeline_id),
            tags=[TagResponse(id=str(t.id), tag=t.tag) for t in tags],
        )
```

### Step 6: Register the Dependency Factory

Add to `backend/app/dependencies.py`:

```python
from app.repositories.tag_repo import TagRepository
from app.services.tag_service import TagService

def get_tag_repo(session: AsyncSession = Depends(get_db_session)) -> TagRepository:
    return TagRepository(session)

def get_tag_service(
    tag_repo: TagRepository = Depends(get_tag_repo),
) -> TagService:
    return TagService(tag_repo)
```

### Step 7: Create the Router

Create `backend/app/routers/tags.py`:

```python
import uuid
from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.dependencies import get_tag_service
from app.models.user import User
from app.schemas.tags import TagsResponse
from app.services.tag_service import TagService

router = APIRouter(prefix="/api/pipelines", tags=["tags"])

@router.get("/{pipeline_id}/tags", response_model=TagsResponse)
async def get_pipeline_tags(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TagService = Depends(get_tag_service),
):
    return await service.get_pipeline_tags(pipeline_id)
```

### Step 8: Register the Router in main.py

```python
from app.routers import ..., tags

app.include_router(tags.router)
```

### Step 9: Verify

Navigate to http://localhost:8000/docs to confirm the new endpoint appears in the Swagger UI.

---

## 12. How to Add a New Frontend Feature

This section walks through adding a "Tags" card to the Bento Workspace that displays the pipeline's tags.

### Step 1: Add the TypeScript Type

Create or extend `frontend/src/types/tags.ts`:

```typescript
export interface TagItem {
  id: string;
  tag: string;
}

export interface TagsResponse {
  pipeline_id: string;
  tags: TagItem[];
}
```

### Step 2: Add the API Function

Create `frontend/src/api/tags.ts`:

```typescript
import apiClient from "./client";
import type { TagsResponse } from "@/types/tags";

export async function fetchPipelineTags(pipelineId: string): Promise<TagsResponse> {
  const { data } = await apiClient.get<TagsResponse>(`/pipelines/${pipelineId}/tags`);
  return data;
}
```

### Step 3: Create the TanStack Query Hook

Create `frontend/src/hooks/use-pipeline-tags.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchPipelineTags } from "@/api/tags";

export function usePipelineTags(pipelineId: string | null) {
  return useQuery({
    queryKey: ["pipeline-tags", pipelineId],
    queryFn: () => fetchPipelineTags(pipelineId!),
    enabled: !!pipelineId,
    staleTime: 5 * 60_000,
  });
}
```

The `enabled: !!pipelineId` guard prevents the query from firing when no pipeline is selected.

### Step 4: Create the Component

Create `frontend/src/components/bento-workspace/TagsCard.tsx`:

```typescript
import { usePipelineTags } from "@/hooks/use-pipeline-tags";

interface Props {
  pipelineId: string;
}

export function TagsCard({ pipelineId }: Props) {
  const { data, isLoading } = usePipelineTags(pipelineId);

  if (isLoading) {
    return <div className="animate-pulse bg-white/5 rounded-2xl h-16" />;
  }

  if (!data || data.tags.length === 0) {
    return null;
  }

  return (
    <div className="rounded-2xl bg-[#18181b] border border-white/5 p-4">
      <p className="text-xs font-mono text-slate-500 uppercase tracking-wide mb-3">Tags</p>
      <div className="flex flex-wrap gap-2">
        {data.tags.map((t) => (
          <span
            key={t.id}
            className="px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 text-xs font-mono"
          >
            {t.tag}
          </span>
        ))}
      </div>
    </div>
  );
}
```

### Step 5: Add the Card to BentoWorkspace

Import and add the card to `BentoWorkspace.tsx` inside the grid:

```typescript
import { TagsCard } from "./TagsCard";

// In the return JSX, inside the grid:
<TagsCard pipelineId={pipeline.id} />
```

### Step 6: If Adding a New Top-Level Tab

1. Add the tab constant to `frontend/src/lib/constants.ts`:

```typescript
export const TABS = {
  // ... existing tabs
  TAGS: "tags",
} as const;
```

2. Add the tab button to `frontend/src/components/layout/Sidebar.tsx`.

3. Add the lazy-loaded view to `App.tsx`:

```typescript
const TagsView = lazy(() =>
  import("@/components/tags/TagsView").then((m) => ({ default: m.TagsView }))
);

// In AppContent:
{activeTab === "tags" && (
  <Suspense fallback={<TabSkeleton />}>
    <TagsView />
  </Suspense>
)}
```

### Step 7: Type-Check

```bash
cd frontend
pnpm tsc --noEmit
```

Fix all TypeScript errors before committing. Do not use `any` as a workaround — define proper types.

---

## 13. How to Add a Database Migration

Alembic migrations are managed in `backend/alembic/versions/`. The project uses a manual naming convention: `NNN_description.py` where `NNN` is zero-padded (e.g., `020_add_pipeline_tags.py`).

### Autogenerate (Recommended for New Tables or Columns)

```bash
cd backend

# Ensure your model is imported in app/models/__init__.py
uv run alembic revision --autogenerate -m "add_pipeline_tags"
```

Review the generated file carefully — autogenerate sometimes produces incorrect `downgrade()` functions for complex changes. Always verify both `upgrade()` and `downgrade()`.

### Manual Migration (For Custom SQL, Indexes, or Constraints)

```bash
cd backend
uv run alembic revision -m "add_composite_index_on_tags"
```

Then edit the generated file manually:

```python
from alembic import op
import sqlalchemy as sa

revision: str = "020_add_pipeline_tags"
down_revision: str = "019_add_grant_level"

def upgrade() -> None:
    op.create_table(
        "pipeline_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("tag", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_tags_pipeline_id", "pipeline_tags", ["pipeline_id"])

def downgrade() -> None:
    op.drop_index("ix_pipeline_tags_pipeline_id")
    op.drop_table("pipeline_tags")
```

### Apply the Migration

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Roll back one step
uv run alembic downgrade -1

# Check current revision
uv run alembic current
```

### Migration Checklist

- The `revision` identifier must match the filename prefix exactly (e.g., `"020_add_pipeline_tags"`).
- `down_revision` must point to the immediately preceding migration.
- Every `upgrade()` must have a matching `downgrade()`.
- If the migration adds a non-nullable column to a table that may already contain data, provide a `server_default` value.
- Alembic auto-runs on backend startup (in Docker Compose, via `uv run alembic upgrade head && exec uvicorn ...`).
- Register new models in `backend/app/models/__init__.py` so Alembic's autogenerate can detect them.

---

## 14. Naming Conventions

### ETL and Task Naming

| Entity | Convention | Example |
|--------|-----------|---------|
| ETL task_id (Airflow) | PascalCase | `SwitchPortCollector` |
| API dummy task | `{Name}Dummy` | `NetworkInsightsApiDummy` |
| Sensor task_id | PascalCase | `BgpRouteChangeDetector` |
| Task group | `{TeamName}{Function}` | `DaggerCollection`, `VaultAnalysis` |

The `_task_id_to_display_name()` helper in `AirflowSyncService` converts both PascalCase and snake_case task IDs to human-readable display names via regex split.

### Teams and DAGs

Five teams own pipelines:

| Team | DAGs |
|------|------|
| Dagger | backbone_core, heartbeat_probe |
| Vault | perimeter_defense |
| Prism | application_mesh |
| Relay | transit_exchange |
| Oasis | noc_sentinel |

Six DAGs exist: `backbone_core`, `perimeter_defense`, `application_mesh`, `transit_exchange`, `heartbeat_probe`, `noc_sentinel`.

### Python (Backend)

- Modules: `snake_case.py`
- Classes: `PascalCase`
- Functions and variables: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE`
- Pydantic models: `PascalCase` (e.g., `PipelineListItem`, `VisibilityGrantRequest`)

### TypeScript (Frontend)

- Files: `kebab-case.ts` / `kebab-case.tsx`
- React components: `PascalCase` function with matching export name
- Hooks: `useCamelCase`
- Stores: `useCamelCaseStore`
- Types and interfaces: `PascalCase`
- API functions: `fetchCamelCase`, `updateCamelCase`, `createCamelCase`

### API Routes

All routes are prefixed with `/api`. Router files declare their own prefixes:

```python
router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])
```

Routes are RESTful: `GET /resource` for lists, `GET /resource/{id}` for detail, `POST /resource` for creation, `PATCH /resource/{id}` for partial update, `DELETE /resource/{id}` for deletion.

Sub-resources use nested paths: `GET /api/pipelines/{id}/lineage`, `GET /api/pipelines/{id}/resources`.

---

## 15. Configuration Reference

All settings are loaded by `backend/app/config.py` via Pydantic Settings from environment variables (case-insensitive). The `DATABASE_URL` variable is always overridden by the Docker Compose `environment` block to ensure the correct internal hostname.

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://etlnexus:etlnexus@db:5432/etlnexus` | Full async DSN |
| `POSTGRES_PASSWORD` | `etlnexus` | Used only in docker-compose; not read by the app directly |

### Airflow Integration

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRFLOW_BASE_URL` | `http://airflow-webserver:8080/api/v1` | Airflow REST API v1 base URL |
| `AIRFLOW_USERNAME` | `admin` | Basic auth username |
| `AIRFLOW_PASSWORD` | `admin` | Basic auth password |
| `AIRFLOW_POLL_INTERVAL_MINUTES` | `20` | How often to sync pipelines and poll statuses |

### Iceberg Catalog

| Variable | Default | Description |
|----------|---------|-------------|
| `ICEBERG_CATALOG_URI` | `http://iceberg-rest:8181` | Iceberg REST catalog URL |
| `ICEBERG_NAMESPACE_PREFIX` | `dagger` | Only tables under this namespace prefix are synced |

### LLM / AI

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_BASE_URL` | `""` | OpenAPI-compatible endpoint base URL |
| `LLM_API_KEY` | `""` | API key (sent as Bearer token) |
| `LLM_MODEL` | `default` | Model name passed in the request body |
| `LLM_MAX_TOKENS` | `1024` | Maximum tokens in LLM response |

### Spark Cluster Capacity

These values are used to compute utilization percentages in the Resource Performance card. They should reflect the actual capacity of the cluster the Airflow workers run on.

| Variable | Default | Description |
|----------|---------|-------------|
| `SPARK_MAX_DRIVER_MEMORY_GB` | `16` | Total driver memory available |
| `SPARK_MAX_EXECUTOR_MEMORY_GB` | `64` | Total executor memory available |
| `SPARK_MAX_EXECUTOR_CORES` | `32` | Total executor cores available |
| `SPARK_MAX_TOTAL_EXECUTORS` | `20` | Maximum number of executors |

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins (JSON list or comma-separated) |
| `DEBUG` | `false` | Enables `DEBUG` log level when `true` |

### SSO / OIDC

| Variable | Default | Description |
|----------|---------|-------------|
| `SSO_ENABLED` | `false` | Master switch for SSO. When `false`, all requests use a default admin user. |
| `SSO_ISSUER_URL` | `http://keycloak:8090/realms/etlnexus` | Internal issuer URL (used by backend for JWKS fetch) |
| `SSO_PUBLIC_ISSUER_URL` | `http://localhost:8090/realms/etlnexus` | Public issuer URL (sent to frontend; also accepted in JWT `iss` claim) |
| `SSO_CLIENT_ID` | `etlnexus-app` | OIDC client ID |
| `SSO_AUDIENCE` | `etlnexus-app` | Expected `aud` claim in JWTs |
| `SSO_GROUPS_CLAIM` | `groups` | JWT claim path for group memberships |
| `SSO_ROLE_CLAIM` | `realm_access.roles` | Dot-separated JWT claim path for roles |
| `SSO_ADMIN_ROLE` | `admin` | Role string that grants admin privileges |

The dual issuer URL design (`SSO_ISSUER_URL` vs `SSO_PUBLIC_ISSUER_URL`) solves a Keycloak quirk: JWTs are minted with the public-facing URL as the `iss` claim, but the backend validates against the internal Docker hostname for JWKS fetching.

---

## 16. Testing Strategy

The project does not currently have an automated test suite. This section describes the recommended testing approach for contributors.

### Backend Testing

**Recommended framework:** `pytest` with `pytest-asyncio` and `httpx.AsyncClient`.

#### Unit Tests (Services and Repositories)

Services should be tested with mock repositories:

```python
import pytest
from unittest.mock import AsyncMock
from app.services.pipeline_service import PipelineService

@pytest.mark.asyncio
async def test_list_pipelines_returns_empty_for_no_data():
    mock_pipeline_repo = AsyncMock()
    mock_pipeline_repo.list_visible.return_value = []
    mock_pipeline_repo.get_success_rates.return_value = {}
    mock_lineage_repo = AsyncMock()

    service = PipelineService(mock_pipeline_repo, mock_lineage_repo)
    result = await service.list_pipelines(query=None, user=None)

    assert result == []
    mock_pipeline_repo.list_visible.assert_called_once()
```

#### Integration Tests (HTTP Endpoints)

Use `httpx.AsyncClient` with `transport=ASGITransport` to test endpoints against a real database:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    assert "status" in response.json()
```

#### Install Test Dependencies

```bash
cd backend
uv add --dev pytest pytest-asyncio
uv run pytest
```

### Frontend Testing

**Recommended framework:** Vitest with React Testing Library.

```bash
cd frontend
pnpm add -D vitest @testing-library/react @testing-library/user-event jsdom
```

Focus tests on:
- Hook logic (mock the API layer with `msw`).
- Store actions and selectors.
- Complex utility functions in `lib/`.

### Manual Testing Checklist

Before submitting a change, verify the following manually:

- [ ] `pnpm tsc --noEmit` passes with no TypeScript errors.
- [ ] The backend starts without errors (`docker compose up backend`).
- [ ] The new or changed endpoint returns the correct shape at http://localhost:8000/docs.
- [ ] The UI renders without console errors.
- [ ] The feature works with SSO disabled (default local dev).
- [ ] The feature works with SSO enabled (log in as alice, bob, charlie, diana and verify team-scoped visibility is respected).
- [ ] Admin-only features return HTTP 403 for non-admin users.
- [ ] `docker compose down && docker compose up` (clean state) still works.

### Critical Rules for Contributions

These rules are enforced via code review and must not be violated:

1. **Never create mock data or simplified components.** If a component does not work, debug the root cause. Do not replace it with a stub.
2. **Never replace existing complex components with simplified versions.**
3. **Never use Redux.** Zustand is the only allowed client state library.
4. **Never introduce `any` types in TypeScript** without an explicit justification comment.
5. **Always check `DOCS/` before making structural changes** to ensure consistency with existing architecture decisions.

---

## 17. Deployment Guide

### Production Stack

The production compose file (`docker-compose.prod.yml`) contains only three services: `db`, `backend`, and `frontend`. It does not include Airflow, Keycloak, or Iceberg — those are expected to be pre-existing infrastructure.

```bash
# Create the production env file
cp .env.example .env.prod
# Edit .env.prod with your production values

# Build and start
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f backend
```

### Required Production Environment Variables

At minimum, set these in `.env.prod`:

```bash
POSTGRES_PASSWORD=<strong-random-password>
AIRFLOW_BASE_URL=https://your-airflow-host/api/v1
AIRFLOW_USERNAME=<airflow-user>
AIRFLOW_PASSWORD=<airflow-password>
ICEBERG_CATALOG_URI=https://your-iceberg-host
LLM_API_BASE_URL=https://your-llm-endpoint
LLM_API_KEY=<your-key>
LLM_MODEL=<model-name>
CORS_ORIGINS=["https://your-frontend-domain"]
SSO_ENABLED=true
SSO_ISSUER_URL=http://keycloak-internal:8080/realms/etlnexus
SSO_PUBLIC_ISSUER_URL=https://auth.your-domain.com/realms/etlnexus
SSO_CLIENT_ID=etlnexus-app
SSO_AUDIENCE=etlnexus-app
```

### Container Architecture

**Backend container** (`backend/Dockerfile`):
- Base: `python:3.12-slim` with `default-jre-headless` (Java 17, required by PySpark).
- Runs as non-root user `appuser` (uid 1000).
- On startup: `uv run alembic upgrade head` then `uvicorn`.
- Memory limit in production: 2 GB.

**Frontend container** (`frontend/Dockerfile`):
- Multi-stage: Node 20 Alpine builds the Vite bundle, then Nginx Alpine serves it.
- `nginx.conf` handles SPA routing (`try_files ... /index.html`) and reverse-proxies `/api/` to `http://backend:8000/api/`.
- Static assets are cached for 1 year (`/assets/`); `index.html` is `no-cache`.
- Memory limit in production: 256 MB.

### Upgrading the Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart with zero-downtime approach
docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Alembic migrations run automatically on backend startup. Downtime is limited to the container restart window (typically under 10 seconds).

### Monitoring

Check service health via the health endpoint:

```bash
curl https://your-domain.com/api/health
# Returns: {"status": "healthy", "services": {"database": "connected", "airflow": "connected", "iceberg": "connected"}}
```

Backend logs stream in JSON format by default. Set `DEBUG=true` in the env file for verbose output during incident investigation, but revert afterwards to avoid log volume overhead.

### Database Backup

```bash
# Backup
docker exec <db-container> pg_dump -U etlnexus etlnexus | gzip > backup-$(date +%Y%m%d).sql.gz

# Restore
gunzip -c backup-20260101.sql.gz | docker exec -i <db-container> psql -U etlnexus etlnexus
```

---

## 18. Troubleshooting

### Backend Won't Start

**Symptom:** Backend container exits immediately.

**Check logs:**
```bash
docker compose logs backend
```

**Common causes:**

| Symptom in log | Fix |
|----------------|-----|
| `asyncpg.exceptions.ConnectionDoesNotExistError` | The `db` container is not healthy. Wait for `pg_isready` or run `docker compose up db --wait`. |
| `alembic.util.exc.CommandError: Can't locate revision` | The migration chain is broken. Run `uv run alembic heads` to see all heads; there should be exactly one. |
| `ImportError: No module named 'pyspark'` | Dependencies not installed. Run `uv sync` or rebuild the Docker image. |
| `ValueError: Unsafe iceberg_namespace_prefix` | `ICEBERG_NAMESPACE_PREFIX` contains characters outside `[a-zA-Z0-9_.]`. |

### Airflow Sync Returns Zero Pipelines

**Symptom:** The pipeline registry shows no pipelines after startup.

**Checklist:**
1. Is Airflow reachable? `curl http://localhost:8080/api/v1/health` — should return `{"metadatabase": {"status": "healthy"}, ...}`.
2. Are DAGs enabled? In Airflow UI, check that DAGs are not paused.
3. Have the DAGs been triggered at least once? The sync reads task instances from the most recent run; if no run exists, there are no instances to read.
4. Check backend logs for `Skipping task ... — no etl_name in op_kwargs` messages — this indicates tasks exist but lack the expected metadata.

### Iceberg Schema Sync Not Working

**Symptom:** Pipeline fields are empty even though Iceberg tables exist.

**Checklist:**
1. Check if the Iceberg REST catalog is healthy: `curl http://localhost:8181/v1/config`.
2. Verify the `ICEBERG_NAMESPACE_PREFIX` matches the actual namespace (default: `dagger`).
3. PySpark initialization takes ~30–60 seconds on first run. Look for `SparkSession created for Iceberg catalog` in the backend logs.
4. Iceberg tables must contain data for PySpark to read the schema. The `iceberg-data-seed` container populates seed data; ensure it completed successfully: `docker compose ps iceberg-data-seed`.

### SSO Login Loop

**Symptom:** After logging in at Keycloak, the app redirects back to the login page.

**Checklist:**
1. Verify `SSO_PUBLIC_ISSUER_URL` matches the URL in the browser's address bar when hitting Keycloak (they must be identical to pass the `iss` claim check).
2. Check that `SSO_CLIENT_ID` matches the client configured in the Keycloak realm.
3. Inspect the browser's network tab for the `/api/auth/me` request. A `401` with `"Invalid token"` indicates a JWKS or issuer mismatch.
4. Look for `JWT validation failed:` in the backend logs for detailed error messages.

### Frontend Shows Stale Data After Manual DB Changes

The application caches pipeline data for 30–60 seconds and does not subscribe to database change events. After a direct database change, either:
- Wait for the cache TTL to expire.
- Or trigger a manual sync: `POST /api/pipelines/{id}/sync` for a single pipeline.
- Or restart the backend to clear all in-memory caches.

### TypeScript Build Fails

```bash
cd frontend
pnpm tsc --noEmit 2>&1 | head -50
```

The most common causes are:
- Missing type import after adding a new type file.
- `null | undefined` not handled on optional fields.
- TanStack Query `data` accessed without the `enabled` guard (it will be `undefined` when the query is disabled).

### Database Migration Conflict

If two developers add migrations concurrently, Alembic will detect multiple heads:

```bash
uv run alembic heads
# Shows two head revisions
```

Resolve by editing one migration's `down_revision` to point to the other, creating a linear chain.

### Docker Compose Watch Not Reflecting Changes

`docker compose watch` syncs files but does not restart the container. For backend Python changes, it syncs to `/app/app` and uvicorn's `--reload` restarts the ASGI process. If the change is not reflected:
1. Ensure the change is in `backend/app/` (not `backend/pyproject.toml`, which requires a full rebuild).
2. Check uvicorn's reload log: `docker compose logs -f backend`.
3. For `pyproject.toml` changes: `docker compose build backend && docker compose up backend -d`.

### Keycloak Not Starting

Keycloak 26.2 can take 60–90 seconds to start in development mode. The `--import-realm` flag imports the `etlnexus-realm.json` file on first boot. If it fails:

```bash
docker compose logs keycloak | tail -50
```

A `WARN` about realm already existing is harmless. Actual failures are usually port conflicts (8090 in use) or insufficient memory.

---

*This guide reflects the codebase state on branch `feature/sso-teams-rbac`. For questions or corrections, update this file in the same commit as the code change it documents.*
