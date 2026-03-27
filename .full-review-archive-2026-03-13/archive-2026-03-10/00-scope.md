# Review Scope

## Target
Full EtlNexus codebase — an ETL Explorer Hub with a FastAPI backend, React/TypeScript frontend, Airflow integration, and Docker containerization. Computer networking-themed demo data with 6 DAGs and 30 ETL pipelines.

## Files

### Backend — Application Code (65 files)
- `backend/app/main.py` — FastAPI app entry point
- `backend/app/config.py` — Settings/configuration
- `backend/app/database.py` — SQLAlchemy async engine
- `backend/app/dependencies.py` — FastAPI dependency injection

#### Models
- `backend/app/models/__init__.py`
- `backend/app/models/pipeline.py`
- `backend/app/models/lineage.py`
- `backend/app/models/airflow_status.py`
- `backend/app/models/pipeline_usage.py`
- `backend/app/models/resource_config.py`
- `backend/app/models/run_history.py`
- `backend/app/models/dag_task.py`

#### Schemas (Pydantic DTOs)
- `backend/app/schemas/pipeline.py`
- `backend/app/schemas/lineage.py`
- `backend/app/schemas/airflow.py`
- `backend/app/schemas/common.py`
- `backend/app/schemas/schema_matrix.py`
- `backend/app/schemas/ai.py`
- `backend/app/schemas/consumer.py`
- `backend/app/schemas/topology.py`
- `backend/app/schemas/usage.py`
- `backend/app/schemas/resources.py`

#### Routers (API endpoints)
- `backend/app/routers/pipelines.py`
- `backend/app/routers/lineage.py`
- `backend/app/routers/airflow.py`
- `backend/app/routers/schema_matrix.py`
- `backend/app/routers/ai.py`
- `backend/app/routers/topology.py`
- `backend/app/routers/usage.py`
- `backend/app/routers/consumers.py`
- `backend/app/routers/resources.py`
- `backend/app/routers/health.py`

#### Repositories (Data access)
- `backend/app/repositories/pipeline_repo.py`
- `backend/app/repositories/lineage_repo.py`
- `backend/app/repositories/airflow_repo.py`
- `backend/app/repositories/field_frequency_repo.py`
- `backend/app/repositories/usage_repo.py`
- `backend/app/repositories/resource_repo.py`
- `backend/app/repositories/dag_task_repo.py`

#### Services (Business logic)
- `backend/app/services/pipeline_service.py`
- `backend/app/services/airflow_service.py`
- `backend/app/services/airflow_sync_service.py`
- `backend/app/services/catalog_sync_service.py`
- `backend/app/services/schema_matrix_service.py`
- `backend/app/services/ai_service.py`
- `backend/app/services/consumer_service.py`
- `backend/app/services/usage_service.py`
- `backend/app/services/resource_service.py`

#### Integrations (External clients)
- `backend/app/integrations/airflow_client.py`
- `backend/app/integrations/iceberg_client.py`
- `backend/app/integrations/llm_client.py`

#### Tasks (Background jobs)
- `backend/app/tasks/scheduler.py`
- `backend/app/tasks/airflow_poll_task.py`
- `backend/app/tasks/airflow_sync_task.py`
- `backend/app/tasks/catalog_sync_task.py`
- `backend/app/tasks/seed_usage_data.py`

#### Parsers
- `backend/app/parsers/dagger_catalog.py`

### Backend — Migrations (9 files)
- `backend/alembic/versions/001_initial_schema.py` through `009_add_dag_tasks.py`

### Frontend — Source Code (65+ files)
#### Core
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/vite-env.d.ts`

#### API Layer
- `frontend/src/api/client.ts`
- `frontend/src/api/pipelines.ts`
- `frontend/src/api/lineage.ts`
- `frontend/src/api/airflow.ts`
- `frontend/src/api/schema-matrix.ts`
- `frontend/src/api/ai.ts`
- `frontend/src/api/topology.ts`
- `frontend/src/api/usage.ts`
- `frontend/src/api/consumers.ts`
- `frontend/src/api/resources.ts`

#### Types
- `frontend/src/types/pipeline.ts`
- `frontend/src/types/lineage.ts`
- `frontend/src/types/airflow.ts`
- `frontend/src/types/schema-matrix.ts`
- `frontend/src/types/ai.ts`
- `frontend/src/types/topology.ts`
- `frontend/src/types/consumer.ts`
- `frontend/src/types/usage.ts`
- `frontend/src/types/resources.ts`

#### Hooks (TanStack Query)
- `frontend/src/hooks/use-pipelines.ts`
- `frontend/src/hooks/use-pipeline-detail.ts`
- `frontend/src/hooks/use-lineage.ts`
- `frontend/src/hooks/use-join-suggestions.ts`
- `frontend/src/hooks/use-airflow-status.ts`
- `frontend/src/hooks/use-schema-matrix.ts`
- `frontend/src/hooks/use-ai-chat.ts`
- `frontend/src/hooks/use-topology.ts`
- `frontend/src/hooks/use-pipeline-usage.ts`
- `frontend/src/hooks/use-pipeline-consumers.ts`
- `frontend/src/hooks/use-resource-metrics.ts`
- `frontend/src/hooks/use-sync-pipeline.ts`

#### Stores (Zustand)
- `frontend/src/stores/pipeline-store.ts`
- `frontend/src/stores/navigation-store.ts`
- `frontend/src/stores/ai-store.ts`

#### Components — Layout
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/layout/NavIcon.tsx`

#### Components — Pipeline Registry
- `frontend/src/components/pipeline-registry/PipelineRegistry.tsx`
- `frontend/src/components/pipeline-registry/PipelineListItem.tsx`
- `frontend/src/components/pipeline-registry/PipelineSearch.tsx`

#### Components — Bento Workspace
- `frontend/src/components/bento-workspace/BentoWorkspace.tsx`
- `frontend/src/components/bento-workspace/BentoHeader.tsx`
- `frontend/src/components/bento-workspace/LineageTopology.tsx`
- `frontend/src/components/bento-workspace/MetricsCards.tsx`
- `frontend/src/components/bento-workspace/SchemaViewer.tsx`
- `frontend/src/components/bento-workspace/ConsumeSnippet.tsx`
- `frontend/src/components/bento-workspace/JoinIntelligence.tsx`
- `frontend/src/components/bento-workspace/DagNetworkCard.tsx`
- `frontend/src/components/bento-workspace/UsageCard.tsx`
- `frontend/src/components/bento-workspace/ResourcePerformanceCard.tsx`

#### Components — Schema Matrix
- `frontend/src/components/schema-matrix/SchemaMatrixView.tsx`
- `frontend/src/components/schema-matrix/FieldFrequencyRow.tsx`

#### Components — AI Terminal
- `frontend/src/components/ai-terminal/AIArchitectView.tsx`
- `frontend/src/components/ai-terminal/ChatMessage.tsx`
- `frontend/src/components/ai-terminal/ChatInput.tsx`
- `frontend/src/components/ai-terminal/TypingIndicator.tsx`
- `frontend/src/components/ai-terminal/TerminalHeader.tsx`

#### Components — Shared
- `frontend/src/components/shared/LoadingState.tsx`
- `frontend/src/components/shared/ErrorState.tsx`
- `frontend/src/components/shared/EmptyState.tsx`
- `frontend/src/components/shared/StatusBadge.tsx`
- `frontend/src/components/shared/CopyButton.tsx`

#### Components — UI (shadcn)
- `frontend/src/components/ui/button.tsx`
- `frontend/src/components/ui/input.tsx`
- `frontend/src/components/ui/badge.tsx`
- `frontend/src/components/ui/tooltip.tsx`
- `frontend/src/components/ui/skeleton.tsx`
- `frontend/src/components/ui/card.tsx`
- `frontend/src/components/ui/separator.tsx`
- `frontend/src/components/ui/scroll-area.tsx`
- `frontend/src/components/ui/sonner.tsx`

### Dev — Seed Data & DAGs (90+ files)
- `dev/dags/{backbone_core,perimeter_defense,application_mesh,transit_exchange,heartbeat_probe,noc_sentinel}.py`
- `dev/dags/etl_runner.py`
- `dev/dags/daily/task_configs/*.py` (27 files)
- `dev/dags/daily/resources/*.py` (27 files)
- `dev/dags/hourly/task_configs/*.py` (3 files)
- `dev/dags/hourly/resources/*.py` (3 files)
- `dev/seeds/seed_iceberg.py`
- `dev/seeds/etl_code/dagger/*.py` (30 files)

### Infrastructure & Config
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `backend/pyproject.toml`
- `backend/alembic.ini`
- `frontend/vite.config.ts`
- `frontend/tsconfig.json`
- `frontend/tsconfig.node.json`
- `.env.example`

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
