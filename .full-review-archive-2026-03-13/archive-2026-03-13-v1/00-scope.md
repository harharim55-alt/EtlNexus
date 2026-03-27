# Review Scope

## Target

Entire EtlNexus codebase — a full-stack ETL Explorer Hub with dark-themed "bento-box" UI for discovering, understanding, and utilizing ETL pipelines. Includes backend (FastAPI + SQLAlchemy + PostgreSQL), frontend (React 19 + TypeScript + Vite), SSO/RBAC (Keycloak OIDC), Docker infrastructure, and dev/seed tooling.

## Files

### Backend (104 files)
- `backend/app/main.py`, `config.py`, `database.py`, `auth.py`, `exceptions.py`, `cache.py`, `dependencies.py`
- **Routers (16):** health, auth, pipelines, lineage, topology, airflow, sensors, resources, usage, consumers, schema_matrix, ai, dag_summary, teams, users, visibility
- **Models (14):** pipeline, lineage, run_history, resource_config, pipeline_usage, sensor, airflow_status, dag_task, user, team, user_team, visibility_grant, pipeline_revision
- **Schemas/DTOs (18):** pipeline, lineage, airflow, resources, usage, sensor, execution_plan, schema_matrix, ai, dag_summary, consumer, common, auth, team, visibility, date_range, topology
- **Services (17):** pipeline, airflow, lineage, airflow_sync, catalog_sync, resource, usage, consumer, schema_matrix, ai, dag_summary, team, user_auth, visibility, topology, sensor + sync/task_classifier
- **Repositories (14):** base, pipeline, lineage, airflow, resource, usage, sensor, field_frequency, dag_task, team, user, visibility_grant, revision
- **Integrations (4):** airflow_client, iceberg_client, llm_client, oidc_client
- **Parsers (2):** dagger_catalog, log_parser
- **Tasks (5):** scheduler, airflow_sync_task, airflow_poll_task, catalog_sync_task, seed_bouncer_volumes, seed_usage_data

### Frontend (147 files)
- **API Layer (16):** client, auth, pipelines, lineage, topology, airflow, bouncers, resources, usage, consumers, schema-matrix, ai, dag-summary, execution-plan, admin
- **Types (14):** pipeline, lineage, airflow, bouncer, resources, usage, consumer, schema-matrix, execution-plan, ai, dag-summary, topology, auth, admin
- **Stores (7):** pipeline-store, navigation-store, ai-store, bouncer-store, auth-store, date-range-store, onboarding-store
- **Hooks (20):** use-pipelines, use-pipeline-detail, use-lineage, use-topology, use-airflow-status, use-bouncers, use-resource-metrics, use-pipeline-usage, use-pipeline-consumers, use-schema-matrix, use-ai-chat, use-dag-summary, use-execution-plan, use-auth, use-join-suggestions, use-upstream-topology, use-update-pipeline, use-sync-pipeline, use-revisions, use-admin
- **Components (73):** layout(3), auth(3), pipeline-registry(4), bento-workspace(15+), lineage(3), execution-plan(6), documentation(3), resource-performance(2), bouncers(4), dag-summary(4), schema-matrix(2), ai-terminal(5), admin(4), onboarding(5), shared(7), ui(9)
- **Lib/Utils (7):** utils, constants, format, status-config, config, permissions, admin-styles
- **Tests (4):** setup, format.test, permissions.test, plan-parsers.test
- **Root:** App.tsx, main.tsx

### Database Migrations (29)
- `backend/alembic/versions/` — 001 through 028 covering schema evolution

### Infrastructure
- `docker-compose.yml`, `docker-compose.prod.yml`
- `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`
- `.env.example`, `backend/pyproject.toml`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`
- `dev/keycloak/etlnexus-realm.json`

### Dev/Seed Files (110)
- 6 DAG definitions, etl_runner.py, sensor_runner.py, spark_metrics_collector.py
- 30 resource config files, 30 task config files
- 30 ETL class implementations (PySpark)
- Iceberg seed scripts

## Flags

- Security Focus: no
- Performance Critical: no
- Strict Mode: no
- Framework: FastAPI + React 19

## Review Phases

1. Code Quality & Architecture
2. Security & Performance
3. Testing & Documentation
4. Best Practices & Standards
5. Consolidated Report
