# EtlNexus Test Coverage Analysis

**Date:** 2026-03-27
**Scope:** Full-stack ETL Explorer Hub -- backend (Python/FastAPI) and frontend (TypeScript/React)

---

## Executive Summary

The EtlNexus codebase has a solid foundation of **27 backend test files** (~6,200 lines) and **20 frontend test files** across unit, integration, and E2E layers. The test suite covers most service-layer business logic, Pydantic schema validation, and key frontend component rendering states. However, there are **critical gaps** in security-sensitive paths (visibility enforcement on sub-resource endpoints, cache isolation, metrics auth), **zero tests** for several core modules (graph_builder.py, visibility_filter.py, rate limiting, background tasks), and the E2E suite is skeletal. BFS algorithms use `list.pop(0)` instead of `collections.deque` (O(n) per pop), which is a correctness risk under load but is untested for large graphs.

### Test Pyramid Summary

| Layer | Backend | Frontend | Status |
|-------|---------|----------|--------|
| **Unit tests** | 25 files, ~5,000 lines | 11 files (6 utility + 5 store) | Good foundation |
| **Integration tests** | 2 files, ~1,250 lines | 0 | Moderate coverage |
| **E2E tests** | 0 | 3 files (skeletal) | Critical gap |

---

## 1. Critical Findings

### 1.1 No Visibility Enforcement Tests on Sub-Resource Endpoints

**Severity: Critical**

All sub-resource endpoints (`/lineage`, `/topology`, `/resources`, `/runs`, `/execution-plan`) only require `get_current_user` -- they do **not** enforce that a non-admin user has visibility to the parent pipeline. The integration tests for these endpoints (in `test_integration_expanded.py`) only use an `admin_client` or verify 404/200 shapes. No test verifies that a `member_client` accessing another team's pipeline sub-resource is denied.

**What is untested:**
- A member of Team Dagger accessing `/api/pipelines/{vault_pipeline_id}/lineage` should be denied (or filtered)
- A member with no grant accessing `/api/pipelines/{private_pipeline_id}/topology` should be denied
- All 6 sub-resource router files lack team/visibility enforcement tests

**Recommendation:**

```python
# test_integration_visibility.py
class TestSubResourceVisibilityEnforcement:
    async def test_member_cannot_access_other_team_lineage(
        self, member_client: AsyncClient, app
    ):
        """Non-admin user must not access lineage for pipelines outside their team."""
        from app.dependencies import get_lineage_repo, get_pipeline_repo

        other_team_id = uuid.uuid4()
        pipeline = make_pipeline(team="Vault", team_id=other_team_id)

        mock_pipeline_repo = AsyncMock()
        mock_pipeline_repo.get_by_id.return_value = pipeline

        mock_lineage_repo = AsyncMock()
        mock_lineage_repo.get_by_pipeline_id.return_value = {
            "reads_from": [], "writes_to": [],
        }

        app.dependency_overrides[get_pipeline_repo] = lambda: mock_pipeline_repo
        app.dependency_overrides[get_lineage_repo] = lambda: mock_lineage_repo

        response = await member_client.get(
            f"/api/pipelines/{pipeline.id}/lineage"
        )

        # Should be 403 or 404, NOT 200
        assert response.status_code in (403, 404)

    async def test_member_cannot_access_other_team_topology(self, ...):
        """Same pattern for /topology, /resources, /runs, /execution-plan."""
        ...

    async def test_member_cannot_access_other_team_resources(self, ...):
        ...
```

**Note:** This is also a code-level security issue -- the routers themselves may need `require_team_membership` or visibility checks added. Tests should be written to verify the expected security behavior first, then the routers should be fixed if tests fail.

### 1.2 No Tests for graph_builder.py BFS Algorithms

**Severity: Critical**

`backend/app/services/graph_builder.py` contains 4 BFS algorithms (`bfs_find_bouncers`, `bfs_upstream_semantic`, `bfs_bouncer_discovery`, `connect_bouncers_forward`) totaling 220 lines of pure algorithm code. This module has **zero direct tests**. The `topology_service` tests exercise these indirectly through mocked service calls, but do not test edge cases like:

- Cycles in the DAG graph (infinite loop risk)
- Large graphs (performance with `list.pop(0)`)
- Disconnected components
- Empty graph inputs
- Tasks referencing non-existent task_ids in needs/prefers

All 5 usages of `queue.pop(0)` in this file are O(n) operations that should use `collections.deque.popleft()` for O(1). Tests must verify the migration preserves correctness.

**Recommendation:**

```python
# test_graph_builder.py
from collections import deque
from app.services.graph_builder import bfs_upstream_semantic, bfs_find_bouncers

class TestBfsUpstreamSemantic:
    def test_linear_chain_depths(self):
        """A -> B -> C produces correct depths."""
        dt_a = MockDT(task_id="A", needs=["B"], prefers=[])
        dt_b = MockDT(task_id="B", needs=["C"], prefers=[])
        dt_c = MockDT(task_id="C", needs=[], prefers=[])
        tid_map = {"A": dt_a, "B": dt_b, "C": dt_c}

        visited, edges = bfs_upstream_semantic("A", tid_map)
        assert visited == {"A": 0, "B": 1, "C": 2}
        assert len(edges) == 2

    def test_diamond_graph_no_duplicates(self):
        """A needs B,C; B needs D; C needs D -- D visited once."""
        ...

    def test_cycle_terminates(self):
        """A needs B, B needs A -- must not infinite loop."""
        dt_a = MockDT(task_id="A", needs=["B"], prefers=[])
        dt_b = MockDT(task_id="B", needs=["A"], prefers=[])
        visited, edges = bfs_upstream_semantic("A", {"A": dt_a, "B": dt_b})
        assert "A" in visited and "B" in visited  # terminates

    def test_missing_task_id_in_needs_skipped(self):
        """A needs NonExistent -- gracefully skipped."""
        dt_a = MockDT(task_id="A", needs=["NonExistent"], prefers=[])
        visited, edges = bfs_upstream_semantic("A", {"A": dt_a})
        assert visited == {"A": 0, "NonExistent": 1}
```

### 1.3 Join Suggestions Cache Visibility Leak

**Severity: Critical**

`test_pipeline_service.py::TestGetJoinSuggestions` tests that join suggestions are returned and cached. However, there is **no test** verifying that a cached result from an admin query does not leak to a non-admin user who should not see certain pipelines in the suggestions. The `get_join_suggestions` method in `pipeline_service.py` accepts visibility parameters (`user_id`, `user_team_ids`, `is_admin`, `grant_repo`) as shown in the router, but the unit test calls it without these parameters.

**Recommendation:**

```python
class TestGetJoinSuggestionsCacheIsolation:
    async def test_admin_cache_does_not_leak_to_non_admin(
        self, service, pipeline_repo
    ):
        """Cache key must incorporate user visibility context."""
        from app.cache import join_suggestions_cache
        join_suggestions_cache.clear()

        pipeline = make_pipeline(name="P1")
        pipeline_repo.get_by_id.return_value = pipeline
        pipeline_repo.get_shared_field_pipelines.return_value = [
            {"pipeline_id": uuid.uuid4(), "pipeline_name": "Secret", "shared_fields": ["ip"]},
        ]

        # Admin request populates cache
        admin_result = await service.get_join_suggestions(
            pipeline.id, user_id=uuid.uuid4(), user_team_ids=set(),
            is_admin=True, grant_repo=AsyncMock(),
        )

        # Non-admin with different teams should NOT hit admin's cache
        pipeline_repo.get_shared_field_pipelines.return_value = []
        non_admin_result = await service.get_join_suggestions(
            pipeline.id, user_id=uuid.uuid4(), user_team_ids={uuid.uuid4()},
            is_admin=False, grant_repo=AsyncMock(),
        )

        assert len(non_admin_result.schema_matches) == 0  # filtered result
        join_suggestions_cache.clear()
```

### 1.4 Metrics Endpoint Has No Auth -- No Test Verifies This

**Severity: Critical**

The `/api/metrics` endpoint in `backend/app/routers/metrics.py` has **no authentication dependency**. It is marked `include_in_schema=False` but is publicly accessible. There are **zero tests** for this endpoint in any test file. Internal metrics (request counts, durations per path) could reveal operational intelligence to unauthenticated attackers.

**Recommendation:**

```python
class TestMetricsEndpoint:
    async def test_metrics_requires_auth(self, client: AsyncClient):
        """Metrics endpoint should require authentication."""
        response = await client.get("/api/metrics")
        # Currently returns 200 -- this test documents the gap.
        # If auth is added, change assertion to 401.
        assert response.status_code == 200  # <-- DOCUMENTS THE VULNERABILITY

    async def test_metrics_returns_prometheus_format(self, admin_client: AsyncClient):
        response = await admin_client.get("/api/metrics")
        assert response.status_code == 200
        assert "http_requests_total" in response.text
```

---

## 2. High-Severity Findings

### 2.1 No Tests for VisibilityFilter (SQL Authorization Logic)

**Severity: High**

`backend/app/repositories/visibility_filter.py` contains the centralized SQL condition builder for grant-based pipeline visibility. This is the **single source of truth** for authorization in list queries and single-pipeline checks. It has zero tests. The SQL conditions for direct pipeline grants, team grants, source-team grants, and batch visibility are entirely untested.

**Recommendation:** Unit test `build_single_pipeline_conditions` with combinations of user grants, team grants, and edge cases (no teams, no grants, both pipeline and source_team grants).

### 2.2 No Tests for Rate Limiting

**Severity: High**

`backend/app/rate_limit.py` configures `slowapi` with `get_remote_address` as the key function. Behind a reverse proxy (Docker/nginx), `get_remote_address` returns the proxy IP, making rate limiting ineffective. No tests verify:
- Rate limiting behavior at the endpoint level
- IP extraction with `X-Forwarded-For` headers
- Rate limit response format (HTTP 429)

**Recommendation:**

```python
class TestRateLimiting:
    async def test_sync_endpoint_rate_limited(self, admin_client: AsyncClient, app):
        """POST /api/pipelines/{id}/sync is rate-limited to 30/min."""
        # Make 31 rapid requests and verify 429 on the 31st
        ...

    async def test_rate_limit_key_uses_forwarded_for(self):
        """When behind a proxy, rate limit should use X-Forwarded-For."""
        ...
```

### 2.3 No Tests for Background Tasks (APScheduler)

**Severity: High**

Three background task modules (`airflow_sync_task.py`, `airflow_poll_task.py`, `catalog_sync_task.py`) and the scheduler (`scheduler.py`) have zero tests. These are critical data pipelines:
- `airflow_sync_task` discovers pipelines, lineage, and team assignments
- `airflow_poll_task` updates run statuses and resource metrics
- `catalog_sync_task` syncs Iceberg schemas

**Recommendation:** Extract pure logic into testable functions. Test the task orchestration with mocked dependencies.

### 2.4 IcebergClient Uses Synchronous PySpark in Async Context

**Severity: High**

`backend/app/integrations/iceberg_client.py` methods (`list_tables_in_namespace`, `get_table_schema`, `get_all_schemas`) are synchronous (use `spark.sql(...).collect()`) but are called from async service code. This blocks the event loop. The `catalog_sync_service.py` calls `iceberg_client.get_all_schemas()` which can take minutes for large catalogs. There are no tests verifying:
- That sync calls are wrapped in `asyncio.to_thread()`
- That the event loop is not blocked during catalog sync
- Input validation (`_validate_identifier`) edge cases

**Recommendation:**

```python
class TestIcebergClientValidation:
    def test_validate_identifier_rejects_sql_injection(self):
        with pytest.raises(ValueError):
            _validate_identifier("table; DROP TABLE--", "test")

    def test_validate_identifier_accepts_valid_names(self):
        assert _validate_identifier("dagger.PortScanCollector", "test") == "dagger.PortScanCollector"

    def test_validate_identifier_rejects_spaces(self):
        with pytest.raises(ValueError):
            _validate_identifier("my table", "test")
```

### 2.5 No Tests for LLM Client or OasisProd Client Integration

**Severity: High**

`backend/app/integrations/llm_client.py` and `oasis_prod_client.py` have zero direct test files. The AI service tests mock the `llm_client` module, and usage service tests mock `oasis_prod_client`, but the clients themselves (HTTP request construction, response parsing, error handling, timeout behavior) are untested.

### 2.6 No Unauthenticated Endpoint Access Tests

**Severity: High**

The integration tests verify that `member_client` gets 403 on admin routes and `admin_client` gets 200 on all routes. But there is **no test** for a fully unauthenticated request (no `get_current_user` override) hitting protected endpoints. The `client` fixture (without auth override) is only used for health check and auth config tests.

**Recommendation:**

```python
class TestUnauthenticatedAccess:
    async def test_pipeline_list_requires_auth(self, client: AsyncClient):
        """Unauthenticated request to /api/pipelines should return 401."""
        # Note: with SSO disabled, the default user is returned.
        # This test should use SSO-enabled settings.
        response = await client.get("/api/pipelines")
        # With SSO disabled, this returns 200 (default user). Document this.
```

---

## 3. Medium-Severity Findings

### 3.1 Frontend Hook Tests Missing (0 of 22 hooks tested)

**Severity: Medium**

None of the 22 TanStack Query hooks (`use-pipelines`, `use-pipeline-detail`, `use-lineage`, `use-topology`, `use-runs`, etc.) have direct tests. Hooks wrap API calls with caching, error handling, and refetch logic. The component tests mock these hooks entirely, so the actual hook behavior (query key construction, stale time, retry logic, error mapping) is untested.

**Recommendation:** Test hooks with `@testing-library/react-hooks` and mock the API layer.

### 3.2 Frontend Component Coverage: 9 of 96 Components Tested (~9%)

**Severity: Medium**

Only 9 of approximately 96 non-UI components have tests:
- **Tested:** BentoWorkspace, ConsumeSnippet, DagCard, ErrorBoundary, ErrorState, MetricsCards, PipelineListItem, SchemaMatrixView, SchemaViewer
- **Untested critical components:** LineageTopology, ResourcePerformanceCard, JoinIntelligence, UsageCard, AdminPanel (user/team/grant management), AITerminal, OnboardingFlow, FilterPanel, TopologyViewer, DocumentationEditor

The admin panel components are security-critical (managing roles, visibility grants) and have zero frontend tests.

### 3.3 No Frontend Store Tests for 3 of 8 Stores

**Severity: Medium**

**Tested stores (5):** auth-store, bouncer-store, date-range-store, navigation-store, pipeline-store
**Untested stores (3):** ai-store, onboarding-store, run-selector-store

### 3.4 AirflowSyncService Main Logic Untested

**Severity: Medium**

`test_airflow_sync_helpers.py` and `test_task_classifier.py` test pure helper functions (parsing, classification). The core `AirflowSyncService.sync_all()` and `sync_single_pipeline()` methods -- which orchestrate pipeline discovery, lineage building, team assignment, and status polling -- have no tests. These methods contain complex conditional logic (bouncer vs ETL vs API classification, multi-DAG deduplication).

### 3.5 Repository Layer Has Only 1 Test File

**Severity: Medium**

16 repository files exist, but only `test_base_repo.py` tests the shared `apply_updates` utility. No repository-specific tests exist for:
- `pipeline_repo.py` -- visibility-aware queries (`list_visible`, `get_shared_field_pipelines`)
- `visibility_grant_repo.py` -- grant condition queries
- `resource_repo.py`, `resource_stats.py` -- aggregate statistics queries
- `lineage_repo.py` -- lineage edge queries

These are tested indirectly through service tests with mocked repos, but the actual SQL query construction and ORM behavior is untested.

### 3.6 E2E Tests Are Skeletal

**Severity: Medium**

Three Playwright E2E spec files exist but contain only 5 tests total:
- `auth.spec.ts`: 2 tests (page loads, health check)
- `pipeline-registry.spec.ts`: 2 tests (list visible, search filters)
- `bento-workspace.spec.ts`: 1 test (click pipeline, with fragile selectors)

No E2E tests for: admin panel, AI terminal, schema matrix, documentation editing, SSO login flow, visibility grant management, pipeline sync trigger.

---

## 4. Low-Severity Findings

### 4.1 BFS Performance: list.pop(0) Instead of deque.popleft()

**Severity: Low** (correctness preserved, O(n^2) vs O(n) for large graphs)

5 locations in `graph_builder.py` and `bouncer_service.py` use `queue.pop(0)` on a Python list. This is O(n) per pop operation, making BFS O(n^2) overall. For the current graph sizes (tens of nodes per DAG), this is not a practical issue, but it should be fixed and tests should verify the deque migration.

### 4.2 Cache TTLCache Stores None as a Valid Value

**Severity: Low**

`test_cache.py` documents that `TTLCache.get("none")` returns `None` for both a stored `None` value and a cache miss. This is a known ambiguity but not tested to distinguish the two cases. If a service caches a `None` result, subsequent calls will treat it as a miss and re-query.

### 4.3 Duplicate Test Coverage

**Severity: Low**

`test_airflow_sync_helpers.py` and `test_task_classifier.py` test many of the same functions (`is_bouncer`, `is_api`, `task_id_to_display_name`, `unwrap_params`, `parse_datetime`, etc.) with overlapping test cases. This is not harmful but indicates the helpers file was written before the classifier was extracted, and the older tests were not removed.

### 4.4 Test Configuration: No Coverage Reporting Configured

**Severity: Low**

`pytest-cov` is listed as a test dependency but no `--cov` configuration exists in `pyproject.toml`. Running `pytest --cov=app` would provide line-level coverage data but is not part of the default test invocation.

**Recommendation:** Add to `[tool.pytest.ini_options]`:
```toml
addopts = "--cov=app --cov-report=term-missing --cov-fail-under=60"
```

### 4.5 Frontend Vitest Config: No Coverage Threshold

**Severity: Low**

Similar to backend, the frontend Vitest setup (`setup.ts`) only imports jest-dom matchers. No coverage configuration or thresholds are set.

---

## 5. Test Quality Assessment

### 5.1 Strengths

- **Behavioral testing pattern:** Tests verify service outputs rather than internal implementation. Service tests mock repos and check response shapes/values.
- **Factory helpers:** `conftest.py` provides `make_user`, `make_team`, `make_pipeline`, `make_grant` factories that make test data creation consistent.
- **Cache isolation:** Most service tests clear caches in `autouse` fixtures, preventing test pollution.
- **Integration test quality:** `test_integration.py` and `test_integration_expanded.py` exercise the full FastAPI request/response cycle with realistic dependency overrides.
- **Frontend store tests:** Zustand store tests directly manipulate state and verify side effects, which is a clean pattern.
- **Error path coverage:** Most service tests include "returns None when not found" and "raises on invalid input" test cases.

### 5.2 Weaknesses

- **Heavy mocking in integration tests:** Integration tests mock service methods via `patch.object`, meaning they test router wiring but not actual service logic under HTTP.
- **No database-level tests:** All repository interactions are mocked. No tests verify SQL queries against a real (or in-memory) database.
- **Frontend component tests are shallow:** Tests mock all hooks and sub-components, only verifying branching logic (loading/error/data states). No interaction tests (click handlers, form submissions).
- **No concurrent access tests:** No tests for race conditions in cache access, concurrent grant creation, or parallel pipeline syncs.
- **No input sanitization tests:** No tests for XSS in pipeline descriptions/documentation, SQL injection in search queries, or oversized payloads.

---

## 6. Prioritized Recommendations

### Immediate (Sprint 1)

1. **Add visibility enforcement tests for sub-resource endpoints** (Finding 1.1)
   - This is both a testing gap AND likely a code-level security bug
   - Test first, then add `require_team_membership` or visibility checks to routers

2. **Add graph_builder.py unit tests** (Finding 1.2)
   - Pure functions, easy to test in isolation
   - Include cycle detection, empty graph, diamond graph test cases
   - Migrate `list.pop(0)` to `deque.popleft()` with tests

3. **Add metrics endpoint auth test** (Finding 1.4)
   - Quick win: add `Depends(get_current_user)` to the metrics router and verify with a test

4. **Add join suggestions cache isolation test** (Finding 1.3)

### Short-term (Sprint 2-3)

5. **Add VisibilityFilter unit tests** (Finding 2.1)
6. **Add rate limiting tests** (Finding 2.2)
7. **Add IcebergClient input validation tests** (Finding 2.4)
8. **Add unauthenticated access tests** (Finding 2.6)
9. **Enable pytest-cov with minimum threshold** (Finding 4.4)

### Medium-term (Sprint 4-6)

10. **Add frontend hook tests** (Finding 3.1)
11. **Add background task tests** (Finding 2.3)
12. **Expand E2E test suite** (Finding 3.6)
13. **Add repository tests with test database** (Finding 3.5)
14. **Add admin panel component tests** (Finding 3.2)

---

## 7. Coverage Map

### Backend: Service Layer Coverage

| Service | Has Tests | Test Quality | Key Gaps |
|---------|-----------|-------------|----------|
| ai_service | Yes | Good | No LLM client error handling |
| airflow_sync_service | Helpers only | Partial | Core sync_all() untested |
| bouncer_service | Yes | Good | BFS uses list.pop(0) |
| catalog_sync_service | Yes | Basic | Only 3 tests |
| consumer_service | Yes | Good | - |
| dag_summary_service | Yes | Good | - |
| graph_builder | **No** | **None** | 4 BFS algorithms untested |
| pipeline_service | Yes | Good | Cache isolation gap |
| resource_service | Yes | Good | - |
| schema_matrix_service | Yes | Good | - |
| team_service | Yes | Basic | Only 3 tests |
| topology_service | Yes | Good | Relies on graph_builder untested |
| usage_service | Yes | Good | - |
| user_auth_service | Yes | Good | - |
| visibility_service | Yes | Good | - |

### Backend: Router Coverage

| Router | Integration Test | Auth Test | Visibility Test |
|--------|-----------------|-----------|-----------------|
| pipelines | Yes | Yes | Partial (detail only) |
| lineage | Yes | No | **No** |
| topology | Yes | No | **No** |
| resources | Yes | No | **No** |
| health | Yes | N/A | N/A |
| auth | Yes | N/A | N/A |
| visibility | Yes | Yes | Yes |
| teams | Yes | Yes | Yes |
| users | Yes | Yes | N/A |
| ai | Yes | No | N/A |
| bouncers | Yes | No | N/A |
| schema_matrix | Yes | No | N/A |
| dag_summary | Yes | No | N/A |
| usage | Yes | No | N/A |
| consumers | Yes | No | N/A |
| metrics | **No** | **No** | N/A |
| airflow | **No** | **No** | N/A |

### Backend: Module Coverage

| Module | Has Tests |
|--------|-----------|
| repositories/visibility_filter.py | **No** |
| rate_limit.py | **No** |
| integrations/iceberg_client.py | **No** (mocked in catalog_sync) |
| integrations/llm_client.py | **No** (mocked in ai_service) |
| integrations/oasis_prod_client.py | **No** (mocked in usage_service) |
| tasks/airflow_sync_task.py | **No** |
| tasks/airflow_poll_task.py | **No** |
| tasks/catalog_sync_task.py | **No** |
| tasks/scheduler.py | **No** |

### Frontend Coverage

| Category | Files | Tested | Coverage |
|----------|-------|--------|----------|
| Components (non-UI) | 96 | 9 | 9% |
| Hooks | 22 | 0 | 0% |
| Stores | 8 | 5 | 63% |
| Utility libs | ~8 | 5 | ~63% |
| E2E specs | - | 3 files (5 tests) | Skeletal |
