# Phase 1: Code Quality & Architecture Review

## Code Quality Findings

### Critical

**CQ-C1. Fire-and-forget background tasks with no error propagation**
- **File:** `backend/app/main.py:66-67`
- `asyncio.create_task()` used without storing references. Exceptions silently swallowed; GC can cancel unreferenced tasks.
- **Fix:** Store task references, add done callbacks with exception logging.

**CQ-C2. New httpx.AsyncClient created per Airflow API request**
- **File:** `backend/app/integrations/airflow_client.py:53-56`
- Every `_request()` call creates/destroys a client. During sync, 50+ sequential HTTP requests each establish new TCP connections. No connection reuse/keep-alive.
- **Fix:** Use a persistent `httpx.AsyncClient` with connection pool, created once and shared.

**CQ-C3. N+1 query pattern in FieldFrequencyRepository**
- **File:** `backend/app/repositories/field_frequency_repo.py:11-47`
- Queries all distinct field names, then executes a separate query per field to find pipelines. Can result in 50-100+ sequential DB queries per API call.
- **Fix:** Single query with join + Python-side grouping, or use `array_agg`.

**CQ-C4. `get_all()` called repeatedly for small-set lookups**
- **Files:** `backend/app/routers/topology.py:53`, `backend/app/services/consumer_service.py:30`, `backend/app/services/usage_service.py:40`, `backend/app/services/pipeline_service.py:79`
- Full-table reads (up to 200 pipelines with eager-loaded relations) on every API request just to build lookup maps.
- **Fix:** Add targeted repository methods like `get_by_task_ids(task_ids)`.

### High

**CQ-H1. Duplicated code across AirflowService and AirflowSyncService**
- **Files:** `backend/app/services/airflow_service.py:136-210`, `backend/app/services/airflow_sync_service.py:462-580`
- `_parse_datetime()`, `_parse_resource_actual()`, and run history recording logic identically duplicated. Also `_to_task_id()` duplicated in `consumer_service.py:12`, `usage_service.py:13`, `usage_repo.py:24`.
- **Fix:** Extract shared utilities into `backend/app/utils/`.

**CQ-H2. Inconsistent timezone handling**
- **Files:** `backend/app/repositories/pipeline_repo.py:86`, `backend/app/repositories/resource_repo.py:117`, `backend/app/services/airflow_sync_service.py:246,411,445-446,485,489,496`
- Mixes deprecated `datetime.utcnow()` with `datetime.now(timezone.utc).replace(tzinfo=None)`.
- **Fix:** Standardize on a single `utc_now_naive()` utility function.

**CQ-H3. Airflow sync does serial API calls across all DAGs**
- **Files:** `backend/app/services/airflow_sync_service.py:59-148`, `backend/app/services/airflow_service.py:63-166`
- 50+ sequential HTTP requests with no parallelism. Combined with CQ-C2, makes sync extremely slow.
- **Fix:** Use `asyncio.gather()` to parallelize at the DAG level.

**CQ-H4. `sync_single_pipeline` is ~230 lines with cyclomatic complexity ~25+**
- **File:** `backend/app/services/airflow_sync_service.py:274-501`
- Single method handles lookup, DAG iteration, metadata collection, resource syncing, status tracking, log parsing, lineage rebuild, and run history — all with 5 levels of nesting.
- **Fix:** Decompose into focused private methods.

**CQ-H5. `DagTaskRepository.delete_stale` loads all rows for O(N) comparison**
- **File:** `backend/app/repositories/dag_task_repo.py:63-77`
- Loads every row, iterates in Python, deletes individually.
- **Fix:** Use bulk SQL DELETE with NOT IN clause.

**CQ-H6. Topology endpoint bypasses service layer**
- **File:** `backend/app/routers/topology.py:21-24`
- Directly creates repository instances, violating Router → Service → Repository pattern.
- **Fix:** Create `TopologyService` and wire through dependency injection.

**CQ-H7. Broad `except Exception` blocks in critical sync paths**
- **Files:** `backend/app/services/airflow_sync_service.py:202,249,392,413,469`, `backend/app/services/airflow_service.py:141`
- Catches all exceptions including programming errors. Failed syncs still counted as successful.
- **Fix:** Catch specific expected exceptions; only increment success counter after full pipeline sync succeeds.

**CQ-H8. Frontend IIFE inside JSX in ResourcePerformanceCard**
- **File:** `frontend/src/components/bento-workspace/ResourcePerformanceCard.tsx:380-437`
- IIFE in JSX return computes filtered data; no memoization, re-runs every render.
- **Fix:** Extract to `useMemo` hooks.

### Medium

**CQ-M1. Duplicated `parseMemoryGb` logic between backend and frontend**
- Backend: `backend/app/services/resource_service.py:194-206`, Frontend: `frontend/src/components/bento-workspace/ResourcePerformanceCard.tsx:272-280`

**CQ-M2. TTL cache in AirflowClient not thread-safe, unbounded growth**
- `backend/app/integrations/airflow_client.py:17-38` — stale entries only cleaned on access.

**CQ-M3. Object identity comparison `if run is runs[0]`**
- `backend/app/services/airflow_service.py:148` — should use index comparison.

**CQ-M4. Search query vulnerable to SQL LIKE wildcard injection**
- `backend/app/repositories/pipeline_repo.py:39-40` — `%` and `_` in user input treated as wildcards.

**CQ-M5. Frontend constructs `etlName` from display name via string manipulation**
- `frontend/src/components/bento-workspace/BentoWorkspace.tsx:80` — fragile reverse-engineering of task_id.

**CQ-M6. `_compute_capacity` repeats identical boilerplate 4 times**
- `backend/app/services/resource_service.py:98-192` — missed data-driven abstraction.

**CQ-M7. Stale "git sync" comments**
- `backend/app/services/catalog_sync_service.py:34` — references removed git-based discovery.

**CQ-M8. Status tracking vs history recording not separated in poll loop**
- `backend/app/services/airflow_service.py:66-167` — interleaved logic.

**CQ-M9. Missing input validation on `etl_name` path parameter**
- `backend/app/routers/usage.py:10`, `backend/app/routers/consumers.py:10`.

**CQ-M10. STATUS_CONFIG / STATUS_DOT duplicated across 3 frontend components**
- `LineageTopology.tsx:12-36`, `UsageCard.tsx:10-22`, `ResourcePerformanceCard.tsx:21-28` — with inconsistent colors.

**CQ-M11. Health endpoint makes real Airflow HTTP call on every check**
- `backend/app/routers/health.py:13-30`.

**CQ-M12. Module-level singleton clients prevent testing/reconfiguration**
- `airflow_client.py:178`, `iceberg_client.py:168`, `llm_client.py:70`.

### Low

**CQ-L1.** `SyncResponse` defined inline in `api/pipelines.ts` instead of `types/`.
**CQ-L2.** `typing.Optional` import in topology router (rest of codebase uses `X | None`).
**CQ-L3.** Circular import workarounds via bottom-of-file imports in models.
**CQ-L4.** `_parse_description` duplicates `_task_id_to_display_name`.
**CQ-L5.** `DagNetworkCard` and `LineageTopology` both call `useTopology` independently.
**CQ-L6.** `SchemaViewer.getDisplayDataType` uses substring matching (e.g., "valid" matches "id").
**CQ-L7.** `seed_usage_data` uses `datetime.now()` without timezone.

---

## Architecture Findings

### High

**AR-H1. Topology router bypasses service layer** (same as CQ-H6)
- Router directly instantiates repos, embeds ~80 lines of business logic.
- Only domain not following the Router → Service → Repository pattern.

**AR-H2. Duplicated Airflow parsing logic across two services** (same as CQ-H1)
- Identical `_parse_datetime`, `_parse_resource_actual`, and run history loops in both `AirflowService` and `AirflowSyncService`.

**AR-H3. Race condition in startup initialization**
- **File:** `backend/app/main.py:66-67`
- `_startup_sync()` and `poll_airflow_statuses()` launched concurrently. Both mutate `airflow_run_statuses` and `pipeline_run_history` tables. Poll may run before sync creates pipelines, or both may upsert same rows concurrently.
- **Fix:** Await `_startup_sync()` before launching poll.

**AR-H4. Inconsistent API identifiers across endpoints**
- Pipelines use UUID (`/api/pipelines/{pipeline_id}`), but usage and consumers use string name (`/api/usage/{etl_name}`, `/api/consumers/{etl_name}`).
- Forces frontend to reverse-engineer `etl_name` from display name.
- **Fix:** Standardize on UUID, or expose `task_id` in `PipelineDetail` schema.

### Medium

**AR-M1. Lineage router bypasses service layer**
- `backend/app/routers/lineage.py:18-82` — directly injects repositories and assembles graph.

**AR-M2. `PipelineUsage` not linked to `Pipeline` by foreign key**
- Uses `etl_name` (String) with no FK to `pipelines` table. No referential integrity or cascading deletes.

**AR-M3. `AirflowSyncService` mixes abstraction levels**
- Uses repositories for CRUD but also calls `self.session.commit()` and `self.session.begin_nested()` directly.

**AR-M4. CORS uses wildcard methods and headers**
- `backend/app/main.py:90-96` — `allow_methods=["*"]`, `allow_headers=["*"]` when only GET/POST used.

**AR-M5. No pagination on list endpoints**
- `GET /api/pipelines` returns all (up to hardcoded 200 limit). `GET /api/schema-matrix` returns all field frequencies.

**AR-M6. ResourcePerformanceCard contains excessive server-side business logic**
- 448-line component with `parseMemoryGb`, `recomputeCapacityBars`, `computeRunStats` — logic the API should handle with a `dag_id` filter parameter.

**AR-M7. New HTTP client per request (architectural impact)**
- No connection pooling across the sync lifecycle.

**AR-M8. Production compose may be missing backend port binding / proxy config**
- `docker-compose.prod.yml` doesn't expose backend ports. Needs Nginx proxy_pass verification.

### Low

**AR-L1.** Airflow router directly uses repository (minor inconsistency).
**AR-L2.** Missing `ai_join_insight` response model (no Pydantic schema).
**AR-L3.** `DagTask` model missing back-relationship to `Pipeline.dag_tasks`.
**AR-L4.** String-typed enumerations instead of proper enums (`status`, `edge_type`, `usage_type`).
**AR-L5.** No rate limiting on API endpoints (especially AI chat).
**AR-L6.** Background tasks create own sessions — correct but undocumented dual-use pattern.

---

## Critical Issues for Phase 2 Context

The following findings should inform the Security and Performance reviews:

1. **SQL LIKE wildcard injection** (CQ-M4) — needs security assessment for broader injection surface
2. **CORS wildcard configuration** (AR-M4) — security posture weakness
3. **Module-level singletons with hardcoded defaults** (CQ-M12) — credential exposure in config
4. **N+1 queries and `get_all()` overuse** (CQ-C3, CQ-C4) — primary performance bottlenecks
5. **Serial Airflow API calls with no connection pooling** (CQ-C2, CQ-H3) — sync performance
6. **No pagination** (AR-M5) — scalability concern
7. **Race condition in startup** (AR-H3) — data integrity risk
8. **No rate limiting** (AR-L5) — DoS and cost exposure risk
9. **Frontend business logic duplication** (AR-M6) — render performance concern
10. **Health endpoint real HTTP call** (CQ-M11) — availability under load
