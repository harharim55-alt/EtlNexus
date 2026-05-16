# Execution Plans: End-to-End Flow

How ETL execution plans are generated, emitted, ingested, stored, served, and rendered.

---

## 1. Generation (Spark-side)

**File:** `etlnexus-hooks/src/etlnexus_hooks/spark_introspect.py`

After an ETL task completes, `extract_execution_plan(spark, result_df)` builds a JSON-serializable tree from Spark's internal plan representation.

### Primary path: StatusStore graph

`_build_tree_from_graph(spark)` reads the **AppStatusStore** — the same data source backing the Spark UI.

```
spark._jsparkSession.sharedState().statusStore()
  → executionsList() → last execution ID
  → planGraph(execId)   — graph structure (nodes + edges)
  → executionMetrics(execId) — accumulator values (timing, row counts, bytes)
```

The graph is walked root-first. For each node:

1. **Name** extracted from the first line of `node.desc()`, stripped of column IDs (`#123L`)
2. **Type** classified by `_classify_node()`:
   - `read` — name contains "scan" or "datasource"
   - `write` — contains "write", "insert", "overwrite", "append"
   - `shuffle` — contains "join", "exchange", "sort", "shuffle"
   - `transform` — everything else
3. **Detail / full_detail** extracted by node-type-specific parsers (`_parse_join_detail`, `_parse_scan_detail`, `_parse_filter_detail`, etc.) that pull structured info from the raw description
4. **Metrics** collected from accumulator IDs — zero values and noise metrics are filtered out, display names are mapped via `_METRIC_DISPLAY`
5. **Wrapper nodes skipped** — `AdaptiveSparkPlan`, `WholeStageCodegen`, `InputAdapter`, `ColumnarToRow`, etc. are elided; their children are promoted

### Fallback: initial plan (pre-AQE)

If AQE collapsed the StatusStore graph to 3 or fewer nodes (e.g., `LocalTableScan`), `_build_tree_from_initial_plan(spark, result_df)` builds the tree from the pre-AQE plan instead:

```python
plan = result_df._jdf.queryExecution().executedPlan()
initial = plan.initialPlan()  # if AdaptiveSparkPlan
info = SparkPlanInfo.fromSparkPlan(initial)
graph = SparkPlanGraph.apply(info)
```

Same tree-building logic, but **without metrics** (different accumulator ID space).

### Output node structure

```json
{
  "id": 1,
  "name": "SortMergeJoin",
  "type": "shuffle",
  "detail": "inner on port_id",
  "full_detail": "inner on [port_id] = [port_id]",
  "metrics": { "sort time": "1.2s", "output rows": "45,230" },
  "children": [ /* recursive */ ]
}
```

---

## 2. Emission (Log Marker)

**File:** `etlnexus-hooks/src/etlnexus_hooks/mixin.py` (lines 123-131)

After `extract()` / `transform()` / `load()` complete, the mixin prints the plan as a log marker:

```python
plan = extract_execution_plan(spark, result_df)
if plan:
    print(f"ETL_EXECUTION_PLAN: {json.dumps(plan)}")
```

This goes to **stdout**, which Airflow captures in the task instance log. The marker prefix `ETL_EXECUTION_PLAN:` is the contract between the hooks library and the backend parser.

Other markers emitted in the same flow: `ETL_WRITES_TO:`, `ETL_DESCRIPTION:`, `ETL_RESOURCE_ACTUAL:`.

---

## 3. Ingestion (Backend)

Two background jobs fetch Airflow logs and extract execution plans:

### 3a. Log fetching

**File:** `backend/app/integrations/airflow_client.py` — `get_task_log(dag_id, dag_run_id, task_id, try_number)`

```
GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/{try_number}
```

Returns raw log text. Fetched in parallel with semaphore-limited concurrency (6-10 concurrent).

### 3b. Marker parsing

**File:** `backend/app/parsers/log_parser.py` — `parse_execution_plan(log_content)`

```python
def parse_execution_plan(log_content: str) -> str | None:
    raw = parse_log_marker(log_content, "ETL_EXECUTION_PLAN:")
    if raw is None:
        return None
    json.loads(raw)  # validate only — not parsed
    return raw        # returns the raw JSON string
```

`parse_log_marker` scans lines, splits on the marker, returns the trimmed text after it.

The raw JSON string is returned (not a dict) for direct storage.

### 3c. Orchestration

**Polling** (`backend/app/services/airflow_service.py` — `poll_all_statuses`, every 20 min):

Fetches the 5 most recent DAG runs per pipeline. For successful runs missing resource data, fetches logs and extracts:

```python
actuals = parse_resource_actual(log_content)
plan_json = parse_execution_plan(log_content)
if plan_json:
    actuals = actuals or {}
    actuals["execution_plan"] = plan_json
if actuals:
    await self.resource_repo.update_run_actuals(pipeline_id, dag_id, dag_run_id, actuals)
```

**Sync** (`backend/app/services/airflow_sync_service.py` — `sync_all`, every 20 min):

Same extraction logic during initial pipeline discovery and periodic sync.

---

## 4. Storage

### Database model

**File:** `backend/app/models/run_history.py` — table `pipeline_run_history`

```python
execution_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Stored as a **TEXT column** containing the raw JSON string. Added in migration `013_add_execution_plan`.

### Repository queries

**File:** `backend/app/repositories/resource_repo.py`

| Method | Purpose | Filters |
|---|---|---|
| `get_latest_execution_plan(pipeline_id)` | Most recent plan | `status='success'`, `execution_plan IS NOT NULL`, ordered by `start_date DESC` |
| `get_execution_plan_by_run(pipeline_id, dag_run_id)` | Plan for specific run | `execution_plan IS NOT NULL` |
| `get_execution_plan_runs(pipeline_id, skip, limit)` | Paginated list of runs with plans | `status='success'`, `execution_plan IS NOT NULL` |

### Service layer

**File:** `backend/app/services/resource_service.py` — `get_execution_plan(pipeline_id, dag_run_id=None)`

Parses the stored JSON string at request time (`json.loads`), assembles the response with metadata (dag_id, task_id, duration, execution_date).

### API endpoints

**File:** `backend/app/routers/resources.py`

| Endpoint | Response |
|---|---|
| `GET /api/pipelines/{id}/execution-plan?dag_run_id=` | `ExecutionPlanResponse` — plan tree + run metadata |
| `GET /api/pipelines/{id}/execution-plan/runs?skip=&limit=` | `ExecutionPlanRunsResponse` — paginated run list |

Both protected by `require_pipeline_visibility()`.

### API schema

**File:** `backend/app/schemas/execution_plan.py`

```python
class ExecutionPlanNode(BaseModel):
    id: int
    name: str
    type: str              # "read" | "write" | "shuffle" | "transform"
    detail: str
    full_detail: str = ""
    metrics: dict[str, str] = {}
    children: list[ExecutionPlanNode] = []   # recursive

class ExecutionPlanResponse(BaseModel):
    dag_id: str
    dag_run_id: str
    task_id: str
    status: str
    duration_seconds: float | None = None
    execution_date: str | None = None
    execution_plan: ExecutionPlanNode | None = None
```

---

## 5. Frontend Rendering

### Data fetching

| File | What |
|---|---|
| `frontend/src/api/execution-plan.ts` | Axios functions: `fetchExecutionPlan`, `fetchExecutionPlanRuns` |
| `frontend/src/hooks/use-execution-plan.ts` | `useExecutionPlan(pipelineId, dagRunId)` — TanStack Query, 5 min stale time |
| `frontend/src/types/execution-plan.ts` | TypeScript interfaces mirroring Pydantic schemas |

### Component hierarchy

```
BentoWorkspace
  └─ TransformInspectorCard          (embedded, col-span-12, max-h 500px)
       ├─ Header: DAG icon, title, dag_id, duration, RunPicker, Overview toggle, Full Plan button
       ├─ Tree viewport (pannable, scaleable via useOverview)
       │    └─ TreeNode (recursive <ul><li>)
       │         └─ PlanNodeCard (compact 170-260px card)
       │              ├─ Icon + name (colored by type)
       │              ├─ Detail text (2-line clamp)
       │              ├─ Metrics (time keys prominent, noise hidden)
       │              └─ Expand button → NodeDetailModal
       └─ Full Plan button → ExecutionPlanModal (92vw x 88vh, dot-grid bg)
```

**File:** `frontend/src/components/bento-workspace/TransformInspectorCard.tsx`
**File:** `frontend/src/components/bento-workspace/ExecutionPlanModal.tsx`
**File:** `frontend/src/components/bento-workspace/execution-plan/PlanTree.tsx`
**File:** `frontend/src/components/bento-workspace/execution-plan/PlanNodeCard.tsx`

### Node styling

**File:** `frontend/src/components/bento-workspace/execution-plan/plan-constants.ts`

| Type | Color | Icon |
|---|---|---|
| `read` | Blue | Database |
| `write` | Emerald | HardDrive |
| `shuffle` | Amber | ArrowRightLeft |
| `transform` | Indigo | Activity |

### Detail modal & formatters

When a user clicks "expand" on a node card, `NodeDetailModal` opens with two tabs: **Formatted** and **Raw**.

**File:** `frontend/src/components/bento-workspace/execution-plan/PlanFormatters.tsx`

`FormattedDetail` dispatches to a specialized formatter based on node name:

| Node pattern | Formatter | Parses |
|---|---|---|
| scan, datasource | `ScanFormatter` | Table, namespace, columns, pushed filters |
| join | `JoinFormatter` | Join type, left/right keys, strategy |
| filter | `FilterFormatter` | Date ranges, IN lists, equality, ranges, NOT NULL, complex expressions |
| project | `ProjectFormatter` | Columns and expressions |
| aggregate | `AggregateFormatter` | GROUP BY keys, aggregate functions |
| sort | `SortFormatter` | Sort columns + ASC/DESC |
| window | `WindowFormatter` | PARTITION BY, ORDER BY, window functions |
| exchange | `ExchangeFormatter` | Partition strategy |
| union, expand, generate, limit | `LightFormatter` | Basic detail |
| fallback | `FallbackFormatter` | Raw detail text |

**Parsers:** `frontend/src/components/bento-workspace/execution-plan/plan-parsers.ts`

Includes `parseSmartFilter` which classifies filter predicates into semantic groups (date ranges, IN lists, equality, ranges, complex expressions) and simplifies `CASE WHEN` patterns into `IN` lists.

### Interaction

| Hook | Purpose |
|---|---|
| `usePannable` | Drag-to-pan on the tree viewport |
| `useOverview` | Calculate scale to fit tree in viewport, toggle overview mode |
| `RunPicker` (`PlanRunSelector.tsx`) | Dropdown to switch between historical runs, infinite scroll pagination |

---

## Data Flow Summary

```
ETL task completes
  → spark_introspect.extract_execution_plan(spark, result_df)
    → _build_tree_from_graph(spark)  [or _build_tree_from_initial_plan fallback]
    → returns dict tree
  → mixin prints: ETL_EXECUTION_PLAN: {json}
  → Airflow captures in task log

Backend poll/sync job (every 20 min)
  → airflow_client.get_task_log(dag_id, run_id, task_id)
  → log_parser.parse_execution_plan(log_content) → raw JSON string
  → resource_repo.update_run_actuals(..., {"execution_plan": json_str})
  → stored in pipeline_run_history.execution_plan (TEXT)

Frontend request
  → GET /api/pipelines/{id}/execution-plan
  → resource_service.get_execution_plan() → json.loads(stored_string)
  → ExecutionPlanResponse (Pydantic → JSON)

Frontend render
  → useExecutionPlan hook → TransformInspectorCard
  → PlanTree → PlanNodeCard (per node)
  → NodeDetailModal → type-specific Formatter
```
