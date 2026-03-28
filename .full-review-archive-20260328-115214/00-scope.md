# Review Scope

## Target

Entire EtlNexus codebase — full-stack ETL Explorer Hub application including Python/FastAPI backend, React 19/TypeScript frontend, Docker infrastructure, and database migrations.

## Files

### Backend (Python)
- **Core:** `backend/app/main.py`, `config.py`, `database.py`, `dependencies.py`, `exceptions.py`, `logging_config.py`, `cache.py`, `rate_limit.py`, `auth.py`
- **Routers (18):** `ai.py`, `airflow.py`, `auth.py`, `bouncers.py`, `consumers.py`, `dag_summary.py`, `health.py`, `lineage.py`, `metrics.py`, `pipelines.py`, `resources.py`, `schema_matrix.py`, `teams.py`, `topology.py`, `usage.py`, `users.py`, `visibility.py`
- **Services (17):** `ai_service.py`, `airflow_service.py`, `airflow_sync_service.py`, `bouncer_service.py`, `catalog_sync_service.py`, `consumer_service.py`, `dag_summary_service.py`, `graph_builder.py`, `pipeline_service.py`, `resource_service.py`, `schema_matrix_service.py`, `team_service.py`, `topology_service.py`, `usage_service.py`, `user_auth_service.py`, `visibility_service.py`, `sync/task_classifier.py`
- **Repositories (16):** `base.py`, `airflow_repo.py`, `bouncer_repo.py`, `dag_task_repo.py`, `field_frequency_repo.py`, `lineage_repo.py`, `pipeline_repo.py`, `resource_repo.py`, `resource_stats.py`, `revision_repo.py`, `team_repo.py`, `usage_repo.py`, `user_repo.py`, `visibility_filter.py`, `visibility_grant_repo.py`
- **Integrations (5):** `airflow_client.py`, `iceberg_client.py`, `llm_client.py`, `oasis_prod_client.py`, `oidc_client.py`
- **Parsers:** `log_parser.py`, `namespace_filter.py`
- **Tasks (7):** `scheduler.py`, `airflow_poll_task.py`, `airflow_sync_task.py`, `catalog_sync_task.py`, `seed_bouncer_volumes.py`, `seed_usage_data.py`
- **Models (14):** All ORM models (pipeline, user, team, visibility_grant, etc.)
- **Schemas (19):** All Pydantic DTOs
- **Tests (27):** Full test suite under `backend/tests/`
- **Migrations (31):** Alembic versions 001-031

### Frontend (TypeScript/React)
- **API Layer (15):** All API client modules
- **Types (15):** All TypeScript interface modules
- **Stores (8):** Zustand state management
- **Hooks (22):** TanStack Query hooks
- **Components (100+):** Admin, AI Terminal, Auth, Bento Workspace (with sub-modules: documentation, execution-plan, formatters, lineage, resource-performance), Bouncers, DAG Summary, Layout, Onboarding, Pipeline Registry, Schema Matrix, Shared, UI (shadcn)
- **Tests (20+):** Component and utility tests
- **Lib (7):** Utilities, config, constants, formatting, permissions

### Infrastructure
- **Docker:** `docker-compose.yml`, `docker-compose.prod.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/docker-entrypoint.sh`
- **Nginx:** `frontend/nginx.conf`
- **Config:** `pyproject.toml`, `package.json`, `tsconfig.json`, `vite.config.ts`, `vitest.config.ts`, `playwright.config.ts`, `alembic.ini`

## Flags

- Security Focus: no
- Performance Critical: no
- Strict Mode: no
- Framework: FastAPI + React 19 (auto-detected)

## Review Phases

1. Code Quality & Architecture
2. Security & Performance
3. Testing & Documentation
4. Best Practices & Standards
5. Consolidated Report
