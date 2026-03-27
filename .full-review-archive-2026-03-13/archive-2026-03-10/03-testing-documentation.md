# Phase 3: Testing & Documentation Review

## Test Coverage Findings

### Critical

**TEST-C1. Zero Application-Level Tests — 0% Coverage**
- No unit tests, integration tests, E2E tests, or any form of automated testing for backend or frontend.
- No test frameworks installed: no `pytest` in `pyproject.toml`, no `vitest`/`jest` in `package.json`.
- No `tests/` directory, no `conftest.py`, no test configuration.
- No CI/CD pipeline enforcing test execution.
- **~102 source files with 0 test files.**

**TEST-C2. Core Pipeline Discovery Logic Completely Untested**
- **File:** `backend/app/services/airflow_sync_service.py` (581 lines)
- The heart of the application — discovers pipelines, lineage, resources, DAG membership from Airflow.
- Key untested functions: `_parse_writes()`, `_parse_description()`, `_task_id_to_display_name()`, `_unwrap_params()`, `_parse_resource_actual()`, `sync_pipelines_from_airflow()`, `sync_single_pipeline()`.
- A single bug here silently corrupts the entire pipeline catalog.

**TEST-C3. Airflow Integration Client Untested**
- **File:** `backend/app/integrations/airflow_client.py`
- Retry logic, TTL caching, pagination, auth, error handling — all untested.
- Regression here breaks all pipeline discovery and status polling.

**TEST-C4. LLM Prompt Injection — No Security Tests**
- `AIChatMessage.role` is unconstrained `str` — no test verifies system role rejection.
- No tests for message length bounds, history size limits, or catalog context leakage.

### High

**TEST-H1.** `ResourceService._parse_memory_gb()` — converts `"8g"`/`"512m"` to GB floats. Incorrect parsing corrupts capacity bar calculations. Zero tests.
**TEST-H2.** IcebergClient — blocking Spark calls on async event loop. `_validate_identifier()` prevents SQL injection but is untested.
**TEST-H3.** Pipeline search SQL LIKE wildcard injection — `%` and `_` not escaped. No validation tests.
**TEST-H4.** All API endpoints unauthenticated — no auth tests to add when auth is implemented.
**TEST-H5.** All 25+ frontend components — zero rendering, interaction, or accessibility tests. `ResourcePerformanceCard` has 4 utility functions with significant logic.

### Medium

**TEST-M1.** Pydantic schemas — no validation edge case tests. `PipelineListItem.id` is plain `str` not UUID. `AIChatMessage.role` unconstrained.
**TEST-M2.** `DagTaskRepository.delete_stale()` — N+1 delete pattern untested, no performance regression test.
**TEST-M3.** `CatalogSyncService._sync_fields()` — destructive delete+recreate with no transactional safety test.
**TEST-M4.** Frontend Zustand stores — state transitions (e.g., `setSelectedPipelineId` resets `selectedDagId`) untested.
**TEST-M5.** `DaggerCatalog` parser — `filter_dagger_namespaces()` handles both list and string formats, no tests.
**TEST-M6.** `TASK_STATE_MAP` completeness — 8 states mapped, additional Airflow states fall to "unknown" untested.

### Low

**TEST-L1.** Frontend API client — no error handling, timeout, or base URL tests.
**TEST-L2.** Alembic migrations — no upgrade/downgrade round-trip tests (9 migrations).
**TEST-L3.** Docker Compose — no smoke tests for service startup and inter-service communication.

### Recommended Test Infrastructure

**Backend (pytest):**
```toml
[project.optional-dependencies]
test = ["pytest>=8.0", "pytest-asyncio>=0.23", "pytest-cov>=5.0", "httpx>=0.28", "aiosqlite>=0.20"]
```

**Frontend (vitest):**
```json
{"devDependencies": {"vitest": "^3.0.0", "@testing-library/react": "^16.0.0", "jsdom": "^25.0.0", "msw": "^2.7.0"}}
```

### Prioritized Test Roadmap

1. **Week 1 — Pure Unit Tests (~80 tests):** Static methods in `AirflowSyncService`, `ResourceService`, `AirflowService`, `_validate_identifier`, `_TTLCache`, Pydantic schemas, frontend utility functions, Zustand stores.
2. **Week 2 — Service Integration Tests (~33 tests):** Mock repositories, test business logic orchestration.
3. **Week 3 — API Route Tests (~34 tests):** FastAPI TestClient with dependency overrides.
4. **Week 4 — DB Integration Tests (~27 tests):** Async SQLite or test PostgreSQL.
5. **Week 5 — Frontend Component Tests (~34 tests):** Vitest + Testing Library.
6. **Week 6 — E2E & Security Tests (~15 tests):** Playwright E2E, auth enforcement, prompt injection.

---

## Documentation Findings

### Critical

**DOC-C1. CLAUDE.md References Deprecated Git-Based Pipeline Discovery**
- **File:** `CLAUDE.md`
- 6+ stale references: "Git (code reading via cloned repos)" in integrations, "Pipeline lineage is derived by parsing ETL source code from a configurable git repository", "docker compose up... git-seed", "ETL code AST parser" in parsers, "git pull" in background tasks.
- **Fix:** Rewrite Architecture, Technology Stack, and Commands sections. Remove all git references. Document `op_kwargs`-based discovery and log markers.

**DOC-C2. CLAUDE.md Omits Entire Existing Features**
- Missing documentation for: resource/performance tracking, DAG task graph caching, manual pipeline sync endpoint, success rate calculation, task_id field, and the current 9-migration DB schema.
- **Fix:** Add Database Schema section and document all 8 tables and their relationships.

**DOC-C3. README.md Describes Pre-Airflow Architecture**
- References git repository auto-discovery, AST parsing, old business-themed names (Mixpanel, Shopify, Stripe), `GIT_REPO_URL` env vars, claims "6 pipelines" (actual: 30).
- **Fix:** Full README rewrite for current architecture.

### High

**DOC-H1.** No API endpoint reference — only auto-generated FastAPI docs. Dual identifier scheme (UUID vs `etl_name`) undocumented.
**DOC-H2.** Pydantic schemas lack `Field(description=...)` annotations — degrades auto-generated OpenAPI docs quality.
**DOC-H3.** Route handlers have no docstrings — affects Swagger UI operation descriptions.
**DOC-H4.** No Architecture Decision Records (ADRs) for: git-to-Airflow migration, dual identifiers, PySpark for Iceberg, no authentication decision.
**DOC-H5.** Topology and lineage routers bypass documented service layer pattern without explanation.

### Medium

**DOC-M1.** `.env.example` accurate but conflicts with README's stale git variable references.
**DOC-M2.** Startup race condition undocumented — concurrent tasks with ordering requirements.
**DOC-M3.** No documentation on running tests (because no tests exist).
**DOC-M4.** Migration history undocumented — 9 migrations with no changelog.
**DOC-M5.** Production Integration Guide incorrectly describes startup syncs as "blocking" (they are fire-and-forget `asyncio.create_task()`).
**DOC-M6.** No security posture documentation — expected deployment model (internal network, behind proxy) not stated.

### Low

**DOC-L1.** Backend services have good module-level docstrings (positive finding).
**DOC-L2.** Frontend code has minimal inline documentation — complex components lack JSDoc.
**DOC-L3.** Repository methods mostly lack docstrings — `get_success_rates`, `get_run_stats` need explanation.
**DOC-L4.** `project_plan.md` contains raw requirements in conversational format — not labeled as historical artifact.

### Documentation Strengths
- Production Integration Guide (`docs/PRODUCTION_INTEGRATION_GUIDE.md`) is comprehensive and well-structured
- `.env.example` is clean and well-organized
- Backend service module-level docstrings are accurate
- Migration files have good docstrings
- Scheduler documentation explains job ordering well
