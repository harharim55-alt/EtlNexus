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

ETL Nexus transforms a static data dictionary into an interactive, engineering-grade workspace. It automatically discovers pipelines from your Git repository and Iceberg catalog, monitors their health via Airflow, and presents everything through a dark-themed bento-box UI.

**Instead of digging through code, Slack threads, and wikis to find data** — open ETL Nexus and get instant answers: what data exists, where it flows, how fresh it is, and how to consume it.

### The Workspace

```
 +--[ Pipeline Registry ]--+--[ Bento Workspace ]-----------------------------+
 |                         |                                                   |
 |  Q Search pipelines...  |  [Analytics]  [Airflow: Success]                  |
 |                         |  Mixpanel User Events                             |
 |  > Mixpanel User Events |                                                   |
 |    Analytics             |  +--[ Topology ]--------+  +--[ Metrics ]-----+  |
 |    Every 4 Hours         |  | core_backend  -----> |  | Volume: 1.2M/day |  |
 |                         |  | raw_telemetry -----> |  | Schedule: 4h     |  |
 |    Shopify Sales Sync   |  |    --> dim_sessions   |  +------------------+  |
 |    E-commerce            |  |    --> fact_events    |                        |
 |    Daily at 00:00 UTC    |  +----------------------+  +--[ Schema ]------+  |
 |                         |                              | event_id STRING |  |
 |    Stripe Billing Agg.  |  +--[ Join Intelligence ]--+ | user_id  STRING |  |
 |    Finance               |  | Stripe Billing Agg.    | | event_time TS   |  |
 |    Hourly                |  |  ON: created_at, ...   | +------------------+  |
 |                         |  +-------------------------+                      |
 +-------------------------+  +--[ Consume ]---+ +--[ DAG Networks ]--------+  |
                              | from etls ...  | | analytics_pipeline       |  |
                              | Catalog(...)   | | product_insights         |  |
                              +----------------+ +--------------------------+  |
                              +------------------------------------------------+
```

## Features

### Pipeline Discovery & Search
- **Auto-discovery** from Git repositories via AST parsing of Python ETL code
- **Schema discovery** from Iceberg catalog via PySpark `spark.table().schema`
- **Deep search** across pipeline names, descriptions, and field names — find which ETLs contain `user_id`

### Visual Pipeline Workspace
- **Lineage topology** — source tables, pipeline, destination tables in a single view
- **Schema structure** — every field with its Iceberg data type (BIGINT, STRING, TIMESTAMP_NTZ, etc.)
- **Volume & schedule metrics** — rows/day and cron schedule at a glance
- **Consume snippets** — copy-paste Python code for both ETL import and Catalog import patterns:
  ```python
  # ETL Import
  from etls import shopify_sales_sync
  shopify_sales_sync("2026-01-25").consume()

  # Catalog Import
  from etls import Catalog, Engine
  Catalog(Engine.Spark).iceberg.dagger.shopify_sales_sync("date").consume().as_pyspark()
  ```

### Join Intelligence
- **Schema matches** — automated cross-catalog field overlap detection (e.g., "Join with Stripe Billing ON: `created_at`, `currency`, `customer_id`")
- **AI insights** — LLM-powered semantic join recommendations with business context

### DAG Network Mapping
- See which Airflow networks each pipeline is scheduled on
- Parsed directly from ETL code `self.networks` declarations

### Live Airflow Monitoring
- Real-time DAG run status polling (configurable interval, default 20 min)
- Green/red status indicators on every pipeline in the registry
- Graceful degradation when Airflow is unreachable

### Global Schema Matrix
- Cross-pipeline field frequency analysis
- Spot the most common join keys (`customer_id`, `email`, `created_at`) across your entire catalog

### AI Architect Terminal
- Natural language queries against your full ETL catalog
- Ask business questions: *"How do I calculate Customer LTV from support tickets?"*
- Pluggable — works with any OpenAPI-compatible LLM endpoint

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, async SQLAlchemy, asyncpg, Alembic, APScheduler |
| **Frontend** | React 19, TypeScript, Vite, TanStack Query, Zustand, shadcn/ui, Tailwind CSS v4 |
| **Catalog** | PySpark 3.5.1, Apache Iceberg (REST catalog), `spark.table().schema` |
| **Integrations** | Airflow REST API, Git (HTTPS clone/pull), OpenAPI-compatible LLM |
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

# Start everything (backend, frontend, db, airflow, iceberg catalog, git seed)
docker compose up
```

That's it. The dev environment includes:
- **Backend** at [localhost:8000](http://localhost:8000/api/health)
- **Frontend** at [localhost:5173](http://localhost:5173)
- **Airflow UI** at [localhost:8080](http://localhost:8080) (admin/admin)
- **Iceberg REST catalog** at localhost:8181
- **PostgreSQL** at localhost:5432
- 6 pre-seeded ETL pipelines with lineage, schemas, and Airflow DAGs

### File Watching (auto-reload on save)

```bash
docker compose watch
```

Backend files sync automatically (uvicorn reloads), frontend files trigger Vite HMR.

### Run in Production

```bash
# Configure external integrations
cp .env.example .env.prod
# Edit .env.prod with real Airflow URL, Git repo, Iceberg catalog, LLM endpoint...

docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Production runs only `backend`, `frontend` (nginx), and `db` — all integrations point to external services via environment variables.

## Configuration

All settings via environment variables (see `.env.example`):

| Variable | Description | Dev Default |
|----------|-------------|-------------|
| `AIRFLOW_BASE_URL` | Airflow REST API | `http://airflow-webserver:8080/api/v1` |
| `GIT_REPO_URL` | ETL code repository (HTTPS or local path) | `/data/dev-repo` |
| `GIT_HTTPS_TOKEN` | GitHub PAT for private repos | _(empty)_ |
| `ICEBERG_CATALOG_URI` | Iceberg REST catalog endpoint | `http://iceberg-rest:8181` |
| `ICEBERG_NAMESPACE_PREFIX` | Namespace to scan for tables | `dagger` |
| `LLM_API_BASE_URL` | OpenAPI-compatible LLM endpoint | _(empty)_ |
| `LLM_API_KEY` | LLM API key | _(empty)_ |

## Architecture

```
Browser (React SPA)  <-- REST -->  FastAPI Backend  <-- SQL -->  PostgreSQL
                                        |
                                 +------+------+--------+
                                 |      |      |        |
                              Airflow  Git   Iceberg   LLM
                               API    Repo   Catalog  Endpoint
```

### Backend — Three-Layer Pattern

```
Router (HTTP) --> Service (business logic) --> Repository (data access)
                       |
                  Integrations (Airflow, Git, Iceberg, LLM)
```

- `app/routers/` — FastAPI endpoints under `/api/`
- `app/services/` — orchestrates repositories and integration clients
- `app/repositories/` — async SQLAlchemy queries
- `app/integrations/` — external system clients
- `app/parsers/` — AST-based ETL code parser, Iceberg catalog navigator
- `app/tasks/` — APScheduler background jobs (git pull 60min, airflow poll 20min, catalog sync 2h)

### Frontend — State Separation

- **TanStack Query** — all server state (pipelines, lineage, airflow statuses)
- **Zustand** — client-only UI state (active tab, selected pipeline, chat history)
- Components organized by feature: `layout/`, `pipeline-registry/`, `bento-workspace/`, `schema-matrix/`, `ai-terminal/`, `shared/`

### Background Tasks

| Task | Interval | What it does |
|------|----------|-------------|
| Git Sync | 60 min | Clone/pull repo, AST-parse ETL files, upsert pipelines + lineage + networks |
| Airflow Poll | 20 min | Fetch latest DAG run statuses for all matched pipelines |
| Catalog Sync | 2 hours | Read table schemas from Iceberg via PySpark, sync fields to DB |

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
      models/                   # SQLAlchemy ORM (Pipeline, PipelineField, LineageEdge, ...)
      schemas/                  # Pydantic DTOs
      routers/                  # API endpoints
      services/                 # Business logic
      repositories/             # Database queries
      integrations/             # Airflow, Git, Iceberg (PySpark), LLM clients
      parsers/                  # AST-based ETL code parser
      tasks/                    # APScheduler background jobs
    alembic/                    # Database migrations

  frontend/
    src/
      components/               # React components by feature
      hooks/                    # TanStack Query hooks
      stores/                   # Zustand state stores
      api/                      # Axios API client layer
      types/                    # TypeScript interfaces

  dev/
    dags/                       # Sample Airflow DAGs (dev only)
    seeds/                      # ETL code seeds + Iceberg catalog seeder
```

## License

MIT
