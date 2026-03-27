# Review Scope

## Target

Entire EtlNexus codebase (post tech-debt remediation) — full-stack ETL Explorer Hub with dark-themed bento-box UI. Includes backend (FastAPI + SQLAlchemy + PostgreSQL), frontend (React 19 + TypeScript + Vite), SSO/RBAC (Keycloak OIDC), Docker infrastructure, backend tests, and dev/seed tooling.

## Files

### Backend (106 app files + 19 test files)
- **Core (8):** main.py, auth.py, cache.py, config.py, database.py, dependencies.py, exceptions.py, rate_limit.py (NEW)
- **Routers (15):** health, auth, pipelines, lineage, topology, airflow, sensors, resources, usage, consumers, schema_matrix, ai, dag_summary, teams, users, visibility
- **Models (13):** pipeline, lineage, run_history, resource_config, pipeline_usage, sensor, airflow_status, dag_task, user, team, user_team, visibility_grant, pipeline_revision
- **Schemas (17+1):** pipeline, lineage, airflow, resources, usage, sensor, execution_plan, schema_matrix, ai, dag_summary, consumer, common, auth, team, visibility, date_range, topology, internal (NEW)
- **Services (16):** pipeline, airflow, lineage, airflow_sync, catalog_sync, resource, usage, consumer, schema_matrix, ai, dag_summary, team, user_auth, visibility, topology, sensor + sync/task_classifier
- **Repositories (14):** base, pipeline, lineage, airflow, resource, usage, sensor, field_frequency, dag_task, team, user, visibility_grant, revision
- **Integrations (4):** airflow_client, iceberg_client, llm_client, oidc_client
- **Parsers (2):** dagger_catalog, log_parser
- **Tasks (6):** scheduler, airflow_sync_task, airflow_poll_task, catalog_sync_task, seed_bouncer_volumes, seed_usage_data
- **Tests (19):** conftest, test_integration (NEW), test_airflow_client, test_airflow_sync_helpers, test_auth, test_auth_schema_helpers, test_base_repo, test_cache, test_catalog_sync_service, test_log_parser, test_oidc_client, test_pipeline_service, test_schemas, test_task_classifier, test_team_service, test_topology_service, test_user_auth_service, test_visibility_service

### Frontend (166 files)
- **API (16)**, **Types (14)**, **Stores (7)**, **Hooks (19)**, **Lib (7)**
- **Components:** layout(3), auth(3), pipeline-registry(4), bento-workspace(18+ with sub-dirs), lineage(5), execution-plan(11+ with formatters/), documentation(3), resource-performance(2), bouncers(4), dag-summary(4), schema-matrix(2), ai-terminal(5), admin(4), onboarding(5), shared(9 incl ErrorBoundary NEW), ui(9)
- **Tests (7):** setup, format.test, permissions.test, plan-parsers.test, lineage-utils.test (NEW), status-config.test, utils.test
- **Root:** App.tsx, main.tsx

### Database Migrations (28)

### Infrastructure
- docker-compose.yml, docker-compose.prod.yml
- backend/Dockerfile, frontend/Dockerfile, dev/airflow/Dockerfile
- frontend/nginx.conf, dev/keycloak/etlnexus-realm.json
- .env.example, pyproject.toml, package.json, vite.config.ts, vitest.config.ts

### Dev/Seed (110 files)

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
