# ETL Explorer Hub — Backend

The ETL Explorer Hub backend is a FastAPI application that serves as the data architecture command center API for discovering, understanding, and utilizing ETL pipelines. It discovers pipeline metadata exclusively from Airflow — no git cloning — and exposes a REST API consumed by the React frontend.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [API Endpoints](#api-endpoints)
4. [Authentication and Authorization](#authentication-and-authorization)
5. [Services](#services)
6. [Background Tasks](#background-tasks)
7. [Database](#database)
8. [Integration Clients](#integration-clients)
9. [Caching](#caching)
10. [Rate Limiting](#rate-limiting)
11. [Testing](#testing)
12. [Development](#development)
13. [Configuration](#configuration)

---

## Overview

The backend provides:

- **Pipeline Registry** — searchable list of ETL pipelines discovered from Airflow task definitions, with team ownership, Airflow run status, and Iceberg schema fields
- **Lineage and Topology** — data flow graphs (reads_from / writes_to edges) and DAG dependency traversal
- **Bento Workspace** — per-pipeline detail: schema structure, Spark resource metrics, execution plan trees, revision history, and documentation
- **Schema Matrix** — cross-pipeline field frequency and entity mapping aggregated from Iceberg catalog
- **AI Architect Terminal** — goal-oriented natural language queries against the catalog via an OpenAPI-compatible LLM endpoint
- **Admin Panel** — user management, team overview, and visibility grant management (admin-only)

All pipeline metadata originates from Airflow task instances. The `AirflowSyncService` reads `rendered_fields`, `op_kwargs`, task group hierarchy, and task logs to derive pipelines, lineage, resource configs, and Spark execution plans.

---

## Architecture

### Three-Layer Pattern

```
HTTP Request
     |
     v
+----------+     FastAPI router, path/query parameter parsing,
|  Router  |     HTTP status codes, rate limiting decorators
+----------+
     |
     v
+---------+      Business logic, caching, cross-repo orchestration,
| Service |      data assembly and transformation
+---------+
     |
     v
+------------+   Async SQLAlchemy queries, upserts, joins,
| Repository |   visibility filtering
+------------+
     |
     v
  PostgreSQL 16
```

Dependency injection is handled by FastAPI `Depends`. Each request receives its own `AsyncSession` via `get_db_session`. Integration clients (`airflow_client`, `llm_client`, `spark_connect_client`, `oidc_client`) are module-level singletons initialized once at application startup.

### Application Startup Sequence

1. `oidc_client.initialize()` — fetch OIDC well-known config and initial JWKS (no-op when `SSO_ENABLED=false`)
2. `run_startup_sync()` launched as a background asyncio task — waits up to 5 minutes for Airflow health, then runs the full sync sequence: pipeline discovery, bouncer volume seeding, usage seeding, catalog mirror refresh, and status poll
3. `setup_scheduler()` — starts APScheduler with three recurring jobs

### Directory Structure

```
backend/
  app/
    routers/        HTTP layer — 17 router modules
    services/       Business logic — 16 service classes
    repositories/   Data access — 14 repository classes
    models/         SQLAlchemy ORM — 14 model files
    schemas/        Pydantic request/response DTOs
    integrations/   External clients (Airflow, Iceberg, LLM, OIDC)
    parsers/        Log parsing utilities
    tasks/          APScheduler background tasks + seed scripts
    auth.py         JWT validation, dependency factories
    cache.py        TTLCache singletons
    config.py       Pydantic Settings
    database.py     Async engine and session factory
    rate_limit.py   SlowAPI limiter instance
  alembic/
    versions/       29 migration files (001 – 029)
  tests/            424 tests across 27 test files
  pyproject.toml
  alembic.ini
```

---

## API Endpoints

All endpoints require a valid Bearer JWT except `GET /api/health` and `GET /api/auth/config`. The interactive documentation is available at `/api/docs` (Swagger UI) and `/api/redoc` (ReDoc).

### Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/auth/config` | Public | Returns OIDC configuration (SSO enabled, issuer URL, client ID) for frontend bootstrap |
| GET | `/api/auth/me` | Required | Returns the current authenticated user with team memberships |

### Pipelines

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/pipelines` | Required | List pipelines — filterable by search query (`q`), date range (`date_from`/`date_to`), paginated; visibility-scoped per user |
| GET | `/api/pipelines/{pipeline_id}` | Required | Full pipeline detail with fields, lineage summary, resource config, and edit-permission flag |
| PATCH | `/api/pipelines/{pipeline_id}` | Team member or editor grant | Update pipeline description and/or documentation; records revision |
| POST | `/api/pipelines/{pipeline_id}/sync` | Team member | Trigger an on-demand Airflow sync for a single pipeline (rate limited: 30/min) |
| GET | `/api/pipelines/{pipeline_id}/revisions` | Required | List edit history for a pipeline, filterable by `field` (description \| documentation) |
| POST | `/api/pipelines/{pipeline_id}/revisions/{revision_id}/restore` | Team member or editor grant | Restore a previous revision of description or documentation |
| GET | `/api/pipelines/{pipeline_id}/joins` | Required | Schema-based join suggestions — fields shared with other visible pipelines |

### Lineage

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/pipelines/{pipeline_id}/lineage` | Required | Returns a graph of source nodes (reads_from) and target nodes (writes_to) with typed edges |

### Topology

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/pipelines/{pipeline_id}/topology` | Required | Direct dependency topology within the DAG — tasks this pipeline needs and tasks that need it; filterable by `dag_id` |
| GET | `/api/pipelines/{pipeline_id}/topology/upstream` | Required | Full recursive upstream dependency subgraph via BFS through `needs`/`prefers` relationships; filterable by `dag_id` |

### Resources and Execution Plans

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/pipelines/{pipeline_id}/resources` | Required | Spark resource metrics — allocated config, run history with actual usage, capacity utilization bars; filterable by date range |
| GET | `/api/pipelines/{pipeline_id}/execution-plan` | Required | Spark physical execution plan tree from the most recent (or a specific) run; returns 404 when no plan exists |
| GET | `/api/pipelines/{pipeline_id}/execution-plan/runs` | Required | List of runs that have recorded execution plans, paginated |

### Bouncers

Bouncers are data-ingestion root tasks (task IDs containing `"Bouncer"`) discovered from Airflow.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/bouncers` | Required | List all bouncers with volume and status; filterable by `team` |
| GET | `/api/bouncers/topology` | Required | Given a list of bouncer names, return the union or intersection of downstream pipelines they feed |

### Schema Matrix

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/schema-matrix` | Required | Cross-pipeline field frequency matrix — field names, their data types, and the pipelines each field appears in; cached 60 s |

### Usage and Consumers

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/usage/{etl_name}` | Required | Pipeline usage record keyed by ETL name — access count, last accessed, filterable by date range |
| GET | `/api/consumers/{etl_name}` | Required | Downstream consumers — pipelines that depend on this ETL's output, with current status |

### DAG Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/dags/summary` | Required | DAG-level statistics: task counts, success/failure rates, resource totals; filterable by date range |

### Airflow Status

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/airflow/status` | Required | Latest task run status for all pipelines; includes `airflow_connected` flag |
| GET | `/api/airflow/status/{pipeline_id}` | Required | Latest task run status for a single pipeline |

### AI Chat

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/ai/chat` | Required | Send a message to the AI architect with full catalog context (rate limited: 60/min) |
| GET | `/api/pipelines/{pipeline_id}/joins/ai` | Required | AI-generated join insights for a specific pipeline |

### Teams

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/teams` | Required | List all teams with member counts |
| GET | `/api/teams/{team_id}` | Team member or admin | Team details with full member list (restricted to same-team members and admins) |
| GET | `/api/teams/{team_id}/pipelines` | Team member or admin | Pipelines owned by this team |

### Users (Admin Only)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/users` | Admin | List all users with team memberships, paginated |
| PATCH | `/api/users/{user_id}/role` | Admin | Change a user's global role (admin/member/viewer); prevents self-demotion and demotion of the last admin |
| PATCH | `/api/users/{user_id}/active` | Admin | Activate or deactivate a user account; prevents self-deactivation |

### Visibility Grants (Admin Only)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/visibility/grants` | Admin | List all visibility grants with grantee and target information, paginated |
| POST | `/api/visibility/grants` | Admin | Create a grant — exactly one of `pipeline_id` / `source_team_id` as target, exactly one of `grantee_team_id` / `grantee_user_id` as recipient |
| DELETE | `/api/visibility/grants/{grant_id}` | Admin | Revoke a grant |

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | Public | Checks database connectivity, Airflow health, and Iceberg connection; excluded from request logging |

---

## Authentication and Authorization

### SSO Flow (Keycloak OIDC)

When `SSO_ENABLED=true` the following sequence applies on every authenticated request:

```
Client                  Backend                    Keycloak
  |                        |                           |
  |-- Bearer JWT --------> |                           |
  |                        |-- fetch JWKS (cached) --> |
  |                        |<-- signing keys ----------|
  |                        |                           |
  |                        | validate JWT signature,
  |                        | expiry, issuer, audience
  |                        |
  |                        | upsert_from_claims()
  |                        |   - find/create User by sub
  |                        |   - sync role from realm_access.roles
  |                        |   - sync team memberships from groups claim
  |                        |
  |<-- 200 + response ---- |
```

When `SSO_ENABLED=false` (default for local development), `get_current_user` returns a stable `default-admin` user without any token validation.

### JIT User Provisioning

`UserAuthService.upsert_from_claims()` runs on every authenticated request (with a 120 s LRU cache keyed by `sub` + SHA-256 hash of role/group claims to avoid per-request DB round trips). It:

1. Looks up the user by OIDC `sub` claim
2. Creates the user record if it does not exist (JIT provisioning)
3. Synchronizes `email`, `display_name`, and `role` from JWT claims
4. Reconciles team memberships against the `groups` claim — adds missing memberships and removes stale ones

### Auth Dependencies

Four dependency functions are available for use in router handlers:

| Dependency | Behaviour |
|------------|-----------|
| `get_current_user` | Validates Bearer JWT (or returns default admin); raises `HTTP 401` if credentials are absent when SSO is enabled |
| `get_current_user_optional` | Same but returns `None` instead of raising |
| `require_role(*roles)` | Factory — raises `HTTP 403` if `user.role` is not in the provided roles list |
| `require_team_membership(pipeline_id_param)` | Factory — raises `HTTP 403` if the user does not belong to the team that owns the referenced pipeline (admins bypass; unassigned pipelines allow all) |
| `require_team_membership_or_editor_grant(pipeline_id_param)` | Like above but also allows users who hold an editor-level `VisibilityGrant` for that pipeline or its owning team |

### RBAC Roles

| Role | Capabilities |
|------|-------------|
| `admin` | Full access to all endpoints, including user management and visibility grants. Bypasses all team-membership checks. Cannot be self-demoted. |
| `member` | Read and edit access to own team's pipelines and any pipelines/teams explicitly granted. Cannot access admin endpoints. |
| `viewer` | Read-only access to own team's pipelines and granted pipelines. The `require_team_membership` check will block mutation even on granted pipelines (editors are added via `require_team_membership_or_editor_grant`). |

The role is stored in the `users.role` column with a `CHECK` constraint enforcing `IN ('admin', 'member', 'viewer')`.

### Visibility Model

A non-admin user sees pipelines that satisfy any of:

1. The pipeline's `team_id` matches one of the user's team memberships
2. The pipeline has no `team_id` (unassigned — globally visible)
3. A `VisibilityGrant` exists with `pipeline_id` matching this pipeline and `grantee_team_id`/`grantee_user_id` matching the user
4. A `VisibilityGrant` exists with `source_team_id` matching the pipeline's owning team and `grantee_team_id`/`grantee_user_id` matching the user

Grant levels are `viewer` (read-only) and `editor` (read plus PATCH/sync). The `VisibilityGrant` table enforces mutually exclusive target and recipient columns via database `CHECK` constraints and a composite `UNIQUE` constraint.

### JWKS Caching and Key Rotation

The `OIDCClient` maintains an in-memory JWKS cache with a 6-hour TTL. Dual issuer URL support is provided: `SSO_ISSUER_URL` (internal Docker DNS for container startup) and `SSO_PUBLIC_ISSUER_URL` (public URL used to validate the `iss` claim in incoming tokens). When a JWT presents an unknown `kid`, the cache is refreshed once with a 30-second cooldown before failing, enabling transparent handling of Keycloak key rotation.

---

## Services

| Service | Description |
|---------|-------------|
| `AIService` | Builds a catalog context prompt (all pipeline names and fields) and forwards chat messages to the LLM client; also generates pipeline-specific join insights |
| `AirflowService` | Polls Airflow task run statuses, parses `ETL_RESOURCE_ACTUAL:` and `ETL_EXECUTION_PLAN:` markers from task logs, and writes to `airflow_run_statuses` and `pipeline_run_history` |
| `AirflowSyncService` | Discovers pipelines and lineage from Airflow task metadata; auto-discovers all tasks by `task_id`; classifies bouncers (`"Bouncer" in task_id`); derives category from TaskGroup; parses `needs`/`prefers` from `params` for lineage; reads descriptions from `ETL_DESCRIPTION:` / `BOUNCER_DESCRIPTION:` log markers |
| `BouncerService` | Lists bouncers from the `bouncers` table with optional team filtering; builds union/intersection topology of downstream pipelines for a given set of bouncers |
| `CatalogSyncService` | Uses `SparkConnectClient` to enumerate tables under the configured namespace prefix; upserts each table as a pipeline and synchronizes its fields (name, type, ordinal position) from the Iceberg schema |
| `ConsumerService` | Finds downstream pipelines that reference this ETL's task ID in their `needs`/`prefers` params, enriched with current Airflow status from the DB |
| `DagSummaryService` | Aggregates per-DAG statistics from `dag_tasks`, `airflow_run_statuses`, and `pipeline_run_history`; queries Airflow directly for live DAG schedule information; cached 60 s |
| `PipelineService` | Core pipeline listing (with visibility-scoped query and TTL caching), detail assembly, metadata update with revision recording, revision restore, and schema-based join suggestion generation |
| `ResourceService` | Assembles `ResourceMetricsResponse` from `pipeline_resource_configs` and `pipeline_run_history`; calculates capacity utilization bars against cluster limits; retrieves Spark execution plan trees |
| `SchemaMatrixService` | Reads field frequency aggregations from `FieldFrequencyRepository` and assembles the cross-pipeline schema matrix; cached 60 s |
| `TeamService` | Lists and retrieves teams with eager-loaded members; enforces access restriction so only admins and same-team members can view full team detail |
| `TopologyService` | Builds direct dependency `TopologyGraph` and recursive upstream `UpstreamTopologyGraph` from cached `dag_tasks` data using BFS traversal through `needs`/`prefers` relationships |
| `UsageService` | Returns usage records keyed by ETL name with date-range filtering; enriches with consumer discovery from DAG task data |
| `UserAuthService` | JIT user provisioning, SSO claims reconciliation, and role/team synchronization; maintains a 120 s LRU provision cache (max 500 entries) to reduce DB round trips |
| `VisibilityService` | Creates, lists, and deletes visibility grants; validates the mutually exclusive target/recipient constraint before delegating to the repository |
| `sync/task_classifier` | Utility module (not a class) with pure functions for Airflow sync: `is_bouncer`, `is_api`, `extract_team_from_task_group`, `extract_category_from_task_group`, `extract_dag_schedule`, `unwrap_params`, `task_id_to_display_name` |

---

## Background Tasks

All background tasks use APScheduler's `AsyncIOScheduler`. Separate asyncio locks prevent concurrent executions of the sync and poll jobs. Each lock is non-blocking — if a job is already running, the new invocation logs a skip message and returns immediately.

| Job ID | Name | Interval | Description |
|--------|------|----------|-------------|
| `airflow_pipeline_sync` | Airflow Pipeline Discovery | Every 20 min (configurable via `AIRFLOW_POLL_INTERVAL_MINUTES`) | Discovers pipelines, lineage, team assignments, bouncer metadata, and resource configs from Airflow task definitions |
| `airflow_status_poll` | Airflow Status Poll | Every 20 min (offset +2 min from sync) | Polls task run statuses, parses actual resource usage and execution plans from task logs |
| `spark_catalog_mirror` | Spark Connect Catalog Mirror | Every `CATALOG_MIRROR_INTERVAL_SECONDS` (default 30s) | Reads Iceberg schemas from Spark Connect into the `catalog_columns` mirror table (only live Spark caller), then projects them onto `pipeline_fields` in-DB. Guarded against overlapping runs |

All caches are cleared via `cache.clear_all()` at the end of every sync and poll cycle.

### Startup Sync

`run_startup_sync()` runs once at application startup inside `_sync_lock`. It:

1. Waits for Airflow health — up to `AIRFLOW_STARTUP_MAX_ATTEMPTS` × `AIRFLOW_STARTUP_RETRY_SECONDS` (default: 20 × 15 s = 5 minutes)
2. Runs `sync_pipelines_from_airflow()`
3. Runs `seed_bouncer_volumes()` and `seed_usage_data()` (idempotent seed tasks)
4. Runs `sync_from_catalog()`
5. If pipeline sync succeeded, runs `poll_airflow_statuses()`
6. Clears all caches

Each step has independent exception handling so a failure in one step does not abort subsequent steps.

---

## Database

### Technology

- PostgreSQL 16
- async SQLAlchemy 2.0 with `asyncpg` driver
- Alembic for schema migrations (29 migrations, `001` through `029`)

### Models

| Model | Table | Description |
|-------|-------|-------------|
| `Pipeline` | `pipelines` | Core pipeline record — name, task_id, description, category, schedule, documentation, team FK, revision tracking flags |
| `PipelineField` | `pipeline_fields` | Schema fields synced from Iceberg — name, data_type, ordinal_position; cascade-deleted with pipeline |
| `LineageEdge` | `lineage_edges` | Directed data flow edges — source and target pipeline FKs, source/target table strings, edge type (`reads_from` \| `writes_to`) |
| `AirflowRunStatus` | `airflow_run_statuses` | Latest task run status per pipeline — one-to-one with pipeline; status, execution_date, last_checked_at |
| `PipelineResourceConfig` | `pipeline_resource_configs` | Allocated Spark resources per pipeline per DAG — unique constraint on (pipeline_id, dag_id) |
| `PipelineRunHistory` | `pipeline_run_history` | Per-run performance data — duration, actual resource usage, 15 sparkMeasure metric columns, execution plan text; unique constraint on (pipeline_id, dag_id, dag_run_id) |
| `PipelineRevision` | `pipeline_revisions` | Revision history for description and documentation fields — field_name, content, changed_by, change_source |
| `PipelineUsage` | `pipeline_usages` | Usage enrichment keyed by `etl_name` (String) — consumer_name, usage_type, access_count, last_accessed_at |
| `Bouncer` | `bouncers` | Data-ingestion root tasks — bouncer_name, display_name, team, volume_per_day, status, dag_ids (JSON) |
| `DagTask` | `dag_tasks` | Cached Airflow task graph — dag_id, task_id, pipeline FK, downstream_task_ids, needs, prefers, task_group_id, bouncer FK; unique on (dag_id, task_id) |
| `Team` | `teams` | Organizational team — name (unique), description, source |
| `User` | `users` | SSO user — sub (unique), email (unique), display_name, role with CHECK constraint, is_active |
| `UserTeam` | `user_teams` | Many-to-many junction between users and teams — role_in_team |
| `VisibilityGrant` | `visibility_grants` | Cross-team access grants — CHECK constraints ensure exactly one target (pipeline_id XOR source_team_id) and exactly one recipient (grantee_team_id XOR grantee_user_id); grant_level CHECK enforces `viewer` \| `editor`; unique constraint on (grantee_team_id, grantee_user_id, pipeline_id, source_team_id) |

### Key Relationships

```
Team ──< UserTeam >── User
 |
 | (team_id FK, SET NULL)
 v
Pipeline ──< PipelineField
    |──< LineageEdge (source_pipeline_id)
    |──< LineageEdge (target_pipeline_id)
    |── AirflowRunStatus (one-to-one)
    |──< PipelineResourceConfig
    |──< PipelineRunHistory
    |──< PipelineRevision
    |── DagTask (pipeline_id FK)

VisibilityGrant ── grantee_team_id → Team
                ── grantee_user_id → User
                ── pipeline_id → Pipeline
                ── source_team_id → Team

DagTask ── bouncer_id → Bouncer
```

### Notable Schema Details

- `pipelines.team` is a denormalized cache of the team name to avoid a join on every list query; it is always set atomically alongside `team_id` by `PipelineRepository.set_team()`
- `pipeline_run_history` carries 15 sparkMeasure metric columns added in migration 012 (executor run time, CPU time, GC time, shuffle bytes, input/output bytes, memory spilled, etc.) plus an `execution_plan` TEXT column added in migration 013
- Trigram GIN indexes on `pipelines.name` and `pipeline_fields.name` (migration 025) support full-text search with `ILIKE` patterns
- All timestamp columns use `timezone=True` (migrations 023 and 024 retrofitted earlier columns)

### Running Migrations

```bash
cd backend
uv run alembic upgrade head          # apply all migrations
uv run alembic revision --autogenerate -m "description"  # create a new migration
uv run alembic downgrade -1          # roll back one migration
```

---

## Integration Clients

### Airflow Client (`app/integrations/airflow_client.py`)

Uses a persistent `httpx.AsyncClient` with a connection pool (`max_connections=10`, `max_keepalive_connections=5`, `keepalive_expiry=30 s`) to reuse TCP connections across requests. All requests use HTTP Basic authentication against the Airflow REST API v1. Requests retry once on failure. A `TTLCache` with a 300 s TTL (configurable via `CACHE_TTL_AIRFLOW`) caches responses to avoid repeated calls during sync. The client tracks `is_connected` state for the health endpoint. A semaphore (`AIRFLOW_SEMAPHORE_LIMIT`, default 6) limits concurrent Airflow calls during sync to stay within the connection pool. `strip_group_prefix()` normalizes task IDs by stripping the `{group_id}.` prefix that Airflow prepends when `prefix_group_id=True`.

### Spark Connect Client (`app/integrations/spark_connect_client.py`)

Connects to a remote **Spark Connect** server (`SPARK_CONNECT_URL`, e.g. `sc://spark-connect:15002`) to discover Iceberg table schemas — no Iceberg REST catalog and no local JVM required. The remote `SparkSession` is created lazily on first use and reused thereafter. It enumerates namespaces matching the configured `SPARK_NAMESPACE_PREFIX` (default: `dagger,prism,vault,oasis`) within the `SPARK_CATALOG_NAME` catalog (default: `iceberg`) and reads each table's schema via `spark.table("catalog.db.table").schema`. Identifier validation prevents Spark SQL injection. The client's `stop()` method is called during application shutdown to release the session.

### LLM Client (`app/integrations/llm_client.py`)

An OpenAPI-compatible client (compatible with OpenAI Chat Completions format) using `httpx` with a 30-second timeout and a small connection pool (`max_connections=5`). The client is created lazily on first use. When `LLM_API_BASE_URL` is not configured, all chat methods return a graceful error message rather than raising. The system prompt includes the full pipeline catalog context assembled by `AIService`.

### OIDC Client (`app/integrations/oidc_client.py`)

Validates JWTs issued by Keycloak. On `initialize()`, it fetches the OpenID Connect well-known configuration from `SSO_ISSUER_URL` to discover the JWKS endpoint, then caches the signing keys. JWKS are cached for 6 hours. When a token presents an unknown `kid` (indicating key rotation), the cache is refreshed on demand with a 30-second cooldown. The client is a no-op when `SSO_ENABLED=false`. Dual-issuer support allows the internal Docker URL for startup health checks while the public URL is used for `iss` claim validation.

---

## Caching

The application uses a generic `TTLCache[T]` class (`app/cache.py`) — a plain-dict-backed cache keyed by string with configurable TTL in seconds. Entries are lazily evicted on access. The implementation uses `time.monotonic()` for TTL tracking.

Nine module-level singleton caches serve different domains:

| Cache | TTL | Data |
|-------|-----|------|
| `pipeline_list_cache` | 30 s (`CACHE_TTL_SHORT`) | `list_pipelines` results (unfiltered requests only — search queries bypass cache) |
| `topology_cache` | 30 s | Direct and upstream topology graphs per pipeline + DAG combination |
| `bouncer_topology_cache` | 30 s | Bouncer downstream topology per request signature |
| `grant_level_cache` | 30 s | Per-user editor-grant check results per pipeline |
| `schema_matrix_cache` | 60 s (`CACHE_TTL_MEDIUM`) | Schema matrix response per skip/limit |
| `dag_summary_cache` | 60 s | DAG summary statistics |
| `bouncer_cache` | 60 s | Bouncer list per team filter |
| `join_suggestions_cache` | 60 s | Join suggestions per pipeline |
| `task_id_map_cache` | 30 s | Lightweight task_id-to-pipeline summary lookup |

`cache.clear_all()` invalidates all caches atomically and is called at the end of every background sync and poll cycle, ensuring users see fresh data within one page load after a sync completes. The Airflow client also maintains its own internal TTL cache (300 s) for Airflow API responses.

The `UserAuthService` maintains a separate provision cache for SSO user lookups — an `OrderedDict`-based LRU cache (max 500 entries, 120 s TTL) that evicts stale entries on overflow to avoid unbounded memory growth.

---

## Rate Limiting

Rate limiting is implemented with `SlowAPI`, which wraps the `limits` library. The limiter is keyed by remote IP address (`get_remote_address`).

| Endpoint | Limit | Rationale |
|----------|-------|-----------|
| All endpoints (default) | 200/minute | Baseline protection against abuse |
| `POST /api/ai/chat` | 60/minute | LLM backend has finite capacity; 60 req/min is generous for interactive use |
| `POST /api/pipelines/{id}/sync` | 30/minute | Prevents hammering Airflow with on-demand sync requests |

When a rate limit is exceeded the response is `HTTP 429 Too Many Requests` with a `Retry-After` header, handled by SlowAPI's built-in `_rate_limit_exceeded_handler`.

---

## Testing

### Summary

- **424 tests** across **27 test files** (`tests/test_*.py`)
- All tests are async (`pytest-asyncio`, `asyncio_mode = "auto"`)
- No live external services required — integration clients are mocked

### Running Tests

```bash
cd backend
uv run pytest                          # run all tests
uv run pytest -x                       # stop on first failure
uv run pytest tests/test_pipeline_service.py   # run a single file
uv run pytest -k "test_visibility"     # run tests matching a pattern
uv run pytest --cov=app --cov-report=term-missing  # with coverage
```

### Test Organization

| Test File | Count | Coverage Area |
|-----------|-------|---------------|
| `test_airflow_sync_helpers.py` | 54 | Sync helper functions, auto-discovery logic, log parsing integration |
| `test_task_classifier.py` | 37 | Pure functions: `is_bouncer`, `is_api`, team/category extraction, schedule parsing |
| `test_integration_expanded.py` | 36 | End-to-end API route tests with mocked services |
| `test_log_parser.py` | 30 | Log marker parsing: `ETL_WRITES_TO:`, `ETL_RESOURCE_ACTUAL:`, `ETL_EXECUTION_PLAN:`, descriptions |
| `test_schemas.py` | 26 | Pydantic schema validation and serialization |
| `test_resource_service.py` | 23 | Resource metrics assembly, capacity bar calculations, execution plan retrieval |
| `test_airflow_client.py` | 20 | HTTP client retry logic, caching, health check, graceful degradation |
| `test_pipeline_service.py` | 18 | Visibility-scoped listing, join suggestion generation, caching behaviour |
| `test_auth.py` | 18 | JWT validation, JIT provisioning, role/team dependency enforcement |
| `test_oidc_client.py` | 16 | JWKS fetching, token validation, key rotation, dual-issuer handling |
| `test_user_auth_service.py` | 15 | Provision cache, claims reconciliation, team sync |
| `test_integration.py` | 15 | Core API route integration tests |
| `test_dag_summary_service.py` | 14 | DAG statistics aggregation |
| `test_bouncer_service.py` | 13 | Bouncer listing, union/intersection topology |
| `test_ai_service.py` | 13 | Catalog context building, LLM chat, join insights |
| `test_topology_service.py` | 12 | Direct topology graph, upstream BFS traversal |
| `test_visibility_service.py` | 10 | Grant creation validation, mutually exclusive constraint checks |
| `test_usage_service.py` | 9 | Consumer discovery, date-range filtering |
| `test_consumer_service.py` | 9 | Downstream pipeline lookup |
| `test_cache.py` | 9 | TTL expiry, clear_all, LRU eviction |
| `test_schema_matrix_service.py` | 7 | Field frequency aggregation, cache behaviour |
| `test_base_repo.py` | 6 | Base repository query patterns |
| `test_catalog_sync_service.py` | 5 | Iceberg schema upsert logic |
| `test_auth_schema_helpers.py` | 5 | Auth Pydantic schema helpers |
| `test_team_service.py` | 4 | Team listing, access restriction |

---

## Development

### Prerequisites

- Python 3.12
- `uv` package manager
- PostgreSQL 16 (or Docker Compose for the full stack)

### Local Commands

```bash
cd backend

# Install dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the dev server (hot reload)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app --cov-report=term-missing

# Type-check and lint
uv run ruff check app/
uv run ruff format app/

# Create a new migration
uv run alembic revision --autogenerate -m "add_my_column"
```

### Docker Compose (Recommended)

```bash
# Start all services (backend, frontend, db, airflow, keycloak, iceberg)
docker compose up

# Start with file-watching auto-sync
docker compose watch

# Stop all services
docker compose down

# Reset database (removes volumes)
docker compose down -v
```

### OpenAPI Documentation

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

### Logging

Structured logging uses Python's standard `logging` module with a timestamp + level + logger name format. Log level is `DEBUG` when `DEBUG=true`, otherwise `INFO`. Request logging middleware logs every non-health request with method, path, status code, and duration in milliseconds. The `X-Request-ID` header (UUID v4) is added to every response.

---

## Configuration

All settings are loaded by `pydantic-settings` from environment variables or a `.env` file. Boolean, integer, and list values are coerced automatically.

| Variable | Default | Description |
|----------|---------|-------------|
| **Database** | | |
| `DATABASE_URL` | `postgresql+asyncpg://etlnexus:etlnexus@db:5432/etlnexus` | Async SQLAlchemy connection string |
| **Airflow** | | |
| `AIRFLOW_BASE_URL` | `http://airflow-webserver:8080/api/v1` | Airflow REST API base URL |
| `AIRFLOW_USERNAME` | `admin` | Airflow basic auth username |
| `AIRFLOW_PASSWORD` | `admin` | Airflow basic auth password |
| `AIRFLOW_POLL_INTERVAL_MINUTES` | `20` | Interval for pipeline sync and status poll background jobs |
| `AIRFLOW_SEMAPHORE_LIMIT` | `6` | Maximum concurrent Airflow API calls during sync |
| `AIRFLOW_STARTUP_MAX_ATTEMPTS` | `20` | Number of health-check retries before giving up on startup sync |
| `AIRFLOW_STARTUP_RETRY_SECONDS` | `15` | Seconds between startup health-check retries |
| `AIRFLOW_EXCLUDE_OPERATOR_TYPES` | `EmptyOperator,DummyOperator,BranchPythonOperator,TriggerDagRunOperator,ShortCircuitOperator` | Comma-separated operator types skipped during auto-discovery |
| **Spark Connect / Iceberg** | | |
| `SPARK_CONNECT_URL` | `sc://spark-connect:15002` | Spark Connect server endpoint (gRPC). Leave empty to disable schema browsing |
| `SPARK_CATALOG_NAME` | `iceberg` | Spark catalog alias holding the Iceberg tables (hadoop catalog) |
| `SPARK_NAMESPACE_PREFIX` | `dagger,prism,vault,oasis` | Comma-separated namespace prefixes used to filter tables during catalog sync |
| **AI / LLM** | | |
| `LLM_API_BASE_URL` | _(empty — disables AI)_ | OpenAPI-compatible chat completions base URL |
| `LLM_API_KEY` | _(empty)_ | API key sent as `Authorization: Bearer` header |
| `LLM_MODEL` | `default` | Model name sent in the completion request |
| `LLM_MAX_TOKENS` | `1024` | Maximum tokens per completion response |
| **App** | | |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | List of allowed CORS origins |
| `DEBUG` | `false` | Enables DEBUG log level |
| **Spark Cluster Capacity** | | |
| `SPARK_MAX_DRIVER_MEMORY_GB` | `16` | Cluster driver memory limit used for capacity bar calculations |
| `SPARK_MAX_EXECUTOR_MEMORY_GB` | `64` | Cluster executor memory limit |
| `SPARK_MAX_EXECUTOR_CORES` | `32` | Cluster executor core limit |
| `SPARK_MAX_TOTAL_EXECUTORS` | `20` | Cluster total executor limit |
| **Cache and Pagination** | | |
| `CACHE_TTL_SHORT` | `30` | TTL in seconds for short-lived caches (pipeline list, topology, grants) |
| `CACHE_TTL_MEDIUM` | `60` | TTL in seconds for medium-lived caches (schema matrix, DAG summary, bouncer list) |
| `CACHE_TTL_AIRFLOW` | `300` | TTL in seconds for Airflow client response cache |
| `DEFAULT_PAGE_LIMIT` | `200` | Default pagination limit for most list endpoints |
| `DEFAULT_PAGE_LIMIT_SMALL` | `20` | Default pagination limit for smaller result sets |
| **SSO / OIDC** | | |
| `SSO_ENABLED` | `false` | Enables Keycloak OIDC authentication; when false a default admin user is returned on all requests |
| `SSO_ISSUER_URL` | `http://keycloak:8090/realms/etlnexus` | Internal Docker issuer URL used for JWKS discovery at startup |
| `SSO_CLIENT_ID` | `etlnexus-app` | OIDC client ID for audience validation |
| `SSO_AUDIENCE` | `etlnexus-app` | Expected `aud` claim value |
| `SSO_GROUPS_CLAIM` | `groups` | JWT claim name carrying the user's team group memberships |
| `SSO_ROLE_CLAIM` | `realm_access.roles` | JWT claim path carrying the user's realm roles |
| `SSO_ADMIN_ROLE` | `admin` | Role string that maps to the `admin` application role |
| `SSO_PUBLIC_ISSUER_URL` | `http://localhost:8090/realms/etlnexus` | Public-facing issuer URL used for `iss` claim validation in incoming tokens |
