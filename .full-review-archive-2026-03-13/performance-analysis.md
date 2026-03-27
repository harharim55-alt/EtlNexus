# EtlNexus Performance & Scalability Analysis

**Date:** 2026-03-13
**Scope:** Full codebase — backend (FastAPI + async SQLAlchemy + PostgreSQL), frontend (React 19 + TypeScript + Vite), background tasks (APScheduler), integrations (Airflow API, Iceberg/PySpark, LLM)

---

## Table of Contents

1. [Critical Issues](#1-critical-issues)
2. [High-Severity Issues](#2-high-severity-issues)
3. [Medium-Severity Issues](#3-medium-severity-issues)
4. [Low-Severity Issues](#4-low-severity-issues)
5. [Architecture-Level Scalability Concerns](#5-architecture-level-scalability-concerns)
6. [Summary Matrix](#6-summary-matrix)

---

## 1. Critical Issues

### 1.1 Synchronous PySpark Blocks the Async Event Loop

**File:** `backend/app/integrations/iceberg_client.py`
**Severity:** Critical
**Impact:** During catalog sync (every 2 hours), all synchronous Spark calls (`_get_spark()`, `list_tables_in_namespace()`, `get_table_schema()`, `get_all_dagger_schemas()`) block the single asyncio event loop. While Spark is executing, **no HTTP requests can be served**. SparkSession creation alone can take 5-15 seconds; iterating over all tables can take minutes.

**Root Cause:** The `IcebergClient` methods are synchronous (no `async`), but they are called from `CatalogSyncService.sync_from_catalog()`, which itself is an `async` method. The call at line 25 (`iceberg_client.get_all_dagger_schemas()`) is not wrapped in `asyncio.to_thread()` or `run_in_executor()`.

**Recommendation:** Wrap all Spark calls in `asyncio.to_thread()`:

```python
# In CatalogSyncService.sync_from_catalog():
schemas = await asyncio.to_thread(iceberg_client.get_all_dagger_schemas)
```

Or wrap each synchronous method at the client level:

```python
async def get_all_dagger_schemas_async(self) -> list[IcebergTableSchema]:
    return await asyncio.to_thread(self.get_all_dagger_schemas)
```

---

### 1.2 Full Pipeline Table Load on Every Request — 6 Services

**Files:**
- `backend/app/services/topology_service.py` lines 64, 221
- `backend/app/services/ai_service.py` lines 45, 74
- `backend/app/services/consumer_service.py` line 27
- `backend/app/services/sensor_service.py` (BouncerService) line 82
- `backend/app/services/usage_service.py` line 43

**Severity:** Critical
**Impact:** Every topology, consumer, usage, bouncer topology, or AI request calls `pipeline_repo.get_all()`, which loads all Pipeline rows with eager-loaded `airflow_status`. With 30 pipelines this is tolerable; at 300+ pipelines, each call fetches hundreds of rows just to build a `task_id -> pipeline` dict. At 1000+ pipelines, response times degrade to seconds and memory pressure increases significantly.

**Root Cause:** Services need a `task_id -> pipeline` lookup but achieve it by loading the entire table. There is no pre-built index/cache for this mapping.

**Recommendation:**
1. Create a dedicated repository method that returns only `(task_id, id, name, airflow_status)` tuples:
```python
async def get_task_id_map(self) -> dict[str, Pipeline]:
    stmt = (
        select(Pipeline.task_id, Pipeline.id, Pipeline.name)
        .where(Pipeline.task_id.isnot(None))
    )
    # Returns lightweight mapping without loading full ORM objects
```
2. Cache this mapping at the application layer (already have `pipeline_list_cache`) with a dedicated key like `"task_id_map"`. Invalidate on sync.
3. For `AIService._build_catalog_context()` which already limits to 20 pipelines (line 79), this is less impactful, but `get_join_insight()` calls `get_all_with_fields()` which is the heaviest variant -- loads all pipelines with all field relationships.

---

### 1.3 BFS Uses `list.pop(0)` — O(n^2) Quadratic Time

**Files:**
- `backend/app/services/topology_service.py` lines 94, 237, 269, 330
- `backend/app/services/sensor_service.py` (BouncerService) lines 111, 269 (same `pop(0)` pattern)

**Severity:** Critical
**Impact:** `list.pop(0)` in Python is O(n) because it shifts all remaining elements. In a BFS loop, this makes the overall algorithm O(n^2) instead of O(n). The `TopologyService.build_upstream_topology()` method has **four** separate BFS loops, each using `list.pop(0)`. For deep dependency graphs (10+ levels, 100+ nodes), this compounds to significant latency.

**Recommendation:** Replace `list` with `collections.deque`:

```python
from collections import deque

queue = deque([my_task_id])
while queue:
    tid = queue.popleft()  # O(1) instead of O(n)
    ...
    queue.append(upstream_tid)
```

This is a one-line change per BFS loop, 8 locations total.

---

### 1.4 N+1 Queries in DagSummaryService — Per-DAG Sequential Queries

**File:** `backend/app/services/dag_summary_service.py` lines 90-116
**Severity:** Critical
**Impact:** For each DAG in the system (currently 6, but designed to grow), the service issues **four sequential DB queries** inside a loop:
1. `resource_repo.get_dag_run_stats(dag_id)` (line 101)
2. `resource_repo.get_latest_runs_by_dag(dag_id)` (line 107)
3. `resource_repo.get_typical_finish_hour(dag_id)` (line 110)
4. `dag_task_repo.get_tasks_for_dag_with_pipeline(dag_id)` (line 115)

With 6 DAGs: 24 sequential queries. With 50 DAGs: 200 queries. Even though the response is cached, the first request (or after cache invalidation every 60 seconds) pays the full cost.

**Recommendation:**
1. **Batch the aggregations.** Create repository methods that accept `list[str]` of DAG IDs and return results for all DAGs in a single query using `GROUP BY dag_id`.
2. **Use `asyncio.gather` for independent DAG queries** at minimum:
```python
# Instead of sequential loop, gather all per-dag stats in parallel:
all_run_stats = await asyncio.gather(*[
    self.resource_repo.get_dag_run_stats(dag_id)
    for dag_id in all_dag_ids
])
```
3. **Increase cache TTL** from 60s (medium) to match the sync interval (20 min) since DAG summary data only changes on sync.

---

### 1.5 LLM Client Creates New HTTP Connection Per Request

**File:** `backend/app/integrations/llm_client.py` lines 50-56
**Severity:** Critical
**Impact:** Every call to `llm_client.chat()` creates a new `httpx.AsyncClient`, performs TCP + TLS handshake, sends the request, then closes the connection. LLM calls have 30-second timeouts and are user-facing (AI terminal chat). The TCP/TLS overhead adds 50-200ms per call unnecessarily.

**Root Cause:** Line 50: `async with httpx.AsyncClient(timeout=self.timeout) as client:` creates and destroys a client on every invocation.

**Contrast:** The Airflow client (`airflow_client.py`) correctly uses a persistent `self._client` with connection pooling. The LLM client should follow the same pattern.

**Recommendation:** Use a persistent client, matching the Airflow client pattern:

```python
class LLMClient:
    def __init__(self):
        ...
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
        )

    async def chat(self, messages, system_prompt=None):
        ...
        resp = await self._client.post(...)

    async def close(self):
        await self._client.aclose()
```

Add `llm_client.close()` to the app lifespan shutdown handler.

---

## 2. High-Severity Issues

### 2.1 `get_all_entries()` Loads Entire `dag_tasks` Table into Memory

**File:** `backend/app/repositories/dag_task_repo.py` line 93-96
**Caller:** `backend/app/services/sensor_service.py` (BouncerService) line 71

**Severity:** High
**Impact:** `BouncerService.get_bouncer_topology()` calls `dag_task_repo.get_all_entries()` which executes `SELECT * FROM dag_tasks` with no filtering. All rows are loaded into Python memory, then two dict indexes are built in-memory (lines 73-79). Currently ~200 rows, but this scales linearly with DAG count x task count.

**Recommendation:** Move the graph traversal to SQL or at minimum filter to only the relevant DAGs. For the BFS pattern, consider a recursive CTE or load only the DAGs that contain the selected bouncers:

```python
# Only load tasks for DAGs containing the selected bouncers
bouncer_dag_ids = {dt.dag_id for b in bouncer_names for dt in task_by_id[b]}
relevant_tasks = await self.dag_task_repo.get_tasks_for_dags(list(bouncer_dag_ids))
```

---

### 2.2 No Database Index on `pipeline_run_history.start_date`

**File:** `backend/app/models/run_history.py` line 23
**Severity:** High
**Impact:** Multiple queries filter by `start_date`:
- `get_recent_runs()`: `ORDER BY start_date DESC`
- `get_run_stats()`: `WHERE start_date >= cutoff`
- `get_dag_run_stats()`: `WHERE start_date >= cutoff`
- `get_latest_runs_by_dag()`: `ORDER BY start_date DESC LIMIT 1`
- `get_typical_finish_hour()`: `WHERE start_date >= cutoff`
- `get_execution_plan_runs()`: `ORDER BY start_date DESC`
- `PipelineRepository.list_visible()`: subquery on `start_date` range

Without an index, all these queries do full table scans. `pipeline_run_history` grows continuously (5 runs per DAG per poll, 6 DAGs = 30 rows per 20 min = 2160 rows/day). After months: hundreds of thousands of rows.

**Recommendation:** Add a composite index:
```python
# In PipelineRunHistory model
__table_args__ = (
    UniqueConstraint(...),
    Index("ix_run_history_pipeline_start", "pipeline_id", "start_date"),
    Index("ix_run_history_dag_start", "dag_id", "start_date"),
)
```

---

### 2.3 No Index on `lineage_edges.(source_table, target_table, edge_type)`

**File:** `backend/app/models/lineage.py`
**Severity:** High
**Impact:** `LineageRepository.upsert_edge()` (called dozens of times per sync cycle) queries by `(source_table, target_table, edge_type)` to check for existing edges. Without a composite index, each upsert does a full table scan. During a full sync with 30 pipelines having 3-5 edges each = 90-150 sequential scans per sync cycle.

**Recommendation:**
```python
# Add to LineageEdge model
__table_args__ = (
    Index("ix_lineage_edge_lookup", "source_table", "target_table", "edge_type"),
)
```

---

### 2.4 `_fetch_single_pipeline_data` Calls `get_all_dags()` Twice

**File:** `backend/app/services/airflow_sync_service.py` lines 525-526, 566
**Severity:** High
**Impact:** `_find_target_dags()` calls `airflow_client.get_all_dags()` (line 526), and then `_fetch_single_pipeline_data()` calls it again (line 566). The Airflow client has a 5-minute TTL cache, so the second call hits the cache. However, the result is a potentially large list of DAG definitions that gets deserialized and allocated twice in the calling code. More importantly, the architectural pattern creates confusion and makes the code harder to optimize.

**Recommendation:** Pass the `all_dags` result from `_find_target_dags()` into `_fetch_single_pipeline_data()` to avoid the redundant call:

```python
async def sync_single_pipeline(self, pipeline_id):
    ...
    all_dags = await airflow_client.get_all_dags()
    target_dag_ids = await self._find_target_dags(task_id, all_dags)
    meta, ... = await self._fetch_single_pipeline_data(task_id, target_dag_ids, all_dags)
```

---

### 2.5 Unbounded Chat History in AI Store (Frontend Memory Leak)

**File:** `frontend/src/stores/ai-store.ts` lines 21-22
**Severity:** High
**Impact:** The `addMessage` action appends to an ever-growing array: `messages: [...state.messages, msg]`. Each message creates a new array copy (immutable pattern). Over a long session, this creates significant memory pressure:
- 100 messages x ~2KB each = 200KB of messages + 100 intermediate array copies
- Messages include the full LLM catalog context that is echoed back
- No upper bound or eviction policy

Additionally, all `messages` are sent back to the backend on each `/api/ai/chat` request as `history`, meaning request payload size grows linearly.

**Recommendation:**
1. Cap the in-memory message array to e.g. 50 messages:
```typescript
addMessage: (msg) =>
    set((state) => {
        const updated = [...state.messages, msg];
        return { messages: updated.length > 50 ? updated.slice(-50) : updated };
    }),
```
2. When sending history to the backend, limit to the last N messages (e.g., 10) to keep payload reasonable:
```typescript
const recentHistory = messages.slice(-10);
```

---

### 2.6 No Pagination on `get_all()` Usage in Background Tasks

**Files:**
- `backend/app/services/airflow_service.py` line 56: `pipelines = await self.pipeline_repo.get_all()`
- `backend/app/services/airflow_service.py` line 77: `all_bouncers = await self.bouncer_repo.get_all()`

**Severity:** High
**Impact:** The poll task loads all pipelines and all bouncers into memory before processing. With growth, this becomes a memory concern. The poll task already loads all DAG runs and all task instances -- each additional pipeline amplifies the Airflow API call count (O(DAGs x runs_per_DAG x tasks_per_run)).

**Recommendation:** Process pipelines in batches, or at minimum use streaming/cursoring for the DB query to avoid loading all ORM objects simultaneously. For the poll service specifically, consider processing one DAG at a time and committing per-DAG to limit transaction scope and memory.

---

## 3. Medium-Severity Issues

### 3.1 Cache Invalidation is Too Aggressive — `clear_all()` After Every Sync/Poll

**File:** `backend/app/tasks/scheduler.py` lines 37-38, 53-54
**Severity:** Medium
**Impact:** After every sync and poll cycle (every 20 minutes), ALL caches are cleared, including:
- `pipeline_list_cache` (30s TTL anyway)
- `schema_matrix_cache` (60s TTL)
- `topology_cache` (30s TTL)
- `dag_summary_cache` (60s TTL)
- `bouncer_cache` (60s TTL)
- `join_suggestions_cache` (60s TTL)
- `grant_level_cache` (30s TTL)

This creates a "thundering herd" problem: immediately after sync/poll completes, all next requests hit the database simultaneously since no caches are warm.

**Recommendation:**
1. Only clear caches relevant to the completed operation. Pipeline sync should only clear `pipeline_list_cache`, `topology_cache`, and `join_suggestions_cache`. Status poll should only clear `dag_summary_cache`.
2. Consider staggered cache warming -- after clearing, pre-populate the most common cache keys (e.g., the unfiltered admin pipeline list).

---

### 3.2 Sequential Lineage Upserts During Sync

**File:** `backend/app/services/airflow_sync_service.py` lines 349-353
**Severity:** Medium
**Impact:** For each pipeline, lineage edges are upserted one at a time in a loop. With 30 pipelines having 3-5 edges each, this is 90-150 individual SELECT + INSERT/UPDATE pairs. Using bulk `INSERT ... ON CONFLICT` would reduce this to 1 query per pipeline.

**Recommendation:**
```python
# Instead of looping upsert_edge(), use bulk insert with ON CONFLICT:
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = pg_insert(LineageEdge).values(edges_to_create)
stmt = stmt.on_conflict_do_update(
    index_elements=["source_table", "target_table", "edge_type"],
    set_={...}
)
await self.session.execute(stmt)
```

---

### 3.3 `list_visible()` Issues Two Queries (Count + Data)

**File:** `backend/app/repositories/pipeline_repo.py` lines 256-273
**Severity:** Medium
**Impact:** Every paginated pipeline list request issues two separate queries: one for the total count, one for the data. For complex visibility-filtered queries with subqueries and OR conditions, the count query re-evaluates all the same conditions.

**Recommendation:** Use a window function to get the total count in a single query:
```python
from sqlalchemy import over, func

total_col = func.count().over().label("total")
# Add total_col to the SELECT, fetch total from the first row
```

Alternatively, for the common case where the full list fits in one page (pipelines.length < limit), skip the count query entirely:
```python
if len(pipelines) < limit:
    total = skip + len(pipelines)  # No need for count query
```

---

### 3.4 TTL Cache Has No Maximum Size Bound

**File:** `backend/app/cache.py`
**Severity:** Medium
**Impact:** The `TTLCache` class uses a plain dict with no size limit. Keys are generated from various combinations of user IDs, team IDs, skip/limit, pipeline IDs, etc. In theory, an attacker could generate thousands of unique cache keys (via different pagination params) to exhaust server memory. Additionally, expired entries are only removed on access (lazy eviction), so stale entries can accumulate.

**Recommendation:**
1. Add a `max_size` parameter to `TTLCache`:
```python
class TTLCache[T]:
    def __init__(self, ttl: int = 30, max_size: int = 1000):
        self._max_size = max_size
        ...

    def set(self, key: str, value: T) -> None:
        if len(self._store) >= self._max_size:
            self._evict_expired_or_oldest()
        self._store[key] = (time.monotonic(), value)
```
2. Add periodic eviction of expired entries (e.g., in `set()` or via a background sweep).

---

### 3.5 `TopologyService.build_pipeline_topology` Calls `get_tasks_for_dag` Per Active DAG

**File:** `backend/app/services/topology_service.py` lines 78-79
**Severity:** Medium
**Impact:** For each active DAG, a separate query is issued to load all tasks. With `asyncio.gather`, these could be parallelized, but currently they run sequentially in a `for` loop.

**Recommendation:**
```python
all_dag_tasks = await asyncio.gather(*[
    self.dag_task_repo.get_tasks_for_dag(adid)
    for adid in active_dag_ids
])
```
Or better, create a bulk method:
```python
async def get_tasks_for_dags(self, dag_ids: list[str]) -> list[DagTask]:
    stmt = select(DagTask).where(DagTask.dag_id.in_(dag_ids))
    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

---

### 3.6 `bouncer_repo.get_by_name()` Called Per Bouncer in Poll Phase 5

**File:** `backend/app/services/airflow_service.py` lines 214-217
**Severity:** Medium
**Impact:** After the poll completes, each bouncer status is updated via a per-bouncer `get_by_name()` SELECT query. With 10 bouncers, that is 10 extra queries. This could be done in a single bulk query.

**Recommendation:**
```python
# Replace per-bouncer lookups with a single batch
bouncers = await self.bouncer_repo.get_by_names(list(bouncer_best_status.keys()))
for bouncer in bouncers:
    if bouncer.sensor_name in bouncer_best_status:
        bouncer.status = bouncer_best_status[bouncer.sensor_name]
```

---

### 3.7 No Response Compression for Backend API

**File:** `backend/app/main.py`
**Severity:** Medium
**Impact:** The nginx reverse proxy has gzip enabled, but when running the backend directly (local dev, or if nginx is bypassed), API responses are uncompressed. Large responses like the DAG summary (which includes per-task details for all DAGs) or the schema matrix can be 50-200KB of JSON.

**Recommendation:** Add gzip middleware to FastAPI:
```python
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

### 3.8 `PipelineRegistry` Fetches `dagSummary` on the Pipeline List View

**File:** `frontend/src/components/pipeline-registry/PipelineRegistry.tsx` line 52
**Severity:** Medium
**Impact:** The pipeline registry sidebar calls `useDagSummary()` to build a DAG-to-pipeline mapping for client-side filtering. This triggers a full DAG summary fetch (which on the backend hits the expensive `_build_dag_summaries()` method) even when the user never uses DAG filters. The DAG summary response includes per-task details for every DAG -- a large payload loaded eagerly.

**Recommendation:** Fetch the DAG-to-pipeline mapping from a lightweight dedicated endpoint (e.g., `GET /api/dag-tasks/dag-pipeline-map`) instead of piggybacking on the full DAG summary. Or defer the `useDagSummary()` call until the filter drawer is opened:
```typescript
const { data: dagSummary } = useDagSummary({
    enabled: filtersOpen && dagFilters.size > 0
});
```

---

### 3.9 No Connection Pool Tuning Documentation or Dynamic Sizing

**File:** `backend/app/database.py` lines 9-10
**Severity:** Medium
**Impact:** Pool is set to `pool_size=20, max_overflow=10` (30 max connections). This is reasonable for a single backend instance, but:
- If multiple backend replicas are deployed, each gets its own pool, potentially exhausting PostgreSQL's default `max_connections=100`.
- The pool size isn't configurable via environment variables, requiring code changes to tune for different deployment sizes.
- No connection pool metrics/monitoring (exhaustion is silent -- requests just queue).

**Recommendation:**
1. Make pool settings configurable:
```python
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,      # default 20
    max_overflow=settings.db_max_overflow,  # default 10
    ...
)
```
2. Add pool event listeners for monitoring:
```python
from sqlalchemy import event
@event.listens_for(engine.sync_engine, "checkout")
def log_checkout(dbapi_conn, connection_record, connection_proxy):
    logger.debug("Pool checkout: %d/%d in use", pool.checkedin(), pool.size())
```

---

## 4. Low-Severity Issues

### 4.1 `request_id_middleware` Generates UUID But Doesn't Use It for Correlation

**File:** `backend/app/main.py` lines 139-143
**Severity:** Low
**Impact:** A UUID is generated per request and added to the response header, but it is not passed to the logger or used in log messages. This makes request tracing in logs difficult. The request ID should be added to the logging context.

**Recommendation:** Use Python's contextvars or logging filters to attach the request ID to all log output within a request:
```python
import contextvars
request_id_var = contextvars.ContextVar("request_id", default="-")

@app.middleware("http")
async def request_id_middleware(request, call_next):
    rid = str(uuid.uuid4())[:8]
    request_id_var.set(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response
```

---

### 4.2 `PipelineListItem` Is Not Memoized

**File:** `frontend/src/components/pipeline-registry/PipelineListItem.tsx`
**Severity:** Low
**Impact:** When the pipeline list re-renders (e.g., on selection change), every `PipelineListItem` re-renders even though only the active item changed. The virtualizer mitigates this by only rendering visible items, but wrapping the component in `React.memo` with a custom comparator would still reduce unnecessary reconciliation.

**Recommendation:**
```typescript
export const PipelineListItem = React.memo(
    function PipelineListItem({ pipeline, isActive, onClick }) { ... },
    (prev, next) =>
        prev.pipeline.id === next.pipeline.id &&
        prev.isActive === next.isActive
);
```

---

### 4.3 `Set` in Zustand Store Not Serializable

**File:** `frontend/src/stores/pipeline-store.ts` lines 8-10
**Severity:** Low
**Impact:** `teamFilters`, `dagFilters`, and `statusFilters` use JavaScript `Set`, which is not JSON-serializable. This prevents using Zustand's `persist` middleware if ever needed, and complicates debugging with DevTools.

**Recommendation:** Use plain arrays or records instead of Sets, or keep Sets but note this is a design trade-off that prevents persistence.

---

### 4.4 Frontend: No Error Boundary Around Individual Bento Cards

**File:** `frontend/src/components/bento-workspace/BentoWorkspace.tsx`
**Severity:** Low
**Impact:** If any individual bento card (e.g., `ResourcePerformanceCard`, `TransformInspectorCard`) throws a render error, the entire workspace crashes. There is a global `ErrorBoundary` component available at `frontend/src/components/shared/ErrorBoundary.tsx` but it is not used around individual cards.

**Recommendation:** Wrap each card in `<ErrorBoundary>`:
```tsx
<ErrorBoundary fallback={<CardErrorState />}>
    <ResourcePerformanceCard pipelineId={pipeline.id} />
</ErrorBoundary>
```

---

### 4.5 `delete_stale` Uses Large `NOT IN` Set

**File:** `backend/app/repositories/dag_task_repo.py` lines 98-115
**Severity:** Low
**Impact:** `delete_stale()` passes the full set of current `(dag_id, task_id)` pairs in a `WHERE NOT IN (...)` clause. With 200+ current pairs, this generates a very large SQL statement. PostgreSQL handles this reasonably well, but it's suboptimal compared to a temp table approach for large sets.

**Recommendation:** For small sets (< 500), the current approach is acceptable. For larger sets, consider:
```python
# Alternative: DELETE WHERE NOT EXISTS (SELECT FROM unnest(array))
# Or: Use a staging table pattern
```

---

### 4.6 nginx Configuration Missing `proxy_buffering` Tuning

**File:** `frontend/nginx.conf` lines 42-49
**Severity:** Low
**Impact:** The default nginx proxy buffering settings may cause issues with large API responses or SSE streams. No `proxy_buffer_size` or `proxy_buffers` are configured, relying on nginx defaults (4k/8k buffers). Large JSON responses (DAG summary, execution plans) may trigger multiple buffer allocations.

**Recommendation:**
```nginx
location /api/ {
    proxy_pass http://backend:8000/api/;
    ...
    proxy_buffer_size 16k;
    proxy_buffers 4 32k;
    proxy_busy_buffers_size 64k;
}
```

---

### 4.7 Rate Limiter Uses IP-Based Key — Shared IP Issue

**File:** `backend/app/rate_limit.py`
**Severity:** Low
**Impact:** `get_remote_address` uses the client IP for rate limiting (200/min). Behind a reverse proxy (nginx), all requests appear from the same IP unless `X-Forwarded-For` is properly handled. The nginx config sets `X-Real-IP` and `X-Forwarded-For`, but the SlowAPI default `get_remote_address` may not use these headers.

**Recommendation:** Use a custom key function that reads the forwarded header:
```python
def get_real_ip(request: Request) -> str:
    return request.headers.get("X-Real-IP", request.client.host)

limiter = Limiter(key_func=get_real_ip, default_limits=["200/minute"])
```

---

## 5. Architecture-Level Scalability Concerns

### 5.1 Single-Instance Scheduler — Horizontal Scaling Barrier

**File:** `backend/app/tasks/scheduler.py`
**Severity:** Architecture
**Impact:** APScheduler runs in-process with asyncio locks (`_sync_lock`, `_poll_lock`). If the backend is scaled to multiple replicas:
- Each replica runs its own scheduler, leading to duplicate sync/poll executions
- In-memory locks are not shared across processes
- In-memory caches are per-process and diverge

**Recommendation for horizontal scaling:**
1. Move scheduler to a separate worker process (Celery/ARQ/Dramatiq with Redis broker)
2. Use Redis-backed distributed locks (e.g., `python-redis-lock`)
3. Replace in-memory TTLCache with Redis-backed cache (ensures consistency across replicas)
4. Current architecture works fine for single-instance deployments

---

### 5.2 In-Memory Cache Not Shared Across Workers

**File:** `backend/app/cache.py`
**Severity:** Architecture
**Impact:** All caches are Python dicts in the process memory. If running with multiple Uvicorn workers (`--workers N`), each worker has its own cache, leading to:
- N times the memory usage for cached data
- Inconsistent responses between workers (one worker may have warm cache, another cold)
- Cache invalidation in one worker doesn't affect others

**Recommendation:** For multi-worker deployments, use a shared cache (Redis). For single-worker deployments (current), the in-memory cache is appropriate and performant.

---

### 5.3 Production Docker Compose Missing Backend Health Check Dependency

**File:** `docker-compose.prod.yml` lines 53-57
**Severity:** Architecture
**Impact:** The frontend depends on the backend with `depends_on: [backend]` but the backend has a healthcheck defined. The frontend should use `condition: service_healthy` to ensure it only starts after the backend is truly ready (migrations complete, initial sync started):
```yaml
depends_on:
    backend:
        condition: service_healthy
```

---

### 5.4 No Request Timeout Enforcement on Backend

**File:** `backend/app/main.py`
**Severity:** Architecture
**Impact:** There is no server-side request timeout. If a downstream service (Airflow, LLM) is slow, the request handler can block indefinitely (up to the httpx timeout of 10-30s). Multiple slow requests can exhaust the connection pool and degrade all users.

**Recommendation:** Add a request timeout middleware:
```python
import asyncio

@app.middleware("http")
async def timeout_middleware(request, call_next):
    try:
        return await asyncio.wait_for(call_next(request), timeout=60.0)
    except asyncio.TimeoutError:
        return JSONResponse(status_code=504, content={"detail": "Gateway timeout"})
```

---

### 5.5 Execution Plan JSON Stored as TEXT — No Structural Queries Possible

**File:** `backend/app/models/run_history.py` line 50
**Severity:** Architecture
**Impact:** Execution plans are stored as JSON strings in a TEXT column. They must be fully loaded and parsed in Python. Using PostgreSQL's native `JSONB` type would allow:
- Indexing on plan properties (e.g., find all plans with shuffle operations)
- Partial extraction without full deserialization
- GIN indexes for containment queries

**Recommendation:** In a future migration, change `execution_plan` to `JSONB`:
```python
from sqlalchemy.dialects.postgresql import JSONB
execution_plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

---

## 6. Summary Matrix

| # | Issue | Severity | Category | Est. Impact | Fix Effort |
|---|-------|----------|----------|-------------|------------|
| 1.1 | Synchronous PySpark blocks event loop | Critical | I/O Blocking | 100% request failures during sync | Low (1 line) |
| 1.2 | Full pipeline table load in 6 services | Critical | Database / Memory | 2-5x latency at 300+ pipelines | Medium |
| 1.3 | BFS `list.pop(0)` O(n^2) | Critical | Algorithm | 10x slower for deep graphs | Low (8 line changes) |
| 1.4 | N+1 queries in DagSummaryService | Critical | Database | 4 queries * N DAGs sequential | Medium |
| 1.5 | LLM client creates connection per request | Critical | I/O / Latency | 50-200ms overhead per chat | Low |
| 2.1 | `get_all_entries()` loads entire dag_tasks | High | Memory | Unbounded memory growth | Medium |
| 2.2 | Missing index on `run_history.start_date` | High | Database | Full table scans on growing table | Low (migration) |
| 2.3 | Missing composite index on lineage_edges | High | Database | 90-150 scans per sync | Low (migration) |
| 2.4 | Double `get_all_dags()` call | High | Network / Code | Redundant API call (cached) | Low |
| 2.5 | Unbounded chat history in AI store | High | Memory (Frontend) | Memory leak over long sessions | Low |
| 2.6 | No pagination in poll task pipeline load | High | Memory | Growing memory pressure | Medium |
| 3.1 | Cache `clear_all()` thundering herd | Medium | Caching | Spike after every sync/poll | Low |
| 3.2 | Sequential lineage upserts | Medium | Database | 90-150 round trips per sync | Medium |
| 3.3 | Dual count + data query for pagination | Medium | Database | 2x queries per list request | Medium |
| 3.4 | TTL cache has no max size | Medium | Memory | Potential OOM via key flooding | Low |
| 3.5 | Sequential `get_tasks_for_dag` per DAG | Medium | Database | N sequential queries | Low |
| 3.6 | Per-bouncer `get_by_name` in poll | Medium | Database | N queries at poll end | Low |
| 3.7 | No backend gzip compression | Medium | Network | 2-5x response sizes (no nginx) | Low |
| 3.8 | PipelineRegistry eagerly fetches dagSummary | Medium | Frontend / Network | Large unnecessary fetch | Low |
| 3.9 | Non-configurable DB pool size | Medium | Operations | Deploy flexibility | Low |
| 4.1 | Request ID not in log context | Low | Observability | Hard to trace requests | Low |
| 4.2 | PipelineListItem not memoized | Low | Frontend Render | Extra reconciliation work | Low |
| 4.3 | Set in Zustand not serializable | Low | Frontend / DX | Prevents persistence middleware | Low |
| 4.4 | No error boundary on bento cards | Low | Frontend Resilience | Single card crash = full crash | Low |
| 4.5 | Large NOT IN for stale deletion | Low | Database | Large SQL for 500+ pairs | Low |
| 4.6 | Missing nginx proxy buffer tuning | Low | Infrastructure | Suboptimal large response handling | Low |
| 4.7 | IP-based rate limiter behind proxy | Low | Security | Shared IP = shared limit | Low |
| 5.1 | Single-instance scheduler | Architecture | Scalability | Cannot scale horizontally | High |
| 5.2 | In-memory cache not shared | Architecture | Scalability | Inconsistent multi-worker behavior | High |
| 5.3 | Missing health check dependency (prod) | Architecture | Reliability | Frontend may start before backend | Low |
| 5.4 | No request timeout enforcement | Architecture | Reliability | Slow requests exhaust pool | Low |
| 5.5 | Execution plan as TEXT not JSONB | Architecture | Future Queries | No structural queries on plans | Medium |

---

## Priority Recommendations (Ordered by Impact/Effort Ratio)

**Immediate wins (high impact, low effort):**
1. Fix BFS `list.pop(0)` -> `deque.popleft()` — 8 one-line changes
2. Wrap IcebergClient calls in `asyncio.to_thread()` — 1 line change
3. Make LLM client use persistent `httpx.AsyncClient` — ~10 lines
4. Add `start_date` index to `pipeline_run_history` — 1 migration
5. Add composite index to `lineage_edges` — 1 migration

**Next tier (high impact, medium effort):**
6. Replace `get_all()` with `get_task_id_map()` across 6 services
7. Batch DagSummaryService queries with `asyncio.gather` or SQL aggregation
8. Add max size to TTLCache and cap AI chat history

**Strategic (architecture-level, for horizontal scaling):**
9. Move to Redis-backed cache if deploying multiple workers
10. Extract scheduler to a separate worker process
11. Add request timeout middleware
