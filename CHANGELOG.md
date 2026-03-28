# Changelog

All notable changes to ETL Explorer Hub are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.10.0] — 2026-03-27 — Security, Performance & Architecture Hardening

### Security
- Add visibility enforcement to all pipeline sub-resource endpoints (lineage, topology, resources, runs, execution-plan, revisions, usage, consumers)
- Add authentication requirement to `/api/metrics` endpoint (admin-only)
- Fix join suggestions cache to include user context in cache key (prevents admin→non-admin data leakage)
- Fix rate limiting to use X-Forwarded-For header behind reverse proxy
- Filter AI chat catalog context by user visibility
- Fix nginx security header inheritance on cached asset locations
- Add Keycloak URL to Content-Security-Policy connect-src

### Performance
- Replace O(n) list.pop(0) with O(1) deque.popleft() in all BFS algorithms
- Replace full pipeline table scan in TopologyService with cached lightweight lookup
- Filter bouncer service dag_tasks query by relevant DAG IDs instead of full table scan
- Add exponential backoff to Airflow API client retries
- Cap in-memory metrics dictionaries to prevent unbounded memory growth
- Add lazy eviction to TTLCache to prevent stale entry accumulation
- Wrap IcebergClient sync Spark calls with asyncio.to_thread() to unblock event loop
- Batch sequential pipeline upserts with INSERT ON CONFLICT
- Fix N+1 query in catalog sync service with bulk pipeline load
- Add missing index on pipeline_run_history.dag_id

### Changed
- Wire TopologyService and AirflowService through FastAPI dependency injection
- Add revision_repo to PipelineService constructor (consistent DI)
- Extract duplicated _limited() semaphore helper to module-level utility
- Only commit database session when dirty (skip no-op commits on read endpoints)
- Return HTTP 503 from health check when database is unreachable
- Replace bare ValueError raises with domain exception types
- Add centralized exception handlers in FastAPI app
- Split production backend into separate API and scheduler containers
- Add PostgreSQL memory tuning (shared_buffers, work_mem, effective_cache_size)
- Add SCHEDULER_ENABLED environment variable toggle
- Consolidate conflicting Axios response error interceptors into single handler
- Add hash-based URL routing for deep linking and browser back/forward
- Add React.memo to TopologySvgEdges component
- Dynamic writes_to: remove static SUFFIXES, rely on DataFrame.writeTo() interception
- Execution plan: comprehensive PySpark 3.5.4 node support
- Add data_quality_audit DAG exercising all execution plan node types

### Fixed
- Fix lineage bulk insert error, show running status in topology

### Documentation
- Fix CLAUDE.md: lineage edges use params (not op_kwargs) for needs
- Fix README.md: correct dev SSO credentials to match Keycloak realm
- Fix ARCHITECTURE.md: router count, cache names, lock descriptions, remove phantom etl_name gate
- Add Architecture Decision Records (ADR-001: cache design, ADR-002: visibility model)
- Add security warning about SSO-disabled default behavior
- Document in-memory cache single-process assumption

### Testing
- Add visibility enforcement integration tests
- Add graph_builder BFS algorithm unit tests
- Add scheduler lock guard and retry tests
- Infrastructure improvements: rate limiting, logging, Docker hardening, test coverage

---

## [0.9.0] — 2026-03-26 — etlnexus-hooks & Run Navigation

### Added
- Add etlnexus-hooks auto-instrumentation package for production Spark ETL integration
- Add run-centric navigation for pipeline workspace
- Add centralized date formatting utilities
- Add SparkMetricsCollector mixin in etlnexus-hooks for self-contained metrics collection
- Smart predicate display: collapse CASE/WHEN to IN lists, format SQL
- Smart filter display: semantic grouping with date ranges, IN lists, conditions
- Add e2e tests and backup scripts

### Changed
- Refactor frontend components and backend repositories
- Move SparkMetricsCollector into etlnexus-hooks for self-contained mixin
- Remove duplicate ETL_RESOURCE_ACTUAL from mixin — runner emits richer sparkMeasure version

### Fixed
- Fix ETL marker emission: mixin run() and resource metrics collection
- Fix filter parser: recursively flatten nested AND predicates
- Restore json import in etl_runner, incorporate linter changes

---

## [0.8.0] — 2026-03-23 — Packaging & Stabilization

### Changed
- Package restructuring and dependency organization
- Export fixes and module resolution improvements
- General stabilization and working state improvements

---

## [0.7.0] — 2026-03-15 — Documentation

### Added
- Rewrite README.md with comprehensive architecture overview
- Add backend sub-README with API documentation
- Add frontend sub-README with component guide

---

## [0.6.0] — 2026-03-14 — Polish & Hardening (PRs #8–#10)

### Added
- Date range control across all data views (24h/7d/30d/90d/Custom) (PR #8)
- DateRangePicker component with preset pills and custom datetime popover
- Zustand date-range-store with presets and useDateParams() helper
- Paginated execution plan runs endpoint with RunPicker dropdown
- Comprehensive test suite: 110 new tests (175→285 total) (PR #10)
- Add ruff linting with config, auto-fix 233 style issues (PR #9)
- Add typed exception hierarchy (app/exceptions.py)
- Add request logging middleware (method, path, status, duration)
- Multi-stage backend Dockerfile (builder + runtime)

### Changed
- Run history upsert on re-runs (ON CONFLICT DO UPDATE) — stale data overwritten (PR #8)
- DateRangeParams FastAPI dependency for optional date_from/date_to query params
- Extract log parsers to app/parsers/log_parser.py (PR #9)
- Extract task classifiers to app/services/sync/task_classifier.py
- Extract topology business logic from router to TopologyService (426→60 lines)
- Create shared apply_updates() utility for 6 repository upsert patterns
- Extract magic numbers to config (semaphore, startup retries)
- Comprehensive code review fixes: security, performance, and naming consistency (PR #10)

### Fixed
- Fix silent exception swallowing in iceberg_client (PR #9)
- Fix undefined variable bug in sensor_repo
- Fix name-shadowing bug in airflow_sync_service
- Fix sensor_name → bouncer_name in topology service and tests
- Fix useMemo called after early returns in SchemaMatrixView
- Fix onboarding auto-select to use pipeline_type instead of category
- Fix isApiPipeline to use pipeline_type instead of category
- Fix onboarding pipeline selection and hide ETL-only cards for API pipelines
- Improve API pipeline workspace layout

---

## [0.5.0] — 2026-03-13 — SSO, Onboarding & Features (PRs #4–#7)

### Added
- SSO/OIDC authentication via Keycloak with JWT validation (PR #4)
- User, Team, UserTeam, VisibilityGrant models (migrations 015–019)
- Auth middleware: get_current_user(), require_team_membership_or_editor_grant()
- OIDC client with JWKS caching and token introspection
- Admin panel with Users, Teams, and Grants management tabs
- Pipeline visibility: per-user and per-team grants with viewer/editor levels
- Pipeline filters: multi-dimension filtering by team, DAG network, status
- AuthProvider with react-oidc-context, SSO login page, auth guard
- Sidebar: user avatar, SSO logout, admin nav, Airflow link
- Interactive onboarding overlay with guided tour, section spotlights, and CRT exit animation (PR #5)
- Pipeline documentation revision history with restore capability (PR #6)
- `pipeline_revisions` table for description/documentation change tracking
- Auto-selection fallbacks: all-API pipeline handling and smart bouncer pairing
- pipeline_type field on API response for correct registry display (PR #7)
- Bouncer volume seeding on startup

### Changed
- Rename sensors to bouncers across entire codebase (PR #7)
- PascalCase rename of all 30 ETL code files, task configs, and resources
- Catalog sync switched from name-based to task_id-based matching
- BentoHeader: inline description editing gated by can_edit permission
- Wrap pipeline, user, and grant list endpoints with {items, total} pagination responses
- Convert pipelines, schema-matrix, admin hooks to useInfiniteQuery with infinite scroll
- Add GIN trigram indexes (migration 025) for pipeline search performance

### Fixed
- Fix JWT validation to handle Keycloak azp claim (access tokens lack aud)
- Make all datetime columns timezone-aware (migrations 023–026)
- Replace user upsert SELECT+INSERT with atomic INSERT ON CONFLICT DO UPDATE (concurrent SSO login race)
- Fix startup sync race condition with Airflow health polling (up to 5 min)
- Airflow sync no longer overwrites user-edited descriptions (description_edited_by_user flag)

### Security
- Sanitize markdown HTML via rehype-sanitize to prevent stored XSS
- Rate-limit on-demand JWKS refresh to prevent DoS via forged kid values
- Restrict team detail/pipelines endpoints to admins and same-team members
- Guard AdminView render behind isAdmin check in frontend
- Escape LIKE wildcards in search queries
- Add granted_by_user_id FK for immutable audit trail on grants
- Add missing indexes on visibility_grants.pipeline_id and source_team_id
- Retry 401 once before logout to handle silent token renewal race

---

## [0.4.0] — 2026-03-11 — Sensors, Execution Plans & Teams

### Added
- Database migrations 010–014: task_group_id, sensors, expanded run history, execution plans, documentation fields
- Backend APIs for sensor monitoring, DAG summary, and execution plans
- Sensor-aware topology with upstream dependency modal
- Task_group_id support and expanded run history with Spark internals
- DAG definitions with sensor tasks, execution plan extraction, and seed data
- Spark execution plan tree with tabbed modal (Formatted/Raw) and type-specific renderers
- Frontend views for sensors, DAG summary, and execution plan tree
- Sidebar navigation for sensors and DAG summary views
- Documentation modal with edit capability in BentoHeader

### Changed
- Enhance pipeline topology, resource metrics, and Airflow sync
- Parse TaskGroup structure from DAG source via Airflow dagSources API for team assignment
- Remove task_group from op_kwargs — team derived purely from structural Airflow TaskGroup

### Fixed
- Fix user grants visibility: add user_id parameter to list_visible() with grantee_user_id subqueries
- Fix snake_case fallback patterns across backend and frontend to handle PascalCase task_ids
- Add sys.exit(0) after spark.stop() in iceberg seed script to prevent JVM thread hang

---

## [0.3.0] — 2026-03-10 — Caching, Performance & Resource Tracking

### Added
- Shared TTL cache layer (30–60s) for pipeline list, schema matrix, and topology
- Resource tracking: resource_configs and run_history tables (migrations 006–008)
- Per-pipeline Spark resource configs synced from op_kwargs
- Run history with actual resource usage parsed from task logs
- Resource metrics API endpoint with cluster capacity limits
- ResourcePerformanceCard: Spark allocation vs actual usage with run history chart
- Sync button in BentoHeader for manual pipeline re-sync from Airflow
- Pipeline registry: category filter, sort options, task_id display
- DB-backed topology via dag_tasks table (migration 009) — zero per-request Airflow API calls
- 5-minute TTL cache on get_all_dags() and get_dag_tasks() in Airflow client

### Changed
- Rename all ETLs and DAGs from business theme to computer network theme (30 ETLs across 6 DAGs)
- Extract shared etl_runner with weight-based sleep simulation and seeded resource usage
- Params fallback for upstream_failed tasks (rendered op_kwargs empty → fall back to task params)
- Parallelize sync_single_pipeline: DB cache lookup + differential check + asyncio.gather (47→6 batches)
- Use persistent connection pool in Airflow client (10 max, 5 keepalive connections)
- Remove DagNetworkCard — info already in topology card; expand UsageCard to full-width
- Frontend poll intervals aligned to 5 min to match cache TTL

### Fixed
- Fix race condition in concurrent startup and scheduled tasks (sequential sync→poll, asyncio.Lock guard)
- Fix N+1 query in FieldFrequencyRepository with single-pass subquery filter
- Fix usage type detection with case-insensitive category check
- Add self-read count rows to seed data

### Performance
- Persistent Airflow HTTP connection pool replaces per-request clients
- Parallel pipeline sync reduces wall-clock from ~47 sequential round-trips to ~6 parallel batches

---

## [0.2.0] — 2026-03-09 — Airflow Integration (PRs #2–#3)

### Changed
- Replace git-based pipeline discovery with Airflow-sourced metadata and log-based lineage (PR #2)
- Lineage reads_from edges derived from `needs` task_ids in params
- Lineage writes_to edges parsed from task logs (ETL_WRITES_TO: markers)
- APIs excluded from writes_to edges
- Rewrite consumers & usage to use Airflow API with name-based keys (PR #3)
- Migration 005: pipeline_usages.pipeline_id → etl_name (string key)
- Usage/consumer endpoints now take ETL name: /api/usage/{etl_name}
- Frontend UsageCard shows name, network (DAG), and reads per consumer

### Performance
- Lazy-load BentoWorkspace, SchemaMatrixView, and AIArchitectView with React.lazy + Suspense
- Vite manual chunks to split vendor libraries into cache-stable bundles
- Switch docker-compose frontend to production build (nginx) for minification
- Increase gzip compression level, cache fonts and static assets for 1 year

---

## [0.1.0] — 2026-03-08 — Initial Release (PR #1)

### Added
- Full-stack ETL Explorer Hub: FastAPI backend with async SQLAlchemy, React frontend with bento-box workspace
- Pipeline registry with searchable master list
- Bento workspace with pipeline topology/lineage, schema viewer, consume snippets, join intelligence
- Global schema matrix for cross-pipeline field frequency
- AI architect terminal with natural language queries against catalog
- PySpark Iceberg catalog integration for schema sync
- Airflow DAG status polling and pipeline discovery
- Docker Compose dev environment with local Airflow, Iceberg REST catalog, and seeded data
- Comprehensive README with architecture docs and quick start guide

### Changed
- Harden backend, Docker, and nginx for production deployment (PR #1)
- Startup sync tasks run as background asyncio tasks (Docker health checks no longer timeout)
- Replace curl-based health check with Python urllib (curl not in python:3.12-slim)
- Health endpoint executes SELECT 1 for real DB connectivity check
- DB connection pooling (pool_size=20, pool_pre_ping, pool_recycle=3600)
- Airflow client paginates DAG listing (handles 100+ DAGs)
- Backend Dockerfile: non-root user, pinned uv, exec for signal forwarding, frozen lockfile
- Nginx: gzip, security headers, asset caching, proxy_read_timeout
- docker-compose.prod.yml: memory limits, log rotation, required POSTGRES_PASSWORD, start_period
