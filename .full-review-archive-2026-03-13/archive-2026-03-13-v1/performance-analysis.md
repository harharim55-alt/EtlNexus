# EtlNexus Performance & Scalability Analysis

**Date:** 2026-03-13
**Scope:** Full-stack (Backend + Frontend + Infrastructure)
**Branch:** `feature/sensor-to-bouncer-rename`

---

## Table of Contents

1. [Critical Issues](#1-critical-issues)
2. [High Severity Issues](#2-high-severity-issues)
3. [Medium Severity Issues](#3-medium-severity-issues)
4. [Low Severity Issues](#4-low-severity-issues)
5. [Summary Matrix](#5-summary-matrix)

---

## 1. Critical Issues

### 1.1 Synchronous Spark Blocking the Async Event Loop

**Location:** `backend/app/integrations/iceberg_client.py` (lines 87-155), `backend/app/services/catalog_sync_service.py` (line 25)

**Problem:** `IcebergClient` methods (`list_tables_in_namespace`, `get_table_schema`, `get_all_dagger_schemas`) are **synchronous**, using `spark.sql().collect()` and `spark.table()`. These are called from the async `CatalogSyncService.sync_from_catalog()` without any thread delegation. PySpark operations are CPU-heavy and I/O-heavy (JVM interop, network calls to Iceberg REST catalog). Running them on the asyncio event loop blocks **all** concurrent request handling for the entire duration of the catalog sync.

**Impact:** During the 2-hour catalog sync cycle, the FastAPI server becomes unresponsive. With ~27 tables to read schemas for, each `spark.table().schema` call can take 1-5 seconds, creating a 30-135 second window of total backend unavailability.

**Recommendation:** Run Spark operations in a thread pool executor:

```python
# catalog_sync_service.py
import asyncio

async def sync_from_catalog(self) -> int:
    loop = asyncio.get_running_loop()
    schemas = await loop.run_in_executor(
        None,  # default ThreadPoolExecutor
        iceberg_client.get_all_dagger_schemas
    )
    # ... rest of async DB operations
```

---

### 1.2 `get_all()` Pipeline Loading Pattern — O(N) Full Table Scans on Every Request

**Location:** Multiple services load all pipelines into memory per request:

| Service | File | Line | Call |
|---------|------|------|------|
| TopologyService.build_pipeline_topology | topology_service.py | 64 | `get_all()` |
| TopologyService.build_upstream_topology | topology_service.py | 221 | `get_all()` |
| BouncerService.get_bouncer_topology | sensor_service.py | 82 | `get_all()` |
| ConsumerService.get_pipeline_consumers | consumer_service.py | 27 | `get_all()` |
| UsageService.get_pipeline_usage | usage_service.py | 43 | `get_all()` |
| AIService.chat | ai_service.py | 74 | `get_all()` |
| AIService.get_join_insight | ai_service.py | 45 | `get_all_with_fields()` |
| AirflowService.poll_all_statuses | airflow_service.py | 56 | `get_all()` |

**Problem:** Every topology/consumer/usage/AI request loads the entire `pipelines` table with `selectinload(Pipeline.airflow_status)`. With 30 pipelines this is acceptable, but with hundreds or thousands, this becomes a critical bottleneck. The `get_all()` method issues at minimum 2 SQL queries per call (main + selectinload), transferring all pipeline rows each time.

**Impact:** At 30 pipelines, each `get_all()` call costs ~2-5ms. At 500 pipelines, expect 50-200ms per call. Services that call `get_all()` and then do in-memory dictionary lookups are essentially reimplementing SQL indexes in Python.

**Recommendation:** Replace `get_all()` lookups with targeted queries:

```python
# For topology_service.py — replace get_all() with targeted lookup
async def get_pipelines_by_task_ids(
    self, task_ids: list[str]
) -> dict[str, Pipeline]:
    stmt = (
        select(Pipeline)
        .options(selectinload(Pipeline.airflow_status))
        .where(Pipeline.task_id.in_(task_ids))
    )
    result = await self.session.execute(stmt)
    return {p.task_id: p for p in result.scalars().all() if p.task_id}
```

For TopologyService, first collect the relevant task_ids from dag_task entries, then query only those pipelines. This reduces O(N) full-table reads to O(K) where K is the number of relevant tasks.

---

### 1.3 BFS Using `list.pop(0)` — O(n^2) Queue Operations

**Location:** 5 BFS loops in `topology_service.py` and `sensor_service.py`:

| File | Line | Context |
|------|------|---------|
| topology_service.py | 94 | `queue.pop(0)` — bouncer BFS in `build_pipeline_topology` |
| topology_service.py | 237 | `queue.pop(0)` — upstream BFS in `build_upstream_topology` |
| topology_service.py | 269 | `bouncer_queue.pop(0)` — bouncer discovery BFS |
| topology_service.py | 330 | `fwd_queue.pop(0)` — forward edge BFS |
| sensor_service.py | 111 | `queue.pop(0)` — bouncer topology BFS |

**Problem:** `list.pop(0)` is O(n) because it shifts all remaining elements. In a BFS that visits N nodes, this makes the total time complexity O(n^2). Python's `collections.deque` provides O(1) `popleft()`.

**Impact:** With current 30 pipelines + 6 DAGs, this is negligible (~30 nodes). At 500+ nodes, the quadratic behavior becomes measurable — a 500-node BFS does ~125,000 element shifts vs. 500 deque pops.

**Recommendation:**

```python
from collections import deque

# Replace all occurrences:
queue = deque([my_task_id])
while queue:
    tid = queue.popleft()  # O(1) instead of O(n)
```

---

### 1.4 LLM Client Creates New HTTP Connection Per Request

**Location:** `backend/app/integrations/llm_client.py` (line 50)

**Problem:** Unlike `AirflowClient` which uses a persistent `httpx.AsyncClient`, `LLMClient.chat()` creates a new `httpx.AsyncClient` context manager on every call:

```python
async with httpx.AsyncClient(timeout=self.timeout) as client:
    resp = await client.post(...)
```

Each invocation performs TCP handshake + TLS negotiation (if HTTPS). The AI chat feature and join insights both call this per request.

**Impact:** TCP+TLS setup typically adds 50-200ms latency per request. Under concurrent usage, this also creates connection churn that can hit OS file descriptor limits or trigger connection throttling on the LLM endpoint.

**Recommendation:** Use a persistent client like `AirflowClient`:

```python
class LLMClient:
    def __init__(self):
        # ... existing config ...
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(
                max_connections=5,
                max_keepalive_connections=2,
                keepalive_expiry=60,
            ),
        )

    async def chat(self, messages, system_prompt=None) -> str:
        # Use self._client directly instead of context manager
        resp = await self._client.post(...)

    async def close(self):
        await self._client.aclose()
```

---

## 2. High Severity Issues

### 2.1 N+1 Query in DagSummaryService

**Location:** `backend/app/services/dag_summary_service.py` (lines 90-112)

**Problem:** The `_build_dag_summaries` method iterates over all DAG IDs and issues **3 sequential DB queries per DAG** inside the loop:

```python
for dag_id in all_dag_ids:
    run_stats = await self.resource_repo.get_dag_run_stats(dag_id, ...)      # Query 1
    latest_runs = await self.resource_repo.get_latest_runs_by_dag(dag_id)     # Query 2-3
    finish_hour = await self.resource_repo.get_typical_finish_hour(dag_id, ...)  # Query 4
    tasks_in_dag = await self.dag_task_repo.get_tasks_for_dag_with_pipeline(dag_id)  # Query 5
```

With 6 DAGs, this fires ~30 sequential SQL queries. Each round-trip to PostgreSQL costs 1-3ms minimum.

**Impact:** 30-90ms of sequential DB query time per DAG summary request. At 20+ DAGs, this becomes 100-300ms of pure DB latency.

**Recommendation:** Batch these queries. Compute `run_stats` for all DAGs in a single aggregate query using `GROUP BY dag_id`. Fetch all `latest_runs` in one query with a window function (e.g., `ROW_NUMBER() OVER (PARTITION BY dag_id ORDER BY start_date DESC)`).

```python
# Single query for run stats across all DAGs
stmt = (
    select(
        PipelineRunHistory.dag_id,
        func.count().label("run_count"),
        func.avg(PipelineRunHistory.duration_seconds).label("avg_duration"),
        # ... other aggregates
    )
    .where(PipelineRunHistory.start_date >= cutoff)
    .group_by(PipelineRunHistory.dag_id)
)
```

---

### 2.2 Missing Composite Indexes on `pipeline_run_history`

**Location:** `backend/app/models/run_history.py`

**Problem:** The `pipeline_run_history` table has only a single-column index on `pipeline_id`, but queries frequently filter on `(pipeline_id, status)`, `(dag_id, status, start_date)`, and `(pipeline_id, start_date)`. The `get_dag_run_stats`, `get_recent_runs`, and `get_latest_execution_plan` methods all filter on these multi-column predicates.

**Impact:** Without composite indexes, PostgreSQL may perform sequential scans or inefficient index-then-filter operations. As run history grows (5 runs x 30 pipelines x 6 DAGs = 900 rows initially, growing by ~150/day), query times increase linearly.

**Recommendation:**

```python
class PipelineRunHistory(Base):
    __table_args__ = (
        UniqueConstraint("pipeline_id", "dag_id", "dag_run_id", ...),
        Index("ix_run_history_pipeline_start", "pipeline_id", "start_date"),
        Index("ix_run_history_dag_start", "dag_id", "start_date"),
        Index("ix_run_history_pipeline_status", "pipeline_id", "status"),
    )
```

---

### 2.3 TTL Cache Without Size Bounds — Unbounded Memory Growth

**Location:** `backend/app/cache.py`

**Problem:** The `TTLCache` class uses a plain `dict` with no maximum size limit. While entries expire after TTL, they are only evicted on access (lazy deletion). If many unique keys are inserted (e.g., per-user grant caches, per-pipeline topology caches), the cache grows unboundedly.

The `grant_level_cache` is keyed by `{user_id}:{pipeline_id}`, meaning with U users and P pipelines, the cache can hold up to U*P entries. With 100 users and 500 pipelines, that is 50,000 entries that persist until TTL expires on access.

**Impact:** Gradual memory growth over time. With 30 pipelines and few users, this is negligible. At scale (100+ concurrent users), the in-process cache could consume significant memory.

**Recommendation:** Add a maximum size with LRU eviction:

```python
class TTLCache:
    def __init__(self, ttl: int = 30, max_size: int = 1000):
        self._ttl = ttl
        self._max_size = max_size
        self._store: dict[str, tuple[float, Any]] = {}

    def set(self, key: str, value: Any) -> None:
        if len(self._store) >= self._max_size:
            # Evict oldest entry
            oldest_key = min(self._store, key=lambda k: self._store[k][0])
            del self._store[oldest_key]
        self._store[key] = (time.monotonic(), value)
```

Or use `cachetools.TTLCache` which provides both TTL and maxsize.

---

### 2.4 No Database Connection Pool Monitoring or Tuning for Background Tasks

**Location:** `backend/app/database.py`, `backend/app/tasks/scheduler.py`

**Problem:** A single connection pool (`pool_size=20, max_overflow=10`) is shared between HTTP request handlers and background tasks (sync, poll, catalog sync). Background tasks can hold connections for extended periods (sync_pipelines_from_airflow: 30+ seconds, poll_all_statuses: 20+ seconds). During these windows, the remaining pool capacity may be insufficient for concurrent API requests.

The scheduler uses `asyncio.Lock` to prevent concurrent sync/poll, but there is no mechanism to limit how many pool connections a background task can consume.

**Impact:** When background sync/poll runs, it holds a session for the entire duration. If it also triggers N sub-queries, it may hold the session open across many awaits, keeping the connection checked out for the full operation. With 20 pool connections and a slow sync taking 60+ seconds, concurrent users may experience connection wait timeouts.

**Recommendation:**
1. Use separate connection pools for background tasks vs. API requests
2. Configure `pool_timeout` to fail fast rather than hang:

```python
api_engine = create_async_engine(
    settings.database_url,
    pool_size=15, max_overflow=5,
    pool_timeout=10,  # Fail after 10s instead of blocking
)

task_engine = create_async_engine(
    settings.database_url,
    pool_size=5, max_overflow=2,
    pool_timeout=30,
)
```

---

### 2.5 `get_all_entries()` Loads Entire `dag_tasks` Table

**Location:** `backend/app/repositories/dag_task_repo.py` (line 93-96), called by `BouncerService.get_bouncer_topology` (sensor_service.py line 71)

**Problem:** `get_all_entries()` loads every row from the `dag_tasks` table into memory with no filtering. This is used to build an in-memory graph for BFS traversal in bouncer topology. With 6 DAGs x ~10 tasks each = ~60 rows currently, but the table grows linearly with DAGs and tasks.

**Impact:** At 100+ DAGs with 50+ tasks each, this loads 5,000+ ORM objects into memory per bouncer topology request.

**Recommendation:** Filter to only the DAGs containing the requested bouncers:

```python
async def get_entries_for_dags(self, dag_ids: list[str]) -> list[DagTask]:
    stmt = select(DagTask).where(DagTask.dag_id.in_(dag_ids))
    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

---

## 3. Medium Severity Issues

### 3.1 AI Chat Rebuilds Catalog Context on Every Message

**Location:** `backend/app/services/ai_service.py` (lines 23-26, 72-87)

**Problem:** Every chat message triggers `_build_catalog_context()`, which calls `get_all()` on the pipeline repository, iterates all pipelines, and builds a string. Similarly, `get_join_insight()` calls `get_all_with_fields()` which loads all pipelines with all their fields.

**Impact:** Redundant DB load and string construction on every chat turn. With 30 pipelines and ~10 fields each, the `get_all_with_fields()` call loads ~300 field ORM objects per join-insight request.

**Recommendation:** Cache the catalog context string in a module-level TTL cache (already have `pipeline_list_cache` with 30s TTL). For join insights, use the SQL-based `get_shared_field_pipelines()` method (which already exists in the pipeline_repo) instead of loading all fields into memory.

---

### 3.2 Airflow Status Poll Loads All Bouncers Into Memory

**Location:** `backend/app/services/airflow_service.py` (lines 77-78)

**Problem:** `poll_all_statuses()` calls `self.bouncer_repo.get_all()` to build a name-set for bouncer detection, loading all bouncer ORM objects when only the `sensor_name` column is needed.

**Impact:** Minor — loads ~10 bouncer objects. But the pattern is wasteful.

**Recommendation:** Add a targeted method:

```python
async def get_all_sensor_names(self) -> set[str]:
    stmt = select(Bouncer.sensor_name)
    result = await self.session.execute(stmt)
    return {row[0] for row in result.all()}
```

---

### 3.3 Frontend: PipelineRegistry Fetches DagSummary for Client-Side Filtering

**Location:** `frontend/src/components/pipeline-registry/PipelineRegistry.tsx` (line 48)

**Problem:** The `PipelineRegistry` component calls `useDagSummary()` to build a mapping from DAG IDs to pipeline IDs, solely for client-side DAG filtering. The DAG summary endpoint is heavyweight — it fetches run stats, latest runs, finish hours, and per-task summaries for every DAG. This full payload is loaded even when the user never uses DAG filtering.

**Impact:** Unnecessary network payload (could be several KB) and server-side query work for every pipeline registry mount, regardless of whether DAG filtering is used.

**Recommendation:** Either:
1. Make the DAG filter use a lightweight endpoint (e.g., `GET /api/dag-tasks/dag-pipeline-map` that returns only `{dag_id: [pipeline_id]}`)
2. Fetch the DAG summary lazily only when the filter drawer is opened

---

### 3.4 No Pagination on Several Endpoints

**Location:** Multiple services return unbounded result sets:

| Endpoint | Service Method | Issue |
|----------|---------------|-------|
| `GET /api/consumers/{etl_name}` | `ConsumerService.get_pipeline_consumers` | No pagination, returns all downstream |
| `GET /api/usage/{etl_name}` | `UsageService.get_pipeline_usage` | No pagination, returns all consumers |
| `GET /api/pipelines/{id}/topology` | `TopologyService.build_pipeline_topology` | Returns all upstream+downstream nodes |
| `GET /api/bouncers/topology` | `BouncerService.get_bouncer_topology` | Returns all downstream ETLs |
| `GET /api/dag-summary` | `DagSummaryService.get_dag_summaries` | Returns all DAGs with all tasks |

**Impact:** With current data volumes (~30 pipelines, 6 DAGs), these are small payloads. As the system scales, these unbounded responses grow linearly and can cause latency spikes and large payload sizes.

**Recommendation:** Add optional `skip` and `limit` query parameters to these endpoints. For topology endpoints, consider depth-limiting the BFS.

---

### 3.5 Redundant Pipeline Loading in Auth Middleware

**Location:** `backend/app/auth.py` (lines 163, 203)

**Problem:** Both `require_team_membership` and `require_team_membership_or_editor_grant` call `PipelineRepository(session).get_by_id(pipeline_uuid)` to check team ownership. The PATCH endpoint for pipeline updates also loads the pipeline in the service layer. Although `require_team_membership_or_editor_grant` stores the loaded pipeline on `request.state.pipeline` to avoid double-loading, `require_team_membership` does not.

Similarly, the `GET /{pipeline_id}/joins` endpoint loads the pipeline in both the visibility check (in the router) and in the service method (via `get_join_suggestions`).

**Impact:** 1-2 extra DB queries per mutating request. With current low traffic, this is minor, but it compounds under load.

**Recommendation:** Ensure all auth dependencies store loaded pipelines on `request.state` for downstream reuse, and have service methods accept pre-loaded pipelines.

---

### 3.6 `delete_stale` Builds Large IN Clause

**Location:** `backend/app/repositories/dag_task_repo.py` (lines 98-115)

**Problem:** `delete_stale()` constructs a `NOT IN` clause with all current `(dag_id, task_id)` tuples. With 60+ current pairs, this generates a large SQL statement. PostgreSQL handles this reasonably well, but the query planner may choose a sequential scan when the NOT IN list is large.

**Impact:** At 500+ dag_task entries, the NOT IN clause becomes unwieldy.

**Recommendation:** Use a temporary table or CTE-based approach for large sets:

```python
async def delete_stale_efficient(self, current_pairs: set[tuple[str, str]]) -> int:
    """Mark-and-sweep: delete all rows not matching any current pair."""
    # Alternative: set a "seen_at" timestamp during sync, then DELETE WHERE seen_at < sync_start
```

---

### 3.7 Frontend: Chat History Grows Unbounded in Zustand Store

**Location:** `frontend/src/stores/ai-store.ts` (line 22)

**Problem:** The `addMessage` action appends to the `messages` array with no limit:

```typescript
addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),
```

Each message also spreads the entire array (creating a new array copy). There is no truncation of old messages.

Additionally, the full chat history is sent to the backend on every message (via `use-ai-chat.ts` line 11: `history: messages`), which means the LLM request payload grows with every turn.

**Impact:** After 50+ messages, the LLM payload may exceed model context limits, the backend catalog context + history could exceed token budgets, and the frontend holds an ever-growing array in memory.

**Recommendation:** Limit history to the last N messages:

```typescript
addMessage: (msg) =>
    set((state) => ({
        messages: [...state.messages.slice(-49), msg],
    })),
```

---

### 3.8 No Response Compression on API Endpoints

**Location:** `backend/app/main.py` (not shown), `frontend/nginx.conf`

**Problem:** While nginx has gzip configured for static assets, there is no compression middleware on the FastAPI backend. When the frontend talks directly to the backend during development (via Vite proxy), and in production if the API is accessed directly, JSON responses are sent uncompressed. The DAG summary and schema matrix endpoints can return large JSON payloads.

**Impact:** 2-5x larger response payloads than necessary, impacting latency on slower networks.

**Recommendation:** Add GZip middleware to FastAPI:

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

In production, nginx already handles gzip for proxied `/api/` requests since `gzip_types` includes `application/json`. But adding it at the FastAPI level provides coverage for direct API access and development.

---

## 4. Low Severity Issues

### 4.1 Frontend: No Debouncing on Pipeline Search

**Location:** `frontend/src/components/pipeline-registry/PipelineSearch.tsx` (not fully read, but `usePipelines` hook uses `searchQuery` directly as query key)

**Problem:** The `usePipelines` hook includes `searchQuery` in the TanStack Query key (line 8 of `use-pipelines.ts`). If the search input fires on every keystroke, this triggers a new API request per character typed.

**Impact:** Rapid successive API calls during typing, most of which are immediately superseded. TanStack Query's `keepPreviousData` mitigates the UI flicker, but the backend still processes the abandoned requests.

**Recommendation:** Debounce the search query with a 300ms delay before updating the store:

```typescript
const [inputValue, setInputValue] = useState("");
const debouncedValue = useDeferredValue(inputValue);
// or useEffect with setTimeout
```

---

### 4.2 `pool_pre_ping=True` Adds Latency Per Connection Checkout

**Location:** `backend/app/database.py` (line 12)

**Problem:** `pool_pre_ping=True` sends a `SELECT 1` to the database every time a connection is checked out from the pool to verify it is still alive. While this prevents errors from stale connections, it adds 0.5-1ms per DB operation.

**Impact:** At high request volumes, this adds measurable overhead. With 20-30 DB queries per complex request (like DAG summary), it can add 10-30ms.

**Recommendation:** Keep `pool_pre_ping=True` in production for reliability, but consider disabling it in development or using `pool_recycle` alone (already set to 3600s) to reduce overhead when the database is co-located.

---

### 4.3 Frontend: `BentoWorkspace` Renders All Cards Unconditionally

**Location:** `frontend/src/components/bento-workspace/BentoWorkspace.tsx` (lines 70-97)

**Problem:** When a pipeline is selected, `BentoWorkspace` renders all child components simultaneously: `LineageTopology`, `MetricsCards`, `ResourcePerformanceCard`, `TransformInspectorCard`, `SchemaViewer`, `UsageCard`, `JoinIntelligence`, `ConsumeSnippet`. Each of these triggers its own API call via TanStack Query hooks. The user only sees the top of the page initially.

**Impact:** 6-8 concurrent API requests fire immediately on pipeline selection. All are needed eventually, but loading below-the-fold cards eagerly wastes bandwidth and backend resources.

**Recommendation:** Use `IntersectionObserver` or TanStack Query's `enabled` prop to defer loading below-fold components:

```typescript
// Example: Only fetch execution plan when card is near viewport
const ref = useRef<HTMLDivElement>(null);
const isVisible = useIntersectionObserver(ref, { rootMargin: '200px' });

return (
    <div ref={ref}>
        {isVisible && <TransformInspectorCard pipelineId={pipeline.id} />}
    </div>
);
```

---

### 4.4 Airflow Client Retry Strategy is Fixed at 2 Attempts

**Location:** `backend/app/integrations/airflow_client.py` (line 53)

**Problem:** The `_request` method retries exactly once on failure with no backoff delay. For transient network errors, an immediate retry may hit the same condition.

**Impact:** Low — the current setup works for the dev environment. In production with an external Airflow, network blips may cause both attempts to fail in quick succession.

**Recommendation:** Add exponential backoff:

```python
for attempt in range(3):
    try:
        # ... request ...
    except (...) as e:
        if attempt < 2:
            await asyncio.sleep(0.5 * (2 ** attempt))
        else:
            return None
```

---

### 4.5 Docker Prod: No Multi-Process Workers for Backend

**Location:** `docker-compose.prod.yml` — backend uses default uvicorn command (single worker)

**Problem:** The production docker-compose does not specify `--workers` for uvicorn. A single asyncio process handles all requests. While asyncio handles concurrency well for I/O-bound work, CPU-intensive operations (JSON serialization of large payloads, Pydantic validation) and the synchronous Spark calls (issue 1.1) require multiple processes to avoid blocking.

**Impact:** Single-process uvicorn cannot utilize multiple CPU cores and has no fault isolation — a memory leak or crash in one request handler takes down the entire service.

**Recommendation:** Use gunicorn with uvicorn workers in production:

```yaml
backend:
  command: >
    gunicorn app.main:app
    --worker-class uvicorn.workers.UvicornWorker
    --workers 4
    --bind 0.0.0.0:8000
    --timeout 120
```

Note: The APScheduler background tasks must be configured to run in only one worker (use a leader-election mechanism or move background tasks to a separate process).

---

### 4.6 No Index on `lineage_edges` for Composite Upsert Lookup

**Location:** `backend/app/models/lineage.py`, `backend/app/repositories/lineage_repo.py` (line 48-52)

**Problem:** The `upsert_edge` method queries by `(source_table, target_table, edge_type)` but there is no composite index on these columns. There is also no unique constraint on this triple, meaning the upsert relies on finding at most one match — which is not guaranteed by the schema.

**Impact:** With hundreds of lineage edges, each upsert during sync performs a sequential scan on `lineage_edges`.

**Recommendation:** Add a unique composite index:

```python
class LineageEdge(Base):
    __table_args__ = (
        Index("ix_lineage_edges_src_tgt_type",
              "source_table", "target_table", "edge_type",
              unique=True),
    )
```

---

### 4.7 Frontend: Vite Manual Chunks Could Be More Granular

**Location:** `frontend/vite.config.ts` (lines 17-28)

**Problem:** The `vendor-ui` chunk bundles `@base-ui/react`, `lucide-react`, `class-variance-authority`, `clsx`, and `tailwind-merge` together. Lucide-react alone can be large if tree-shaking isn't aggressive. There is no chunk for `zustand`, `axios`, `@tanstack/react-virtual`, `react-markdown`, or other significant dependencies.

**Impact:** The initial bundle may be larger than necessary. Missing manual chunks mean these libraries end up in the main chunk or in arbitrary auto-split chunks.

**Recommendation:** Add more granular chunking:

```typescript
manualChunks: {
    "vendor-react": ["react", "react-dom"],
    "vendor-query": ["@tanstack/react-query"],
    "vendor-virtual": ["@tanstack/react-virtual"],
    "vendor-state": ["zustand"],
    "vendor-http": ["axios"],
    "vendor-ui": ["@base-ui/react", "class-variance-authority", "clsx", "tailwind-merge"],
    "vendor-icons": ["lucide-react"],
},
```

---

### 4.8 Stale Cache Entries Not Cleaned Proactively

**Location:** `backend/app/cache.py`

**Problem:** TTL cache entries are only evicted on `get()` (lazy deletion). The `clear_all()` function only runs after sync/poll cycles. Between cycles (20-minute windows), expired entries accumulate in memory without being freed.

**Impact:** Minimal with current usage. Could become relevant with many per-user cache entries.

**Recommendation:** Add a periodic cleanup method called from the scheduler:

```python
def evict_expired(self) -> int:
    now = time.monotonic()
    expired = [k for k, (ts, _) in self._store.items() if now - ts > self._ttl]
    for k in expired:
        del self._store[k]
    return len(expired)
```

---

## 5. Summary Matrix

| # | Issue | Severity | Impact Area | Est. Perf Impact |
|---|-------|----------|-------------|-----------------|
| 1.1 | Synchronous Spark blocks event loop | **Critical** | Backend availability | 30-135s total blocking |
| 1.2 | `get_all()` on every request (7 services) | **Critical** | DB load, latency | O(N) per request, scales poorly |
| 1.3 | BFS uses `list.pop(0)` — O(n^2) | **Critical** | CPU | Quadratic at scale |
| 1.4 | LLM client new connection per request | **Critical** | Latency | +50-200ms per AI call |
| 2.1 | N+1 in DagSummaryService | **High** | DB load | 30-90ms unnecessary latency |
| 2.2 | Missing composite indexes on run_history | **High** | DB query time | Sequential scans at scale |
| 2.3 | TTL cache unbounded size | **High** | Memory | Gradual growth |
| 2.4 | Shared connection pool for API + tasks | **High** | Availability | Pool exhaustion risk |
| 2.5 | `get_all_entries()` full table load | **High** | Memory, DB | Linear growth |
| 3.1 | AI rebuilds catalog context per message | **Medium** | DB load | Redundant queries |
| 3.2 | Poll loads all bouncer objects | **Medium** | DB load | Minor waste |
| 3.3 | PipelineRegistry fetches heavy DagSummary | **Medium** | Network, backend | Unnecessary payload |
| 3.4 | No pagination on several endpoints | **Medium** | Scalability | Linear payload growth |
| 3.5 | Redundant pipeline loading in auth | **Medium** | DB load | 1-2 extra queries |
| 3.6 | `delete_stale` large NOT IN clause | **Medium** | Query planning | At scale |
| 3.7 | Chat history grows unbounded | **Medium** | Memory, API size | Linear growth |
| 3.8 | No response compression on API | **Medium** | Network | 2-5x larger payloads |
| 4.1 | No debounce on search | **Low** | Backend load | Burst requests |
| 4.2 | `pool_pre_ping` per-checkout overhead | **Low** | Latency | +0.5ms per checkout |
| 4.3 | All bento cards render eagerly | **Low** | Network | 6-8 concurrent API calls |
| 4.4 | Fixed retry with no backoff | **Low** | Reliability | Edge case failures |
| 4.5 | Single-worker production deploy | **Low** | CPU utilization | Underutilized cores |
| 4.6 | Missing index on lineage upsert | **Low** | Sync performance | Slow upserts at scale |
| 4.7 | Vite chunks could be more granular | **Low** | Bundle size | Suboptimal splitting |
| 4.8 | Expired cache entries not proactively cleaned | **Low** | Memory | Minimal |

---

### Overall Assessment

**Current state with 30 pipelines / 6 DAGs / low concurrency:** The application performs adequately. Most issues are architectural patterns that will not manifest until data volume or user concurrency increases.

**Scaling to 200+ pipelines / 20+ DAGs / 50+ concurrent users:** The Critical and High issues (1.1-1.4, 2.1-2.5) will cause measurable degradation. The Spark event loop blocking (1.1) is the most immediately dangerous as it causes total unavailability during catalog sync. The `get_all()` pattern (1.2) is the most pervasive and will require the most refactoring effort.

**Priority order for optimization:**
1. Fix Spark event loop blocking (1.1) — immediate availability impact
2. Replace `list.pop(0)` with `deque.popleft()` (1.3) — trivial fix, no risk
3. Persist the LLM client (1.4) — trivial fix, immediate latency improvement
4. Add composite indexes (2.2) — Alembic migration, immediate query improvement
5. Refactor `get_all()` pattern (1.2) — largest effort, largest long-term impact
6. Batch DagSummary queries (2.1) — moderate effort, good payoff
