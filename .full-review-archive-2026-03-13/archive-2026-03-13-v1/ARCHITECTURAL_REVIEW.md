# EtlNexus Architectural Review

**Date:** 2026-03-13
**Scope:** Full-stack codebase -- backend (FastAPI/SQLAlchemy/PostgreSQL), frontend (React 19/TypeScript/Vite), infrastructure (Docker Compose), integrations (Airflow, Iceberg, Keycloak, LLM)
**Reviewer:** Claude Opus 4.6 (Architectural Review)

---

## Executive Summary

EtlNexus is a well-structured ETL catalog application that follows a clear three-layer architecture (Router, Service, Repository) with appropriate separation of concerns. The codebase demonstrates strong conventions around dependency injection, async operations, and data model integrity. The overall architectural quality is **good**, with several areas where targeted improvements would meaningfully enhance maintainability, testability, and operational resilience.

The most significant architectural concerns are: (1) naming inconsistencies from an incomplete domain rename ("sensor" to "bouncer"), (2) some services bypassing the three-layer pattern by directly instantiating repositories, (3) the `TopologyService` and `BouncerService` loading all pipelines into memory per request, and (4) the `AirflowSyncService` accumulating too many responsibilities into a single 750-line method.

---

## 1. Component Boundaries & Separation of Concerns

### 1.1 Backend Three-Layer Architecture (Router -> Service -> Repository)

**Assessment: Well-Implemented With Exceptions**

The codebase consistently follows the three-layer pattern declared in `CLAUDE.md`. Routers handle HTTP concerns (request parsing, response formatting, error codes), services contain business logic, and repositories encapsulate data access. The `dependencies.py` file centralizes FastAPI dependency injection composition, which is a clean approach.

**Finding 1.1a -- TopologyService bypasses the dependency injection pattern**
- Severity: **Medium**
- File: `/home/ip04/EtlNexus/backend/app/routers/topology.py` (lines 30-31)
- The topology router directly instantiates `TopologyService(session)` instead of using the `dependencies.py` pattern. This is the only router that constructs its own service, while all others receive pre-composed services via `Depends()`.
- Architectural Impact: This inconsistency means the topology service is harder to test (cannot swap dependencies) and diverges from the established convention.
- Recommendation: Add a `get_topology_service()` factory to `dependencies.py` and inject it via `Depends()`, consistent with all other routers.

**Finding 1.1b -- AirflowService internally instantiates its own repositories**
- Severity: **Low**
- File: `/home/ip04/EtlNexus/backend/app/services/airflow_service.py` (lines 37-43)
- `AirflowService.__init__` creates its own `AirflowRepository`, `PipelineRepository`, `ResourceRepository`, and `BouncerRepository` from the session, rather than accepting them as constructor parameters.
- Architectural Impact: Tighter coupling. The service cannot have its repositories replaced for testing without patching constructor internals. Compare with `AirflowSyncService` which accepts all repositories as optional constructor parameters -- a better pattern.
- Recommendation: Align `AirflowService` with the `AirflowSyncService` pattern: accept repositories as optional constructor parameters, defaulting to session-based creation.

### 1.2 Frontend Component Architecture

**Assessment: Well-Organized**

The frontend follows a feature-based component structure under `components/` with shared UI primitives in `components/ui/` and `components/shared/`. State management is cleanly split: Zustand for UI state (navigation, pipeline selection, chat history), TanStack Query for server state. The `api/` layer wraps Axios calls, and `hooks/` wrap TanStack Query -- providing a clean data-fetching pipeline.

**Finding 1.2a -- App.tsx uses conditional rendering instead of a router**
- Severity: **Low**
- File: `/home/ip04/EtlNexus/frontend/src/App.tsx` (lines 51-95)
- Tab switching is done via `activeTab` from Zustand with conditional rendering. This is a deliberate single-page design choice and works well for the current feature set. However, it means there are no shareable URLs for specific views, and browser history navigation is not supported.
- Architectural Impact: Acceptable for an internal tool. Would become a limitation if the application needs deep-linking or multi-user collaboration features.
- Recommendation: No immediate action required. If deep-linking becomes necessary, consider adding a lightweight router (e.g., TanStack Router) with URL-state synchronization.

---

## 2. Dependency Management & Coupling

### 2.1 Circular Import Handling in Models

**Assessment: Pragmatic but Fragile**

**Finding 2.1a -- Circular imports resolved via bottom-of-file imports**
- Severity: **Medium**
- Files: `/home/ip04/EtlNexus/backend/app/models/pipeline.py` (lines 78-82), `/home/ip04/EtlNexus/backend/app/models/lineage.py` (line 33), `/home/ip04/EtlNexus/backend/app/models/airflow_status.py` (line 25), `/home/ip04/EtlNexus/backend/app/models/resource_config.py` (line 31), `/home/ip04/EtlNexus/backend/app/models/run_history.py` (line 55), `/home/ip04/EtlNexus/backend/app/models/pipeline_revision.py` (line 28)
- Six model files use bottom-of-file `import` statements with `# noqa: E402, F401` to resolve circular references between SQLAlchemy relationship back-references. This is a well-known pattern in SQLAlchemy codebases but can be confusing to new contributors.
- Architectural Impact: Works correctly at runtime but makes static analysis tools and IDE navigation less reliable. The `models/__init__.py` file imports all models, which triggers the proper resolution order -- but this is implicit.
- Recommendation: Consider using SQLAlchemy's string-based forward references for relationship annotations (e.g., `Mapped["Pipeline"]` already uses strings) and removing the bottom-of-file imports. The `__init__.py` barrel file already ensures all models are loaded. Alternatively, document this pattern prominently in the module docstrings.

### 2.2 Service Layer Dependencies

**Finding 2.2a -- PipelineService receives RevisionRepository and VisibilityGrantRepository ad-hoc through method parameters**
- Severity: **Medium**
- File: `/home/ip04/EtlNexus/backend/app/services/pipeline_service.py` (lines 82-89, 220-227)
- `update_pipeline_metadata()` accepts `revision_repo` as an optional parameter. `get_pipeline_detail_for_user()` accepts `grant_repo` as a required parameter. These are not injected at construction time like the primary repos.
- Architectural Impact: This breaks the clean constructor injection pattern. The service has hidden dependencies that vary by call site, making it harder to reason about its full dependency set.
- Recommendation: Add `revision_repo` and `grant_repo` as optional constructor parameters of `PipelineService`, injected via `dependencies.py`. Methods that need them should access `self.revision_repo` and `self.grant_repo`.

### 2.3 Deferred Imports in auth.py

**Finding 2.3a -- Inline imports of repositories inside dependency functions**
- Severity: **Low**
- File: `/home/ip04/EtlNexus/backend/app/auth.py` (lines 162, 218)
- `require_team_membership` and `require_team_membership_or_editor_grant` use inline `from app.repositories...` imports inside the dependency function body to avoid circular imports.
- Architectural Impact: Minor. The imports are encapsulated within the closure and don't affect runtime performance (cached after first import). However, they obscure the dependency graph.
- Recommendation: These could be restructured to accept the repos via FastAPI `Depends()` sub-dependencies, which would make the dependency chain explicit. However, the current approach works correctly and the trade-off may not be worth the refactor complexity.

---

## 3. API Design

### 3.1 Endpoint Organization

**Assessment: Well-Designed**

All endpoints are consistently prefixed with `/api/`, use appropriate HTTP methods, and follow RESTful conventions. The router splitting by domain (`pipelines.py`, `lineage.py`, `topology.py`, `resources.py`) keeps individual files focused.

**Finding 3.1a -- Multiple routers share the `/api/pipelines` prefix**
- Severity: **Low**
- Files: `pipelines.py` (`/api/pipelines`), `lineage.py` (`/api/pipelines`), `topology.py` (`/api/pipelines`), `resources.py` (`/api/pipelines`)
- Four routers register sub-endpoints under `/api/pipelines/{id}/...`. This is actually reasonable -- it keeps related endpoints grouped by their parent resource -- but the router file boundaries are organized by feature domain rather than URL path.
- Architectural Impact: Acceptable. The domain-based file organization is clearer than URL-based organization for this codebase size.
- Recommendation: Consider adding a brief comment to `main.py` where routers are included, noting which routers contribute sub-routes under `/api/pipelines`.

### 3.2 Error Handling & Contracts

**Finding 3.2a -- Inconsistent error response shape for non-HTTPException routes**
- Severity: **Low**
- File: `/home/ip04/EtlNexus/backend/app/routers/visibility.py` (line 106), `/home/ip04/EtlNexus/backend/app/routers/users.py` (line 71)
- Delete grant returns `{"ok": True}`, role update returns `{"ok": True}`, active update returns `{"ok": True}`. These ad-hoc response shapes are not covered by Pydantic response models.
- Architectural Impact: Minor. Clients cannot rely on a typed response contract for these endpoints.
- Recommendation: Define a small `ActionResponse` schema (e.g., `{"ok": bool}`) and annotate these endpoints with `response_model=ActionResponse`.

**Finding 3.2b -- Validation duplication between router and service for grants**
- Severity: **Low**
- File: `/home/ip04/EtlNexus/backend/app/routers/visibility.py` (lines 62-81), `/home/ip04/EtlNexus/backend/app/services/visibility_service.py` (lines 44-53)
- The visibility router performs exclusive-or validation on `pipeline_id`/`source_team_id` and `grantee_team_id`/`grantee_user_id`. The service repeats this validation with `ValueError` raises.
- Architectural Impact: The dual validation is defensive and not harmful, but it means the constraint is defined in two places. The DB CHECK constraint provides the third level.
- Recommendation: Consider using a Pydantic `model_validator` on `VisibilityGrantRequest` to enforce the exclusive-or logic at the schema level, removing the need for both router-level and service-level checks.

### 3.3 API Versioning

**Finding 3.3a -- No API versioning strategy**
- Severity: **Low**
- The API has no versioning mechanism (no `/api/v1/` prefix or header-based versioning). All endpoints are under `/api/`.
- Architectural Impact: Acceptable for an internal-facing application at this stage. Would need attention if the API is consumed by external clients or if breaking changes are anticipated.
- Recommendation: No immediate action needed. If versioning becomes necessary, the `/api/v1/` prefix approach is simplest to retrofit given the existing `prefix="/api/..."` router configuration.

---

## 4. Data Model

### 4.1 Schema Design

**Assessment: Solid**

The data model is well-normalized with appropriate denormalization where justified (e.g., `pipeline.team` caching the team name to avoid JOINs on list queries, documented with a comment). UUID primary keys, timezone-aware timestamps, and proper foreign key relationships with `ondelete` cascades are consistently applied.

**Finding 4.1a -- The `sensors` table name does not match the `Bouncer` model class name**
- Severity: **High**
- File: `/home/ip04/EtlNexus/backend/app/models/sensor.py` (line 13)
- The ORM class is `Bouncer` with `__tablename__ = "sensors"`. The column is `sensor_name`. The repository file is `sensor_repo.py` containing class `BouncerRepository`. The service file is `sensor_service.py` containing class `BouncerService`. The `DagTask` model has `sensor_name` and `sensor_id` columns.
- Architectural Impact: This naming split creates a persistent cognitive load for developers. The domain concept is "bouncer" (per the rename), but the database and half the codebase still says "sensor". A developer searching for "bouncer" will miss database-level references, and someone reading SQL queries will encounter "sensors" without understanding the domain mapping.
- Recommendation: Complete the rename at the database level with a migration that renames: (1) table `sensors` to `bouncers`, (2) columns `sensor_name` to `bouncer_name`, `sensor_id` to `bouncer_id` in `dag_tasks`, (3) rename `sensor_repo.py` to `bouncer_repo.py`. This is a significant change but eliminates the naming ambiguity permanently.

**Finding 4.1b -- `pipeline_usages.etl_name` uses String key instead of UUID foreign key**
- Severity: **Medium**
- File: `/home/ip04/EtlNexus/backend/app/models/pipeline_usage.py` (line 14)
- The `pipeline_usages` table references pipelines by `etl_name` (String) rather than `pipeline_id` (UUID FK). This means it is a soft reference -- no referential integrity, no cascade deletes, and lookups require a string match.
- Architectural Impact: If a pipeline is renamed, the usage records become orphaned. There is no database-enforced consistency between the two tables.
- Recommendation: Add a nullable `pipeline_id` UUID column with an FK to `pipelines.id` and populate it during sync. Keep `etl_name` for display/enrichment but use the FK for joins. This can be done incrementally.

### 4.2 Index Strategy

**Finding 4.2a -- No composite index on `lineage_edges(source_pipeline_id, edge_type)` or `(target_pipeline_id, edge_type)`**
- Severity: **Low**
- File: `/home/ip04/EtlNexus/backend/app/models/lineage.py`
- Both `source_pipeline_id` and `target_pipeline_id` have individual indexes, but the `LineageRepository.get_by_pipeline_id()` queries filter on `target_pipeline_id` and `source_pipeline_id` separately. The `upsert_edge()` queries filter on `(source_table, target_table, edge_type)` which has no index.
- Architectural Impact: At the current data volume (30 pipelines) this is irrelevant. At scale (hundreds of pipelines with dense lineage), the upsert lookup would benefit from a composite index.
- Recommendation: Add a composite index on `(source_table, target_table, edge_type)` for the upsert lookup path. Low priority.

---

## 5. Design Patterns

### 5.1 Repository Pattern

**Assessment: Consistently Applied**

All repositories follow a uniform pattern: constructor takes `AsyncSession`, methods return domain models or `None`, mutations use `flush()` (not `commit()`) to defer transaction control to the caller. The shared `apply_updates()` utility in `base.py` reduces boilerplate in upsert operations.

**Finding 5.1a -- Repositories return raw dicts instead of typed results in some cases**
- Severity: **Low**
- File: `/home/ip04/EtlNexus/backend/app/repositories/pipeline_repo.py` (`get_shared_field_pipelines()` returns `list[dict]`), `/home/ip04/EtlNexus/backend/app/repositories/resource_repo.py` (`get_run_stats()` returns `dict`, `get_execution_plan_runs()` returns `tuple[list[dict], int]`)
- Architectural Impact: These untyped dicts break the otherwise clean type contract between repository and service layers. Callers access dict keys with string literals, which is error-prone.
- Recommendation: Define lightweight dataclasses or TypedDicts for these return types (e.g., `SharedFieldResult`, `RunStats`). This adds type safety without requiring full Pydantic models.

### 5.2 Caching Strategy

**Assessment: Well-Designed**

The `TTLCache` in `cache.py` provides simple, effective in-memory caching for read-heavy data. The `clear_all()` function is called after every sync/poll cycle, ensuring caches are invalidated when data changes. Cache instances are module-level singletons with appropriate TTLs (30-60 seconds).

**Finding 5.2a -- The TTLCache is not thread-safe or asyncio-safe**
- Severity: **Low**
- File: `/home/ip04/EtlNexus/backend/app/cache.py`
- The `TTLCache` uses a plain dict without locks. In the current async architecture (single event loop), this is safe because dict operations in CPython are atomic at the bytecode level. However, it would not be safe under multi-worker deployment (e.g., multiple Uvicorn workers).
- Architectural Impact: Currently safe because the backend runs a single Uvicorn worker process. If scaled to multiple workers, the cache would be per-process (which is fine for TTL caches) but concurrent writes within a process could theoretically cause issues in non-CPython runtimes.
- Recommendation: No immediate action needed. Document the single-worker assumption. If multi-worker deployment is anticipated, consider replacing with a shared cache (Redis) or accepting per-worker caching.

**Finding 5.2b -- AirflowClient has its own separate TTLCache instance**
- Severity: **Low**
- File: `/home/ip04/EtlNexus/backend/app/integrations/airflow_client.py` (line 40)
- The `AirflowClient` maintains a private `TTLCache(ttl=300)` for caching DAG lists, task definitions, etc. This cache is independent from the application-level caches in `cache.py` and is NOT cleared by `cache.clear_all()`.
- Architectural Impact: After a sync cycle, the Airflow client's internal cache still holds stale data for up to 5 minutes. This is intentional -- the Airflow API data changes infrequently -- but it creates a non-obvious cache layer that could cause confusion during debugging.
- Recommendation: Document this dual-cache architecture. Consider registering the Airflow client cache with `clear_all()` or adding an explicit `airflow_client.clear_cache()` method callable from the scheduler.

### 5.3 Error Handling

**Finding 5.3a -- Custom exceptions defined but rarely raised**
- Severity: **Medium**
- File: `/home/ip04/EtlNexus/backend/app/exceptions.py`
- Five domain exceptions are defined (`AirflowConnectionError`, `AirflowSyncError`, `PipelineNotFoundError`, `IcebergCatalogError`, `AuthorizationError`), but a grep of the codebase reveals they are never raised. All error paths use `HTTPException` (in routers), `ValueError` (in services), or bare `Exception` catches with logging.
- Architectural Impact: The domain exception hierarchy was designed but never adopted. This means error classification is inconsistent -- some errors are silently swallowed (`except Exception: logger.exception(...)`) and the service layer communicates errors through `None` returns rather than typed exceptions.
- Recommendation: Adopt the defined exceptions in services (e.g., `raise PipelineNotFoundError(...)` instead of returning `None`), and add a FastAPI exception handler that maps domain exceptions to HTTP status codes. This would make error paths more explicit and enable better observability.

### 5.4 Singleton Pattern for Integration Clients

**Assessment: Appropriate**

Module-level singletons (`airflow_client`, `iceberg_client`, `llm_client`, `oidc_client`) are the right pattern for long-lived integration clients with connection pools. Each client has proper lifecycle management (`initialize()`, `close()`, `stop()`) called in the FastAPI lifespan handler.

**Finding 5.4a -- LLMClient creates a new httpx.AsyncClient per request**
- Severity: **Medium**
- File: `/home/ip04/EtlNexus/backend/app/integrations/llm_client.py` (line 50)
- Unlike `AirflowClient` and `OIDCClient`, the `LLMClient.chat()` method creates a new `httpx.AsyncClient` inside an `async with` context manager for every request. This means a new TCP connection (and TLS handshake if applicable) is established for each LLM call.
- Architectural Impact: Higher latency per LLM request due to connection setup overhead. At low volume this is negligible, but it is architecturally inconsistent with the other clients.
- Recommendation: Add a persistent `httpx.AsyncClient` as an instance variable (matching the `AirflowClient` pattern) and add a `close()` method called during app shutdown.

---

## 6. Architectural Consistency

### 6.1 Transaction Management

**Assessment: Mostly Consistent**

The `get_db_session()` dependency auto-commits on success and rollbacks on exception (lines 21-28 of `database.py`). Services use `flush()` to stage changes within the session scope, and background tasks create their own sessions via `async_session_factory()`.

**Finding 6.1a -- Two services call `session.commit()` directly, bypassing the dependency scope**
- Severity: **Medium**
- Files: `/home/ip04/EtlNexus/backend/app/services/airflow_sync_service.py` (lines 410, 745), `/home/ip04/EtlNexus/backend/app/services/airflow_service.py` (line 220), `/home/ip04/EtlNexus/backend/app/services/catalog_sync_service.py` (line 56)
- The `AirflowSyncService.sync_pipelines_from_airflow()`, `AirflowSyncService.sync_single_pipeline()`, `AirflowService.poll_all_statuses()`, and `CatalogSyncService.sync_from_catalog()` all call `self.session.commit()` explicitly.
- Architectural Impact: When these services are invoked from background tasks (via `async_session_factory()`), the explicit commit is correct and necessary because there is no `get_db_session()` dependency to auto-commit. However, when `AirflowSyncService` is injected via `get_airflow_sync_service()` in router endpoints (e.g., `sync_pipeline()`), the explicit `commit()` at line 745 commits before the `get_db_session()` context manager exits, which means the auto-commit in `get_db_session()` becomes a no-op.
- Recommendation: The dual invocation context (background task vs. HTTP request) is the root issue. Consider extracting the "commit boundary" decision to the caller. Background tasks would call `await session.commit()` after the service method returns; HTTP handlers would let `get_db_session()` handle it. The service methods themselves should only `flush()`.

### 6.2 Method Size & Complexity

**Finding 6.2a -- `AirflowSyncService.sync_pipelines_from_airflow()` is ~340 lines with 5 sequential phases**
- Severity: **Medium**
- File: `/home/ip04/EtlNexus/backend/app/services/airflow_sync_service.py` (lines 78-418)
- This method handles: (Phase A) parallel Airflow API fetches, (Phase B) task instance fetching, (Phase C) instance processing, (Phase D) log fetching, (Phase E) log processing, then 5 sequential DB write passes. It is well-documented with phase labels but difficult to unit test in isolation.
- Architectural Impact: The method's size makes it the highest-risk area for bugs during modifications. Each "pass" depends on data structures built in previous passes, creating implicit coupling.
- Recommendation: Extract each phase into a private method. The current data structures (`seen_tasks`, `seen_bouncers`, `resource_by_dag`, `dag_task_graph`) could be bundled into a `SyncResult` dataclass that flows between phases. The five DB-write passes could each be a separate method.

**Finding 6.2b -- `sync_single_pipeline()` duplicates significant logic from `sync_pipelines_from_airflow()`**
- Severity: **Medium**
- File: `/home/ip04/EtlNexus/backend/app/services/airflow_sync_service.py` (lines 420-747)
- The single-pipeline sync method repeats lineage construction, resource upsert, and status polling logic that is similar to the full sync method. Changes to sync logic must be made in two places.
- Architectural Impact: Code duplication increases the probability of behavioral drift between full-sync and single-pipeline sync.
- Recommendation: Extract shared logic (lineage edge building, resource config upsert, status determination) into private helper methods that both sync paths invoke.

### 6.3 Naming Consistency

**Finding 6.3a -- Pervasive sensor/bouncer naming confusion across the codebase**
- Severity: **High**
- This is the most significant consistency issue in the codebase. The domain term "bouncer" coexists with "sensor" across multiple layers:
  - Database: table `sensors`, columns `sensor_name`, `sensor_id`
  - Backend model: class `Bouncer` in `sensor.py`, `DagTask.sensor_name`, `DagTask.sensor_id`
  - Backend repo: file `sensor_repo.py`, class `BouncerRepository`
  - Backend service: file `sensor_service.py`, class `BouncerService`
  - Backend schemas: file `sensor.py`, classes `BouncerResponse`, `BouncerListResponse`
  - Frontend types: file `bouncer.ts` (fully renamed)
  - Frontend components: directory `bouncers/` (fully renamed)
  - Frontend API: file `bouncers.ts` hitting endpoint `/api/bouncers`
  - Backend router: `sensors.py` serving prefix `/api/bouncers`
- Architectural Impact: Any developer working on bouncer-related features must mentally translate between "sensor" and "bouncer" when crossing layer boundaries. This is a source of bugs and confusion.
- Recommendation: Create a migration to rename the database table and columns. Rename `sensor_repo.py` to `bouncer_repo.py`, `sensor_service.py` to `bouncer_service.py`, `sensor.py` (model) to `bouncer.py`, and `sensors.py` (router) to `bouncers.py`. The frontend is already fully renamed and requires no changes.

---

## 7. Scalability Considerations

### 7.1 N+1 Query Patterns

**Finding 7.1a -- TopologyService loads all pipelines for every topology request**
- Severity: **High**
- File: `/home/ip04/EtlNexus/backend/app/services/topology_service.py` (lines 64-65, 221)
- Both `build_pipeline_topology()` and `build_upstream_topology()` call `self.pipeline_repo.get_all()` to build a `task_id_to_pipeline` lookup and a `status_map`. This loads every pipeline (with `selectinload(airflow_status)`) into memory for each topology request.
- Architectural Impact: With 30 pipelines this is fast. At 300+ pipelines, this becomes wasteful since the topology typically references only 5-20 upstream/downstream tasks.
- Recommendation: Precompute the `task_id_to_pipeline_id` mapping (it only changes on sync) and cache it. Or, collect the set of relevant task_ids from the BFS traversal first, then query only those pipelines.

**Finding 7.1b -- BouncerService.get_bouncer_topology() loads all dag_tasks and all pipelines**
- Severity: **Medium**
- File: `/home/ip04/EtlNexus/backend/app/services/sensor_service.py` (lines 71-86)
- The bouncer topology method loads the entire `dag_tasks` table and the entire `pipelines` table into memory for BFS traversal.
- Architectural Impact: Similar to the topology finding -- acceptable at current scale, problematic at larger scale.
- Recommendation: For the BFS traversal, consider a recursive CTE query or loading only the dag_tasks for the DAGs that contain the selected bouncers.

### 7.2 Background Task Scalability

**Finding 7.2a -- Full Airflow sync fetches all DAG runs/instances sequentially per DAG then processes serially**
- Severity: **Low**
- The sync is well-parallelized with `asyncio.gather()` and a semaphore, which is appropriate for the current scale. The phased approach (parallel fetch, then serial DB writes) correctly avoids database contention.
- Recommendation: No immediate action. The design handles the current 6-DAG, 30-pipeline workload efficiently.

---

## 8. Security Architecture

### 8.1 Authentication & Authorization

**Assessment: Well-Implemented**

The RBAC system with three roles (admin, member, viewer) and team-based visibility is comprehensive. The `VisibilityGrant` model with CHECK constraints prevents invalid grant states at the database level. JIT user provisioning handles concurrent first-login atomically via `ON CONFLICT DO UPDATE`.

**Finding 8.1a -- Health endpoint exposes integration status without authentication**
- Severity: **Low**
- File: `/home/ip04/EtlNexus/backend/app/routers/health.py`
- The `/api/health` endpoint reveals whether Airflow, Iceberg, and the database are connected/disconnected without requiring authentication.
- Architectural Impact: This is standard practice for health endpoints (needed by load balancers and container orchestrators). However, the detailed service status could be considered information disclosure.
- Recommendation: Consider splitting into a public liveness probe (`/api/health/live` returning only `200`/`503`) and a protected readiness probe (`/api/health/ready` with service details, requiring auth).

**Finding 8.1b -- CORS configured with wildcard methods and headers**
- Severity: **Low**
- File: `/home/ip04/EtlNexus/backend/app/main.py` (lines 118-124)
- `allow_methods=["*"]` and `allow_headers=["*"]` is permissive. The `allow_origins` is properly restricted to `settings.cors_origins`.
- Recommendation: Restrict `allow_methods` to the actually used methods (`GET`, `POST`, `PATCH`, `DELETE`, `OPTIONS`) and `allow_headers` to the required set (`Authorization`, `Content-Type`).

### 8.2 Token Management

**Finding 8.2a -- Frontend 401 retry uses a fixed 2-second sleep**
- Severity: **Low**
- File: `/home/ip04/EtlNexus/frontend/src/api/client.ts` (line 31)
- On a 401 response, the Axios interceptor waits 2 seconds before checking if the token was renewed. This is a reasonable heuristic for silent OIDC renewal, but the fixed delay is arbitrary.
- Recommendation: Consider using a token-change event listener or a promise that resolves when the OIDC library completes its silent renewal, rather than a fixed timeout.

---

## 9. Observability & Operations

### 9.1 Logging

**Assessment: Good**

Structured logging is configured in `main.py` with appropriate log levels per component. The request logging middleware captures method, path, status code, and duration for all non-health requests.

**Finding 9.1a -- Background task errors are logged but not surfaced to any monitoring system**
- Severity: **Low**
- File: `/home/ip04/EtlNexus/backend/app/tasks/scheduler.py`
- Failed sync/poll tasks log at `exception` level but there is no alerting, metrics counter, or health status update. The health endpoint always reports the last-known connection state.
- Recommendation: Consider tracking the last successful sync timestamp and exposing it via the health endpoint. This enables monitoring systems to alert on stale data.

### 9.2 Error Recovery

**Finding 9.2a -- Iceberg client uses synchronous PySpark in an async application**
- Severity: **Medium**
- File: `/home/ip04/EtlNexus/backend/app/integrations/iceberg_client.py`
- The `IcebergClient` methods (`list_tables_in_namespace`, `get_table_schema`, `get_all_dagger_schemas`) are synchronous (they call `spark.sql().collect()` which blocks the thread). The `CatalogSyncService.sync_from_catalog()` method is `async` but calls these synchronous methods directly.
- Architectural Impact: When the catalog sync runs, it blocks the event loop for the duration of all Spark SQL operations. During this time, no other async tasks (including HTTP request handling) can proceed on that event loop.
- Recommendation: Run Iceberg/Spark operations in a thread pool executor (`asyncio.to_thread()` or `loop.run_in_executor()`) to avoid blocking the event loop. The catalog sync only runs every 2 hours, so the impact is limited but could cause request timeouts during sync.

---

## 10. Test Architecture

### 10.1 Test Coverage

**Finding 10.1a -- Tests exist for services and pure functions but not for routers or integration end-to-end**
- Severity: **Medium**
- Directory: `/home/ip04/EtlNexus/backend/tests/`
- Test files cover: `task_classifier`, `log_parser`, `cache`, `schemas`, `base_repo`, `airflow_client`, `auth`, `oidc_client`, `auth_schema_helpers`, `pipeline_service`, `visibility_service`, `team_service`, `user_auth_service`, `topology_service`, `catalog_sync_service`, `airflow_sync_helpers`.
- Missing: No integration tests for routers (HTTP layer), no tests for `AirflowSyncService.sync_pipelines_from_airflow()` (the most complex method), no tests for `AirflowService.poll_all_statuses()`.
- Architectural Impact: The most complex and critical code paths (sync and poll) lack test coverage. Service-level tests for `pipeline_service` and `visibility_service` provide good coverage of business logic.
- Recommendation: Add integration tests for the sync and poll services using mocked Airflow responses. The phased architecture of these services (fetch, process, write) makes them amenable to testing with mock data at each phase boundary.

---

## 11. Infrastructure & Deployment

### 11.1 Docker Compose Architecture

**Assessment: Well-Structured**

The compose file cleanly separates core services (db, backend, frontend), dev-only services (Airflow, Keycloak, Iceberg), and init containers. Health checks and dependency ordering ensure services start in the correct sequence.

**Finding 11.1a -- Production compose file exists but shares no base configuration**
- Severity: **Low**
- Files: `/home/ip04/EtlNexus/docker-compose.yml`, `/home/ip04/EtlNexus/docker-compose.prod.yml`
- The production compose file is separate from the dev compose file with no shared base (no `extends` or `include`). Changes to service configuration must be applied to both files.
- Recommendation: Consider using Docker Compose `include` (v2.20+) or a base `docker-compose.base.yml` with environment-specific overrides.

---

## Summary of Findings by Severity

### Critical (0)
None.

### High (2)
1. **[6.3a]** Pervasive sensor/bouncer naming inconsistency across database, models, repos, services, schemas
2. **[7.1a]** TopologyService loads all pipelines into memory for every topology request

### Medium (8)
1. **[1.1a]** TopologyService bypasses the dependency injection pattern
2. **[2.1a]** Circular imports resolved via fragile bottom-of-file imports
3. **[2.2a]** PipelineService receives RevisionRepository and VisibilityGrantRepository ad-hoc through method parameters
4. **[4.1b]** `pipeline_usages.etl_name` uses String key instead of UUID FK
5. **[5.3a]** Custom domain exceptions defined but never raised
6. **[5.4a]** LLMClient creates a new HTTP client per request
7. **[6.1a]** Two services call `session.commit()` directly, creating dual transaction management
8. **[6.2a]** `sync_pipelines_from_airflow()` is 340 lines with significant complexity

### Low (12)
Various minor findings around API design, error contracts, caching documentation, CORS configuration, and test coverage gaps.

---

## Recommended Priority Actions

1. **Complete the sensor-to-bouncer rename** at the database and file level to eliminate the naming split (High severity, addresses finding 6.3a/4.1a).

2. **Extract TopologyService pipeline loading** into a cached lookup to avoid loading all pipelines per request (High severity, addresses finding 7.1a).

3. **Refactor AirflowSyncService** by extracting phases into private methods and sharing logic between full-sync and single-pipeline-sync (Medium severity, addresses findings 6.2a/6.2b).

4. **Standardize dependency injection** for `TopologyService` and `PipelineService` by adding missing dependencies to constructors and `dependencies.py` (Medium severity, addresses findings 1.1a/2.2a).

5. **Adopt domain exceptions** to replace `None` returns and bare `ValueError` raises in services, enabling structured error handling (Medium severity, addresses finding 5.3a).

6. **Add integration tests** for the sync and poll services (Medium severity, addresses finding 10.1a).
