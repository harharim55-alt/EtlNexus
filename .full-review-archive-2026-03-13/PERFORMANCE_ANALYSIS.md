# EtlNexus Performance & Scalability Analysis

**Date:** 2026-03-13
**Branch:** `feature/sensor-to-bouncer-rename`
**Scope:** Full-stack analysis -- backend (FastAPI + SQLAlchemy + PostgreSQL), frontend (React 19 + Vite), background tasks (APScheduler), integrations (Airflow API, Iceberg/PySpark, LLM)

---

## Executive Summary

The codebase is well-structured with good separation of concerns and several intentional performance decisions already in place (connection pooling, TTL caching, `selectinload` to avoid lazy-load N+1s, parallel Airflow API calls with semaphores, frontend lazy loading and chunking). However, the analysis reveals **5 Critical**, **7 High**, **9 Medium**, and **5 Low** severity findings across database access, memory management, I/O patterns, caching, concurrency, and frontend performance.

The most impactful issues are: (1) synchronous Spark blocking the async event loop during catalog sync, (2) repeated `get_all()` calls loading all pipelines into memory across 6+ services per request, (3) BFS algorithms using `list.pop(0)` creating O(n^2) behaviour, (4) the LLM client creating a new HTTP connection per request, and (5) N+1 sequential database queries in `DagSummaryService`.

---

## 1. Database Performance

### 1.1 N+1 Sequential Queries in DagSummaryService

**Severity: Critical**
**Impact: 4+ sequential DB queries per DAG, multiplied by number of DAGs (6). Total: ~24+ sequential queries per request.**

**File:** `/home/ip04/EtlNexus/backend/app/services/dag_summary_service.py`, lines 90-116

The `_build_dag_summaries` method loops over all DAG IDs and issues 4 sequential queries per DAG:

```python
for dag_id in all_dag_ids:
    run_stats = await self.resource_repo.get_dag_run_stats(dag_id, ...)      # Query 1
    latest_runs = await self.resource_repo.get_latest_runs_by_dag(dag_id)    # Query 2
    finish_hour = await self.resource_repo.get_typical_finish_hour(dag_id, ...) # Query 3
    tasks_in_dag = await self.dag_task_repo.get_tasks_for_dag_with_pipeline(dag_id) # Query 4
```

**Recommendation:** Batch these queries. Use `asyncio.gather` for independent queries within the same DAG iteration. Better: create batch repository methods that accept multiple `dag_id`s and return results grouped by `dag_id`:

```python
# Batch all DAGs at once
all_run_stats = await self.resource_repo.get_dag_run_stats_batch(all_dag_ids, ...)
all_latest_runs = await self.resource_repo.get_latest_runs_by_dag_batch(all_dag_ids)
all_finish_hours = await self.resource_repo.get_typical_finish_hours_batch(all_dag_ids, ...)
all_tasks = await self.dag_task_repo.get_tasks_for_dags_with_pipeline(all_dag_ids)
```

### 1.2 Full Pipeline Table Load via get_all() on Every Request

**Severity: Critical**
**Impact: Loads all ~30 pipelines with `selectinload(airflow_status)` into memory on every request to topology, consumer, usage, bouncer topology, and AI services -- potentially 6+ times concurrently.**

**Files:**
- `/home/ip04/EtlNexus/backend/app/services/topology_service.py`, lines 64, 221 (`get_all()` in both `build_pipeline_topology` and `build_upstream_topology`)
- `/home/ip04/EtlNexus/backend/app/services/consumer_service.py`, line 27
- `/home/ip04/EtlNexus/backend/app/services/usage_service.py`, line 43
- `/home/ip04/EtlNexus/backend/app/services/sensor_service.py`, line 82 (BouncerService)
- `/home/ip04/EtlNexus/backend/app/services/ai_service.py`, lines 45, 74

Each call executes `SELECT * FROM pipelines LEFT JOIN airflow_run_statuses ... ORDER BY name OFFSET 0 LIMIT 200`. With 30 pipelines now, this is tolerable. At 500+ pipelines, this becomes a bottleneck both for DB query time and memory.

**Recommendation:** Create a lightweight cached materialized view:

```python
# In-memory shared index, rebuilt on cache invalidation
class PipelineIndex:
    """Shared read-only index refreshed on sync cycles."""
    task_id_to_pipeline: dict[str, PipelineSummary]
    status_map: dict[str, str]
    _lock: asyncio.Lock

    async def refresh(self, session: AsyncSession):
        async with self._lock:
            # Single query to populate all indexes
            ...
```

Alternatively, push the task_id lookup into individual SQL queries where possible (e.g., `WHERE task_id IN (...)` instead of loading all).

### 1.3 Missing Composite Index on pipeline_run_history

**Severity: Medium**
**Impact: Suboptimal query plans for the most frequently queried table.**

**File:** `/home/ip04/EtlNexus/backend/app/models/run_history.py`

The `pipeline_run_history` table has a single-column index on `pipeline_id` and a unique constraint on `(pipeline_id, dag_id, dag_run_id)`. However, multiple queries filter on `(pipeline_id, status, start_date)` or `(dag_id, start_date)`:

- `get_run_stats()` filters by `pipeline_id + start_date`
- `get_dag_run_stats()` filters by `dag_id + start_date`
- `get_latest_execution_plan()` filters by `pipeline_id + status + execution_plan IS NOT NULL`

**Recommendation:** Add composite indexes:

```python
__table_args__ = (
    UniqueConstraint(...),
    Index("ix_run_history_pipeline_start", "pipeline_id", "start_date"),
    Index("ix_run_history_dag_start", "dag_id", "start_date"),
    Index("ix_run_history_pipeline_status", "pipeline_id", "status"),
)
```

### 1.4 Missing Index on lineage_edges for Upsert Lookup

**Severity: Medium**
**Impact: Each lineage upsert does a 3-column WHERE without a covering index.**

**File:** `/home/ip04/EtlNexus/backend/app/repositories/lineage_repo.py`, line 48

The `upsert_edge` method queries by `(source_table, target_table, edge_type)` but there is no composite index on these columns. During sync, this is called for every lineage edge.

**Recommendation:** Add a unique composite index:

```python
Index("ix_lineage_edge_lookup", "source_table", "target_table", "edge_type", unique=True)
```

### 1.5 No Index on dag_tasks.sensor_name

**Severity: Low**
**Impact: Linear scan on `sensor_name` column during bouncer topology queries.**

**File:** `/home/ip04/EtlNexus/backend/app/models/dag_task.py`, line 28

`BouncerService.get_bouncer_topology()` iterates all dag_tasks in Python and filters by `sensor_name`. This is already an in-memory operation, but if the query were pushed to SQL, an index would be needed.

**Recommendation:** Add `index=True` to `sensor_name` for future SQL-based filtering.

### 1.6 Connection Pool Sizing

**Severity: Low**
**Impact: Adequate for current scale, but may bottleneck under concurrent user load.**

**File:** `/home/ip04/EtlNexus/backend/app/database.py`

Pool is configured as `pool_size=20, max_overflow=10` (30 total connections). With background tasks (sync, poll, catalog sync) each holding connections during their execution, and concurrent user requests, 30 may be tight under load.

The `pool_recycle=3600` and `pool_pre_ping=True` are good defensive settings.

**Recommendation:** For production, consider making these configurable via environment variables. A `pool_size` of 20 handles ~20 concurrent requests; adjust based on expected user concurrency plus background task concurrency.

---

## 2. Memory Management

### 2.1 All DagTasks Loaded into Memory for Bouncer Topology

**Severity: High**
**Impact: Loads entire `dag_tasks` table (~200 rows currently) into Python for BFS graph traversal. At scale (thousands of tasks), this becomes problematic.**

**File:** `/home/ip04/EtlNexus/backend/app/services/sensor_service.py`, line 71

```python
all_dag_tasks = await self.dag_task_repo.get_all_entries()
```

This loads every row from `dag_tasks` plus builds multiple in-memory indexes (`task_index`, `task_by_id`).

**Recommendation:** For the current scale of ~200 tasks, this is acceptable. For growth, consider a recursive CTE query to push BFS into PostgreSQL:

```sql
WITH RECURSIVE downstream AS (
    SELECT task_id, downstream_task_ids, dag_id
    FROM dag_tasks WHERE sensor_name = ANY(:bouncer_names)
    UNION
    SELECT dt.task_id, dt.downstream_task_ids, dt.dag_id
    FROM dag_tasks dt
    JOIN downstream d ON dt.task_id = ANY(d.downstream_task_ids) AND dt.dag_id = d.dag_id
)
SELECT DISTINCT task_id, dag_id FROM downstream WHERE sensor_name IS NULL;
```

### 2.2 AI Chat History Grows Unbounded

**Severity: Medium**
**Impact: Each AI chat message appends to an in-memory array with no size limit. Full history is sent to the LLM on every request, potentially exceeding token limits.**

**Files:**
- `/home/ip04/EtlNexus/frontend/src/stores/ai-store.ts` -- `messages` array grows without limit
- `/home/ip04/EtlNexus/backend/app/services/ai_service.py`, line 29 -- sends all `history` to LLM

**Recommendation:** Cap the history to the last N messages (e.g., 20) before sending to the backend:

```typescript
// Frontend: in use-ai-chat.ts
const recentHistory = messages.slice(-20);
```

And add a server-side safeguard:

```python
# Backend: in ai_service.py
messages = [
    *[{"role": m["role"], "content": m["content"]} for m in history[-20:]],
    {"role": "user", "content": message},
]
```

### 2.3 TTL Cache Stores Large Response Objects Without Size Limits

**Severity: Medium**
**Impact: Caches store full Pydantic response objects. No eviction beyond TTL -- a single large `DagSummaryResponse` persists for the full TTL period.**

**File:** `/home/ip04/EtlNexus/backend/app/cache.py`

The `TTLCache` has no max-size eviction. While TTLs are short (30-60s), if many different cache keys are generated (e.g., per-user pipeline lists with different team combos), the cache can accumulate many entries before any expire.

**Recommendation:** Add a `max_size` parameter to `TTLCache`:

```python
def set(self, key: str, value: T) -> None:
    if len(self._store) >= self._max_size:
        # Evict oldest entry
        oldest_key = min(self._store, key=lambda k: self._store[k][0])
        del self._store[oldest_key]
    self._store[key] = (time.monotonic(), value)
```

---

## 3. I/O Bottlenecks

### 3.1 Synchronous Spark Blocks the Async Event Loop

**Severity: Critical**
**Impact: During catalog sync, synchronous PySpark calls (`spark.sql()`, `spark.table()`) block the entire asyncio event loop, stalling ALL concurrent requests.**

**File:** `/home/ip04/EtlNexus/backend/app/integrations/iceberg_client.py`

All Iceberg methods (`list_tables_in_namespace`, `get_table_schema`, `get_all_dagger_schemas`) are synchronous but called from async context via:

```python
# catalog_sync_service.py, line 25
schemas = iceberg_client.get_all_dagger_schemas()
```

This chains multiple synchronous Spark SQL calls without yielding to the event loop.

**Recommendation:** Run Spark operations in a thread executor:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

_spark_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="spark")

class IcebergClient:
    async def async_get_all_dagger_schemas(self) -> list[IcebergTableSchema]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_spark_executor, self.get_all_dagger_schemas)
```

### 3.2 LLM Client Creates New HTTP Connection Per Request

**Severity: High**
**Impact: Each AI chat message and join insight request creates a new TCP connection + TLS handshake to the LLM endpoint, adding 50-200ms latency.**

**File:** `/home/ip04/EtlNexus/backend/app/integrations/llm_client.py`, line 50

```python
async with httpx.AsyncClient(timeout=self.timeout) as client:
    resp = await client.post(...)
```

This creates and destroys an `httpx.AsyncClient` (with its connection pool) on every single request, unlike the Airflow client which uses a persistent client.

**Recommendation:** Use a persistent client like `AirflowClient`:

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
        resp = await self._client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
        )
        ...

    async def close(self):
        await self._client.aclose()
```

Add `await llm_client.close()` to the application shutdown in `main.py`.

### 3.3 AI Service Loads All Pipelines + Fields for Join Insight

**Severity: High**
**Impact: `get_join_insight()` calls `get_all_with_fields()` which loads every pipeline with all fields, performs Python-side set intersection, then discards most data.**

**File:** `/home/ip04/EtlNexus/backend/app/services/ai_service.py`, line 45

```python
all_pipelines = await self.pipeline_repo.get_all_with_fields()
# Then Python-side: for other in all_pipelines: set(field_names) & other_fields
```

This is duplicating work that `PipelineRepository.get_shared_field_pipelines()` already does in SQL (used by `PipelineService.get_join_suggestions()`).

**Recommendation:** Reuse the SQL-based shared field query:

```python
async def get_join_insight(self, pipeline_id: uuid.UUID) -> str:
    ...
    # Use SQL instead of Python-side set intersection
    rows = await self.pipeline_repo.get_shared_field_pipelines(pipeline_id)
    overlaps = [
        f"- {row['pipeline_name']}: shared fields [{', '.join(row['shared_fields'])}]"
        for row in rows
    ]
    ...
```

### 3.4 Log Fetching During Sync is Unbounded

**Severity: Medium**
**Impact: During full sync, a log is fetched for every discovered task. With 30 ETLs + 6 bouncers = 36 log fetch requests in parallel. Log content can be large (>100KB per task).**

**File:** `/home/ip04/EtlNexus/backend/app/services/airflow_sync_service.py`, lines 258-264

The semaphore limits concurrent calls to 6, but the total memory for log content in-flight could be significant. Logs are plain text strings held in memory until processed.

**Recommendation:** This is manageable at current scale. For growth, consider streaming log parsing or limiting fetched log length (e.g., only last N lines where markers appear):

```python
# In airflow_client.py
headers={"Accept": "text/plain"},
params={"full_content": "false"},  # if Airflow API supports it
```

---

## 4. Caching

### 4.1 get_all() Called Multiple Times From Different Services Despite Caching

**Severity: High**
**Impact: When a user selects a pipeline, the bento workspace triggers 6-8 parallel API calls. `TopologyService`, `ConsumerService`, `UsageService` each independently call `pipeline_repo.get_all()`, resulting in 3+ identical full-table scans within milliseconds of each other.**

The `pipeline_list_cache` in `PipelineService.list_pipelines()` only caches the list endpoint response, not the raw `get_all()` call used by other services.

**Recommendation:** Add a request-scoped or short-TTL cache at the repository level:

```python
class PipelineRepository:
    _all_cache: TTLCache[list[Pipeline]] = TTLCache(ttl=5)  # 5-second micro-cache

    async def get_all(self, *, skip=0, limit=200) -> list[Pipeline]:
        cache_key = f"{skip}:{limit}"
        cached = self._all_cache.get(cache_key)
        if cached is not None:
            return cached
        ...
        self._all_cache.set(cache_key, result)
        return result
```

Or better, create a shared `PipelineIndex` singleton refreshed by the sync cycle and read by all services.

### 4.2 Cache Not Invalidated on Pipeline Update

**Severity: Medium**
**Impact: After editing a pipeline description or documentation, the topology_cache, bouncer_cache, and other caches may serve stale data for up to their TTL.**

**File:** `/home/ip04/EtlNexus/backend/app/services/pipeline_service.py`, line 124

Only `pipeline_list_cache.clear()` is called after an update. Other caches (`topology_cache`, `bouncer_topology_cache`, `join_suggestions_cache`) are not cleared.

**Recommendation:** Either clear all relevant caches after pipeline updates, or call `clear_all()`:

```python
from app.cache import clear_all
# After pipeline metadata update:
clear_all()
```

### 4.3 Topology Cache Key Does Not Include Pipeline Context

**Severity: Low**
**Impact: The `topology_cache` defined in cache.py is not directly used by TopologyService -- good. But the bouncer_topology_cache key uses sorted bouncer names, which could collide if bouncer names are subsets of each other. Low practical risk.**

**File:** `/home/ip04/EtlNexus/backend/app/services/sensor_service.py`, line 65

This is a low-risk observation -- the key format `topo:A|B:union` is sufficiently unique.

---

## 5. Concurrency Issues

### 5.1 BFS Using list.pop(0) -- O(n^2) Queue Behaviour

**Severity: Critical**
**Impact: Python `list.pop(0)` is O(n) because it shifts all remaining elements. In BFS traversals with hundreds of nodes, this creates O(n^2) total work.**

**Files (4 locations):**
- `/home/ip04/EtlNexus/backend/app/services/topology_service.py`, line 94: `tid = queue.pop(0)`
- `/home/ip04/EtlNexus/backend/app/services/topology_service.py`, line 237: `tid, depth = queue.pop(0)`
- `/home/ip04/EtlNexus/backend/app/services/topology_service.py`, line 269: `tid = bouncer_queue.pop(0)`
- `/home/ip04/EtlNexus/backend/app/services/sensor_service.py`, line 111: `tid = queue.pop(0)`

Additional instances at lines 330, 329 in topology_service.py.

**Recommendation:** Replace with `collections.deque` for O(1) popleft:

```python
from collections import deque

queue = deque([my_task_id])
while queue:
    tid = queue.popleft()  # O(1) instead of O(n)
    ...
    queue.append(upstream_tid)
```

### 5.2 Race Condition in TTL Cache (Not Thread-Safe)

**Severity: Medium**
**Impact: The `TTLCache` uses a plain `dict` without locking. In asyncio this is generally safe (no preemptive threading), but if background tasks (APScheduler) and request handlers access the same cache concurrently, there could be issues during `clear_all()`.**

**File:** `/home/ip04/EtlNexus/backend/app/cache.py`

APScheduler jobs call `clear_all()` which calls `.clear()` on every cache. If a request handler is mid-iteration over a cache entry, the dict could be modified mid-read in certain edge cases (e.g., with uvicorn workers using multiple threads).

**Recommendation:** With asyncio (single-thread event loop per worker), this is safe. However, if ever using multi-worker uvicorn with `--workers N`, the in-process cache becomes per-worker and this is fine. The risk is if using threaded middleware. Add a note or assertion:

```python
# cache.py
# NOTE: This cache is not thread-safe. Only use within asyncio single-thread context.
```

### 5.3 Single-Pipeline Sync Calls get_all_dags() Twice

**Severity: Low**
**Impact: `_fetch_single_pipeline_data` calls `airflow_client.get_all_dags()` again (line 566) after `_find_target_dags` already called it (line 526). The Airflow client caches this for 5 minutes, so it hits the in-memory cache, but the result is unnecessarily re-processed.**

**File:** `/home/ip04/EtlNexus/backend/app/services/airflow_sync_service.py`, lines 526, 566

**Recommendation:** Pass the `all_dags` result from `_find_target_dags` to `_fetch_single_pipeline_data`.

---

## 6. Frontend Performance

### 6.1 Lazy Loading and Code Splitting -- Well Implemented

**Severity: N/A (Positive Finding)**

**File:** `/home/ip04/EtlNexus/frontend/src/App.tsx`

All major view components are lazily loaded via `React.lazy()` and wrapped in `Suspense`. Manual chunk splitting in Vite config separates vendor-react, vendor-query, and vendor-ui. This is well done.

### 6.2 useBouncerTopology Mutates Query Key Array In-Place

**Severity: High**
**Impact: `bouncerNames.sort()` mutates the input array in place AND returns the sorted array. This causes the queryKey to change reference on every render even when the content is identical, triggering unnecessary refetches. Additionally, mutating a prop/derived value during render is a React anti-pattern.**

**File:** `/home/ip04/EtlNexus/frontend/src/hooks/use-bouncers.ts`, line 15

```typescript
queryKey: ["bouncer-topology", ...bouncerNames.sort(), mode],
```

**Recommendation:** Use a non-mutating sort:

```typescript
queryKey: ["bouncer-topology", ...bouncerNames.toSorted(), mode],
// or: [...bouncerNames].sort()
```

### 6.3 PipelineStore Filter Toggling Creates New Set on Every Toggle

**Severity: Low**
**Impact: Each `toggleFilter` call creates a new `Set` instance, which triggers re-renders on all subscribers. This is the correct Zustand pattern (immutable updates), but filtering pipelines client-side after the query returns is done without memoization.**

**File:** `/home/ip04/EtlNexus/frontend/src/stores/pipeline-store.ts`

This is inherent to the Zustand + immutable update pattern. Impact is low because the component tree is small.

### 6.4 BentoWorkspace Triggers Multiple Parallel Data Fetches on Pipeline Select

**Severity: Medium**
**Impact: Selecting a pipeline triggers: pipeline detail, topology, resource metrics, execution plan, join suggestions, usage, and consumer queries -- 7+ parallel requests. While individually fast, this creates a burst of backend load.**

**File:** `/home/ip04/EtlNexus/frontend/src/components/bento-workspace/BentoWorkspace.tsx`

The `BentoWorkspace` component renders `LineageTopology`, `ResourcePerformanceCard`, `TransformInspectorCard`, `SchemaViewer`, `UsageCard`, `JoinIntelligence`, and `ConsumeSnippet` -- each with its own `useQuery` hook.

**Recommendation:** This is acceptable for current scale. For optimization:
1. Consider a combined "pipeline-detail-bundle" API endpoint that returns detail + topology + resources in one response
2. Or use TanStack Query's `prefetchQuery` to start fetching before the workspace component mounts

### 6.5 Missing refetchOnWindowFocus=false on Several Hooks

**Severity: Low**
**Impact: TanStack Query defaults to refetching on window focus. For data that changes only on sync cycles (every 20 min), this creates unnecessary API calls when users alt-tab back.**

**Files:** Most hooks in `/home/ip04/EtlNexus/frontend/src/hooks/` rely on the default `refetchOnWindowFocus: true`.

**Recommendation:** Set `refetchOnWindowFocus: false` globally via QueryClient defaults, relying on `staleTime` and `refetchInterval` instead:

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 5 * 60_000,
    },
  },
});
```

---

## 7. Scalability Concerns

### 7.1 In-Process Caching Prevents Horizontal Scaling

**Severity: High**
**Impact: All caches (`TTLCache`, `_PROVISION_CACHE`) are in-process Python dicts. Running multiple backend instances (e.g., Gunicorn workers, Kubernetes replicas) means each instance has its own cache, leading to: (a) cache misses that should be hits, (b) stale data when one instance clears cache but others do not.**

**Files:**
- `/home/ip04/EtlNexus/backend/app/cache.py`
- `/home/ip04/EtlNexus/backend/app/services/user_auth_service.py` (lines 24-28)

**Recommendation:** For single-worker deployment, this is fine. For multi-worker/multi-instance:
1. Replace `TTLCache` with Redis (e.g., `redis.asyncio`)
2. Use `slowapi`'s Redis backend for rate limiting (currently in-memory)
3. Move `_PROVISION_CACHE` to Redis or accept per-instance caching with short TTL

### 7.2 Background Tasks Coupled to Web Process

**Severity: High**
**Impact: APScheduler runs inside the web server process. If running multiple web workers, each would start its own scheduler, causing duplicate sync/poll operations against Airflow and race conditions on DB writes.**

**File:** `/home/ip04/EtlNexus/backend/app/tasks/scheduler.py`

**Recommendation:**
1. For single-worker: Current setup works. The `docker-compose.prod.yml` runs a single backend container, so this is safe.
2. For scaling: Extract background tasks into a separate worker process (e.g., Celery, or a standalone APScheduler process). Alternatively, use APScheduler with a job store that supports distributed locking (e.g., `APScheduler + SQLAlchemyJobStore`).

### 7.3 Single Backend Container in Production

**Severity: Medium**
**Impact: `docker-compose.prod.yml` defines a single `backend` container with 2GB memory limit. No horizontal scaling, no load balancing.**

**File:** `/home/ip04/EtlNexus/docker-compose.prod.yml`

**Recommendation:** For production growth:
1. Use `uvicorn --workers N` or Gunicorn with uvicorn workers (requires addressing 7.1 and 7.2 first)
2. Add a reverse proxy (nginx or Traefik) in front of multiple backend instances
3. Consider separating the backend into "web" and "worker" services

### 7.4 Nginx Proxy Timeout

**Severity: Low**
**Impact: The nginx proxy has `proxy_read_timeout 120s`. The AI chat endpoint (LLM) can take 30s+ and sync endpoints can take longer. 120s is reasonable but should be monitored.**

**File:** `/home/ip04/EtlNexus/frontend/nginx.conf`, line 48

The frontend axios client has `timeout: 30_000` (30s). If an LLM request exceeds this, the frontend will timeout before nginx does. This asymmetry is acceptable.

### 7.5 No Pagination on get_all_entries()

**Severity: Medium**
**Impact: `DagTaskRepository.get_all_entries()` returns the entire `dag_tasks` table without pagination, used by `BouncerService.get_bouncer_topology()`. At scale, this could return thousands of rows.**

**File:** `/home/ip04/EtlNexus/backend/app/repositories/dag_task_repo.py`, line 93

**Recommendation:** For topology BFS, the entire graph is needed. Consider caching this at the service level (already done via `bouncer_topology_cache`) or using a SQL-based graph traversal.

---

## 8. Additional Observations

### 8.1 Airflow Client Cache TTL vs Sync Interval Mismatch

**Severity: Low**
**Impact: The Airflow client caches DAG definitions for 5 minutes (`cache_ttl_airflow=300`), but sync runs every 20 minutes. The cache may serve stale data if Airflow DAGs change between syncs. In practice this is fine because the sync itself calls `get_all_dags()` which refreshes the cache.**

### 8.2 Resource Repository upsert_run Uses ON CONFLICT with Named Constraint

**Severity: N/A (Positive Finding)**

**File:** `/home/ip04/EtlNexus/backend/app/repositories/resource_repo.py`, line 61

The `pg_insert().on_conflict_do_update()` pattern is the correct PostgreSQL idiom for atomic upserts. Good use of `constraint=` to avoid ambiguity.

### 8.3 Rate Limiting is Global, Not Per-Endpoint Differentiated

**Severity: Low**
**Impact: `200/minute` applies uniformly. Heavy endpoints (AI chat, sync triggers) share the same limit as lightweight ones (health check). A burst of AI requests could exhaust the limit for the entire API.**

**File:** `/home/ip04/EtlNexus/backend/app/rate_limit.py`

**Recommendation:** Apply stricter per-endpoint limits for expensive operations:

```python
@router.post("/ai/chat")
@limiter.limit("10/minute")
async def ai_chat(...):
    ...
```

---

## Summary Table

| # | Finding | Severity | Category | Est. Impact |
|---|---------|----------|----------|-------------|
| 1.1 | N+1 queries in DagSummaryService | Critical | Database | ~24 sequential queries per request |
| 1.2 | get_all() loads all pipelines per request (6+ services) | Critical | Database/Memory | Full table scan x6+ per pipeline select |
| 3.1 | Synchronous Spark blocks async event loop | Critical | I/O | All requests stall during catalog sync (~30s+) |
| 5.1 | BFS uses list.pop(0) -- O(n^2) | Critical | Algorithm | Quadratic scaling with graph size |
| 3.2 | LLM client creates new connection per request | High | I/O | +50-200ms per AI request |
| 3.3 | AI join insight loads all pipelines + fields in Python | High | I/O/Memory | Redundant with existing SQL query |
| 4.1 | get_all() called independently by multiple services | High | Caching | 3+ identical DB queries in <100ms |
| 6.2 | .sort() mutates queryKey array in-place | High | Frontend | Unnecessary refetches, render bugs |
| 7.1 | In-process caching prevents horizontal scaling | High | Scalability | Multi-instance cache inconsistency |
| 7.2 | Background tasks coupled to web process | High | Scalability | Duplicate syncs with multiple workers |
| 2.1 | All DagTasks loaded for bouncer topology | Medium | Memory | Grows linearly with task count |
| 2.2 | AI chat history unbounded | Medium | Memory | Potential LLM token overflow |
| 2.3 | TTL cache has no max-size eviction | Medium | Memory | Unbounded memory growth |
| 1.3 | Missing composite indexes on run_history | Medium | Database | Suboptimal query plans |
| 1.4 | Missing index on lineage_edges lookup | Medium | Database | Slow upserts during sync |
| 4.2 | Cache not invalidated on pipeline update | Medium | Caching | Stale data for up to 60s |
| 5.2 | TTL cache not thread-safe (acceptable for asyncio) | Medium | Concurrency | Risk with threaded middleware |
| 6.4 | 7+ parallel requests on pipeline select | Medium | Frontend | Burst of backend load |
| 7.3 | Single backend container in production | Medium | Scalability | No horizontal scaling |
| 7.5 | No pagination on get_all_entries() | Medium | Database | Full table load |
| 1.5 | No index on dag_tasks.sensor_name | Low | Database | Minor scan cost |
| 1.6 | Connection pool sizing hardcoded | Low | Database | Inflexible under load |
| 5.3 | get_all_dags() called twice in single-sync | Low | I/O | Cached, minimal impact |
| 6.3 | Filter toggle creates new Set (expected) | Low | Frontend | Negligible |
| 6.5 | Missing refetchOnWindowFocus=false | Low | Frontend | Unnecessary refetches |
| 8.3 | Rate limiting not per-endpoint | Low | Scalability | AI bursts exhaust global limit |
