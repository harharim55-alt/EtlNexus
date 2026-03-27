# Changelog

## [Unreleased] — 2026-03-27

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

### Architecture
- Wire TopologyService and AirflowService through FastAPI dependency injection
- Add revision_repo to PipelineService constructor (consistent DI)
- Extract duplicated _limited() semaphore helper to module-level utility
- Only commit database session when dirty (skip no-op commits on read endpoints)
- Return HTTP 503 from health check when database is unreachable
- Replace bare ValueError raises with domain exception types
- Add centralized exception handlers in FastAPI app

### Infrastructure
- Split production backend into separate API and scheduler containers
- Add PostgreSQL memory tuning (shared_buffers, work_mem, effective_cache_size)
- Add SCHEDULER_ENABLED environment variable toggle

### Frontend
- Consolidate conflicting Axios response error interceptors into single handler
- Add hash-based URL routing for deep linking and browser back/forward
- Add React.memo to TopologySvgEdges component

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
