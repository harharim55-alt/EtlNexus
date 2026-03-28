# Phase 3: Testing & Documentation Review

## Test Coverage Findings

### Critical (4)

1. **No visibility enforcement tests on sub-resource endpoints** — Endpoints like `/lineage`, `/topology`, `/resources`, `/runs`, `/execution-plan` authenticate callers but never check team membership or visibility grants. Integration tests only use admin clients. No test verifies that a non-admin user from team A cannot access team B's pipeline sub-resources via UUID.

2. **Zero tests for `graph_builder.py`** (220 lines, 4 BFS algorithms) — All use `list.pop(0)` instead of `deque.popleft()`. No cycle detection, diamond graph, or empty graph tests. Topology service tests exercise these indirectly but miss critical edge cases.

3. **Join suggestions cache visibility leak untested** — Unit tests call `get_join_suggestions` without visibility parameters. No test verifies that an admin-cached result doesn't leak to a non-admin user.

4. **Metrics endpoint has no auth and no tests** — `/api/metrics` exposes request counts and durations per path to any unauthenticated caller. Zero test coverage.

### High (6)

5. **`visibility_filter.py` (authorization SQL conditions) — zero tests** — This is the single source of truth for RBAC enforcement. Critical SQL logic with 6 OR conditions, entirely untested.

6. **Rate limiting behind proxy — zero tests** — `get_remote_address` sees Docker bridge IP, not real client IP. No test verifies correct IP extraction through X-Forwarded-For.

7. **All 3 background tasks — zero tests** — `airflow_sync_task.py`, `airflow_poll_task.py`, `catalog_sync_task.py` have no test coverage. Lock guards, error handling, and cache invalidation untested.

8. **IcebergClient — zero tests** — Synchronous PySpark calls in async context (event loop blocking) untested. `check_health()` declares `async def` but executes synchronous Spark operations.

9. **LLM and OasisProd integration clients — zero direct tests** — `llm_client.py` and `oasis_prod_client.py` have no test files.

10. **No unauthenticated endpoint access tests** — No test verifies that endpoints correctly reject unauthenticated requests (missing/invalid/expired tokens).

### Medium (6)

11. **0 of 22 frontend hooks tested** — TanStack Query hooks wrapping all API calls have zero test coverage. Error handling, refetch behavior, and cache invalidation all untested.

12. **9 of 96 frontend components tested (9%)** — Only BentoWorkspace, ConsumeSnippet, DagCard, ErrorBoundary, ErrorState, MetricsCards, PipelineListItem, SchemaMatrixView, SchemaViewer have tests. Major components like LineageTopology, AdminView, AuthGuard, PipelineRegistry (core), AI Terminal are untested.

13. **3 of 8 Zustand stores untested** — `ai-store`, `onboarding-store`, `run-selector-store` have no tests.

14. **AirflowSyncService core orchestration logic untested** — The 994-line sync service has tests for helpers (`test_airflow_sync_helpers.py`) but the main `sync_pipelines_from_airflow()` flow, `_persist_pipelines_and_lineage()`, and `_fetch_single_pipeline_metadata()` are untested.

15. **Repository layer has only 1 test file** — `test_base_repo.py` tests the UpsertMixin. None of the 15 specific repositories have dedicated tests.

16. **E2E tests are skeletal** — 3 Playwright spec files exist with ~5 tests total. No login flow, no pipeline interaction, no admin panel coverage.

### Low (3)

17. **No performance/load tests** — No benchmarks for topology rendering, BFS algorithms, or sync cycle duration.
18. **Test fixtures use inline mock data** — No shared fixture library; mock data duplicated across test files.
19. **No contract tests** — Frontend API layer and backend response schemas not validated against each other.

### Test Pyramid Summary

| Layer | Backend | Frontend |
|-------|---------|----------|
| Unit | 25 files (~5K lines) | 11 files |
| Integration | 2 files (~1.25K lines) | 0 |
| E2E | 0 | 3 skeletal files |

---

## Documentation Findings

### Critical (3)

1. **CLAUDE.md says lineage comes from `op_kwargs` but code uses `params`** — `CLAUDE.md:38` says "Lineage `reads_from` edges derived from `needs` task_ids in op_kwargs". Code (`airflow_sync_service.py:126,360`) uses `params.get("needs", [])`. AI assistants will misunderstand sync logic.

2. **README.md dev user credentials are completely wrong** — Lists alice/alice123, bob/bob123, carol/carol123, dave/dave123. Actual Keycloak realm has alice/password, bob/password, charlie/password, diana/password with different team assignments. New developers cannot log in.

3. **In-memory cache single-process assumption not documented** — The TTLCache is process-local. Multi-instance deployments will have inconsistent caches and redundant scheduler jobs. Not documented in PRODUCTION_DEPLOYMENT.md or CLAUDE.md.

### High (5)

4. **ARCHITECTURE.md says JWT library is `python-jose`; code uses `PyJWT`** — Three references to `python-jose` in ARCHITECTURE.md. `pyproject.toml` lists `PyJWT[crypto]>=2.8.0`.

5. **PRODUCTION_DEPLOYMENT.md claims 1-hour JWKS TTL; actual is 6 hours** — `oidc_client.py:25`: `_JWKS_TTL: float = 6 * 3600`. Operations teams will have wrong key rotation expectations.

6. **DEVELOPER_GUIDE.md says pipelines discovered by `etl_name` in `op_kwargs`** — Actual code auto-discovers all tasks by `task_id`. No `etl_name` gate exists. Also references `sensors` table (renamed to `bouncers`). Dependencies come from `params`, not `op_kwargs`.

7. **ARCHITECTURE.md pipeline discovery flowchart has phantom `etl_name` gate** — Decision diamond "etl_name in op_kwargs?" with "No -> skip task" is incorrect. All tasks are auto-discovered.

8. **SSO-disabled mode security implications not prominently warned** — Default `SSO_ENABLED=false` means zero authentication. Not warned in CLAUDE.md or as a critical note in deployment docs.

### Medium (9)

9. **ARCHITECTURE.md references `sensor_cache`/`sensor_topology_cache`** — Code has `bouncer_cache`/`bouncer_topology_cache`.

10. **ARCHITECTURE.md claims single shared lock for sync/poll** — Code has two separate locks (`_sync_lock`, `_poll_lock`). Sync and poll CAN run concurrently.

11. **ARCHITECTURE.md mentions phantom `T+5min catchup_sync` job** — No such job exists in scheduler.py.

12. **ARCHITECTURE.md says 14 routers; there are 17** — Missing bouncers, metrics, users. Lists `sensors.py` which doesn't exist.

13. **Migration counts stale across all docs** — Actual: 31. DEVELOPER_GUIDE says 19, backend README says 29, ARCHITECTURE.md says 19.

14. **No CHANGELOG or migration guide** — 31 migrations with no record of breaking changes.

15. **No ADRs** — Non-obvious decisions (task_id as key, no URL routing, PyJWT choice) lack rationale documentation.

16. **No deep-linking documented as known limitation** — Users cannot bookmark or share URLs to specific views.

17. **Visibility enforcement gap on sub-resources not documented** — Whether UUID opacity is intentional access control is undocumented.

### Low (5)

18. Backend README test file count stale (says 27, actual 25)
19. `.env.example` missing `DummyOperator` in exclude list
20. README.md `ICEBERG_NAMESPACE_PREFIX` shows singular `dagger`, default is multi-namespace
21. `db-backup` service in prod compose not documented
22. Frontend `docker-entrypoint.sh` sed injection not documented

### Positive Documentation Observations

- **ARCHITECTURE.md** is exceptionally thorough with Mermaid diagrams for system context, container architecture, DI flow, auth flow, data flow, and deployment comparison
- **RBAC_ARCHITECTURE.md** documents the visibility model precisely with all 6 OR conditions and DB constraints
- **USER_GUIDE.md** is comprehensive and task-oriented with workflow walkthroughs
- **PRODUCTION_DEPLOYMENT.md** includes security checklist, credential rotation, and scaling notes
- **C4-Documentation/** provides structured architectural views at multiple levels
- Backend code has strong inline documentation with module docstrings, type hints, and implementation comments
- Hand-written OpenAPI spec exists alongside auto-generated one
