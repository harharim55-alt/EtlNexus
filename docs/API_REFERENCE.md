# EtlNexus — API Reference

Complete REST API reference for EtlNexus. All endpoints are served under `/api/` and require authentication unless noted otherwise.

**Base URL:** `http://localhost:8000/api` (development) or `https://your-domain.com/api` (production)

**Authentication:** Bearer JWT token in `Authorization` header. See [Authentication](#authentication) section.

**Content Type:** `application/json` for all request and response bodies.

**Interactive docs:** Swagger UI at `/api/docs`, ReDoc at `/api/redoc`, OpenAPI JSON at `/api/openapi.json`.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Auth Endpoints](#auth-endpoints)
3. [Pipeline Endpoints](#pipeline-endpoints)
4. [Airflow Endpoints](#airflow-endpoints)
5. [Resource & Performance Endpoints](#resource--performance-endpoints)
6. [Topology Endpoints](#topology-endpoints)
7. [Lineage Endpoints](#lineage-endpoints)
8. [Bouncer Endpoints](#bouncer-endpoints)
9. [Consumer Endpoints](#consumer-endpoints)
10. [Usage Endpoints](#usage-endpoints)
11. [DAG Summary Endpoints](#dag-summary-endpoints)
12. [Schema Matrix Endpoints](#schema-matrix-endpoints)
13. [AI Endpoints](#ai-endpoints)
14. [Visibility Grant Endpoints](#visibility-grant-endpoints)
15. [User Management Endpoints](#user-management-endpoints)
16. [Team Endpoints](#team-endpoints)
17. [Metrics Endpoint](#metrics-endpoint)
18. [Health Endpoint](#health-endpoint)
19. [Common Schemas](#common-schemas)
20. [Error Responses](#error-responses)
21. [Rate Limiting](#rate-limiting)

---

## Authentication

All endpoints require a valid Bearer JWT token except:
- `GET /api/auth/config` — OIDC discovery (public)
- `GET /health` — Health check (public)

### Request Header

```
Authorization: Bearer <jwt-token>
```

### Roles

| Role | Description |
|------|-------------|
| `admin` | Full access to all pipelines, users, teams, grants |
| `member` | Team-scoped access, can edit own team's pipelines |
| `viewer` | Team-scoped read-only access |

### Visibility Rules

Non-admin users see pipelines matching any of:
1. Pipeline has no team assigned (`team_id IS NULL`)
2. Pipeline belongs to user's team
3. Pipeline explicitly granted via `visibility_grants` (to user or team)

---

## Auth Endpoints

### `GET /api/auth/config`

OIDC configuration discovery. **No authentication required.**

**Response** `200`

```json
{
  "sso_enabled": true,
  "issuer_url": "https://keycloak.example.com/realms/etlnexus",
  "client_id": "etlnexus-app",
  "audience": "etlnexus-app"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `sso_enabled` | `boolean` | Whether SSO/OIDC is active |
| `issuer_url` | `string` | Public OIDC issuer URL for frontend |
| `client_id` | `string` | OIDC client ID |
| `audience` | `string` | Expected JWT audience |

---

### `GET /api/auth/me`

Returns the authenticated user's profile.

**Response** `200`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "alice@example.com",
  "display_name": "Alice",
  "role": "admin",
  "is_active": true,
  "teams": [
    { "id": "...", "name": "Dagger", "role_in_team": "member" }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `uuid` | User ID |
| `email` | `string` | User email |
| `display_name` | `string` | Display name |
| `role` | `string` | Global role: `admin`, `member`, or `viewer` |
| `is_active` | `boolean` | Account active status |
| `teams` | `TeamMembership[]` | Teams the user belongs to |

---

## Pipeline Endpoints

### `GET /api/pipelines`

List pipelines with search, filtering, and visibility enforcement.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | `string` | — | Search across name, description, and field names |
| `skip` | `integer` | `0` | Pagination offset |
| `limit` | `integer` | `200` | Page size (max 500) |
| `team` | `string[]` | — | Filter by team name(s) (repeatable) |
| `dag_id` | `string[]` | — | Filter by DAG ID(s) (repeatable) |
| `status` | `string[]` | — | Filter by Airflow status(es) (repeatable) |
| `date_from` | `string` | — | ISO date, filter runs after this date |
| `date_to` | `string` | — | ISO date, filter runs before this date |

**Response** `200`

```json
{
  "items": [
    {
      "id": "550e8400-...",
      "name": "SwitchPortCollector",
      "description": "Collects switch port interface data",
      "category": "Collection",
      "pipeline_type": "etl",
      "schedule": "@daily",
      "rows_per_day": "1.2M",
      "airflow_status": "success",
      "success_rate": 95.0,
      "team": "Dagger",
      "last_run_at": "2026-03-27T06:00:00Z",
      "execution_date": "2026-03-27T06:00:00Z"
    }
  ],
  "total": 142
}
```

**Example**

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/pipelines?q=bandwidth&team=Dagger&team=Vault&status=success&limit=20"
```

```python
import requests

resp = requests.get("http://localhost:8000/api/pipelines",
    headers={"Authorization": f"Bearer {token}"},
    params={"q": "bandwidth", "team": ["Dagger", "Vault"], "limit": 20})
pipelines = resp.json()["items"]
```

---

### `GET /api/pipelines/{pipeline_id}`

Get full pipeline detail including fields, lineage, and edit permissions.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `pipeline_id` | `uuid` | Pipeline ID |

**Auth:** Requires pipeline visibility (returns `404` if not visible — not `403`, to prevent UUID enumeration).

**Response** `200`

```json
{
  "id": "550e8400-...",
  "name": "SwitchPortCollector",
  "task_id": "SwitchPortCollector",
  "description": "Collects switch port interface data",
  "category": "Collection",
  "fields": [
    { "id": "...", "name": "device_id", "data_type": "VARCHAR", "ordinal_position": 0 },
    { "id": "...", "name": "port_name", "data_type": "VARCHAR", "ordinal_position": 1 }
  ],
  "source_tables": ["catalog.iceberg.dagger.upstream_source"],
  "destination_tables": ["catalog.iceberg.dagger.switch_port_collector"],
  "documentation": "# SwitchPortCollector\n\nCollects...",
  "team_id": "...",
  "can_edit": true,
  "execution_date": "2026-03-27T06:00:00Z",
  "last_checked_at": "2026-03-27T06:20:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `fields` | `PipelineField[]` | Schema columns from Iceberg catalog |
| `source_tables` | `string[]` | Tables this pipeline reads from |
| `destination_tables` | `string[]` | Tables this pipeline writes to |
| `documentation` | `string\|null` | Markdown documentation |
| `can_edit` | `boolean` | Whether the current user can edit this pipeline |

---

### `PATCH /api/pipelines/{pipeline_id}`

Update pipeline description or documentation.

**Auth:** Requires team membership or editor grant.

**Request Body**

```json
{
  "description": "Updated description text",
  "documentation": "# Updated Docs\n\nNew documentation content..."
}
```

Both fields are optional — only provided fields are updated.

**Response** `200`

```json
{
  "id": "550e8400-...",
  "description": "Updated description text",
  "documentation": "# Updated Docs\n\nNew documentation content...",
  "last_updated_by": "alice@example.com",
  "last_updated_at": "2026-03-28T10:30:00Z"
}
```

---

### `POST /api/pipelines/{pipeline_id}/sync`

Trigger immediate re-sync of a single pipeline from Airflow.

**Auth:** Requires team membership. **Rate limit:** 30 requests/minute.

**Response** `200`

```json
{
  "synced": true,
  "pipeline_name": "SwitchPortCollector"
}
```

---

### `GET /api/pipelines/{pipeline_id}/revisions`

List revision history for pipeline description or documentation.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `field` | `string` | — | Filter by field: `description` or `documentation` |
| `skip` | `integer` | `0` | Pagination offset |
| `limit` | `integer` | `200` | Page size |

**Response** `200`

```json
{
  "items": [
    {
      "id": "...",
      "pipeline_id": "...",
      "field_name": "description",
      "content": "Previous description text",
      "changed_by": "alice@example.com",
      "change_source": "user",
      "created_at": "2026-03-25T14:00:00Z"
    }
  ],
  "total": 5
}
```

| `change_source` | Description |
|-----------------|-------------|
| `user` | Changed by a user in the UI |
| `airflow` | Updated during Airflow sync |
| `system` | System operation (restore, migration) |

---

### `POST /api/pipelines/{pipeline_id}/revisions/{revision_id}/restore`

Restore a pipeline field to a previous revision's content.

**Auth:** Requires team membership or editor grant.

**Response** `200` — Same as `PATCH /api/pipelines/{pipeline_id}` response.

---

### `GET /api/pipelines/{pipeline_id}/joins`

Get schema-based join suggestions for this pipeline.

**Response** `200`

```json
{
  "suggestions": [
    {
      "pipeline_id": "...",
      "pipeline_name": "InterfaceTrafficSummary",
      "shared_fields": ["device_id", "port_name", "site_code"]
    }
  ],
  "explanations": []
}
```

---

## Airflow Endpoints

### `GET /api/airflow/status`

Get Airflow run statuses for all pipelines.

**Response** `200`

```json
{
  "statuses": [
    {
      "pipeline_id": "...",
      "dag_id": "backbone_core",
      "status": "success",
      "execution_date": "2026-03-27T06:00:00Z",
      "last_checked_at": "2026-03-27T06:20:00Z"
    }
  ],
  "airflow_connected": true
}
```

---

### `GET /api/airflow/status/{pipeline_id}`

Get Airflow status for a single pipeline.

**Response** `200` — Single `AirflowStatus` object.

---

### `POST /api/airflow/sync-all`

Trigger full Airflow sync (pipelines + statuses + lineage + resources).

**Auth:** Admin only.

**Response** `200`

```json
{
  "synced": 142,
  "message": "Synced 142 pipelines from Airflow"
}
```

---

## Resource & Performance Endpoints

### `GET /api/pipelines/{pipeline_id}/resources`

Get resource allocation, duration history, actual usage, and cluster capacity for a pipeline.

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `date_from` | `string` | ISO date, filter runs after this date |
| `date_to` | `string` | ISO date, filter runs before this date |

**Response** `200`

```json
{
  "avg_duration_seconds": 245.5,
  "min_duration_seconds": 180.0,
  "max_duration_seconds": 420.0,
  "latest_duration_seconds": 210.0,
  "run_count": 30,
  "success_rate": 93.3,
  "recent_runs": [
    {
      "duration_seconds": 210.0,
      "execution_date": "2026-03-27T06:00:00Z",
      "status": "success",
      "dag_id": "backbone_core",
      "spark_application_id": "app-20260327-001",
      "metrics_source": "sparkMeasure"
    }
  ],
  "resource_configs": [
    {
      "dag_id": "backbone_core",
      "spark_driver_memory": "2g",
      "spark_executor_memory": "8g",
      "spark_executor_cores": 4,
      "spark_num_executors": 2,
      "is_dag_override": false
    }
  ],
  "actual_usage": {
    "avg_driver_memory_used_mb": 512,
    "avg_executor_memory_peak_mb": 4096,
    "avg_cpu_utilization_pct": 72.5,
    "avg_executors_active": 2
  },
  "capacity": [
    {
      "label": "Driver Memory",
      "allocated": 2.0,
      "used": 0.5,
      "max_capacity": 16.0,
      "allocated_pct": 12.5,
      "used_pct": 3.1
    }
  ]
}
```

---

### `GET /api/pipelines/{pipeline_id}/resources/history`

Get full run history with per-run resource metrics.

**Response** `200`

```json
{
  "records": [
    {
      "execution_date": "2026-03-27T06:00:00Z",
      "dag_id": "backbone_core",
      "dag_run_id": "manual__2026-03-27",
      "status": "success",
      "duration_seconds": 210.0,
      "driver_memory_used_mb": 512,
      "executor_memory_peak_mb": 4096,
      "cpu_utilization_pct": 72.5,
      "executors_active": 2,
      "peak_execution_memory": 3221225472,
      "jvm_gc_time_ms": 5000,
      "shuffle_read_bytes": 1073741824,
      "shuffle_write_bytes": 536870912,
      "input_bytes": 2147483648,
      "output_bytes": 1073741824,
      "memory_bytes_spilled": 0,
      "disk_bytes_spilled": 0,
      "metrics_source": "sparkMeasure"
    }
  ]
}
```

---

### `GET /api/pipelines/{pipeline_id}/execution-plan`

Get Spark physical execution plan tree from the latest (or a specific) run.

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `dag_run_id` | `string` | Optional — specific run ID. Omit for latest successful run. |

**Response** `200`

```json
{
  "dag_id": "backbone_core",
  "dag_run_id": "manual__2026-03-27",
  "task_id": "SwitchPortCollector",
  "status": "success",
  "duration_seconds": 210.0,
  "execution_date": "2026-03-27T06:00:00Z",
  "execution_plan": {
    "id": 1,
    "name": "Project",
    "type": "transform",
    "detail": "Project [device_id, port_name, ts]",
    "full_detail": "Project [device_id#123, port_name#124, ts#125]",
    "metrics": { "output rows": "1,200,000" },
    "children": [
      {
        "id": 2,
        "name": "SortMergeJoin",
        "type": "shuffle",
        "detail": "inner on device_id",
        "metrics": { "sort time": "1.2s", "output rows": "1,200,000" },
        "children": []
      }
    ]
  }
}
```

**Node types:** `read`, `write`, `shuffle`, `transform`

**Response** `404` — No execution plan available for this pipeline.

---

### `GET /api/pipelines/{pipeline_id}/execution-plan/runs`

List runs that have execution plans available.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | `integer` | `0` | Pagination offset |
| `limit` | `integer` | `20` | Page size |

**Response** `200`

```json
{
  "items": [
    {
      "dag_run_id": "manual__2026-03-27",
      "dag_id": "backbone_core",
      "start_date": "2026-03-27T06:00:00Z",
      "status": "success"
    }
  ],
  "total": 12
}
```

---

### `GET /api/pipelines/{pipeline_id}/runs`

List pipeline run history.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | `integer` | `0` | Pagination offset |
| `limit` | `integer` | `20` | Page size |

**Response** `200`

```json
{
  "items": [
    {
      "dag_run_id": "manual__2026-03-27",
      "dag_id": "backbone_core",
      "status": "success",
      "start_date": "2026-03-27T06:00:00Z",
      "end_date": "2026-03-27T06:03:30Z",
      "duration_seconds": 210.0,
      "has_execution_plan": true
    }
  ],
  "total": 45
}
```

---

### `GET /api/pipelines/{pipeline_id}/runs/{dag_run_id}`

Get detailed metrics for a specific run.

**Response** `200`

```json
{
  "dag_run_id": "manual__2026-03-27",
  "dag_id": "backbone_core",
  "status": "success",
  "start_date": "2026-03-27T06:00:00Z",
  "end_date": "2026-03-27T06:03:30Z",
  "duration_seconds": 210.0,
  "has_execution_plan": true,
  "driver_memory_used_mb": 512,
  "executor_memory_peak_mb": 4096,
  "cpu_utilization_pct": 72.5,
  "executors_active": 2,
  "peak_execution_memory": 3221225472,
  "jvm_gc_time_ms": 5000,
  "shuffle_read_bytes": 1073741824,
  "shuffle_write_bytes": 536870912,
  "input_bytes": 2147483648,
  "output_bytes": 1073741824,
  "memory_bytes_spilled": 0,
  "disk_bytes_spilled": 0,
  "metrics_source": "sparkMeasure",
  "spark_application_id": "app-20260327-001",
  "fields_snapshot": [
    { "name": "device_id", "data_type": "VARCHAR", "ordinal_position": 0 }
  ],
  "source_tables_snapshot": ["catalog.iceberg.dagger.upstream"],
  "destination_tables_snapshot": ["catalog.iceberg.dagger.switch_port_collector"]
}
```

---

## Topology Endpoints

### `GET /api/pipelines/{pipeline_id}/topology`

Get direct dependency topology (upstream bouncers, needs, prefers, downstream).

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `dag_id` | `string` | Optional — scope to single DAG |
| `dag_run_id` | `string` | Optional — use per-run status instead of latest |

**Response** `200`

```json
{
  "pipeline_task_id": "SwitchPortCollector",
  "pipeline_status": "success",
  "dag_ids": ["backbone_core", "perimeter_defense"],
  "upstream_bouncers": [
    {
      "bouncer_name": "SwitchPortBouncer",
      "display_name": "Switch Port Bouncer",
      "bouncer_id": "...",
      "status": "success",
      "team": "Dagger",
      "volume_per_day": 5000000,
      "dag_ids": ["backbone_core"]
    }
  ],
  "upstream_needs": [
    {
      "task_id": "DeviceInventory",
      "pipeline_name": "Device Inventory",
      "pipeline_id": "...",
      "status": "success",
      "dag_id": "backbone_core",
      "task_group_id": "Dagger-Collection"
    }
  ],
  "upstream_prefers": [],
  "downstream": [
    {
      "task_id": "BandwidthUtilization",
      "pipeline_name": "Bandwidth Utilization",
      "pipeline_id": "...",
      "status": "success",
      "dag_id": "backbone_core",
      "task_group_id": "Dagger-Enrichment"
    }
  ]
}
```

---

### `GET /api/pipelines/{pipeline_id}/topology/upstream`

Get full recursive upstream dependency graph via BFS traversal.

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `dag_id` | `string` | Optional — scope to single DAG |
| `dag_run_id` | `string` | Optional — use per-run statuses |

**Response** `200`

```json
{
  "pipeline_task_id": "SwitchPortCollector",
  "pipeline_status": "success",
  "dag_ids": ["backbone_core"],
  "nodes": [
    {
      "task_id": "SwitchPortCollector",
      "pipeline_name": "Switch Port Collector",
      "pipeline_id": "...",
      "status": "success",
      "dag_id": "backbone_core",
      "depth": 0,
      "is_current": true,
      "is_bouncer": false,
      "bouncer_name": null
    },
    {
      "task_id": "DeviceInventory",
      "pipeline_name": "Device Inventory",
      "pipeline_id": "...",
      "status": "success",
      "dag_id": "backbone_core",
      "depth": 1,
      "is_current": false,
      "is_bouncer": false,
      "bouncer_name": null
    }
  ],
  "edges": [
    {
      "source_task_id": "DeviceInventory",
      "target_task_id": "SwitchPortCollector",
      "edge_type": "needs"
    }
  ],
  "bouncers": [],
  "max_depth": 3
}
```

| Edge type | Description |
|-----------|-------------|
| `needs` | Hard dependency (orange) |
| `prefers` | Soft dependency (blue) |

---

## Lineage Endpoints

### `GET /api/pipelines/{pipeline_id}/lineage`

Get data lineage graph (source tables reads_from, destination tables writes_to).

**Response** `200`

```json
{
  "nodes": [
    { "table_name": "upstream_source", "pipeline_id": null, "pipeline_name": null, "node_type": "source" },
    { "table_name": "SwitchPortCollector", "pipeline_id": "...", "pipeline_name": "Switch Port Collector", "node_type": "pipeline" },
    { "table_name": "switch_port_collector", "pipeline_id": null, "pipeline_name": null, "node_type": "target" }
  ],
  "edges": [
    { "source": "upstream_source", "target": "SwitchPortCollector", "edge_type": "reads_from" },
    { "source": "SwitchPortCollector", "target": "switch_port_collector", "edge_type": "writes_to" }
  ],
  "source_tables": ["upstream_source"],
  "destination_tables": ["switch_port_collector"]
}
```

---

## Bouncer Endpoints

### `GET /api/bouncers`

List all bouncers (data ingestion root tasks) with optional team filter.

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `team` | `string` | Optional — filter by team name |

**Response** `200`

```json
{
  "bouncers": [
    {
      "id": "...",
      "bouncer_name": "SwitchPortBouncer",
      "display_name": "Switch Port Bouncer",
      "description": "Ingests switch port interface data",
      "team": "Dagger",
      "volume_per_day": 5000000,
      "status": "success",
      "dag_ids": ["backbone_core"]
    }
  ],
  "teams": ["Dagger", "Vault", "Prism", "Relay", "Oasis"]
}
```

---

### `GET /api/bouncers/topology`

Get downstream ETL topology for selected bouncers.

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `bouncers` | `string[]` | Required — bouncer names (repeatable) |
| `mode` | `string` | `union` (default) or `intersection` |

**Response** `200`

```json
{
  "selected_bouncers": ["SwitchPortBouncer"],
  "downstream_etls": [
    {
      "task_id": "SwitchPortCollector",
      "pipeline_name": "Switch Port Collector",
      "pipeline_id": "...",
      "status": "success",
      "dag_id": "backbone_core",
      "depends_on_bouncers": ["SwitchPortBouncer"]
    }
  ],
  "total_etl_count": 8
}
```

| Mode | Description |
|------|-------------|
| `union` | ETLs downstream of **any** selected bouncer |
| `intersection` | ETLs downstream of **all** selected bouncers |

---

## Consumer Endpoints

### `GET /api/consumers/{etl_name}`

Get downstream consumers of a pipeline.

**Auth:** Requires pipeline visibility (by name).

**Response** `200`

```json
{
  "consumers": [
    {
      "pipeline_id": "...",
      "pipeline_name": "BandwidthUtilization",
      "dag_id": "backbone_core",
      "airflow_status": "success",
      "last_run_at": "2026-03-27T06:00:00Z"
    }
  ]
}
```

---

## Usage Endpoints

### `GET /api/usage/{etl_name}`

Get pipeline usage metrics (downstream ETL and API consumers with access counts).

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `date_from` | `string` | ISO date |
| `date_to` | `string` | ISO date |
| `network` | `string` | Optional — filter by DAG network |

**Response** `200`

```json
{
  "usages": [
    {
      "id": "...",
      "consumer_name": "BandwidthUtilization",
      "usage_type": "etl",
      "description": "Reads switch port data for bandwidth calculation",
      "last_accessed_at": "2026-03-27T06:00:00Z",
      "unique_reads": 30,
      "total_reads": 450,
      "airflow_status": "success",
      "dag_id": "backbone_core",
      "is_current": true
    }
  ]
}
```

---

## DAG Summary Endpoints

### `GET /api/dags/summary`

Get DAG-level aggregate statistics and per-DAG breakdowns.

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `date_from` | `string` | ISO date |
| `date_to` | `string` | ISO date |

**Response** `200`

```json
{
  "aggregate": {
    "total_dags": 6,
    "total_pipelines": 142,
    "active_dags": 5,
    "overall_success_rate": 91.5,
    "total_runs_30d": 1260,
    "period_label": "30d"
  },
  "dags": [
    {
      "dag_id": "backbone_core",
      "description": "Core network data collection and enrichment",
      "schedule_interval": "0 6 * * *",
      "is_paused": false,
      "task_count": 32,
      "pipeline_count": 28,
      "total_duration_seconds": 1800.0,
      "avg_task_duration_seconds": 56.25,
      "min_task_duration_seconds": 12.0,
      "max_task_duration_seconds": 420.0,
      "status_counts": { "success": 28, "failed": 2, "running": 1, "queued": 1 },
      "success_rate": 87.5,
      "latest_run_start": "2026-03-27T06:00:00Z",
      "latest_run_end": "2026-03-27T06:30:00Z",
      "typical_finish_hour": 6,
      "total_runs_30d": 210,
      "dag_success_rate_30d": 93.8,
      "period_label": "30d",
      "tasks": [
        {
          "task_id": "SwitchPortCollector",
          "pipeline_name": "Switch Port Collector",
          "pipeline_id": "...",
          "status": "success",
          "latest_duration_seconds": 210.0,
          "avg_duration_seconds": 245.5,
          "task_group_id": "Dagger-Collection"
        }
      ]
    }
  ]
}
```

---

## Schema Matrix Endpoints

### `GET /api/schema-matrix`

Get cross-pipeline field frequency matrix.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | `integer` | `0` | Pagination offset |
| `limit` | `integer` | `200` | Page size |
| `q` | `string` | — | Search field names |

**Response** `200`

```json
{
  "fields": [
    {
      "field_name": "device_id",
      "frequency": 42,
      "pipelines": [
        { "pipeline_id": "...", "pipeline_name": "SwitchPortCollector" },
        { "pipeline_id": "...", "pipeline_name": "InterfaceTrafficSummary" }
      ]
    }
  ],
  "total": 890
}
```

---

## AI Endpoints

### `POST /api/ai/chat`

Send a message to the AI Architect with catalog context.

**Rate limit:** 60 requests/minute.

**Request Body**

```json
{
  "message": "Which pipelines track bandwidth utilization?",
  "history": [
    { "role": "user", "content": "Previous question" },
    { "role": "assistant", "content": "Previous answer" }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `message` | `string` | User message |
| `history` | `ChatMessage[]` | Previous conversation (max 50 messages) |

**Response** `200`

```json
{
  "role": "assistant",
  "content": "There are several pipelines related to bandwidth utilization..."
}
```

Non-admin users only receive catalog context for pipelines they have visibility to.

---

### `GET /api/pipelines/{pipeline_id}/joins/ai`

Get AI-powered join insights for a specific pipeline.

**Response** `200`

```json
{
  "insight": "SwitchPortCollector can be joined with InterfaceTrafficSummary on device_id and port_name..."
}
```

---

## Visibility Grant Endpoints

All grant endpoints require **admin** role.

### `GET /api/visibility/grants`

List all visibility grants.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | `integer` | `0` | Pagination offset |
| `limit` | `integer` | `100` | Page size |

**Response** `200`

```json
{
  "items": [
    {
      "id": "...",
      "grantee_team_id": "...",
      "grantee_team_name": "Relay",
      "grantee_user_id": null,
      "grantee_user_name": null,
      "grantee_user_email": null,
      "pipeline_id": "...",
      "source_team_id": null,
      "source_team_name": null,
      "grant_level": "viewer",
      "granted_by": "alice@example.com",
      "created_at": "2026-03-25T10:00:00Z"
    }
  ],
  "total": 12
}
```

---

### `POST /api/visibility/grants`

Create a new visibility grant.

**Request Body**

```json
{
  "grantee_team_id": "...",
  "pipeline_id": "...",
  "grant_level": "viewer"
}
```

**Exactly one** of `grantee_team_id` / `grantee_user_id` must be set (recipient).
**Exactly one** of `pipeline_id` / `source_team_id` must be set (target).

| Field | Type | Description |
|-------|------|-------------|
| `grantee_team_id` | `uuid\|null` | Grant to a team |
| `grantee_user_id` | `uuid\|null` | Grant to a specific user |
| `pipeline_id` | `uuid\|null` | Grant access to a specific pipeline |
| `source_team_id` | `uuid\|null` | Grant access to all pipelines owned by a team |
| `grant_level` | `string` | `viewer` or `editor` |

**Response** `200` — Created `VisibilityGrant` object.

**Response** `400` — Validation error (e.g., both `pipeline_id` and `source_team_id` set).

---

### `DELETE /api/visibility/grants/{grant_id}`

Revoke a visibility grant.

**Response** `200`

```json
{ "ok": true }
```

---

## User Management Endpoints

All user management endpoints require **admin** role.

### `GET /api/users`

List all users with pagination.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | `integer` | `0` | Pagination offset |
| `limit` | `integer` | `200` | Page size (max 500) |

**Response** `200`

```json
{
  "items": [
    {
      "id": "...",
      "email": "alice@example.com",
      "display_name": "Alice",
      "role": "admin",
      "is_active": true,
      "teams": [
        { "id": "...", "name": "Dagger", "role_in_team": "member" }
      ]
    }
  ],
  "total": 25
}
```

---

### `PATCH /api/users/{user_id}/role`

Update a user's global role.

**Safeguards:**
- Cannot change your own role (prevents self-demotion)
- Cannot demote the last admin

**Request Body**

```json
{ "role": "member" }
```

**Response** `200`

```json
{ "ok": true }
```

---

### `PATCH /api/users/{user_id}/active`

Activate or deactivate a user account.

**Safeguard:** Cannot deactivate yourself.

**Request Body**

```json
{ "is_active": false }
```

**Response** `200`

```json
{ "ok": true }
```

---

## Team Endpoints

### `GET /api/teams`

List all teams with member counts.

**Response** `200`

```json
[
  {
    "id": "...",
    "name": "Dagger",
    "description": "Network data collection team",
    "source": "sso",
    "member_count": 5
  }
]
```

---

### `GET /api/teams/{team_id}`

Get team detail with full member list.

**Auth:** Admins can view any team; non-admins can only view their own teams.

**Response** `200`

```json
{
  "id": "...",
  "name": "Dagger",
  "description": "Network data collection team",
  "source": "sso",
  "members": [
    {
      "id": "...",
      "email": "alice@example.com",
      "display_name": "Alice",
      "role": "admin",
      "role_in_team": "member"
    }
  ]
}
```

---

### `GET /api/teams/{team_id}/pipelines`

List all pipelines owned by a team.

**Auth:** Same as team detail.

**Response** `200` — Array of `PipelineListItem` objects.

---

## Metrics Endpoint

### `GET /api/metrics`

Prometheus-format metrics. **Admin only.**

**Response** `200` (text/plain)

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/api/pipelines",status="200"} 1234
# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1"} 900
# HELP db_pool_size Database connection pool size
# TYPE db_pool_size gauge
db_pool_size 20
db_pool_checked_out 3
```

---

## Health Endpoint

### `GET /health`

Health check. **No authentication required.**

**Response** `200`

```json
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "airflow": "connected",
    "iceberg": "connected"
  },
  "db_pool": {
    "size": 20,
    "checked_out": 3,
    "overflow": 0
  }
}
```

---

## Common Schemas

### PipelineField

```json
{
  "id": "uuid",
  "name": "string",
  "data_type": "string | null",
  "ordinal_position": "integer"
}
```

### PipelineListItem

```json
{
  "id": "uuid",
  "name": "string",
  "description": "string | null",
  "category": "string | null",
  "pipeline_type": "string | null",
  "schedule": "string | null",
  "rows_per_day": "string | null",
  "airflow_status": "string | null",
  "success_rate": "number | null",
  "team": "string | null",
  "last_run_at": "string | null",
  "execution_date": "string | null"
}
```

### TeamMembership

```json
{
  "id": "uuid",
  "name": "string",
  "role_in_team": "string"
}
```

### ChatMessage

```json
{
  "role": "user | assistant",
  "content": "string"
}
```

---

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Error description"
}
```

| Status | Meaning |
|--------|---------|
| `400` | Bad request — invalid parameters or body |
| `401` | Unauthorized — missing or invalid token |
| `403` | Forbidden — insufficient role or permissions |
| `404` | Not found — resource doesn't exist or not visible to user |
| `429` | Rate limited — too many requests |
| `500` | Internal server error |

**Note:** Pipeline detail returns `404` (not `403`) when a user lacks visibility, to prevent UUID enumeration.

---

## Rate Limiting

| Endpoint | Limit |
|----------|-------|
| `POST /api/pipelines/{id}/sync` | 30/minute |
| `POST /api/ai/chat` | 60/minute |
| All other endpoints | No limit (nginx rate limiting applies at 30 req/s per IP) |

Rate limit headers are included in responses:
- `X-RateLimit-Limit` — Maximum requests per window
- `X-RateLimit-Remaining` — Remaining requests
- `X-RateLimit-Reset` — Window reset timestamp

When rate limited, the API returns `429 Too Many Requests`.
