# EtlNexus — Production Integration Guide

How to deploy EtlNexus against your existing Airflow, Iceberg catalog, and Spark cluster.

---

## Table of Contents

0. [Quickstart with etlnexus-hooks](#0-quickstart-with-etlnexus-hooks)
1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Deployment](#3-deployment)
4. [Airflow Integration](#4-airflow-integration)
5. [Iceberg Catalog Integration](#5-iceberg-catalog-integration)
6. [LLM / AI Architect Integration](#6-llm--ai-architect-integration)
7. [Spark Cluster Capacity Settings](#7-spark-cluster-capacity-settings)
8. [Environment Reference](#8-environment-reference)
9. [Startup Behavior](#9-startup-behavior)
10. [Networking & Reverse Proxy](#10-networking--reverse-proxy)
11. [Troubleshooting](#11-troubleshooting)

---

## 0. Quickstart with etlnexus-hooks

If all your ETLs inherit from a shared `BaseETL` class with `extract() → transform() → load() → run()`, you can auto-instrument them with **one line of code**.

### Step 1: Install the hooks package in your Airflow environment

```bash
pip install etlnexus-hooks
```

### Step 2: Add the mixin to your BaseETL

```python
from etlnexus_hooks import EtlNexusMixin

class BaseETL(EtlNexusMixin):   # ← add the mixin
    def __init__(self, start_date, end_date=None, schedule="daily"):
        ...  # unchanged

    def extract(self): raise NotImplementedError
    def transform(self): raise NotImplementedError
    def load(self): raise NotImplementedError

    def run(self):
        self.extract()
        self.transform()
        self.load()
```

That's it. The mixin wraps `run()` and automatically emits all four log markers to stdout (captured by Airflow in task logs).

### What the mixin automates

| Marker | How it's captured | Manual alternative |
|--------|-------------------|--------------------|
| `ETL_DESCRIPTION:` | Relative file path of the ETL class (e.g., `dagger/PortScanCollector.py`) | `print(f"ETL_DESCRIPTION: ...")` |
| `ETL_WRITES_TO:` | Intercepts `DataFrame.writeTo()` during `load()` + reads module-level `SUFFIXES` | `print(f"ETL_WRITES_TO: ...")` per table |
| `ETL_RESOURCE_ACTUAL:` | Reads Spark StatusStore metrics after `run()` | `print(f"ETL_RESOURCE_ACTUAL: {json.dumps(...)}")` |
| `ETL_EXECUTION_PLAN:` | Extracts plan tree from Spark's plan graph | `print(f"ETL_EXECUTION_PLAN: {json.dumps(...)}")` |

### What you still need in DAG definitions

The mixin automates **output markers**, but **lineage input declarations** still require `params` in your Airflow DAG tasks — the mixin cannot distinguish hard dependencies (`needs`) from soft dependencies (`prefers`) by intercepting Spark reads.

```python
PythonOperator(
    task_id="MyETL",
    python_callable=run_etl,
    params={
        "needs": ["UpstreamETL"],     # Required — reads_from lineage edges
        "prefers": ["OptionalETL"],   # Required — soft dependency edges
    },
    op_kwargs={
        "etl_name": "MyETL",          # Required — pipeline identifier
        "resources": {...},            # Optional — Spark resource config
    },
)
```

### Integration tiers

| Tier | What you change | What EtlNexus discovers |
|------|-----------------|------------------------|
| **Hooks only** (recommended) | Add mixin to BaseETL | Descriptions, write targets, resource metrics, execution plans — all automatic |
| **Hooks + DAG params** | Add mixin + `params.needs`/`prefers` on tasks | Everything above + full lineage graph |
| **Hooks + DAG params + TaskGroups** | Add mixin + params + `TaskGroup("Team-Category")` | Everything above + team/category assignment |
| **Hooks + DAG params + DAG tags** | Add mixin + params + `tags=[{"name": "team:Dagger"}]` | Everything above + team from tags (alternative to TaskGroups) |

### DAG tag team discovery (alternative to TaskGroups)

Instead of wrapping tasks in `TaskGroup("Team-Category")`, you can set team via DAG-level tags:

```python
with DAG(
    dag_id="my_dag",
    tags=[{"name": "team:Dagger"}, {"name": "category:Collection"}],
    ...
):
```

EtlNexus reads these tags as a fallback when no TaskGroup team is found.

### DAG graph lineage inference (opt-in)

If you cannot add `params.needs`/`prefers` to your DAG tasks, enable automatic lineage inference from the DAG task dependency graph:

```bash
INFER_LINEAGE_FROM_DAG_GRAPH=true
```

When enabled, if a task has no explicit `needs`, EtlNexus will create `reads_from` edges based on Airflow task upstream/downstream relationships. This is less precise (cannot distinguish needs vs prefers) but requires zero DAG changes.

---

## 1. Architecture Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│   Frontend   │────▶│   Backend    │────▶│  Your Airflow        │
│  (nginx:80)  │     │ (FastAPI:8000│     │  (REST API v1)       │
│              │     │  + PySpark)  │     └──────────────────────┘
└──────────────┘     │              │     ┌──────────────────────┐
                     │              │────▶│  Your Iceberg Catalog│
                     │              │     │  (REST catalog)      │
                     │              │     └──────────────────────┘
                     │              │     ┌──────────────────────┐
                     │              │────▶│  LLM Endpoint        │
                     │              │     │  (OpenAPI-compatible) │
                     └──────┬───────┘     └──────────────────────┘
                            │
                     ┌──────▼───────┐
                     │  PostgreSQL  │
                     │  (EtlNexus   │
                     │   metadata)  │
                     └──────────────┘
```

**EtlNexus deploys 3 containers.** Everything else (Airflow, Iceberg, Spark, LLM) is external — you point to them via environment variables.

**What EtlNexus does NOT do:**
- Does not modify your Airflow DAGs or configuration
- Does not write to your Iceberg catalog (read-only)
- Does not submit Spark jobs to your cluster (runs a local micro-Spark only for schema reads)

---

## 2. Prerequisites

| Component | Requirement |
|-----------|-------------|
| **Airflow** | v2.x with REST API enabled and basic auth |
| **Iceberg** | REST catalog endpoint (e.g., Tabular, AWS Glue REST, Nessie) |
| **PostgreSQL** | 16+ (included in docker-compose, or use external) |
| **Docker** | Docker Engine 24+ with Compose v2 |
| **Network** | Backend must reach Airflow API and Iceberg REST catalog |

---

## 3. Deployment

### 3.1 Clone and configure

```bash
git clone <repo-url> && cd EtlNexus
cp .env.example .env.prod
```

Edit `.env.prod` — see [Section 8](#8-environment-reference) for all variables.

### 3.2 Launch

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

This starts:
- **db** — PostgreSQL 16 (EtlNexus metadata only)
- **backend** — FastAPI + auto-runs DB migrations on startup
- **frontend** — nginx serving React SPA, proxies `/api/` to backend

### 3.3 Verify

```bash
# Backend health
curl http://localhost:8000/api/health

# Check logs for initial Airflow sync
docker compose -f docker-compose.prod.yml logs backend | grep "sync"
```

---

## 4. Airflow Integration

EtlNexus reads from Airflow's REST API. It **never writes** to Airflow.

### 4.1 Airflow API requirements

| Requirement | Details |
|-------------|---------|
| **API version** | Airflow REST API v1 (`/api/v1/`) |
| **Auth** | Basic authentication (username + password) |
| **Endpoints used** | `GET /dags`, `GET /dags/{id}/tasks`, `GET /dags/{id}/dagRuns`, `GET /dags/{id}/dagRuns/{id}/taskInstances`, `GET .../taskInstances/{id}/logs/{try}` |
| **RBAC permissions** | Read access to: DAGs, DAG Runs, Task Instances, Task Logs |

### 4.2 Enable the Airflow REST API

In your `airflow.cfg` (or env vars):

```ini
[api]
auth_backends = airflow.providers.fab.auth_manager.api.auth.backend.basic_auth

[webserver]
expose_config = False
```

Or via environment variable:
```bash
AIRFLOW__API__AUTH_BACKENDS=airflow.providers.fab.auth_manager.api.auth.backend.basic_auth
```

Create a service account user for EtlNexus:
```bash
airflow users create \
  --username etlnexus-reader \
  --firstname EtlNexus \
  --lastname Service \
  --role Viewer \
  --email etlnexus@internal \
  --password <strong-password>
```

> The **Viewer** role provides read-only access to DAGs, runs, task instances, and logs.

### 4.3 Environment variables

```bash
AIRFLOW_BASE_URL=https://airflow.company.com/api/v1
AIRFLOW_USERNAME=etlnexus-reader
AIRFLOW_PASSWORD=<strong-password>
AIRFLOW_POLL_INTERVAL_MINUTES=20
```

### 4.4 What EtlNexus reads from Airflow

EtlNexus discovers pipelines by reading **task metadata** from your DAGs. Specifically:

1. **DAG list** — discovers all DAGs
2. **Task definitions** — reads `downstream_task_ids` for consumer/lineage graphs
3. **Task instances** — reads `rendered_fields.op_kwargs` for pipeline metadata
4. **Task logs** — parses structured log lines for descriptions, write targets, and resource usage

### 4.5 Adapting your DAGs (the critical part)

EtlNexus reads metadata from three places on each task: **`params`** (lineage dependencies), **`op_kwargs`** (identity and resource config), and **TaskGroup names** (team and category). This is the only change required in your Airflow setup.

#### Complete task definition

```python
from airflow.utils.task_group import TaskGroup

with TaskGroup("MyTeam-Collection", prefix_group_id=True) as collection:
    PythonOperator(
        task_id="SwitchPortCollector",              # PascalCase — becomes the pipeline identifier
        python_callable=run_etl,
        params={
            "needs": ["UpstreamETL1", "UpstreamETL2"],  # Hard dependencies → reads_from lineage edges
            "prefers": [],                               # Soft dependencies (can be empty)
        },
        op_kwargs={
            "etl_name": "SwitchPortCollector",           # Must match task_id exactly
            "resources": {
                "default": {                             # Baseline config (required key)
                    "spark_driver_memory": "2g",
                    "spark_executor_memory": "8g",
                    "spark_executor_cores": 4,
                    "spark_num_executors": 2,
                },
                "production_dag": {                      # Optional per-DAG override (key = dag_id)
                    "spark_executor_memory": "16g",
                    "spark_num_executors": 4,
                },
            },
        },
    )
```

#### Where each field comes from

| Field | Location | Type | Required | Purpose |
|-------|----------|------|----------|---------|
| `task_id` | PythonOperator arg | `str` | Yes | Pipeline identifier. Must be **PascalCase**. Auto-converted to display name: `SwitchPortCollector` → `"Switch Port Collector"` |
| `etl_name` | `op_kwargs` | `str` | Yes | Must match `task_id` exactly |
| `needs` | `params` | `list[str]` | Yes | Upstream canonical task_ids. Creates `reads_from` lineage edges |
| `prefers` | `params` | `list[str]` | Yes | Soft/optional dependencies. Can be `[]` |
| `resources` | `op_kwargs` | `dict` | No | Spark resource allocation (see below) |
| **Team** | TaskGroup name | — | Recommended | Extracted from TaskGroup name prefix before `-` |
| **Category** | TaskGroup name | — | Recommended | Extracted from TaskGroup name suffix after `-` |
| **Schedule** | DAG definition | — | Automatic | Read from DAG's `timetable_description` or `schedule_interval` |

> **Note on `params`:** Airflow internally wraps params as `{"__class": "airflow.models.param.Param", "value": [...]}`. EtlNexus unwraps this automatically — just set plain lists in your DAG definition.

#### TaskGroup naming convention (team & category)

EtlNexus extracts **team** and **category** from the TaskGroup name by splitting on the first `-`:

```python
with TaskGroup("Dagger-Collection", prefix_group_id=True):   # team=Dagger, category=Collection
with TaskGroup("Vault-Enrichment", prefix_group_id=True):    # team=Vault,  category=Enrichment
with TaskGroup("Prism-Analytics", prefix_group_id=True):     # team=Prism,  category=Analytics
```

| TaskGroup name | Team | Category |
|----------------|------|----------|
| `"Dagger-Collection"` | Dagger | Collection |
| `"Vault-Enrichment"` | Vault | Enrichment |
| `"MyTeam"` (no dash) | MyTeam | MyTeam |
| _(no TaskGroup)_ | _(null)_ | Uncategorized |

**Important:** Always use `prefix_group_id=True` — the sync service strips the group prefix from task IDs using the last `.` separator (e.g., `Dagger-Collection.SwitchPortCollector` → `SwitchPortCollector`).

#### Resource config structure

The `"default"` key provides baseline Spark config. Optional DAG-specific keys (matching `dag_id`) override individual values on top:

```python
"resources": {
    "default": {                          # Required baseline
        "spark_driver_memory": "2g",      # e.g., "512m", "4g"
        "spark_executor_memory": "8g",
        "spark_executor_cores": 4,        # Integer
        "spark_num_executors": 2,         # Integer
    },
    "my_prod_dag": {                      # Optional — overrides for dag_id="my_prod_dag"
        "spark_executor_memory": "16g",
        "spark_num_executors": 8,
    },
}
# Effective config for my_prod_dag: driver=2g, exec_mem=16g, cores=4, executors=8
```

Stored in `pipeline_resource_configs` (one row per pipeline per DAG).

#### Special task types (detected by task_id substring)

| Task ID contains | Classification | Behavior |
|------------------|---------------|----------|
| `"Bouncer"` | Data ingestion root | No lineage edges. Uses `BOUNCER_DESCRIPTION:` log marker. Stored in `bouncers` table |
| `"Api"` or `"API"` | API consumer leaf | No `writes_to` edges (read-only endpoint) |
| Neither | Standard ETL | Full lineage + resource tracking + metrics |

### 4.6 Structured log markers (ETL code changes)

> **If using `etlnexus-hooks`:** All markers below are emitted automatically by the `EtlNexusMixin`. See [Section 0](#0-quickstart-with-etlnexus-hooks) for setup. You can skip this section entirely.

Your ETL code must emit structured `print()` lines that EtlNexus parses from Airflow task logs. Add these to your ETL runner/wrapper function (the `python_callable`):

```python
import json

def run_etl(etl_name, **kwargs):
    # ── Required: destination tables (one line per output table) ──
    print(f"ETL_WRITES_TO: {etl_name}")
    print(f"ETL_WRITES_TO: {etl_name}_daily")       # if ETL writes variant tables

    # ── Recommended: pipeline description ──
    print(f"ETL_DESCRIPTION: Aggregates daily sales metrics from all regional sources")

    # ── Recommended: actual Spark resource usage (JSON) ──
    actuals = {
        "driver_memory_used_mb": 512,
        "executor_memory_peak_mb": 4096,
        "cpu_utilization_pct": 72.5,
        "executors_active": 4,
        # Optional sparkMeasure fields:
        "spark_application_id": "app-20260323-001",
        "executor_run_time_ms": 180000,
        "executor_cpu_time_ms": 120000,
        "jvm_gc_time_ms": 5000,
        "shuffle_read_bytes": 1073741824,
        "shuffle_write_bytes": 536870912,
        "input_bytes": 2147483648,
        "output_bytes": 1073741824,
        "memory_bytes_spilled": 0,
        "disk_bytes_spilled": 0,
        "peak_execution_memory": 3221225472,
        "result_size_bytes": 1048576,
        "num_tasks": 200,
        "num_stages": 5,
    }
    print(f"ETL_RESOURCE_ACTUAL: {json.dumps(actuals)}")

    # ── Optional: Spark execution plan tree (JSON) ──
    plan = {
        "id": 1, "name": "Project", "type": "transform",
        "detail": "Project [col1, col2]",
        "full_detail": "Detailed explanation for modal view",
        "metrics": {"rows_output": "1.2M", "bytes_output": "512 MB"},
        "children": [
            {"id": 2, "name": "Filter", "type": "transform", "detail": "...", "children": []}
        ]
    }
    print(f"ETL_EXECUTION_PLAN: {json.dumps(plan)}")

    # ... your actual ETL logic ...
```

#### All supported log markers

| Log marker | Format | Required? | What it populates |
|------------|--------|-----------|-------------------|
| `ETL_WRITES_TO: <table>` | One line per output table (repeatable) | **Yes** | Lineage `writes_to` edges |
| `ETL_DESCRIPTION: <text>` | Single line of text | Recommended | Pipeline description in UI |
| `ETL_RESOURCE_ACTUAL: <json>` | Single JSON dict (see fields above) | Recommended | Resource performance metrics + charts |
| `ETL_EXECUTION_PLAN: <json>` | JSON tree with `id`, `name`, `type`, `detail`, `children` | Optional | Execution plan visualization in UI |
| `BOUNCER_DESCRIPTION: <text>` | Single line of text | Only for Bouncer tasks | Bouncer description |

**Parsing rules:**
- Markers are **case-sensitive** (must be exact: `ETL_WRITES_TO:`, not `etl_writes_to:`)
- For single-value markers (`ETL_DESCRIPTION`, `ETL_RESOURCE_ACTUAL`, `ETL_EXECUTION_PLAN`), only the **first occurrence** is used
- For `ETL_WRITES_TO`, **all occurrences** are collected into a list
- The parser splits on the marker string and trims whitespace from the value

#### If no log markers are found

| Missing marker | Fallback behavior |
|----------------|-------------------|
| No `ETL_WRITES_TO:` | Defaults to `[task_id]` as the single output table |
| No `ETL_DESCRIPTION:` | Description left empty (can be edited manually in UI) |
| No `ETL_RESOURCE_ACTUAL:` | Resource metrics columns null — performance charts empty |
| No `ETL_EXECUTION_PLAN:` | Execution plan tree not shown in UI |

#### Where to add these markers

**Option A: Centralized wrapper (recommended)** — Add to your shared `run_etl()` function that all tasks call as `python_callable`. This way every ETL automatically emits markers without per-task changes.

**Option B: Per-ETL** — Add print statements inside each ETL's execution path or post-execution hook.

### 4.7 What EtlNexus does with this data

| Source | Location | EtlNexus uses for |
|--------|----------|-------------------|
| `etl_name` | `op_kwargs` | Pipeline identity (must match task_id) |
| `needs` | `params` | Lineage graph (`reads_from` edges) |
| `prefers` | `params` | Soft dependency edges + join intelligence |
| `resources` | `op_kwargs` | Resource allocation tracking |
| TaskGroup name | DAG source | Team assignment + category grouping |
| `timetable_description` / `schedule_interval` | DAG definition | Schedule display in pipeline detail |
| `downstream_task_ids` | Airflow task definition | Consumer/downstream discovery |
| Task instance `state` | Airflow API | Pipeline health status (success/failed/running) |
| Task instance `duration`, `start_date`, `end_date` | Airflow API | Run history and performance charts |
| `ETL_WRITES_TO` log lines | Task logs | Destination table lineage (`writes_to` edges) |
| `ETL_DESCRIPTION` log line | Task logs | Pipeline description |
| `ETL_RESOURCE_ACTUAL` log line | Task logs | Actual resource usage metrics + charts |
| `ETL_EXECUTION_PLAN` log line | Task logs | Execution plan tree visualization |

### 4.8 Sync schedule

| Event | When | What happens |
|-------|------|--------------|
| **Startup** | Backend boot | Full sync: discovers all pipelines, lineage, statuses |
| **Catch-up** | 5 min after boot | Re-sync (handles case where Airflow wasn't ready at boot) |
| **Recurring sync** | Every 20 min | Discovers new/updated pipelines and lineage |
| **Recurring poll** | Every 20 min | Updates run statuses and run history (last 5 runs per DAG) |

Interval is configurable via `AIRFLOW_POLL_INTERVAL_MINUTES`.

### 4.9 Minimal adoption path

If you want to onboard gradually:

1. **Start with one DAG** — add `params` and `op_kwargs` to tasks in a single DAG
2. **Minimum required:** `op_kwargs.etl_name` + `params.needs` (even if empty list) + `params.prefers` (even if empty list)
3. Wrap tasks in a **TaskGroup** with `"Team-Category"` naming for automatic team/category assignment
4. Add `ETL_WRITES_TO:` print statements to your ETL runner for lineage — skip `resources` and other markers initially
5. Tasks without `etl_name` in their op_kwargs are silently ignored
6. DAGs with no discoverable tasks are skipped entirely

### 4.10 What happens if you skip something

| Missing item | Consequence |
|---|---|
| No `params.needs` | No `reads_from` lineage edges — pipeline appears as isolated node |
| No `op_kwargs.resources` | No resource config stored — resource performance panel empty |
| No `ETL_WRITES_TO:` markers | Defaults to `[task_id]` as single output — usually fine for simple ETLs |
| No `ETL_RESOURCE_ACTUAL:` | Resource metrics null — performance charts empty |
| No `ETL_EXECUTION_PLAN:` | Execution plan tree not shown |
| No `ETL_DESCRIPTION:` | Description empty — can be edited manually in UI |
| No TaskGroup | Team = null, Category = "Uncategorized" |
| Task not a PythonOperator | May be excluded by `AIRFLOW_EXCLUDE_OPERATOR_TYPES` config |

---

## 5. Iceberg Catalog Integration

EtlNexus reads table schemas from your Iceberg REST catalog to populate the Schema Viewer and Global Schema Matrix. **Read-only access.**

### 5.1 Requirements

| Requirement | Details |
|-------------|---------|
| **Catalog type** | REST catalog (Iceberg REST spec) |
| **Endpoint** | HTTP(S) endpoint serving `/v1/namespaces`, `/v1/namespaces/{ns}/tables` |
| **Compatible** | Tabular, AWS Glue REST adapter, Nessie, Apache Polaris, Gravitino |
| **Network** | Backend container must reach the catalog URL |

### 5.2 Environment variables

```bash
ICEBERG_CATALOG_URI=https://iceberg-catalog.company.com
ICEBERG_NAMESPACE_PREFIX=dagger
```

### 5.3 Namespace convention

EtlNexus looks for tables under a single namespace defined by `ICEBERG_NAMESPACE_PREFIX` (default: `dagger`).

```
your_iceberg_catalog
└── dagger                    ← ICEBERG_NAMESPACE_PREFIX
    ├── your_etl_table_1      ← table name should match task_id / etl_name
    ├── your_etl_table_2
    └── ...
```

**Table name matching:** EtlNexus matches Iceberg table names to pipelines by comparing the table name against the pipeline's `task_id` (or name). The match is case-insensitive with underscores normalized.

### 5.4 What EtlNexus reads

- **Namespaces** — lists namespaces to find `ICEBERG_NAMESPACE_PREFIX`
- **Tables** — lists tables within the namespace
- **Schemas** — reads column names and types from each table's schema

This data populates:
- **Schema Viewer** in the pipeline detail (bento workspace)
- **Global Schema Matrix** — cross-pipeline field frequency analysis

### 5.5 How it connects

EtlNexus uses PySpark internally (local mode, 1 core, 512MB) to query the Iceberg REST catalog. The backend Docker image includes Java (OpenJDK 17) for this purpose.

> The PySpark session is **not** connected to your Spark cluster. It runs locally inside the backend container solely for catalog metadata reads.

### 5.6 Sync schedule

| Event | When |
|-------|------|
| **Startup** | Full catalog scan |
| **Recurring** | Every 2 hours (first run 1 hour after boot) |

### 5.7 No Iceberg catalog?

If you don't have an Iceberg catalog, set `ICEBERG_CATALOG_URI` to an empty string or an unreachable URL. EtlNexus will log a warning and continue without schema data. The Schema Viewer will show empty, but all other features (lineage, status, consumers, resources) work normally.

---

## 6. LLM / AI Architect Integration

The AI Architect terminal connects to any OpenAPI-compatible LLM endpoint.

### 6.1 Environment variables

```bash
LLM_API_BASE_URL=https://api.openai.com/v1       # Or your internal LLM endpoint
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4                                   # Model identifier
LLM_MAX_TOKENS=1024                                # Max response tokens
```

### 6.2 Compatible endpoints

Any endpoint that accepts OpenAI-style chat completions:
- OpenAI API
- Azure OpenAI
- Anthropic (via OpenAI-compatible proxy)
- vLLM, Ollama, LiteLLM, or any OpenAPI-compatible server

### 6.3 No LLM?

Leave `LLM_API_BASE_URL` empty. The AI Architect terminal will be non-functional, but everything else works.

---

## 7. Spark Cluster Capacity Settings

These values define your Spark cluster's **maximum capacity** for the resource utilization gauge in the UI. They don't connect to your cluster — they're reference values for percentage calculations.

```bash
SPARK_MAX_DRIVER_MEMORY_GB=16       # Max driver memory across cluster
SPARK_MAX_EXECUTOR_MEMORY_GB=64     # Max executor memory across cluster
SPARK_MAX_EXECUTOR_CORES=32         # Max executor cores across cluster
SPARK_MAX_TOTAL_EXECUTORS=20        # Max concurrent executors
```

Set these to match your actual Spark cluster limits so the Resource Performance card shows accurate utilization percentages.

---

## 8. Environment Reference

Complete `.env.prod` template:

```bash
# ─── Database ───────────────────────────────────────────
# Only POSTGRES_PASSWORD is required. The rest is handled by docker-compose.
POSTGRES_PASSWORD=<strong-random-password>

# ─── Airflow ────────────────────────────────────────────
AIRFLOW_BASE_URL=https://airflow.company.com/api/v1
AIRFLOW_USERNAME=etlnexus-reader
AIRFLOW_PASSWORD=<airflow-service-password>
AIRFLOW_POLL_INTERVAL_MINUTES=20

# ─── Iceberg Catalog ───────────────────────────────────
ICEBERG_CATALOG_URI=https://iceberg-catalog.company.com
ICEBERG_NAMESPACE_PREFIX=dagger

# ─── LLM / AI Architect ────────────────────────────────
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4
LLM_MAX_TOKENS=1024

# ─── Spark Cluster Capacity (for UI gauges) ────────────
SPARK_MAX_DRIVER_MEMORY_GB=16
SPARK_MAX_EXECUTOR_MEMORY_GB=64
SPARK_MAX_EXECUTOR_CORES=32
SPARK_MAX_TOTAL_EXECUTORS=20

# ─── App ────────────────────────────────────────────────
CORS_ORIGINS=["https://etlnexus.company.com"]
DEBUG=false
```

---

## 9. Startup Behavior

When the backend starts, it runs in this order:

1. **Alembic migrations** — auto-applies all DB migrations (`alembic upgrade head`)
2. **Initial Airflow sync** — discovers all pipelines from Airflow (blocking)
3. **Initial Airflow poll** — fetches latest run statuses (blocking)
4. **Initial catalog sync** — reads Iceberg schemas (blocking)
5. **Seed usage data** — populates `pipeline_usages` if table is empty
6. **Start scheduler** — background jobs begin

If Airflow is unreachable at boot, the initial sync logs a warning and continues. A **catch-up sync** runs 5 minutes later automatically.

---

## 10. Networking & Reverse Proxy

### Default topology (docker-compose.prod.yml)

```
Internet → :80 (frontend/nginx) ─┬─→ static files (React SPA)
                                  └─→ /api/* → backend:8000
```

The frontend nginx container proxies `/api/` requests to the backend container internally. No additional reverse proxy is needed for basic setups.

### Behind a corporate reverse proxy

If placing EtlNexus behind an existing reverse proxy (e.g., nginx, Traefik, ALB):

1. Point the proxy to the frontend container port (80)
2. All routing is handled internally — just proxy everything to port 80
3. Update `CORS_ORIGINS` to match your domain:
   ```bash
   CORS_ORIGINS=["https://etlnexus.company.com"]
   ```
4. If terminating TLS at the proxy, no changes needed — the backend reads `X-Forwarded-Proto`

### Firewall rules

The **backend container** needs outbound access to:

| Destination | Port | Purpose |
|-------------|------|---------|
| Airflow REST API | 443/8080 | Pipeline discovery + status polling |
| Iceberg REST catalog | 443/8181 | Schema reads |
| LLM API endpoint | 443 | AI Architect (optional) |

No inbound access needed to the backend from outside — the frontend nginx handles all external traffic.

---

## 11. Troubleshooting

### Pipelines not appearing

1. Check Airflow connectivity: `docker compose exec backend python -c "import httpx; print(httpx.get('$AIRFLOW_BASE_URL/health').status_code)"`
2. Ensure tasks have `op_kwargs` with `etl_name` — tasks without it are skipped
3. Ensure at least one DAG has had a successful run (EtlNexus reads `rendered_fields` from task instances)
4. Check backend logs: `docker compose logs backend | grep -i "airflow\|sync\|error"`

### Schema viewer is empty

1. Verify Iceberg catalog URI is reachable from the backend container
2. Confirm your tables are under the `ICEBERG_NAMESPACE_PREFIX` namespace (default: `dagger`)
3. Table names must loosely match pipeline task_ids
4. Check logs: `docker compose logs backend | grep -i "iceberg\|catalog\|spark"`

### Status shows "unknown" for all pipelines

1. Airflow must have at least one DAG run for each DAG
2. Check that the Airflow user has `Viewer` role (read access to DAG runs and task instances)
3. Wait for the next poll cycle (20 min) or restart the backend to force an immediate sync

### Resource metrics not showing

1. Your ETL code must print `ETL_RESOURCE_ACTUAL: {json}` to stdout/logs
2. The task must have completed successfully (resource actuals are only parsed from successful runs)
3. `resources` must be present in `op_kwargs` (for allocated values)

### Backend won't start (Java/Spark errors)

The backend requires Java 17 for PySpark (Iceberg schema reads). The Docker image includes it. If running locally without Docker, install JDK 17 and set `JAVA_HOME`.

---

## Quick Start Checklist

### Infrastructure
- [ ] Create `.env.prod` with your Airflow URL, credentials, Iceberg URI
- [ ] Create a read-only Airflow user for EtlNexus (Viewer role)
- [ ] Verify Airflow REST API is enabled with basic auth
- [ ] Run `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d`
- [ ] Check `http://<host>/api/health` and review backend logs

### With etlnexus-hooks (recommended)
- [ ] `pip install etlnexus-hooks` in your Airflow environment
- [ ] Add `EtlNexusMixin` to your `BaseETL` class (one line)
- [ ] Add `params.needs` and `params.prefers` to DAG tasks for lineage
- [ ] Add `op_kwargs.etl_name` to DAG tasks (must match task_id)
- [ ] (Optional) Wrap tasks in `TaskGroup("Team-Category")` or add DAG tags `team:TeamName`

### Without etlnexus-hooks (manual markers)

#### Per-DAG changes (Airflow)
- [ ] Wrap tasks in `TaskGroup("Team-Category", prefix_group_id=True)` for team/category
- [ ] Set a schedule on the DAG (`schedule="0 1 * * *"` or similar)

#### Per-task changes (Airflow)
- [ ] Task ID is **PascalCase** and matches `op_kwargs["etl_name"]`
- [ ] `params` dict with `needs` list (upstream task_ids) and `prefers` list (can be `[]`)
- [ ] `op_kwargs` dict with `etl_name` and optionally `resources` (with `"default"` key containing 4 Spark config keys)

#### ETL code changes (your Python ETL runner)
- [ ] Print `ETL_WRITES_TO: <table>` for each output table
- [ ] (Recommended) Print `ETL_DESCRIPTION: <text>` for auto-populated pipeline description
- [ ] (Recommended) Print `ETL_RESOURCE_ACTUAL: <json>` for resource usage tracking
- [ ] (Optional) Print `ETL_EXECUTION_PLAN: <json>` for execution plan visualization

### Optional
- [ ] Ensure your Iceberg tables are under the `dagger` namespace (or change `ICEBERG_NAMESPACE_PREFIX`)
- [ ] Set `SPARK_MAX_*` vars to match your cluster capacity
- [ ] Set `INFER_LINEAGE_FROM_DAG_GRAPH=true` if you can't add `params.needs`/`prefers` to tasks
