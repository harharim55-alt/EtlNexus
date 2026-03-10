<p align="center">
  <img src="logo.svg" width="80" height="80" alt="ETL Nexus">
</p>

<h1 align="center">ETL Nexus</h1>

<p align="center">
  <strong>A data architecture command center for discovering, understanding, and consuming ETL pipelines.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React_19-61DAFB?style=flat&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/PySpark-E25A1C?style=flat&logo=apachespark&logoColor=white" alt="PySpark">
  <img src="https://img.shields.io/badge/Iceberg-4E8EE9?style=flat&logo=apacheiceberg&logoColor=white" alt="Iceberg">
  <img src="https://img.shields.io/badge/Airflow-017CEE?style=flat&logo=apacheairflow&logoColor=white" alt="Airflow">
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white" alt="Docker">
</p>

---

## What is ETL Nexus?

ETL Nexus transforms a static data dictionary into an interactive, engineering-grade workspace. It automatically discovers pipelines from Airflow, enriches them with schema metadata from an Iceberg catalog, and presents everything through a dark-themed bento-box UI.

**Instead of digging through code, Slack threads, and wikis to find data** — open ETL Nexus and get instant answers: what data exists, where it flows, how it's performing, and how to consume it.

### The Workspace

```
 +--[ Pipeline Registry ]--+--[ Bento Workspace ]---------------------------------------+
 |                         |                                                             |
 |  Q Search pipelines...  |  [Network Infrastructure]  [Airflow: Success]  [Sync]       |
 |                         |  Bgp Route Sync                                             |
 |  > Bgp Route Sync      |                                                             |
 |    Network Infra.       |  +--[ Topology (8 col) ]---------------+ +[ Metrics (4) ]+  |
 |    Daily                |  | switch_port_collector ------>        | | Volume        |  |
 |                         |  | dns_record_sync      ------>        | | 850K/day      |  |
 |    Netflow Capture      |  |    [bgp_route_sync]                 | +---------------+  |
 |    Traffic Analytics    |  |          ------> device_fingerprint  | | Schedule      |  |
 |    Daily                |  |          ------> bandwidth_billing   | | daily         |  |
 |                         |  |   DAG: [all] [backbone] [transit]   | +---------------+  |
 |    Dhcp Lease Sync      |  +-------------------------------------+                    |
 |    Address Mgmt.        |                                                             |
 |    Daily                |  +--[ Resource & Performance (12 col, full width) ]-------+  |
 |                         |  | Run Duration      | Resources         | Capacity       |  |
 +-------------------------+  | avg 4m · max 12m  | Driver: 2g / 16g  | ████░░ 12%     |  |
                              | ▃▅▇▅▃▄▅▆▇▅▃▅     | Executor: 4g/64g  | ██░░░░  6%     |  |
                              | 12 runs  87% pass | Cores: 2 / 32     | █░░░░░  6%     |  |
                              +-------------------+-------------------+----------------+  |
                              |                                                           |
                              | +--[ Schema + Usage (7 col) ]--+ +[ Joins + Code (5) ]+  |
                              | | route_id    STRING           | | Join Intelligence   |  |
                              | | prefix      STRING           | | Dns Record Sync     |  |
                              | | next_hop    STRING           | |  ON: device_id      |  |
                              | | synced_at   TIMESTAMP        | +---------+-----------+  |
                              | +------------------------------+ | Consume Snippet     |  |
                              | | Usage          3 consumers   | | from etls import .. |  |
                              | | 1.2K reads     2 ETL · 1 API | | Catalog(Engine...)  |  |
                              | +------------------------------+ +---------------------+  |
                              +-----------------------------------------------------------+
```

## Features

### Pipeline Discovery & Search
- **Auto-discovery** from Airflow — pipeline metadata extracted from task `op_kwargs` (name, category, schedule, dependencies, resources)
- **Lineage from logs** — destination tables parsed from `ETL_WRITES_TO:` log markers, dependencies from `needs` declarations
- **Schema enrichment** from Iceberg catalog via PySpark `spark.table().schema`
- **Deep search** across pipeline names, descriptions, and field names — find which ETLs contain `device_id`

### Visual Pipeline Workspace
- **Lineage topology** — upstream dependencies, pipeline, downstream consumers in a single interactive view
- **DAG topology** — see task relationships within each Airflow DAG, with status dots (success/failed/running)
- **Schema structure** — every field with its Iceberg data type
- **Volume & schedule metrics** — rows/day and schedule at a glance
- **Consume snippets** — copy-paste Python code for both ETL import and Catalog import patterns:
  ```python
  # ETL Import
  from etls import bgp_route_sync
  bgp_route_sync("2026-01-25").consume()

  # Catalog Import
  from etls import Catalog, Engine
  Catalog(Engine.Spark).iceberg.dagger.bgp_route_sync("date").consume().as_pyspark()
  ```

### Resource & Performance Tracking
- **Allocated resources** — Spark driver/executor memory, cores, and executors per pipeline per DAG
- **DAG-specific overrides** — different resource profiles when a pipeline runs on different DAGs
- **Run history** — duration stats (avg/min/max), success rate from the last 20 runs
- **Actual usage** — real memory/CPU utilization parsed from task logs
- **Cluster capacity bars** — visualize how much of the cluster each pipeline consumes

### Downstream Consumer Tracking
- **Automatic discovery** — downstream consumers derived from Airflow's task dependency graph
- **Usage enrichment** — access counts, descriptions, and usage types (ETL vs API)
- **Status visibility** — see the health of every pipeline that depends on yours

### Join Intelligence
- **Schema matches** — automated cross-catalog field overlap detection (e.g., "Join with Dns Record Sync ON: `device_id`, `zone_name`")
- **AI insights** — LLM-powered semantic join recommendations with business context

### Live Airflow Monitoring
- Real-time DAG run status polling (configurable interval, default 20 min)
- Green/red status indicators on every pipeline in the registry
- Per-pipeline manual sync button for on-demand refresh
- Graceful degradation when Airflow is unreachable

### Global Schema Matrix
- Cross-pipeline field frequency analysis
- Spot the most common join keys (`device_id`, `timestamp`, `zone_name`) across your entire catalog

### AI Architect Terminal
- Natural language queries against your full ETL catalog
- Ask infrastructure questions: *"Which pipelines depend on switch_port_collector?"*
- Pluggable — works with any OpenAPI-compatible LLM endpoint

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, async SQLAlchemy, asyncpg, Alembic, APScheduler |
| **Frontend** | React 19, TypeScript, Vite, TanStack Query, Zustand, shadcn/ui (base-ui), Tailwind CSS v4 |
| **Catalog** | PySpark 3.5.1, Apache Iceberg (REST catalog), `spark.table().schema` |
| **Integrations** | Airflow REST API (pipeline discovery + status), OpenAPI-compatible LLM |
| **Database** | PostgreSQL 16 |
| **Packages** | uv (Python), pnpm (Node) |
| **Infrastructure** | Docker Compose with Watch (dev), nginx (prod) |

## Quick Start

### Prerequisites
- Docker & Docker Compose v2

### Run in Development

```bash
# Clone the repo
git clone <repo-url> && cd EtlNexus

# Copy environment config
cp .env.example .env

# Start everything (backend, frontend, db, airflow, iceberg catalog)
docker compose up
```

That's it. The dev environment includes:
- **Frontend** at [localhost:5173](http://localhost:5173)
- **Backend** at [localhost:8000](http://localhost:8000/api/health)
- **Airflow UI** at [localhost:8080](http://localhost:8080) (admin/admin)
- **Iceberg REST catalog** at localhost:8181
- **PostgreSQL** at localhost:5432
- 30 pre-seeded ETL pipelines across 6 Airflow DAGs with lineage, schemas, resources, and failure simulation

### File Watching (auto-reload on save)

```bash
docker compose watch
```

Backend files sync automatically (uvicorn reloads), frontend files trigger Vite HMR.

### Run in Production

```bash
# Configure external integrations
cp .env.example .env.prod
# Edit .env.prod with real Airflow URL, Iceberg catalog, LLM endpoint...

docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Production runs only `backend`, `frontend` (nginx), and `db` — all integrations point to external services via environment variables.

## Configuration

All settings via environment variables (see `.env.example`):

| Variable | Description | Dev Default |
|----------|-------------|-------------|
| `AIRFLOW_BASE_URL` | Airflow REST API | `http://airflow-webserver:8080/api/v1` |
| `AIRFLOW_USERNAME` | Airflow basic auth username | `admin` |
| `AIRFLOW_PASSWORD` | Airflow basic auth password | `admin` |
| `AIRFLOW_POLL_INTERVAL_MINUTES` | Sync & poll interval | `20` |
| `ICEBERG_CATALOG_URI` | Iceberg REST catalog endpoint | `http://iceberg-rest:8181` |
| `ICEBERG_NAMESPACE_PREFIX` | Namespace to scan for tables | `dagger` |
| `LLM_API_BASE_URL` | OpenAPI-compatible LLM endpoint | _(empty, optional)_ |
| `LLM_API_KEY` | LLM API key | _(empty)_ |
| `SPARK_MAX_DRIVER_MEMORY_GB` | Cluster capacity: max driver memory | `16` |
| `SPARK_MAX_EXECUTOR_MEMORY_GB` | Cluster capacity: max executor memory | `64` |
| `SPARK_MAX_EXECUTOR_CORES` | Cluster capacity: max CPU cores | `32` |
| `SPARK_MAX_TOTAL_EXECUTORS` | Cluster capacity: max executors | `20` |

## Architecture

```
Browser (React SPA)  <-- REST /api -->  FastAPI Backend  <-- SQL -->  PostgreSQL
                                              |
                                       +------+------+
                                       |      |      |
                                    Airflow  Iceberg  LLM
                                     API    Catalog  Endpoint
```

### How Data Flows In

All pipeline metadata originates from **Airflow**. No Git repository is needed.

1. **Pipeline discovery** — the backend calls Airflow's REST API to list DAGs and tasks. Each task's `op_kwargs` carries metadata: `etl_name`, `category`, `schedule`, `needs` (dependencies), `resources` (Spark config).
2. **Lineage** — `needs` fields become `reads_from` edges; `ETL_WRITES_TO:` log markers become `writes_to` edges.
3. **Descriptions** — parsed from `ETL_DESCRIPTION:` log markers, with fallback to title-cased task IDs.
4. **Resources** — `op_kwargs.resources` contains default + DAG-override Spark configs. Actual usage is logged as `ETL_RESOURCE_ACTUAL:` JSON during execution.
5. **Schemas** — enriched from the Iceberg catalog via PySpark every 2 hours.
6. **Consumers** — derived from Airflow's task dependency graph (`downstream_task_ids`), enriched with usage metadata from the database.

### Backend — Three-Layer Pattern

```
Router (HTTP) --> Service (business logic) --> Repository (data access)
                       |
                  Integrations (Airflow, Iceberg, LLM)
```

- `app/routers/` — FastAPI endpoints under `/api/`
- `app/services/` — orchestrates repositories and integration clients
- `app/repositories/` — async SQLAlchemy queries
- `app/integrations/` — external system clients (Airflow, Iceberg, LLM)
- `app/tasks/` — APScheduler background jobs

### Frontend — State Separation

- **TanStack Query** — all server state (pipelines, lineage, topology, resources, usage, airflow statuses)
- **Zustand** — client-only UI state (active tab, selected pipeline, selected DAG, chat history)
- Components organized by feature: `layout/`, `pipeline-registry/`, `bento-workspace/`, `schema-matrix/`, `ai-terminal/`, `shared/`

### Background Tasks

| Task | Interval | What it does |
|------|----------|-------------|
| Airflow Sync | 20 min | Discover pipelines, lineage, resources, DAG topology from Airflow API + task logs |
| Airflow Status Poll | 20 min | Fetch 5 recent runs per DAG, record run history + actual resource usage |
| Catalog Sync | 2 hours | Read table schemas from Iceberg via PySpark, sync fields to DB |

All tasks share an asyncio lock to prevent concurrent execution.

## Project Structure

```
EtlNexus/
  docker-compose.yml            # Dev environment (all services + Compose Watch)
  docker-compose.prod.yml       # Prod (backend + frontend + db only)
  .env.example                  # Configuration template

  backend/
    app/
      main.py                   # FastAPI app + lifespan (scheduler, startup sync)
      config.py                 # Pydantic BaseSettings
      cache.py                  # TTL caches (pipeline list, schema matrix, topology)
      models/                   # SQLAlchemy ORM (Pipeline, LineageEdge, DagTask, ...)
      schemas/                  # Pydantic request/response DTOs
      routers/                  # API endpoints (pipelines, lineage, topology, resources, usage, ai)
      services/                 # Business logic (sync, poll, resource metrics, AI chat)
      repositories/             # Async SQLAlchemy queries
      integrations/             # Airflow (httpx), Iceberg (PySpark), LLM clients
      tasks/                    # APScheduler background jobs + usage seed data
    alembic/                    # Database migrations (9 revisions)

  frontend/
    src/
      components/               # React components by feature
        layout/                 # AppShell, Sidebar, NavIcon
        pipeline-registry/      # PipelineRegistry, PipelineSearch, PipelineListItem
        bento-workspace/        # BentoWorkspace, LineageTopology, SchemaViewer,
                                # ResourcePerformanceCard, UsageCard, JoinIntelligence,
                                # ConsumeSnippet, MetricsCards
        schema-matrix/          # SchemaMatrixView, FieldFrequencyRow
        ai-terminal/            # AIArchitectView, ChatMessage, ChatInput
        shared/                 # StatusBadge, CopyButton, LoadingState, ErrorState
        ui/                     # shadcn/ui primitives (Button, Card, Tooltip, ...)
      hooks/                    # TanStack Query hooks (12 hooks)
      stores/                   # Zustand stores (navigation, pipeline, ai)
      api/                      # Axios client + API functions per domain
      types/                    # TypeScript interfaces mirroring Pydantic schemas

  dev/
    dags/                       # 6 Airflow DAGs (30 ETLs, computer networking theme)
      daily/resources/          # Per-ETL Spark resource configs
      daily/task_configs/       # Per-ETL dependency declarations (needs, prefers)
      etl_runner.py             # Shared task callable (simulates ETL execution + logging)
    seeds/
      etl_code/dagger/          # Mock ETL Python files (docstrings + SUFFIXES)
      seed_iceberg.py           # Iceberg catalog seeder (30 table schemas)
```

## Dev Environment Details

The `dev/` directory creates a fully simulated data platform:

- **6 DAGs**: `backbone_core`, `perimeter_defense`, `application_mesh`, `transit_exchange`, `heartbeat_probe`, `noc_sentinel`
- **30 ETLs** across categories: Network Infrastructure, Transit/Peering, DNS/Resolution, Traffic Analytics, Address Management, Incident Management, Bandwidth/Billing, and more
- **Failure simulation**: `dhcp_lease_sync` always fails (DHCP timeout), `cdn_cost_reconciler` is 40% flaky
- **Realistic execution**: `etl_runner.py` sleeps proportionally to resource weight, logs actual resource usage with randomized but realistic values
- **Iceberg schemas**: 30 tables with realistic field definitions seeded at startup

## How Everything Works

### The Big Picture

EtlNexus is a **command center for ETL pipelines**. It answers: "What pipelines exist, what do they depend on, how are they performing, and how do I use them?" All pipeline metadata comes from **Airflow** (the scheduler), with schema details enriched from **Iceberg** (a data catalog).

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│  PostgreSQL  │
│  React SPA   │ /api│  FastAPI     │     │   Database   │
│  port 5173   │◀────│  port 8000   │◀────│   port 5432  │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌─────────┐
        │ Airflow  │ │ Iceberg  │ │  LLM    │
        │ REST API │ │ REST Cat │ │ (opt.)  │
        │ port 8080│ │ port 8181│ │         │
        └──────────┘ └──────────┘ └─────────┘
```

---

### 1. Where Does the Data Come From?

#### Pipeline Discovery (from Airflow)

Every 20 minutes, `AirflowSyncService` runs:

1. **Calls `GET /dags`** — gets all 6 DAGs (backbone_core, perimeter_defense, etc.)
2. **For each DAG, calls `GET /dags/{id}/tasks`** — gets all tasks (each task = one ETL pipeline)
3. **Fetches the latest DAG run + task instances** — reads `rendered_fields.op_kwargs` from each task instance

The `op_kwargs` is the key — it carries all metadata embedded in the DAG definition:

```python
op_kwargs={
    "etl_name": "bgp_route_sync",
    "category": "Network Infrastructure",
    "schedule": "daily",
    "needs": ["switch_port_collector"],      # hard dependencies
    "prefers": [],                            # soft dependencies
    "resources": {
        "default": {"spark_driver_memory": "2g", ...},
        "backbone_core": {"spark_executor_memory": "8g", ...}  # DAG override
    }
}
```

4. **Parses task logs** for two special markers:
   - `ETL_WRITES_TO: table_name` → destination table (lineage)
   - `ETL_DESCRIPTION: text` → human description
5. **Upserts everything to PostgreSQL** in 4 passes:
   - Pass 1: Create/update `pipelines` table + `reads_from` lineage edges
   - Pass 2: Resolve `source_pipeline_id` on edges (link dependencies)
   - Pass 3: Sync `pipeline_resource_configs` (Spark allocations per DAG)
   - Pass 4: Sync `dag_tasks` table (membership + downstream relationships)

#### Status Polling (from Airflow)

Same 20-minute cycle, `AirflowService.poll_all_statuses()`:

1. Fetches **5 most recent runs** per DAG (not just 1 — for statistics)
2. Maps task states → simplified status (success/failed/running/unknown)
3. Records each run in `pipeline_run_history` (duration, start/end dates)
4. Parses `ETL_RESOURCE_ACTUAL: {json}` from logs → actual memory/CPU used
5. Upserts latest status to `airflow_run_statuses`

#### Schema Enrichment (from Iceberg)

Every 2 hours, `CatalogSyncService`:

1. Uses **PySpark** to connect to Iceberg REST catalog
2. Lists all tables under the `dagger` namespace
3. Reads each table's schema (field names, data types)
4. Matches tables to pipelines by name
5. Updates `pipeline_fields` table

#### Seed/Enrichment Data (one-time on startup)

`seed_usage_data()` populates `pipeline_usages` with consumer descriptions, access counts, and usage types. This is enrichment data — the actual consumer relationships come from Airflow's downstream task graph.

---

### 2. Backend Architecture (Three Layers)

```
HTTP Request
    ↓
Router (FastAPI endpoint — validates input, returns response)
    ↓ Depends()
Service (business logic — aggregates data, computes stats)
    ↓
Repository (async SQLAlchemy queries — single table focus)
    ↓
PostgreSQL
```

#### Key Endpoints

| Endpoint | What It Returns | Data Source |
|----------|----------------|------------|
| `GET /api/pipelines` | Searchable list with status & success rate | DB (pipelines + airflow_run_statuses) |
| `GET /api/pipelines/{id}` | Detail: fields, lineage tables, metadata | DB (pipeline + fields + lineage_edges) |
| `GET /api/pipelines/{id}/lineage` | Graph: source nodes → pipeline → target nodes | DB (lineage_edges) |
| `GET /api/pipelines/{id}/topology` | DAG view: upstream needs → current → downstream | DB (dag_tasks) + enriched with statuses |
| `GET /api/pipelines/{id}/resources` | Spark configs, run history, capacity bars | DB (resource_configs + run_history) + computed stats |
| `GET /api/usage/{etl_name}` | Downstream consumers with access counts | DB (dag_tasks for graph + pipeline_usages for enrichment) |
| `GET /api/schema-matrix` | Fields appearing in 2+ pipelines | DB (pipeline_fields aggregated) |
| `GET /api/airflow/status` | All pipeline statuses + Airflow connectivity | DB (airflow_run_statuses) |
| `POST /api/ai/chat` | LLM response with catalog context | External LLM endpoint |
| `POST /api/pipelines/{id}/sync` | Manual re-sync from Airflow | Airflow API → DB |

#### Database Tables (9 migrations)

```
pipelines ──────┬── pipeline_fields (schema columns)
                ├── lineage_edges (reads_from / writes_to)
                ├── airflow_run_statuses (latest status per pipeline)
                ├── pipeline_resource_configs (Spark allocations per DAG)
                ├── pipeline_run_history (every run: duration + actual usage)
                └── dag_tasks (DAG membership + dependency graph)

pipeline_usages (enrichment: consumer descriptions, access counts)
```

#### Integration Clients

- **AirflowClient** — persistent `httpx.AsyncClient`, basic auth, 10s timeout, 2 retries, 5-min TTL cache for DAG/task definitions
- **IcebergClient** — PySpark `SparkSession` connecting to REST catalog, lazy initialization
- **LLMClient** — OpenAPI-compatible POST to `/chat/completions`, optional (degrades gracefully)

#### Background Tasks (APScheduler)

| Task | Interval | What It Does |
|------|----------|-------------|
| Pipeline sync + status poll | 20 min | Full Airflow discovery + status update |
| Catchup sync | 5 min after start (one-shot) | Ensures sync runs even if Airflow is slow to boot |
| Catalog sync | 2 hours | Iceberg schema refresh |

All tasks share an `asyncio.Lock` — if one is running, others skip.

---

### 3. Frontend Architecture

#### State Management (Two Systems)

**Server state** = TanStack Query (data from the API):

```
Component → useQuery hook → API function (Axios) → Backend → Cache
```

Each hook has a cache key like `["pipeline", id]` with a `staleTime` (1–5 min). Data is automatically refetched when stale.

**Client state** = Zustand stores (UI-only state):

- `navigation-store` — which tab is active (catalog | matrix | ai)
- `pipeline-store` — selected pipeline ID, selected DAG ID, search query
- `ai-store` — chat message history, isTyping flag

#### Data Flow Example: Selecting a Pipeline

1. User clicks a pipeline in `PipelineListItem`
2. → `pipelineStore.setSelectedPipelineId(id)` (Zustand)
3. → `BentoWorkspace` renders, calls `usePipelineDetail(id)` (TanStack Query)
4. → Hook calls `fetchPipelineDetail(id)` → `GET /api/pipelines/{id}`
5. → Backend returns detail + fields + source/destination tables
6. → All child cards render with the data
7. → Each card may fire its own hook: `useLineage(id)`, `useTopology(id)`, `useResourceMetrics(id)`, `usePipelineUsage(name)`

#### UI Layout

```
┌─────────────────┬──────────────────────────────────────┐
│ Sidebar (80px)  │  Main Content                        │
│                 │                                      │
│ [Catalog]       │  Tab: Catalog                        │
│ [Matrix]        │  ┌─────────────┬───────────────────┐ │
│ [AI]            │  │ Pipeline    │ Bento Workspace   │ │
│                 │  │ Registry    │                   │ │
│                 │  │ (400px)     │ Row 1: Lineage +  │ │
│                 │  │             │        Metrics    │ │
│                 │  │ Search bar  │                   │ │
│                 │  │ Grouped     │ Row 2: Resources  │ │
│                 │  │ list items  │        (full w)   │ │
│                 │  │             │                   │ │
│ [Airflow dot]   │  │             │ Row 3: Schema +   │ │
│                 │  │             │  Usage | Joins +  │ │
│                 │  │             │  Snippets         │ │
└─────────────────┴──┴─────────────┴───────────────────┴─┘
```

#### Component → Data Source Map

| Component | Hook | API Endpoint | What It Shows |
|-----------|------|-------------|---------------|
| `PipelineRegistry` | `usePipelines(query)` | `GET /api/pipelines?query=` | Searchable master list grouped by category |
| `BentoHeader` | `usePipelineDetail(id)` | `GET /api/pipelines/{id}` | Name, description, status badge, sync button |
| `LineageTopology` | `useLineage(id)` + `useTopology(id)` | `GET .../lineage` + `GET .../topology` | Upstream → Current → Downstream flow with status dots |
| `MetricsCards` | (from detail) | (same as header) | Volume rate, schedule |
| `ResourcePerformanceCard` | `useResourceMetrics(id)` | `GET .../resources` | Duration stats, Spark configs, capacity bars |
| `SchemaViewer` | (from detail) | (same as header) | Field names + data types |
| `UsageCard` | `usePipelineUsage(name)` | `GET /api/usage/{name}` | Downstream consumers, access counts, status |
| `JoinIntelligence` | `useJoinSuggestions(id)` | `GET .../joins` + `GET .../joins/ai` | Schema matches + AI insight |
| `ConsumeSnippet` | (from detail) | (same as header) | Python import code snippets |
| `SchemaMatrixView` | `useSchemaMatrix()` | `GET /api/schema-matrix` | Field frequency across all pipelines |
| `AIArchitectView` | `useAIChat()` (mutation) | `POST /api/ai/chat` | Chat with LLM using catalog context |
| Sidebar (Airflow dot) | `useAirflowStatuses()` | `GET /api/airflow/status` | Green/red connectivity indicator |

---

### 4. How Specific Features Work End-to-End

#### Pipeline Lineage

```
Airflow task op_kwargs.needs = ["switch_port_collector"]
    ↓ (AirflowSyncService)
lineage_edges: {source_table: "switch_port_collector", edge_type: "reads_from"}
    +
Airflow task logs: "ETL_WRITES_TO: bgp_routes_enriched"
    ↓
lineage_edges: {target_table: "bgp_routes_enriched", edge_type: "writes_to"}
    ↓ (GET /api/pipelines/{id}/lineage)
LineageGraph: {nodes: [...], edges: [...]}
    ↓ (useLineage hook)
LineageTopology component renders: [Sources] → [Pipeline] → [Targets]
```

#### DAG Topology

```
Airflow GET /dags/{id}/tasks → task definitions with downstream_task_ids
    ↓ (AirflowSyncService)
dag_tasks table: {dag_id, task_id, downstream_task_ids, needs, prefers}
    ↓ (GET /api/pipelines/{id}/topology)
TopologyGraph: upstream_needs + upstream_prefers + downstream tasks
    ↓ (useTopology hook)
LineageTopology component: orange (needs) → indigo (current) → white (downstream)
    with status dots and DAG filter buttons
```

#### Resource & Performance

```
Airflow op_kwargs.resources = {"default": {...}, "dag_override": {...}}
    ↓ (AirflowSyncService)
pipeline_resource_configs table: Spark memory/cores/executors per DAG

Airflow task logs: "ETL_RESOURCE_ACTUAL: {driver_memory_used_mb: 1200, ...}"
    ↓ (AirflowService.poll_all_statuses)
pipeline_run_history table: duration + actual usage per run

    ↓ (GET /api/pipelines/{id}/resources)
ResourceMetricsResponse: {
  duration_stats (avg/min/max),
  run_history (last 20 runs),
  configs (allocated resources),
  actual_usage (avg actual),
  capacity_bars (allocated vs used vs cluster max)
}
    ↓ (useResourceMetrics hook)
ResourcePerformanceCard: sparkline + resource grid + capacity bars
```

#### Downstream Consumers (Usage)

```
dag_tasks.downstream_task_ids → who depends on this ETL
    +
pipeline_usages table → enrichment (descriptions, access counts)
    ↓ (GET /api/usage/{etl_name})
Response: current pipeline (is_current=true) + downstream consumers
    ↓ (usePipelineUsage hook)
UsageCard: current pipeline highlighted, then consumers with counts
```

#### Schema Matrix

```
pipeline_fields (from Iceberg catalog sync)
    ↓ (FieldFrequencyRepository)
SQL: SELECT field_name, COUNT(*) FROM pipeline_fields GROUP BY ... HAVING COUNT >= 2
    ↓ (GET /api/schema-matrix)
Fields that appear in 2+ pipelines, sorted by frequency
    ↓ (useSchemaMatrix hook)
SchemaMatrixView: field name + frequency bar + pipeline badges
```

#### AI Architect Terminal

```
User types message
    ↓ (useAIChat mutation)
POST /api/ai/chat {message, history}
    ↓ (AIService)
Builds system prompt with catalog context (20 pipelines + descriptions)
    ↓
POST to external LLM endpoint (OpenAPI-compatible /chat/completions)
    ↓
Response streamed back → ai-store.addMessage → ChatMessage renders
```

---

### 5. Docker: How It All Connects

**Dev mode** (`docker compose watch`):

```
db (PostgreSQL) ← backend depends on (healthy)
iceberg-rest ← iceberg-seed depends on → backend depends on (completed)
airflow-db ← airflow-init ← airflow-webserver + airflow-scheduler
backend ← frontend depends on
```

- Backend auto-runs `alembic upgrade head` (migrations) then starts uvicorn
- Airflow loads DAGs from `dev/dags/` (mounted volume)
- `iceberg-seed` creates table schemas via REST API
- `etl_runner.py` simulates realistic ETL execution (sleep, log writes, resource reporting)
- Frontend Vite dev server proxies `/api` to backend

**Prod mode** (`docker-compose.prod.yml`): Just db + backend + frontend (nginx). Airflow and Iceberg are external services configured via `.env.prod`.

---

### 6. The Dev Simulation

The `dev/` directory creates a realistic mock environment:

- **6 DAGs** with 30 ETLs in a computer networking theme
- **`etl_runner.py`** — the Airflow task callable that simulates ETL runs:
  - Reads the ETL's Python file, extracts docstring + SUFFIXES
  - Logs `ETL_DESCRIPTION:` and `ETL_WRITES_TO:` markers
  - Sleeps proportionally to resource weight (simulates work)
  - Logs `ETL_RESOURCE_ACTUAL:` with randomized but realistic memory/CPU numbers
  - Supports `simulate_failure` (always fails) and `simulate_flaky` (40% fail rate)
- **`seed_iceberg.py`** — seeds 30 Iceberg table schemas with realistic fields
- **Resource files** — per-ETL Spark configs with DAG-specific overrides

This means when you `docker compose up`, you get a fully functional system with real Airflow runs, realistic failures, and populated data — no external infrastructure needed.

---

**The key insight:** Airflow is the single source of truth — pipelines, lineage, topology, resources, and status all flow from Airflow's API and task logs. Iceberg adds schema detail. The LLM is optional for AI features. The backend normalizes everything into PostgreSQL, and the frontend renders it through TanStack Query hooks into a dark-themed bento-box UI.

## License

MIT
