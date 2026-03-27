# EtlNexus Architectural Review

**Date:** 2026-03-13
**Branch:** `feature/sensor-to-bouncer-rename` (at commit `ac9856b`)
**Scope:** Full-stack review -- backend (FastAPI/SQLAlchemy/PostgreSQL), frontend (React 19/TypeScript/Vite), infrastructure (Docker Compose), auth (Keycloak OIDC)

---

## Executive Summary

The EtlNexus codebase demonstrates a well-structured three-layer backend architecture (Router -> Service -> Repository) with clear separation of concerns and consistent application of the project's stated patterns. The frontend follows a clean hooks-first approach with proper state management boundaries between server state (TanStack Query) and client state (Zustand). The recent technical debt remediation has improved module cohesion, particularly around the sync pipeline's task classifier extraction and internal TypedDict formalization.

That said, this review identifies 23 findings across 6 categories, with 2 critical, 4 high, 10 medium, and 7 low severity items. The critical findings relate to a naming inconsistency introduced by the sensor-to-bouncer rename that creates confusion at the database schema level, and a topology service performance concern that fetches all pipelines on every call.

---

## 1. Component Boundaries and Separation of Concerns

### Finding 1.1: TopologyService bypasses the dependency injection pattern

**Severity:** Medium
**Impact:** Architectural consistency

`TopologyService` (in `/home/ip04/EtlNexus/backend/app/services/topology_service.py`) instantiates its own repositories directly from a raw `AsyncSession`, bypassing the established dependency injection pattern via `dependencies.py`. Compare with every other service which receives repositories through constructor injection:

```python
# TopologyService -- constructs its own repos
class TopologyService:
    def __init__(self, session: AsyncSession):
        self.pipeline_repo = PipelineRepository(session)
        self.dag_task_repo = DagTaskRepository(session)
        self.bouncer_repo = BouncerRepository(session)
```

The topology router in `/home/ip04/EtlNexus/backend/app/routers/topology.py` also manually constructs the service instead of using a dependency function:

```python
service = TopologyService(session)
```

**Recommendation:** Create a `get_topology_service` factory in `dependencies.py` and inject repositories through the constructor, matching the pattern established by `get_pipeline_service`, `get_resource_service`, etc. This maintains testability and consistency.

### Finding 1.2: Lineage router contains business logic instead of delegating to a service

**Severity:** Medium
**Impact:** Layer violations, testability

The lineage router at `/home/ip04/EtlNexus/backend/app/routers/lineage.py` directly constructs the response graph (building nodes, edges, source/destination table lists) inside the router handler. This is business logic that belongs in a service layer. Every other domain (pipelines, resources, topology, bouncers) delegates to a service.

**Recommendation:** Extract the lineage graph construction into a `LineageService` or add a method like `get_lineage_graph()` to the existing `PipelineService`. The router should only handle HTTP concerns (parameter extraction, status codes, error mapping).

### Finding 1.3: Cache interaction split across multiple architectural layers

**Severity:** Low
**Impact:** Maintainability

Caching is inconsistently placed:
- `pipeline_list_cache` -- accessed in `PipelineService` (service layer)
- `join_suggestions_cache` -- accessed in `PipelineService` (service layer)
- `topology_cache` -- accessed directly in the topology **router** (HTTP layer)
- `bouncer_cache` / `bouncer_topology_cache` -- accessed in `BouncerService` (service layer)
- `grant_level_cache` -- accessed in `VisibilityGrantRepository` (repository layer)

Caching belongs at a single layer. The topology router and the visibility grant repository are outliers.

**Recommendation:** Standardize caching at the service layer. Move topology caching into the `TopologyService` and move grant-level caching from the repository into the `VisibilityService`.

---

## 2. Dependency Management

### Finding 2.1: Circular import management via bottom-of-file imports in models

**Severity:** Low
**Impact:** Code smell, fragile import ordering

Multiple model files use bottom-of-file imports to resolve circular references:

- `/home/ip04/EtlNexus/backend/app/models/pipeline.py` lines 78-82
- `/home/ip04/EtlNexus/backend/app/models/lineage.py` line 33
- `/home/ip04/EtlNexus/backend/app/models/resource_config.py` line 31
- `/home/ip04/EtlNexus/backend/app/models/run_history.py` line 55
- `/home/ip04/EtlNexus/backend/app/models/pipeline_revision.py` line 28

While these work and are a recognized SQLAlchemy pattern, they create implicit ordering dependencies. The `models/__init__.py` already imports everything correctly, so these bottom-of-file imports may be partially redundant.

**Recommendation:** Since SQLAlchemy's string-based `relationship()` references (already used, e.g., `Mapped["Pipeline"]`) resolve forward references at mapper configuration time, many of these bottom-of-file imports could be replaced with `TYPE_CHECKING`-guarded imports for type annotation only. The critical ones that SQLAlchemy needs at runtime are already covered by `__init__.py` importing all models.

### Finding 2.2: Deferred imports inside auth.py dependency factories

**Severity:** Low
**Impact:** Performance micro-cost, readability

In `/home/ip04/EtlNexus/backend/app/auth.py`, the `_resolve_pipeline_team` function and `require_team_membership_or_editor_grant` contain deferred imports:

```python
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.visibility_grant_repo import VisibilityGrantRepository
```

These are placed inside functions to avoid circular imports with `dependencies.py`. This pattern is acceptable but should be documented as intentional.

**Recommendation:** Add a brief comment explaining the circular dependency reason, or consider restructuring so `auth.py` receives repositories through dependency injection parameters rather than importing them directly.

### Finding 2.3: Module-level singleton pattern for integration clients

**Severity:** Low
**Impact:** Testability

`airflow_client`, `oidc_client`, and `iceberg_client` are all module-level singletons. This makes unit testing harder since you cannot easily substitute test doubles without patching at the module level.

**Recommendation:** This is an acceptable trade-off for an application of this size. The test suite already uses mocking effectively. If the codebase grows, consider a lightweight DI container or factory-based approach for integration clients.

---

## 3. Data Model and Database Design

### Finding 3.1 (CRITICAL): Bouncer model retains "sensor" naming in database schema

**Severity:** Critical
**Impact:** Developer confusion, naming inconsistency across the full stack

The `Bouncer` model at `/home/ip04/EtlNexus/backend/app/models/sensor.py` maps to `__tablename__ = "sensors"` and its columns use `sensor_name` as the unique identifier. The file itself is named `sensor.py`. The `DagTask` model has a column `sensor_name` and FK `sensor_id` referencing `sensors.id`. The bouncer repository at `/home/ip04/EtlNexus/backend/app/repositories/sensor_repo.py` is named `sensor_repo.py` but defines `class BouncerRepository`.

This creates a three-way naming conflict:
- **Python class names:** `Bouncer`, `BouncerRepository`, `BouncerService` (new names)
- **Database table/column names:** `sensors`, `sensor_name`, `sensor_id` (old names)
- **File names:** `sensor.py`, `sensor_repo.py`, `sensor_service.py` (old names)

The inconsistency means developers must constantly context-switch between "bouncer" (code) and "sensor" (database/files).

**Recommendation:** Complete the rename at all three levels:
1. Create an Alembic migration to rename the `sensors` table to `bouncers`, the `sensor_name` columns to `bouncer_name` (on both `sensors` and `dag_tasks`), and `sensor_id` to `bouncer_id` on `dag_tasks`.
2. Rename the Python files: `sensor.py` -> `bouncer.py`, `sensor_repo.py` -> `bouncer_repo.py`, `sensor_service.py` -> `bouncer_service.py`.
3. Update all column attribute references in the ORM model and repository code.

This is critical because the current state is a half-completed rename that will confuse every new contributor.

### Finding 3.2: Denormalized `team` column on Pipeline model

**Severity:** Low
**Impact:** Data consistency risk (mitigated by documented intent)

The `Pipeline` model carries both `team` (String) and `team_id` (FK) columns. The comment on line 24 of `pipeline.py` documents this as intentional denormalization to avoid JOINs on list queries. The `set_team()` method sets both atomically.

**Assessment:** This is acceptable. The denormalization is documented, the update path is centralized, and the sync process is the sole writer. No action needed, but the comment should mention that `set_team()` is the only sanctioned mutation path and that direct `pipeline.team = ...` assignments elsewhere would break consistency.

### Finding 3.3: `edge_type` stored as unconstrained String

**Severity:** Medium
**Impact:** Data integrity

The `LineageEdge` model stores `edge_type` as `String(20)` without a CHECK constraint. The only valid values are `"reads_from"` and `"writes_to"`. Similarly, `AirflowRunStatus.status` and `PipelineRunHistory.status` are unconstrained strings.

**Recommendation:** Add CHECK constraints for `edge_type` on `lineage_edges` (matching the pattern already used for `role` on `users` and `grant_level` on `visibility_grants`). Consider the same for status fields if the enum is stable.

### Finding 3.4: `PipelineUsage` model lacks foreign key to Pipeline

**Severity:** Medium
**Impact:** Referential integrity

`PipelineUsage` at `/home/ip04/EtlNexus/backend/app/models/pipeline_usage.py` uses `etl_name` (String) as its link to pipelines rather than a `pipeline_id` UUID foreign key. This is documented as intentional (keyed by name for consumer discovery), but it means:
- No cascade delete when a pipeline is removed
- No referential integrity enforcement
- Name renames break the association

**Recommendation:** Add a nullable `pipeline_id` FK column alongside `etl_name` and populate it during sync. Keep `etl_name` for backward compatibility but use the FK for integrity. Orphan cleanup can happen during the periodic sync.

---

## 4. API Design

### Finding 4.1: Inconsistent prefix handling across routers

**Severity:** Medium
**Impact:** API surface clarity

Most routers define their own prefix, but the health router omits it, relying on `main.py` to supply `/api`:

```python
# main.py
app.include_router(health.router, prefix="/api")  # explicit prefix
app.include_router(pipelines.router)  # uses router's own prefix="/api/pipelines"
```

This means the health router's actual prefix is split between two locations.

**Recommendation:** Either add `prefix="/api/health"` to the health router itself (for consistency), or move all prefix definitions into `main.py` (for centralized routing). The current mixed approach is confusing.

### Finding 4.2: Delete grant endpoint returns untyped `dict`

**Severity:** Low
**Impact:** API contract clarity

The `DELETE /api/visibility/grants/{grant_id}` endpoint at `/home/ip04/EtlNexus/backend/app/routers/visibility.py` returns `{"ok": True}` as a plain dict. Similarly, the user role/active update endpoints return `{"ok": True}`. These lack response model declarations.

**Recommendation:** Define a `SuccessResponse(BaseModel)` schema with `ok: bool` and use it as `response_model` for these endpoints. This ensures the OpenAPI spec documents the response shape.

### Finding 4.3: No API versioning strategy

**Severity:** Medium
**Impact:** Long-term maintainability

All API endpoints are under `/api/` with no version prefix. The API is tightly coupled between frontend and backend (deployed together), which makes this acceptable for now. However, if external consumers emerge, breaking changes will require coordinated deployments.

**Recommendation:** This is fine for the current single-consumer architecture. Document the decision that API versioning is deferred until external consumers exist. If needed later, introduce `/api/v2/` alongside `/api/` with a deprecation timeline.

### Finding 4.4: Date range filtering implemented inconsistently

**Severity:** Medium
**Impact:** API surface coherence

The `DateRangeParams` dependency is used by pipeline list and resource endpoints, but not by DAG summary, bouncer topology, or lineage endpoints. The `dag_summary` router has its own manual date parameter handling. This means different endpoints have different filtering capabilities.

**Recommendation:** Standardize date range filtering by applying `DateRangeParams` consistently across all endpoints that query time-series data. The `DagSummaryService` already accepts `date_from`/`date_to` internally; it just needs the router wiring.

---

## 5. Design Patterns and Architectural Patterns

### Finding 5.1 (CRITICAL): TopologyService loads all pipelines into memory on every call

**Severity:** Critical
**Impact:** Performance, scalability

Both `build_pipeline_topology()` and `build_upstream_topology()` in `/home/ip04/EtlNexus/backend/app/services/topology_service.py` call `self.pipeline_repo.get_all()` to build a task_id-to-pipeline lookup:

```python
all_pipelines = await self.pipeline_repo.get_all()
task_id_to_pipeline = {p.task_id: p for p in all_pipelines if p.task_id}
```

With 30 pipelines this is negligible, but the architecture should not assume a fixed dataset size. Each topology request loads every pipeline with its eager-loaded `airflow_status` relationship, constructs a dict, and discards it.

**Recommendation:**
1. Add a `get_pipeline_task_id_map()` repository method that returns only `(task_id, id, name, status)` tuples via a lightweight SELECT -- no ORM hydration or relationship loading.
2. Alternatively, cache this map at the service level with the same TTL as `topology_cache`, invalidated on sync.

### Finding 5.2: Upsert pattern uses SELECT-then-INSERT/UPDATE instead of PostgreSQL UPSERT

**Severity:** High
**Impact:** Race conditions, performance

Most repositories implement upsert as two-step: `SELECT` to check existence, then `INSERT` or `setattr`. Examples:
- `PipelineRepository.upsert()` (pipeline_repo.py line 70)
- `LineageRepository.upsert_edge()` (lineage_repo.py line 47)
- `BouncerRepository.upsert()` (sensor_repo.py line 58)
- `AirflowRepository.upsert()` (similar pattern)

Only `ResourceRepository.upsert_run()` correctly uses PostgreSQL's `INSERT ... ON CONFLICT DO UPDATE` via `pg_insert`.

Under concurrent requests (e.g., two sync cycles overlapping despite the lock, or manual sync + scheduled sync), the SELECT-then-INSERT pattern can produce duplicate key violations or lost updates.

**Recommendation:** Migrate the high-traffic upsert paths (pipelines, lineage edges, bouncers) to use `pg_insert().on_conflict_do_update()` matching the pattern already established in `ResourceRepository.upsert_run()`. This is both safer and more performant (one round-trip instead of two).

### Finding 5.3: AirflowSyncService is a 400+ line "god method" coordinator

**Severity:** High
**Impact:** Testability, comprehension

`AirflowSyncService.sync_pipelines_from_airflow()` and its helper methods in `/home/ip04/EtlNexus/backend/app/services/airflow_sync_service.py` span 800+ lines and orchestrate 5 distinct phases (fetch, classify, upsert pipelines, sync resources, sync bouncers, sync DAG task graph).

The recent extraction of `task_classifier.py` was a good step. However, `_fetch_and_process_dag_data()` alone is 156 lines with deep nesting and multiple concerns (API fetching, classification, log parsing, data aggregation).

**Recommendation:**
1. Extract the phase A-E logic into a dedicated `AirflowDataFetcher` class that returns structured data (using the internal TypedDicts already defined in `schemas/internal.py`).
2. The `AirflowSyncService` becomes a pure orchestrator: fetch -> transform -> persist.
3. Each phase becomes independently testable.

### Finding 5.4: Duplicate `_parse_datetime` implementations

**Severity:** Low
**Impact:** DRY violation

The datetime parsing function `_parse_datetime(date_str)` is implemented in three places:
- `app/services/airflow_service.py` line 230 (as static method)
- `app/services/sync/task_classifier.py` line 78 (as `parse_datetime`)
- `app/services/airflow_sync_service.py` (uses the one from task_classifier)

**Recommendation:** Remove the duplicate from `AirflowService` and import `parse_datetime` from `task_classifier` instead.

### Finding 5.5: Domain exceptions defined but rarely used

**Severity:** Medium
**Impact:** Error handling quality

`/home/ip04/EtlNexus/backend/app/exceptions.py` defines five domain exceptions (`EtlNexusError`, `AirflowConnectionError`, `AirflowSyncError`, `PipelineNotFoundError`, `IcebergCatalogError`, `AuthorizationError`), but they are not used anywhere in the codebase. Services raise generic `ValueError` or return `None`, and routers translate to `HTTPException` directly.

**Recommendation:** Either adopt these exceptions in the service layer and add a centralized exception handler in `main.py` that maps them to appropriate HTTP responses, or remove the unused module to avoid dead code. The former approach is architecturally superior because it decouples service-layer error semantics from HTTP status codes.

### Finding 5.6: PipelineService receives repositories it sometimes does not need

**Severity:** Low
**Impact:** Unnecessary coupling

`PipelineService.update_pipeline_metadata()` and `restore_revision()` accept `revision_repo` as an optional parameter, and `get_pipeline_detail_for_user()` / `get_join_suggestions()` accept `grant_repo` as an optional parameter. This breaks the clean constructor-injection pattern: the service sometimes needs a `RevisionRepository` and sometimes needs a `VisibilityGrantRepository`, but they are passed per-method rather than per-instance.

**Recommendation:** Either add `revision_repo` and `grant_repo` to the `PipelineService` constructor (injected via `dependencies.py`), or split the service into `PipelineQueryService` (read operations) and `PipelineMutationService` (write operations with revision tracking). The per-method injection is pragmatic but breaks the expected pattern.

---

## 6. Architectural Consistency

### Finding 6.1 (HIGH): Inconsistent service construction patterns

**Severity:** High
**Impact:** Developer confusion, onboarding friction

Three different patterns exist for service construction:

**Pattern A -- Constructor injection via dependencies.py** (majority of services):
```python
def get_pipeline_service(...) -> PipelineService:
    return PipelineService(pipeline_repo, lineage_repo)
```

**Pattern B -- Raw session injection** (TopologyService, AirflowService):
```python
service = TopologyService(session)  # constructs own repos
```

**Pattern C -- Optional repo injection** (AirflowSyncService):
```python
def __init__(self, session, pipeline_repo=None, ...):
    self.pipeline_repo = pipeline_repo or PipelineRepository(session)
```

Pattern C in `AirflowSyncService` exists to support both dependency injection (router path) and direct construction (background task path). Pattern B is a plain inconsistency.

**Recommendation:** Standardize on Pattern A for all services. For background tasks that cannot use FastAPI's `Depends`, create the full dependency chain explicitly (session -> repos -> service). The `AirflowSyncService.__init__` with optional repos is a reasonable compromise for the background task use case, but `TopologyService` and `AirflowService` should be migrated to Pattern A.

### Finding 6.2 (HIGH): AirflowService and AirflowSyncService have overlapping responsibilities

**Severity:** High
**Impact:** Confusion, code duplication

Two services deal with Airflow:
- `AirflowSyncService` (`airflow_sync_service.py`): Pipeline discovery, lineage, resource configs, bouncers, and DAG task graph from Airflow
- `AirflowService` (`airflow_service.py`): Status polling, run history, resource actuals from Airflow

Both services:
- Parse datetime strings (duplicated)
- Handle Airflow task instance processing
- Interact with the same repositories (`pipeline_repo`, `resource_repo`, `bouncer_repo`, `airflow_repo`)
- Use the same semaphore/concurrency patterns (though each defines its own)
- Use the same `KNOWN_AIRFLOW_STATES` and `_STATUS_PRIORITY` constants (but `_STATUS_PRIORITY` is defined in `AirflowService` and imported by `AirflowSyncService`)

**Recommendation:** Consider merging these into a single `AirflowIntegrationService` with clearly separated public methods (`sync_pipelines()`, `poll_statuses()`), or formalize them as `AirflowDiscoveryService` and `AirflowPollService` with shared constants extracted to a `services/airflow/constants.py` module. The current split creates confusion about which service handles what.

### Finding 6.3: Frontend test coverage is limited to utility functions

**Severity:** Medium
**Impact:** Regression risk

The frontend test suite (under `/home/ip04/EtlNexus/frontend/src/test/`) covers:
- `format.test.ts` -- formatting utilities
- `lineage-utils.test.ts` -- lineage grouping helpers
- `permissions.test.ts` -- `isAdmin()` check
- `plan-parsers.test.ts` -- execution plan parsing
- `status-config.test.ts` -- status configuration
- `utils.test.ts` -- generic utilities

No tests exist for:
- React component rendering
- TanStack Query hook behavior
- Zustand store state transitions
- Auth flow (SSO vs non-SSO paths)
- API client interceptor logic (retry, 401 handling)

**Recommendation:** The utility function tests are good. Prioritize adding tests for the most complex/critical paths: (1) the auth bootstrap flow, (2) the API client retry interceptor, and (3) the pipeline store's filter state management. Component tests can use React Testing Library.

### Finding 6.4: Backend test suite is properly structured but uses only mocks

**Severity:** Low
**Impact:** Integration confidence

The 19 test files in `/home/ip04/EtlNexus/backend/tests/` use `MagicMock`/`AsyncMock` exclusively. There are no integration tests that exercise the actual async SQLAlchemy session against a test database. The `test_integration.py` file name suggests integration tests but would need to be verified.

**Recommendation:** For a project of this size, mock-based unit tests are sufficient. Consider adding a small number of integration tests that use an in-memory SQLite or a test PostgreSQL database to verify query correctness, especially for the complex `list_visible()` query with its visibility grant logic.

---

## 7. Security Posture

### Finding 7.1: Rate limiting applied inconsistently

**Severity:** Medium
**Impact:** Abuse resistance

The global rate limit is 200 requests/minute. Only one endpoint has a custom override:
- `POST /api/pipelines/{id}/sync` -- 30/minute (good, prevents sync flooding)

The AI architect endpoint (`/api/ai/chat`) has no specific rate limit despite proxying to an external LLM with cost implications. Similarly, the grant creation endpoint could be abused to create many grants rapidly.

**Recommendation:** Add endpoint-specific rate limits for:
- AI chat: 10-20/minute (LLM cost control)
- Grant creation: 30/minute (admin abuse prevention)
- User role/active updates: 10/minute (admin action limiting)

### Finding 7.2: Health endpoint leaks service connectivity status

**Severity:** Low
**Impact:** Information disclosure

The `/api/health` endpoint at `/home/ip04/EtlNexus/backend/app/routers/health.py` returns whether Airflow, Iceberg, and the database are connected. This is useful for monitoring but should not be exposed to unauthenticated callers in production.

**Recommendation:** Consider splitting into a public health endpoint (returns only `"healthy"`/`"unhealthy"`) and an authenticated admin health endpoint that returns the full service status breakdown.

---

## 8. Infrastructure and Deployment

### Finding 8.1: Docker Compose development setup is well-structured

**Severity:** N/A (positive finding)
**Impact:** Developer experience

The `docker-compose.yml` demonstrates good practices:
- Health checks on all stateful services
- Proper `depends_on` with `condition` specifications
- `develop.watch` configuration for auto-sync
- Separate init containers for volume permissions
- Iceberg data seeding as a dependency chain

No issues found in the infrastructure layer.

### Finding 8.2: No production Docker Compose Keycloak configuration

**Severity:** Low
**Impact:** Production readiness

The `docker-compose.prod.yml` references exist but the production setup is expected to use external Keycloak. This is fine but should be documented for operators.

---

## Summary Table

| # | Finding | Severity | Category |
|---|---------|----------|----------|
| 1.1 | TopologyService bypasses DI pattern | Medium | Component Boundaries |
| 1.2 | Lineage router contains business logic | Medium | Component Boundaries |
| 1.3 | Cache interaction across multiple layers | Low | Component Boundaries |
| 2.1 | Circular imports via bottom-of-file imports | Low | Dependencies |
| 2.2 | Deferred imports in auth.py | Low | Dependencies |
| 2.3 | Module-level singleton integration clients | Low | Dependencies |
| 3.1 | **Bouncer model retains "sensor" DB naming** | **Critical** | Data Model |
| 3.2 | Denormalized team column (documented, acceptable) | Low | Data Model |
| 3.3 | edge_type stored as unconstrained string | Medium | Data Model |
| 3.4 | PipelineUsage lacks FK to Pipeline | Medium | Data Model |
| 4.1 | Inconsistent router prefix handling | Medium | API Design |
| 4.2 | Delete/update endpoints return untyped dicts | Low | API Design |
| 4.3 | No API versioning strategy | Medium | API Design |
| 4.4 | Date range filtering inconsistency | Medium | API Design |
| 5.1 | **TopologyService loads all pipelines per call** | **Critical** | Patterns |
| 5.2 | Upsert uses SELECT-then-INSERT (race condition) | High | Patterns |
| 5.3 | AirflowSyncService is oversized coordinator | High | Patterns |
| 5.4 | Duplicate _parse_datetime implementations | Low | Patterns |
| 5.5 | Domain exceptions defined but unused | Medium | Patterns |
| 5.6 | Per-method repo injection breaks DI consistency | Low | Patterns |
| 6.1 | **Three service construction patterns** | **High** | Consistency |
| 6.2 | **AirflowService/AirflowSyncService overlap** | **High** | Consistency |
| 6.3 | Frontend tests cover only utilities | Medium | Consistency |

---

## Recommended Prioritization

### Immediate (next sprint)

1. **Finding 3.1** -- Complete the sensor-to-bouncer rename at the database/file level. This is an active source of confusion and the branch is already dedicated to this rename.
2. **Finding 5.1** -- Replace `get_all()` in TopologyService with a lightweight query or cached map. This is a scalability cliff.

### Short-term (next 2-4 weeks)

3. **Finding 5.2** -- Migrate upsert patterns to PostgreSQL `ON CONFLICT` for pipelines, lineage edges, and bouncers.
4. **Finding 6.1** -- Standardize service construction on Pattern A (constructor injection via dependencies.py).
5. **Finding 1.2** -- Extract lineage graph construction into a service.

### Medium-term (next quarter)

6. **Finding 5.3** -- Decompose AirflowSyncService into fetcher + orchestrator.
7. **Finding 6.2** -- Consolidate or clearly separate the two Airflow services.
8. **Finding 5.5** -- Adopt domain exceptions with centralized HTTP mapping.
9. **Finding 6.3** -- Add frontend tests for auth flow and API client interceptors.

---

## Positive Architectural Observations

The review also notes several strong architectural decisions:

1. **Clean three-layer pattern adherence** -- The Router -> Service -> Repository layering is consistently applied across 15+ domain areas with proper dependency injection.

2. **Pydantic schema discipline** -- Request/response DTOs are well-separated from ORM models. The new `schemas/internal.py` TypedDicts bridge the gap between untyped dicts and full Pydantic validation for internal data flow.

3. **Auth architecture** -- The dual-issuer OIDC support, JIT user provisioning with LRU caching, team reconciliation from JWT claims, and the `sso_enabled` toggle for local development are all well-designed. The auth guards (`require_role`, `require_team_membership`, `require_team_membership_or_editor_grant`) form a clean authorization hierarchy.

4. **Frontend state management** -- The clear boundary between server state (TanStack Query for all API data) and client state (Zustand for UI-only state like selected pipeline, active tab, search query) is textbook-correct. No Redux.

5. **Lazy loading** -- Top-level views use `React.lazy()` with `Suspense` boundaries, reducing initial bundle size.

6. **API client resilience** -- The Axios interceptor handles 401 token refresh, transient error retry (502/503/504), and network failure retry with configurable limits.

7. **Background task architecture** -- The APScheduler setup with separate sync/poll locks, startup readiness waiting, and independent error handling per task is robust.

8. **Visibility grant system** -- The CHECK constraints ensuring XOR semantics (exactly one of pipeline_id/source_team_id, exactly one of grantee_team_id/grantee_user_id) at the database level, combined with the Pydantic `model_validator` at the API level, provide defense-in-depth data integrity.

9. **TTL cache with sync-cycle invalidation** -- The `clear_all()` call after every sync/poll cycle ensures caches never serve stale data beyond one sync interval. The cache key construction in `PipelineService` accounts for user/team context correctly.

10. **Task classifier extraction** -- The recent extraction of pure functions into `sync/task_classifier.py` (bouncer detection, API detection, display name conversion, team/category extraction, param unwrapping) is a good example of the project improving its architectural hygiene.
