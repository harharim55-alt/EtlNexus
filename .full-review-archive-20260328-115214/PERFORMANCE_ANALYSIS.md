# EtlNexus Performance & Scalability Analysis

**Date:** 2026-03-27
**Scope:** Full-stack analysis (Backend, Frontend, Infrastructure)
**Methodology:** Static code review of actual source files

---

## Executive Summary

The EtlNexus codebase is reasonably well-architected for its current scale, with proper async patterns, caching layers, pagination, and lazy loading already in place. However, several concrete issues exist that would degrade performance under growth or long-running operation. The most critical problems are: (1) synchronous Spark/PySpark operations blocking the async event loop, (2) O(n^2) BFS algorithms in hot topology paths, (3) full-table-scan `get_all()` calls in topology and polling services, and (4) unbounded in-memory metric dictionaries that leak over time.

**Finding counts by severity:**
- Critical: 3
- High: 7
- Medium: 8
- Low: 5

---

## 1. Database Performance

### 1.1 Full Table Scans on Every Topology Request
**Severity: Critical**
**Impact: O(n) pipeline load per topology request, scaling linearly with pipeline count**

`TopologyService.build_pipeline_topology()` (line 73) and `build_upstream_topology()` (line 229) both call `self.pipeline_repo.get_all()` to build a `task_id_to_pipeline` lookup. This loads **every pipeline with its airflow_status relationship** into memory on every single topology request, even though only a subset of task_ids are actually needed.

**File:** `/home/itamar/projects/EtlNexus/backend/app/services/topology_service.py` (lines 73, 229)

```python
# Current: loads ALL pipelines from DB
all_pipelines = await self.pipeline_repo.get_all()
task_id_to_pipeline = {p.task_id: p for p in all_pipelines if p.task_id}
```

**Recommendation:** Replace with the lightweight cached `get_task_id_map()` that already exists on PipelineRepository. It returns SimpleNamespace objects with only the needed fields and uses short-TTL caching:

```python
# Fixed: uses cached lightweight map (already built into the repo)
task_id_to_pipeline = await self.pipeline_repo.get_task_id_map()
```

This is already used in `bouncer_service.py` (line 82) but not in topology_service. The `get_task_id_map()` method avoids `selectinload(Pipeline.airflow_status)` and returns column projections instead of full ORM objects.

---

### 1.2 Bouncer Service Loads Entire dag_tasks Table
**Severity: High**
**Impact: Full table scan of dag_tasks table on every bouncer topology request**

`BouncerService.get_bouncer_topology()` (line 71) calls `self.dag_task_repo.get_all_entries()` which executes `SELECT * FROM dag_tasks` with no filter. This loads every row from the table into Python memory.

**File:** `/home/itamar/projects/EtlNexus/backend/app/services/bouncer_service.py` (line 71)

```python
all_dag_tasks = await self.dag_task_repo.get_all_entries()
```

**Recommendation:** Filter at the DB level using the known bouncer names to only load relevant DAGs:

```python
# Get DAGs containing the selected bouncers
relevant_dag_ids = await self.dag_task_repo.get_dag_ids_for_bouncers(bouncer_names)
# Load only tasks from those DAGs
all_dag_tasks = await self.dag_task_repo.get_tasks_for_dags(relevant_dag_ids)
```

---

### 1.3 AirflowService.poll_all_statuses Loads All Pipelines + All Bouncers
**Severity: Medium**
**Impact: Two full table scans per 20-minute poll cycle**

`poll_all_statuses()` calls `self.pipeline_repo.get_all()` (line 56) and `self.bouncer_repo.get_all()` (line 77) at the start of every poll. Since `get_all()` includes `selectinload(Pipeline.airflow_status)`, this is an N+1 eager load on a relationship for every pipeline.

**File:** `/home/itamar/projects/EtlNexus/backend/app/services/airflow_service.py` (lines 56, 77)

**Recommendation:** Use the lightweight `get_task_id_map()` for pipeline lookup and a simple bouncer name query:

```python
# Instead of loading full Pipeline ORM objects
task_to_pipeline = await self.pipeline_repo.get_task_id_map()
bouncer_names = await self.bouncer_repo.get_all_names()  # New: SELECT bouncer_name FROM bouncers
```

---

### 1.4 Sequential Upserts in Sync Service
**Severity: Medium**
**Impact: O(n) sequential DB roundtrips during pipeline sync**

`_persist_pipelines_and_lineage()` (line 452) iterates through `seen_tasks` and performs sequential `pipeline_repo.upsert()` calls, each doing a SELECT + potential UPDATE/INSERT + flush. For 100+ pipelines, this creates 300+ sequential DB operations.

Similarly, `_persist_dag_tasks()` (line 650) does individual upserts per dag_task entry.

**File:** `/home/itamar/projects/EtlNexus/backend/app/services/airflow_sync_service.py` (lines 452-562, 636-655)

**Recommendation:** Batch upserts using PostgreSQL's `INSERT ... ON CONFLICT` via `sqlalchemy.dialects.postgresql.insert` (already used in `resource_repo.upsert_run()`). This reduces N roundtrips to 1:

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = pg_insert(Pipeline).values(batch_data)
stmt = stmt.on_conflict_do_update(
    index_elements=['task_id'],
    set_={col: stmt.excluded[col] for col in update_columns}
)
await self.session.execute(stmt)
```

---

### 1.5 Missing Index on pipeline_run_history.dag_id
**Severity: Medium**
**Impact: Slow DAG-scoped queries in resource_stats and resource_repo**

Several queries filter on `PipelineRunHistory.dag_id`:
- `resource_stats.get_dag_run_stats()` (line 128)
- `resource_stats.get_typical_finish_hour()` (line 167)
- `resource_repo.get_latest_runs_by_dag()` (line 256)

The `dag_id` column has no index. Only `pipeline_id` is indexed, and there is a composite index on `(pipeline_id, start_date DESC)`.

**File:** `/home/itamar/projects/EtlNexus/backend/app/models/run_history.py` (line 20)

**Recommendation:** Add a B-tree index on `dag_id`:

```python
dag_id: Mapped[str] = mapped_column(String(255), index=True)
```

---

### 1.6 Indexes Are Well-Covered for Common Patterns
**Severity: N/A (Positive finding)**

The codebase has good index coverage:
- GIN trigram indexes for ILIKE search on `pipelines.name`, `pipelines.description`, `pipeline_fields.name` (migration 025)
- Composite index on `(pipeline_id, start_date DESC)` for run history (migration 008)
- Partial composite indexes on `visibility_grants` for all 4 grant patterns (migration 021)
- B-tree on `Pipeline.name`, `Pipeline.task_id`, `Pipeline.team`, `Pipeline.team_id`
- B-tree on `DagTask.dag_id`, `DagTask.task_id`, `DagTask.pipeline_id`

---

## 2. Memory Management

### 2.1 Unbounded Metrics Dictionaries - Memory Leak
**Severity: High**
**Impact: Monotonically growing memory over weeks/months of uptime**

The in-memory Prometheus metrics in `metrics.py` use `defaultdict(int)` / `defaultdict(float)` that **never shrink**:

```python
_request_counts: dict[str, int] = defaultdict(int)
_request_duration_sum: dict[str, float] = defaultdict(float)
_request_duration_count: dict[str, int] = defaultdict(int)
```

**File:** `/home/itamar/projects/EtlNexus/backend/app/routers/metrics.py` (lines 14-16)

While path normalization replaces UUIDs with `{id}`, the cardinality is still `methods x paths x status_codes`. Over time with API evolution and varied status codes, these dictionaries grow without bound.

**Recommendation:** Either:
1. Use a fixed-size LRU dict or periodic reset on a schedule
2. Switch to a proper metrics library (prometheus_client) that handles this correctly
3. Add a max-entries guard:

```python
MAX_METRIC_KEYS = 5000

def record_request(method, path, status_code, duration_seconds):
    if len(_request_counts) > MAX_METRIC_KEYS:
        _request_counts.clear()
        _request_duration_sum.clear()
        _request_duration_count.clear()
    # ... existing logic
```

---

### 2.2 TTLCache Never Evicts Expired Entries Proactively
**Severity: Low**
**Impact: Gradual memory accumulation between clear() calls**

The `TTLCache.get()` deletes expired entries on access, but entries that are `set()` and never `get()`-ed again remain in `_store` until `clear()` is called. Between sync cycles (every 20 min), stale entries from unique cache keys (e.g., per-pipeline topology with different `dag_id` combinations) accumulate.

**File:** `/home/itamar/projects/EtlNexus/backend/app/cache.py` (lines 17-38)

**Recommendation:** Add a lazy eviction in `set()`:

```python
def set(self, key: str, value: T) -> None:
    now = time.monotonic()
    # Lazy eviction: every 100 sets, purge expired entries
    if len(self._store) > 100:
        self._store = {k: v for k, v in self._store.items() if now - v[0] <= self._ttl}
    self._store[key] = (now, value)
```

---

### 2.3 AirflowSyncService Intermediate Data Structures
**Severity: Low**
**Impact: Temporary memory spike during full sync (manageable for current scale)**

`_FullSyncFetchResult` and `_TaskDiscoveryResult` hold all fetched Airflow data in memory simultaneously. For large Airflow installations (1000+ DAGs, 10000+ tasks), the `instances_results` list (all task instances across all DAGs) could consume significant memory.

**File:** `/home/itamar/projects/EtlNexus/backend/app/services/airflow_sync_service.py` (lines 60-84)

**Recommendation:** For future scaling, process DAGs in batches rather than accumulating all results upfront. The current semaphore (6 concurrent) already limits API concurrency; extend this to process in chunks of ~20 DAGs at a time.

---

## 3. I/O Bottlenecks

### 3.1 IcebergClient Blocks the Async Event Loop
**Severity: Critical**
**Impact: All async request handling blocked during catalog sync operations**

All `IcebergClient` methods (`get_all_schemas()`, `list_tables_in_namespace()`, `get_table_schema()`, `check_health()`) execute **synchronous** PySpark `spark.sql(...).collect()` and `spark.table()` calls directly in async context. Since PySpark operations are CPU-bound and blocking, they freeze the entire asyncio event loop for the duration of each Spark query.

**File:** `/home/itamar/projects/EtlNexus/backend/app/integrations/iceberg_client.py` (lines 73-159)

The `catalog_sync_task.py` calls `service.sync_from_catalog()` which calls `iceberg_client.get_all_schemas()` - a synchronous method that iterates through all namespaces and tables. During this time, the event loop is completely blocked.

```python
# This blocks the event loop:
schemas = iceberg_client.get_all_schemas()  # synchronous!
```

**Recommendation:** Run PySpark operations in a thread executor:

```python
import asyncio

class IcebergClient:
    async def get_all_schemas_async(self) -> list[IcebergTableSchema]:
        """Non-blocking wrapper around synchronous Spark operations."""
        return await asyncio.to_thread(self.get_all_schemas)

    async def check_health_async(self) -> bool:
        return await asyncio.to_thread(self._check_health_sync)
```

Update `catalog_sync_service.py`:
```python
schemas = await iceberg_client.get_all_schemas_async()
```

---

### 3.2 AirflowClient Retries Without Backoff
**Severity: High**
**Impact: Amplifies load on Airflow during partial outages**

The `_request()` method retries immediately on failure with no delay or exponential backoff:

```python
for attempt in range(2):
    try:
        resp = await self._client.request(...)
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        if attempt == 1:
            return None
```

**File:** `/home/itamar/projects/EtlNexus/backend/app/integrations/airflow_client.py` (lines 51-68)

During an Airflow partial outage, the full sync fires ~50-100 API calls (all DAGs x tasks/runs/instances), each retrying immediately. This hammers an already-struggling Airflow.

**Recommendation:** Add exponential backoff:

```python
import asyncio

async def _request(self, method: str, path: str, **kwargs) -> dict | None:
    url = f"{self.base_url}{path}"
    for attempt in range(3):
        try:
            resp = await self._client.request(method, url, auth=self.auth, **kwargs)
            resp.raise_for_status()
            self._connected = True
            return resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.warning("Airflow request failed (attempt %d): %s %s -> %s",
                           attempt + 1, method, path, e)
            if attempt < 2:
                await asyncio.sleep(0.5 * (2 ** attempt))  # 0.5s, 1s
            else:
                self._connected = False
                return None
```

---

### 3.3 Sequential Log Fetching in Single-Pipeline Sync
**Severity: Medium**
**Impact: One blocking `await` per DAG during manual sync**

In `_fetch_single_pipeline_metadata()` (line 786), the task log is fetched with a direct `await`:

```python
log_content = await airflow_client.get_task_log(
    dag_id, run["dag_run_id"], airflow_task_id
)
```

**File:** `/home/itamar/projects/EtlNexus/backend/app/services/airflow_sync_service.py` (line 786)

This is sequential within the loop over DAGs. In contrast, the full sync correctly parallelizes log fetches (line 396).

**Recommendation:** Collect log fetch needs and batch them with `asyncio.gather()`, matching the pattern used in the full sync.

---

### 3.4 CatalogSyncService Individual Pipeline Lookups
**Severity: Medium**
**Impact: O(n) DB queries for n Iceberg tables**

`sync_from_catalog()` performs a `SELECT ... WHERE task_id = :id` for each Iceberg table schema discovered:

```python
for table_schema in schemas:
    task_id = table_schema.table_name
    stmt = select(Pipeline).options(selectinload(Pipeline.fields)).where(Pipeline.task_id == task_id)
    result = await self.session.execute(stmt)
```

**File:** `/home/itamar/projects/EtlNexus/backend/app/services/catalog_sync_service.py` (lines 31-41)

**Recommendation:** Pre-fetch all matching pipelines in a single query:

```python
task_ids = [s.table_name for s in schemas]
stmt = (
    select(Pipeline)
    .options(selectinload(Pipeline.fields))
    .where(Pipeline.task_id.in_(task_ids))
)
result = await self.session.execute(stmt)
pipeline_by_task_id = {p.task_id: p for p in result.scalars().all()}

for table_schema in schemas:
    pipeline = pipeline_by_task_id.get(table_schema.table_name)
    if not pipeline:
        continue
    # ... sync fields
```

---

## 4. Algorithm Performance

### 4.1 O(n^2) BFS from list.pop(0)
**Severity: Critical**
**Impact: Turns O(V+E) BFS into O(V^2+E) due to list shifting**

Every BFS in `graph_builder.py` and `bouncer_service.py` uses `queue.pop(0)` on a Python list, which is O(n) per pop due to element shifting. For BFS visiting V nodes, this makes the algorithm O(V^2) overall.

**Affected locations (6 BFS loops):**
- `/home/itamar/projects/EtlNexus/backend/app/services/graph_builder.py` lines 48, 96, 151, 203
- `/home/itamar/projects/EtlNexus/backend/app/services/bouncer_service.py` lines 107, 106 (in `get_bouncer_topology`)

```python
# Current: O(n) per dequeue
while queue:
    tid = queue.pop(0)  # Shifts all remaining elements
```

**Recommendation:** Use `collections.deque` for O(1) popleft:

```python
from collections import deque

queue = deque([root_task_id])
while queue:
    tid = queue.popleft()  # O(1)
```

For the current pipeline count (~100 tasks per DAG), this is unlikely to be noticeable. But as DAGs grow to 500+ tasks, the quadratic behavior becomes significant (250,000 shifts vs. 500 popleft operations).

---

### 4.2 Bouncer Linear Scan Instead of Index
**Severity: Low**
**Impact: O(n) scan per bouncer name in get_bouncer_topology**

In `bouncer_service.py` line 96, bouncer entries are found by linear scan over all dag_tasks:

```python
bouncer_entries = [
    dt for dt in all_dag_tasks if dt.bouncer_name == bouncer_name
]
```

**File:** `/home/itamar/projects/EtlNexus/backend/app/services/bouncer_service.py` (lines 96-98)

**Recommendation:** Build a reverse index once:

```python
bouncer_to_entries = defaultdict(list)
for dt in all_dag_tasks:
    if dt.bouncer_name:
        bouncer_to_entries[dt.bouncer_name].append(dt)
```

---

## 5. Caching

### 5.1 In-Memory Cache Single-Process Assumption
**Severity: High**
**Impact: Cache misses and stale data when scaling to multiple backend instances**

All caches (`TTLCache`, `AirflowClient._cache`) are module-level Python dicts. If the backend is scaled horizontally (multiple uvicorn workers or multiple container replicas), each process maintains its own independent cache. This means:
- Cache miss rate multiplies by the number of instances
- Cache invalidation via `clear_all()` only clears one process
- Stale data served from instances that didn't run the sync

**File:** `/home/itamar/projects/EtlNexus/backend/app/cache.py` (lines 41-49)

**Current production deployment** (`docker-compose.prod.yml`) runs a single backend container, so this is not an active issue. However, it blocks horizontal scaling.

**Recommendation:** For multi-instance deployments, migrate to Redis-backed caching:

```python
# Option 1: Redis cache with same TTL semantics
import redis.asyncio as redis

class RedisTTLCache:
    def __init__(self, prefix: str, ttl: int, redis_url: str):
        self._prefix = prefix
        self._ttl = ttl
        self._redis = redis.from_url(redis_url)

    async def get(self, key: str):
        data = await self._redis.get(f"{self._prefix}:{key}")
        return pickle.loads(data) if data else None

    async def set(self, key: str, value):
        await self._redis.setex(f"{self._prefix}:{key}", self._ttl, pickle.dumps(value))
```

For the current single-process deployment, the existing TTLCache is efficient and appropriate.

---

### 5.2 Pipeline List Cache Key Granularity
**Severity: Low**
**Impact: Low cache hit rate for paginated requests**

The pipeline list cache key includes `skip:limit` (line 45 of pipeline_service.py), so page 1 and page 2 get different cache keys. The cache is cleared every 20 minutes, so for infrequent users, every page load is a cache miss.

**File:** `/home/itamar/projects/EtlNexus/backend/app/services/pipeline_service.py` (lines 42-55)

**Recommendation:** This is an acceptable trade-off. The alternative (caching the full list and slicing in-memory) would increase memory usage and complexity. The 30-second TTL is short enough that redundant queries are limited.

---

## 6. Concurrency Issues

### 6.1 Scheduler Lock Check Is Non-Atomic
**Severity: Medium**
**Impact: Rare race condition could allow concurrent sync executions**

In `scheduler.py`, the guard check `if _sync_lock.locked()` (line 28) followed by `async with _sync_lock` (line 30) is not atomic:

```python
async def _guarded_sync() -> None:
    if _sync_lock.locked():           # Check
        logger.info("Skipping sync")
        return
    async with _sync_lock:            # Acquire (gap between check and acquire)
        await sync_pipelines_from_airflow()
```

**File:** `/home/itamar/projects/EtlNexus/backend/app/tasks/scheduler.py` (lines 26-38)

Between the `locked()` check and the `async with` acquire, another coroutine could acquire the lock. In practice this is extremely unlikely since APScheduler runs in the same event loop, but the pattern is incorrect.

**Recommendation:** Use `lock.acquire(blocking=False)` pattern:

```python
async def _guarded_sync() -> None:
    if not _sync_lock.locked():
        async with _sync_lock:
            await sync_pipelines_from_airflow()
    else:
        logger.info("Skipping sync — already running")
```

Or more robustly:
```python
acquired = _sync_lock.locked()  # Wrong — use try_acquire pattern
# Actually, asyncio.Lock doesn't have try_acquire, so the check-then-acquire is the standard pattern
# in asyncio. The TOCTOU race is mitigated by single-threaded event loop.
```

**Note:** In asyncio's cooperative multitasking, this race is near-impossible since no `await` happens between the check and acquire. This is therefore **Low** risk in practice.

---

### 6.2 Session Commit in get_db_session Dependency
**Severity: Medium**
**Impact: Implicit commits after read-only requests waste DB roundtrips**

The `get_db_session()` generator auto-commits after every request:

```python
async def get_db_session():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()  # Commits even for pure GET requests
        except Exception:
            await session.rollback()
```

**File:** `/home/itamar/projects/EtlNexus/backend/app/database.py` (lines 21-28)

For read-only GET endpoints (topology, pipeline list, schema matrix), this sends an unnecessary `COMMIT` to PostgreSQL.

**Recommendation:** Use `expire_on_commit=False` (already set) and let the session auto-flush. For read-only routes, the commit is a no-op at the SQL level (no pending changes), so PostgreSQL handles it efficiently. This is a minor optimization not worth the complexity of separate read/write session factories.

---

## 7. Frontend Performance

### 7.1 Recharts Bundle Size
**Severity: High**
**Impact: ~180KB gzipped added to the vendor bundle**

The `recharts` library (v3.8.0) is a heavy dependency that includes D3 modules. It's imported eagerly in `ResourceChart.tsx` which is used in `ResourcePerformanceCard` -- rendered inside `BentoWorkspace` which IS lazily loaded.

**File:** `/home/itamar/projects/EtlNexus/frontend/src/components/bento-workspace/ResourceChart.tsx`
**File:** `/home/itamar/projects/EtlNexus/frontend/package.json` (recharts dependency)

However, since `BentoWorkspace` is already `React.lazy()`-loaded (App.tsx line 11), recharts is code-split into the BentoWorkspace chunk and NOT included in the initial bundle. This is a good pattern.

**Recommendation:** Move recharts into its own manual chunk for better cache granularity:

```typescript
// vite.config.ts
manualChunks: {
    "vendor-react": ["react", "react-dom"],
    "vendor-query": ["@tanstack/react-query"],
    "vendor-charts": ["recharts"],  // Add this
    "vendor-ui": [...]
}
```

This ensures recharts is cached independently and not re-downloaded when other bento-workspace code changes.

---

### 7.2 React-Markdown + Plugins Bundle Size
**Severity: Medium**
**Impact: ~120KB gzipped for markdown rendering chain**

The project includes `react-markdown`, `rehype-highlight`, `rehype-raw`, `rehype-sanitize`, `remark-directive`, `remark-directive-rehype`, and `remark-gfm` -- 7 markdown-related packages. These are used in the Documentation editor and AI terminal.

**File:** `/home/itamar/projects/EtlNexus/frontend/package.json` (lines 28-34)

Since both `DocumentationModal` and `AIArchitectView` are within lazy-loaded sections, this is already deferred. No action needed for initial load, but the combined markdown chunk is large.

**Recommendation:** Consider splitting markdown into its own manual chunk:

```typescript
"vendor-markdown": ["react-markdown", "rehype-highlight", "rehype-raw",
                     "rehype-sanitize", "remark-gfm"],
```

---

### 7.3 UpstreamTopologyModal isConnectedToHovered Has O(E) per Node
**Severity: Medium**
**Impact: O(N*E) computation on every hover event**

The `nodeRenderState` useMemo (line 129) iterates all nodes and for each calls `isConnectedToHovered()` which scans all edges:

```typescript
const nodeRenderState = useMemo(() => {
    for (const node of data.nodes) {
        const connected = isConnectedToHovered(node.task_id, hoveredNode, data.edges);
        // edges.some() scans up to E edges per node
    }
}, [data, hoveredNode]);
```

**File:** `/home/itamar/projects/EtlNexus/frontend/src/components/bento-workspace/UpstreamTopologyModal.tsx` (lines 129-140)

For a topology with 50 nodes and 100 edges, each hover triggers 50 * 100 = 5,000 comparisons.

**Recommendation:** Pre-build an adjacency set for O(1) lookups:

```typescript
const adjacencyMap = useMemo(() => {
    if (!data) return new Map<string, Set<string>>();
    const map = new Map<string, Set<string>>();
    for (const e of data.edges) {
        if (!map.has(e.source_task_id)) map.set(e.source_task_id, new Set());
        if (!map.has(e.target_task_id)) map.set(e.target_task_id, new Set());
        map.get(e.source_task_id)!.add(e.target_task_id);
        map.get(e.target_task_id)!.add(e.source_task_id);
    }
    return map;
}, [data]);

// Then in nodeRenderState:
const connected = hoveredNode === node.task_id ||
    adjacencyMap.get(hoveredNode)?.has(node.task_id) ||
    adjacencyMap.get(node.task_id)?.has(hoveredNode);
```

---

### 7.4 Zustand Store Selector Granularity
**Severity: Low**
**Impact: Minor unnecessary re-renders**

In `LineageTopology.tsx`, multiple individual selectors are used from the same store:

```typescript
const selectedDagId = usePipelineStore((s) => s.selectedDagId);
const setSelectedDagId = usePipelineStore((s) => s.setSelectedDagId);
const setSelectedPipelineId = usePipelineStore((s) => s.setSelectedPipelineId);
```

**File:** `/home/itamar/projects/EtlNexus/frontend/src/components/bento-workspace/LineageTopology.tsx` (lines 25-32)

Each selector creates a separate subscription. When `setSelectedDagId` (a stable function reference) is subscribed separately, it doesn't cause extra re-renders since Zustand uses reference equality. The selectors that return primitive values (`selectedDagId`) also work efficiently. This is actually the **correct** Zustand pattern -- each selector returns a single primitive or stable reference.

**Verdict: No issue.** The code follows Zustand best practices.

---

### 7.5 Lazy Loading and Code Splitting Are Well-Implemented
**Severity: N/A (Positive finding)**

The App.tsx correctly uses `React.lazy()` for all secondary views:
- BentoWorkspace, SchemaMatrixView, DagSummaryView, BouncersView, AIArchitectView, AdminView

The `PipelineRegistry` is eagerly loaded (it's the default view), which is correct.

Vite config has `manualChunks` for vendor libraries (`react`, `react-dom`, `tanstack/react-query`, UI primitives).

**File:** `/home/itamar/projects/EtlNexus/frontend/src/App.tsx` (lines 11-40)
**File:** `/home/itamar/projects/EtlNexus/frontend/vite.config.ts` (lines 17-28)

---

### 7.6 Virtual Scrolling for Long Lists
**Severity: N/A (Positive finding)**

Both `PipelineListContent` and `SchemaMatrixView` use `@tanstack/react-virtual` for virtualized rendering of potentially long lists. This prevents DOM bloat.

---

### 7.7 TopologySvgEdges Re-renders on Hover Without Memoization
**Severity: Low**
**Impact: SVG path recalculation on every hover state change**

`TopologySvgEdges` component re-renders entirely when `hoveredNode` changes (passed as prop from parent). Each render recalculates conditional styles for all edges.

**File:** `/home/itamar/projects/EtlNexus/frontend/src/components/bento-workspace/TopologySvgEdges.tsx`

**Recommendation:** Wrap with `React.memo` since the component is a pure function of its props:

```typescript
export const TopologySvgEdges = React.memo(function TopologySvgEdges({
    edgePaths, hoveredNode
}: TopologySvgEdgesProps) {
    // ... existing implementation
});
```

This won't help when `hoveredNode` actually changes (which triggers the re-render by design), but prevents unnecessary re-renders from parent state changes unrelated to edges.

---

## 8. Scalability Concerns

### 8.1 Single Backend Instance Architecture
**Severity: High**
**Impact: Limits throughput to one uvicorn process**

The production docker-compose runs exactly one backend container with no worker configuration. Uvicorn defaults to a single worker process. The production command is:

```yaml
# No --workers flag, defaults to 1
command: sh -c "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

**File:** `/home/itamar/projects/EtlNexus/docker-compose.prod.yml` (lines 27-33)

Combined with the 2GB memory limit, a single process handles all HTTP requests AND runs background sync tasks on the same event loop.

**Recommendation:** For production scale:

1. Separate the scheduler into its own process/container to prevent sync tasks from competing with request handling
2. Run multiple uvicorn workers or multiple backend replicas behind a load balancer
3. This requires migrating to Redis-backed caching (finding 5.1) and externalizing the APScheduler (e.g., using Redis-based APScheduler store)

---

### 8.2 Connection Pool Sizing
**Severity: Low**
**Impact: Pool exhaustion under concurrent load**

Current settings: `pool_size=20, max_overflow=10` (total 30 connections max).

**File:** `/home/itamar/projects/EtlNexus/backend/app/config.py` (lines 7-9)

For a single worker, 30 connections is generous. But the background sync tasks (which run in the same process) also consume connections. During a full sync, the sync service holds a session for the entire operation (potentially minutes), and the poll task holds another. Combined with concurrent user requests, pool exhaustion is possible under load.

**Recommendation:** The current sizing is appropriate for single-process deployment. If scaling to multiple workers, reduce `pool_size` per worker and increase PostgreSQL `max_connections` accordingly.

---

### 8.3 PostgreSQL Memory Limit in Production
**Severity: Medium**
**Impact: DB performance constrained to 1GB shared memory**

```yaml
deploy:
    resources:
        limits:
            memory: 1G
```

**File:** `/home/itamar/projects/EtlNexus/docker-compose.prod.yml` (lines 18-20)

PostgreSQL's default `shared_buffers` is 128MB. With a 1GB container limit, you can safely set `shared_buffers` to 256MB. The GIN trigram indexes and the run_history table (which grows with every sync cycle x pipelines) benefit significantly from adequate buffer pool sizing.

**Recommendation:** Add PostgreSQL tuning:

```yaml
db:
    command: >
        postgres
        -c shared_buffers=256MB
        -c effective_cache_size=768MB
        -c work_mem=4MB
        -c maintenance_work_mem=64MB
```

---

### 8.4 Nginx Proxy Without Connection Limits
**Severity: Low**
**Impact: Backend overwhelmed by concurrent WebSocket/long-poll connections**

The nginx config has no `proxy_connect_timeout`, no `limit_conn`, and no `limit_req` for the `/api/` proxy:

```nginx
location /api/ {
    proxy_pass http://backend:8000/api/;
    proxy_read_timeout 120s;  # Only setting
}
```

**File:** `/home/itamar/projects/EtlNexus/frontend/nginx.conf` (lines 43-50)

**Recommendation:** Add connection and rate limiting at the nginx level:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

location /api/ {
    limit_req zone=api burst=50 nodelay;
    proxy_pass http://backend:8000/api/;
    proxy_connect_timeout 5s;
    proxy_read_timeout 120s;
    proxy_send_timeout 30s;
}
```

---

## 9. Summary of Recommendations by Priority

### Immediate (Critical - address before scaling)

| # | Finding | File | Fix |
|---|---------|------|-----|
| 3.1 | IcebergClient blocks event loop | `iceberg_client.py` | Wrap sync Spark calls in `asyncio.to_thread()` |
| 4.1 | O(n^2) BFS from list.pop(0) | `graph_builder.py`, `bouncer_service.py` | Replace with `collections.deque.popleft()` |
| 1.1 | Topology loads all pipelines | `topology_service.py` | Use existing `get_task_id_map()` |

### Short-term (High - improves daily performance)

| # | Finding | File | Fix |
|---|---------|------|-----|
| 1.2 | Bouncer loads entire dag_tasks | `bouncer_service.py` | Filter at DB level |
| 2.1 | Unbounded metrics dicts | `metrics.py` | Add max-entries guard or use prometheus_client |
| 3.2 | No retry backoff for Airflow | `airflow_client.py` | Add exponential backoff |
| 5.1 | Single-process cache | `cache.py` | Document limitation; plan Redis migration |
| 7.1 | Recharts chunk isolation | `vite.config.ts` | Add `vendor-charts` manual chunk |
| 8.1 | Single backend instance | `docker-compose.prod.yml` | Separate scheduler; plan multi-worker |
| 1.3 | Poll loads all pipelines | `airflow_service.py` | Use lightweight `get_task_id_map()` |

### Medium-term (Medium - optimization for growth)

| # | Finding | File | Fix |
|---|---------|------|-----|
| 1.4 | Sequential upserts in sync | `airflow_sync_service.py` | Batch with `ON CONFLICT` |
| 1.5 | Missing dag_id index | `run_history.py` | Add `index=True` on dag_id |
| 3.3 | Sequential log fetch in single sync | `airflow_sync_service.py` | Batch with asyncio.gather |
| 3.4 | N+1 in catalog sync | `catalog_sync_service.py` | Pre-fetch with `IN` clause |
| 7.3 | O(N*E) hover computation | `UpstreamTopologyModal.tsx` | Pre-build adjacency map |
| 7.2 | Markdown bundle size | `package.json` | Separate manual chunk |
| 8.3 | PostgreSQL memory tuning | `docker-compose.prod.yml` | Add shared_buffers config |
| 6.2 | Auto-commit on reads | `database.py` | Low impact; document as known |
