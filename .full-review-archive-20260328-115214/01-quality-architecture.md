# Phase 1: Code Quality & Architecture Review

## Code Quality Findings

### Critical

1. **TTL Cache Thread Safety** (`backend/app/cache.py:17-38`) — The `TTLCache` class uses a plain `dict` with no synchronization. The `get()` method performs a read followed by a conditional `del`; concurrent async coroutines hitting an expired key can race. The `set()` and `clear()` methods interleave with `get()`, allowing stale data after `clear_all()`. **Fix:** Use `dict.pop(key, None)` instead of `del`, and consider `asyncio.Lock` for full safety.

### High

2. **TopologyService Loads All Pipelines Into Memory** (`backend/app/services/topology_service.py:73,229`) — Both `build_pipeline_topology` and `build_upstream_topology` call `self.pipeline_repo.get_all()` loading every pipeline with eagerly-loaded `airflow_status`. Only used for a `task_id -> pipeline` lookup. **Fix:** Replace with the lightweight `get_task_id_map()` method that already exists in `PipelineRepository`.

3. **BFS Algorithms Use `list.pop(0)` — O(n) per pop** (`backend/app/services/graph_builder.py:48,96,150,203`, `backend/app/services/bouncer_service.py:107,119`) — Six BFS implementations use `queue.pop(0)` which is O(n) on a Python list, turning O(V+E) BFS into O(V^2+E). **Fix:** Switch to `collections.deque` with `popleft()`.

4. **AirflowService Bypasses DI** (`backend/app/services/airflow_service.py:37-42`) — Directly constructs four repository instances from a raw session, bypassing FastAPI's dependency injection. **Fix:** Accept repositories as constructor parameters.

5. **TopologyService Also Bypasses DI** (`backend/app/services/topology_service.py:29-33`) — Same pattern. Also constructed directly in the router rather than through a dependency factory. **Fix:** Add `get_topology_service` factory to `dependencies.py`.

6. **Frontend Runtime Config Via `sed` Is Fragile** (`frontend/docker-entrypoint.sh:1-9`) — Production uses `sed` to replace a hardcoded string in compiled JS assets. Fails silently with regex-special characters, no validation. **Fix:** Inject a `config.js` file at container start with `window.__RUNTIME_CONFIG__`.

### Medium

7. **`_fetch_single_pipeline_metadata` Returns Untyped Dict** (`backend/app/services/airflow_sync_service.py:695-815`) — Returns a plain dict mixing public and underscore-prefixed keys. Caller pops private keys. **Fix:** Return a typed dataclass.

8. **`_limited()` Helper Duplicated 6 Times** (`backend/app/services/airflow_sync_service.py:243,390,668,708,897`, `airflow_service.py:66`) — Identical semaphore-limiting nested function defined in six different methods. **Fix:** Extract to module-level helper.

9. **PascalCase-to-Display-Name Regex Duplicated** (`backend/app/services/consumer_service.py:52`, `usage_service.py:112,128`) — Same regex duplicated inline. A utility already exists in `sync/task_classifier.py` but is not reused. **Fix:** Consolidate into one utility.

10. **Metrics Endpoint Has No Authentication** (`backend/app/routers/metrics.py:45`) — `/api/metrics` has no `get_current_user` dependency, violating the project convention. Exposes operational data. **Fix:** Add auth dependency.

11. **Prometheus Metrics Unbounded Growth** (`backend/app/routers/metrics.py:14-16`) — In-memory dictionaries grow indefinitely. **Fix:** Add cardinality cap or periodic rotation.

12. **AirflowClient Retries All Errors Without Backoff** (`backend/app/integrations/airflow_client.py:51-68`) — Retries 4xx errors (which will never succeed) and has no delay between retries. **Fix:** Only retry 5xx/network errors with exponential backoff.

13. **Auto-Commit on All Requests** (`backend/app/database.py:21-28`) — `get_db_session` auto-commits at the end of every request including read-only GET endpoints. **Fix:** Document the contract; consider explicit commits only on write paths.

14. **Pipeline `team` Column Denormalized Without Consistency Check** (`backend/app/models/pipeline.py:23-29`) — Both `team` (string) and `team_id` (FK) exist with no database constraint ensuring consistency. **Fix:** Add validation or constraint.

15. **Frontend Axios Has Conflicting Retry Interceptors** (`frontend/src/api/client.ts:20-73`) — Two response error interceptors with overlapping concerns. Custom config properties are untyped. **Fix:** Consolidate into single interceptor.

16. **Join Suggestions Cache Ignores User Visibility** (`backend/app/services/pipeline_service.py:283-339`) — Cached by `pipeline_id` only, but result depends on user visibility context. Admin result cached then served to non-admin. **Fix:** Include user context in cache key.

17. **AirflowSyncService Is a 994-Line God Service** (`backend/app/services/airflow_sync_service.py`) — Handles sync, fetching, classification, parsing, persistence, and history. **Fix:** Extract into `AirflowFetcher`, `TaskDiscoveryService`, `PipelinePersistenceService`.

18. **Broad `except Exception` in Sync Loops** (`backend/app/services/airflow_service.py:202-206`, `airflow_sync_service.py:511,600,863,987`) — Swallows all exceptions including programming errors. **Fix:** Narrow to specific exception types.

### Low

19. **`UserAuthService._PROVISION_CACHE` Reimplements LRU** (`backend/app/services/user_auth_service.py:24-56`) — Manual OrderedDict-based cache reimplements `cachetools.TTLCache` functionality.

20. **Closure Defined Inside Loop in TopologyService** (`backend/app/services/topology_service.py:125-135`) — `_make_task` closure captures loop variable via default arg. Correct but fragile. **Fix:** Move outside loop.

21. **Domain Exceptions Defined But Unused** (`backend/app/exceptions.py`) — Five domain exceptions defined but services raise `ValueError` or `HTTPException` instead.

22. **Frontend `PipelineRegistry` Has Competing `useEffect` Hooks** (`frontend/src/components/pipeline-registry/PipelineRegistry.tsx:132-145`) — Two effects both call `setSelectedPipelineId`. **Fix:** Consolidate into single effect.

23. **`LLMClient.chat` Returns Error Strings Instead of Raising** (`backend/app/integrations/llm_client.py:33-76`) — Cannot distinguish success from error. **Fix:** Use result type or raise exceptions.

24. **Production Docker Compose Missing Explicit Network Config** (`docker-compose.prod.yml:27-54`) — Backend port not exposed; relies on implicit Docker networking.

25. **IcebergClient Methods Are Synchronous in Async Context** (`backend/app/integrations/iceberg_client.py`) — Spark SQL operations block the event loop. **Fix:** Run in thread pool executor.

26. **Hardcoded Default Credentials** (`backend/app/config.py:13-14`) — `airflow_username`/`airflow_password` default to `"admin"/"admin"`. Production compose doesn't enforce overrides.

---

## Architecture Findings

### High

1. **TopologyService Bypasses Dependency Injection** (`backend/app/services/topology_service.py`, `routers/topology.py`) — Constructs its own repositories from raw session. Only service not wired through `dependencies.py`. Breaks testability and consistency. **Fix:** Add `get_topology_service` factory.

2. **Full Table Scan in Topology Construction** (`backend/app/services/topology_service.py:73,229`) — `get_all()` loads every pipeline with eager-loaded relationships just for a key-value lookup. `get_task_id_map()` already exists for this purpose. **Fix:** Use the lightweight method.

3. **In-Memory Cache Not Safe for Multi-Process Deployment** (`backend/app/cache.py`) — Module-level `TTLCache` singletons. `clear_all()` after sync only clears local process. Not an active bug (single-process deployment) but an invisible scaling constraint. **Fix:** Document assumption; plan Redis migration path.

### Medium

4. **Service Layer Mixed DI: Constructor vs Method Parameter** (`backend/app/services/pipeline_service.py`) — `PipelineService` receives some repos via constructor (proper DI) but `grant_repo` and `revision_repo` as method parameters. Creates split dependency model. **Fix:** Add all repos to constructor.

5. **Circular Import Resolution via Bottom-of-File Imports** (`backend/app/models/pipeline.py:78-82` and 6 other model files) — Resolved via bottom-of-file imports with noqa suppressions. Fragile when adding relationships. **Fix:** Test if SQLAlchemy 2.0 Mapped annotations eliminate the need.

6. **AirflowSyncService Constructor Dual Path** (`backend/app/services/airflow_sync_service.py`) — Optional `None` repositories with fallback construction. Background tasks bypass the DI graph entirely. **Fix:** Create dedicated factory for background task construction.

7. **Domain Exceptions Not Fully Utilized** (`backend/app/exceptions.py`) — Services return `None` or raise `ValueError` instead of domain exceptions. Dilutes both error handling patterns. **Fix:** Adopt domain exceptions with centralized handler, or remove unused ones.

8. **Health Check Calls External Airflow API** (`backend/app/routers/health.py`) — Live HTTP request on every health check. Orchestrator restarts if Airflow is slow. **Fix:** Separate liveness (DB-only) from readiness (full dependencies).

9. **No URL-Based Routing on Frontend** (`frontend/src/stores/navigation-store.ts`, `App.tsx`) — Navigation via Zustand `activeTab` only. No bookmarking, deep linking, or browser back/forward. **Fix:** Introduce URL-based routing (hash or React Router).

10. **Visibility Not Enforced on Sub-Resource Endpoints** — `/api/pipelines/{id}/lineage`, `/topology`, `/resources`, `/execution-plan`, `/runs`, plus `/api/usage/{etl_name}` and `/api/consumers/{etl_name}` skip visibility checks. Users who learn a UUID can access unauthorized data. **Fix:** Create `require_pipeline_visibility` dependency and apply to all sub-resource endpoints.

### Low

11. **Prometheus Metrics Use Unbounded In-Memory Dicts** (`backend/app/routers/metrics.py`) — Keys grow monotonically. **Fix:** Cap cardinality or use `prometheus_client`.

12. **TTLCache Lacks Thread Safety** (`backend/app/cache.py`) — Safe under current single-threaded asyncio model. **Fix:** Document assumption.

13. **Inconsistent API Response Contracts for Mutations** — Delete/update endpoints return bare `{"ok": True}` dicts without `response_model`. **Fix:** Define `OkResponse` Pydantic model.

14. **Frontend API Client Has Two Overlapping Error Interceptors** (`frontend/src/api/client.ts`) — Coincidentally correct execution order but fragile. **Fix:** Consolidate into single interceptor.

---

## Positive Observations

- **Clean three-layer separation** consistently followed across all 18 routers
- **Centralized visibility logic** via `VisibilityFilter` class — single source of truth for grant-based authorization SQL
- **Graph algorithms isolated from data access** — `graph_builder.py` is pure Python with no SQLAlchemy imports
- **Well-designed UpsertMixin** with configurable exclusion/condition callbacks
- **Structured logging** with `contextvars`-based request ID correlation
- **Comprehensive test coverage** — 27 backend test files, 20+ frontend test files
- **Background task orchestration** with separate locks, concurrent execution prevention, startup readiness handling
- **SSO with graceful degradation** — JIT provisioning, LRU-cached provisioning, default-admin fallback
- **Lazy-loaded frontend routes** via `React.lazy` and `Suspense`
- **Production Docker hardening** — resource limits, health checks, log rotation

---

## Critical Issues for Phase 2 Context

The following Phase 1 findings should inform the Security and Performance reviews:

### Security-Relevant
- **Visibility not enforced on sub-resource endpoints** — authorization gap allowing data access by UUID guessing
- **Metrics endpoint lacks authentication** — exposes operational data without auth
- **Join suggestions cache ignores visibility** — potential cross-tenant data leak
- **Hardcoded default credentials** in config.py
- **Frontend runtime config via sed** — potential injection vector

### Performance-Relevant
- **TopologyService loads all pipelines** — full table scan on every topology request
- **BFS uses O(n) pop(0)** — turns linear algorithms into quadratic
- **In-memory cache single-process assumption** — scaling limitation
- **IcebergClient blocks event loop** — synchronous Spark operations in async context
- **AirflowClient retries without backoff** — amplifies load during outages
- **Unbounded metrics dictionaries** — memory leak over long uptime
