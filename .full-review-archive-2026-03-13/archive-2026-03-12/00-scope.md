# Review Scope

## Target

PR #4: "Add SSO authentication, team RBAC, admin panel, and pipeline filters"
Branch: `feature/sso-teams-rbac` → `main`
182 files changed across backend, frontend, dev/dags, and docker-compose.

## Key Feature Areas

1. **SSO/OIDC Authentication** — Keycloak integration, JWT validation, JIT user provisioning
2. **Role-Based Access Control** — Team-scoped pipeline visibility, per-user/per-team grants (viewer/editor)
3. **Admin Panel** — Users, Teams, Grants management UI
4. **Pipeline Filters** — Multi-dimension filtering (team, DAG, status) in registry
5. **PascalCase Rename** — All 30 ETL files, task configs, resources, seed tables
6. **Team Assignment from Airflow TaskGroups** — DAG source parsing via Airflow API

## Files (grouped by concern)

### Backend — Auth & RBAC (core review focus)
- `backend/app/auth.py` (345 lines — JWT validation, JIT provisioning, team sync)
- `backend/app/integrations/oidc_client.py` (267 lines — JWKS caching, dual issuer)
- `backend/app/dependencies.py` (auth dependency injection)
- `backend/app/config.py` (SSO settings)

### Backend — Models & Migrations
- `backend/app/models/user.py`, `team.py`, `user_team.py`, `visibility_grant.py`
- `backend/alembic/versions/015_add_users_teams.py`
- `backend/alembic/versions/016_add_team_to_pipelines.py`
- `backend/alembic/versions/017_add_visibility_grants.py`
- `backend/alembic/versions/018_add_user_visibility_grants.py`
- `backend/alembic/versions/019_add_grant_level.py`
- `backend/app/models/pipeline.py` (team fields added)

### Backend — Repositories
- `backend/app/repositories/pipeline_repo.py` (visibility queries)
- `backend/app/repositories/team_repo.py`
- `backend/app/repositories/user_repo.py`
- `backend/app/repositories/visibility_grant_repo.py` (226 lines)
- `backend/app/repositories/usage_repo.py` (minor)

### Backend — Services
- `backend/app/services/pipeline_service.py`
- `backend/app/services/airflow_sync_service.py` (team assignment from TaskGroups)
- `backend/app/services/team_service.py`
- `backend/app/services/visibility_service.py`
- `backend/app/services/catalog_sync_service.py`, `consumer_service.py`, `sensor_service.py`, `usage_service.py`

### Backend — Routers
- `backend/app/routers/auth.py`
- `backend/app/routers/teams.py` (127 lines)
- `backend/app/routers/users.py` (106 lines)
- `backend/app/routers/visibility.py` (115 lines)
- `backend/app/routers/pipelines.py` (visibility-filtered list, team-gated edit)
- `backend/app/routers/topology.py`

### Backend — Schemas
- `backend/app/schemas/auth.py`, `team.py`, `visibility.py`, `pipeline.py`

### Backend — Other
- `backend/app/main.py` (router registration)
- `backend/app/database.py` (minor)
- `backend/pyproject.toml` (python-jose dependency)
- `backend/app/tasks/seed_usage_data.py`
- `backend/app/integrations/airflow_client.py` (dagSources endpoint)

### Frontend — Auth
- `frontend/src/components/auth/AuthProvider.tsx`
- `frontend/src/components/auth/AuthGuard.tsx`
- `frontend/src/components/auth/LoginPage.tsx`
- `frontend/src/stores/auth-store.ts`
- `frontend/src/hooks/use-auth.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/types/auth.ts`
- `frontend/src/lib/permissions.ts`

### Frontend — Admin
- `frontend/src/components/admin/AdminView.tsx`
- `frontend/src/components/admin/UsersPanel.tsx`
- `frontend/src/components/admin/TeamsPanel.tsx`
- `frontend/src/components/admin/GrantsPanel.tsx`
- `frontend/src/hooks/use-admin.ts`
- `frontend/src/api/admin.ts`
- `frontend/src/types/admin.ts`

### Frontend — Modified Components
- `frontend/src/App.tsx`
- `frontend/src/api/client.ts` (bearer interceptor)
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/bento-workspace/BentoHeader.tsx`
- `frontend/src/components/bento-workspace/BentoWorkspace.tsx`
- `frontend/src/components/bento-workspace/DocumentationModal.tsx`
- `frontend/src/components/pipeline-registry/PipelineRegistry.tsx`
- `frontend/src/components/pipeline-registry/PipelineFilters.tsx`
- `frontend/src/components/pipeline-registry/PipelineSearch.tsx`
- `frontend/src/components/sensors/SensorTopology.tsx`
- `frontend/src/components/sensors/TeamFilter.tsx`
- `frontend/src/lib/constants.ts`
- `frontend/src/stores/pipeline-store.ts`
- `frontend/src/types/pipeline.ts`

### Dev/Data — PascalCase Renames & Config
- `dev/dags/application_mesh.py`, `backbone_core.py` (TaskGroup structure)
- `dev/dags/daily/task_configs/*.py` (27 files, minor edits)
- `dev/dags/daily/resources/*.py` (27 files, renames only)
- `dev/dags/hourly/resources/*.py`, `task_configs/*.py` (6 files)
- `dev/seeds/etl_code/dagger/*.py` (30 files, PascalCase renames)
- `dev/seeds/etl_code/etls.py`, `seed_iceberg.py`, `seed_iceberg_data.py`
- `dev/keycloak/` (realm config)
- `docker-compose.yml`

## Flags

- Security Focus: no
- Performance Critical: no
- Strict Mode: no
- Framework: FastAPI + React (auto-detected)

## Review Phases

1. Code Quality & Architecture
2. Security & Performance
3. Testing & Documentation
4. Best Practices & Standards
5. Consolidated Report
