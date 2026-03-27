# EtlNexus Testing Strategy & Coverage Analysis

**Date:** 2026-03-13
**Reviewer:** Claude Opus 4.6 Test Automation Review
**Branch:** `feature/sensor-to-bouncer-rename`
**Scope:** Full codebase -- backend (FastAPI + SQLAlchemy) and frontend (React 19 + TypeScript + Vite)

---

## Executive Summary

The EtlNexus codebase has **206 backend tests across 11 test files** (all passing) and **3 frontend test files** (non-functional -- vitest is not in package.json and `isApiPipeline` is missing from `utils.ts`). The backend test suite covers auth, services, schemas, and integration routing well for the paths it targets, but has significant blind spots in critical areas: **no repository tests against a real database, no tests for 8 of 15 services, zero endpoint tests for 12 of 17 routers, and no security-specific test for the BOLA fix**. The frontend has no working test infrastructure and zero component tests.

**Overall Test Health Score: 4/10**

| Category | Score | Notes |
|----------|-------|-------|
| Backend unit tests | 6/10 | Good depth on covered services; many services untested |
| Backend integration tests | 5/10 | Covers routing/auth; no real DB tests |
| Frontend tests | 1/10 | Broken infrastructure; no component/hook tests |
| Security test coverage | 3/10 | Auth flow tested; BOLA, input validation, prompt injection untested |
| Test pyramid adherence | 4/10 | Heavy on unit mocks; missing middle layer; no E2E |
| Test maintainability | 7/10 | Clean fixtures, good isolation; some mock coupling |
| Edge case coverage | 5/10 | Good for covered paths; missing error/concurrency scenarios |

---

## 1. Test Infrastructure Assessment

### 1.1 Backend (pytest + pytest-asyncio)

**Configuration:** `/home/ip04/EtlNexus/backend/pyproject.toml`
- `asyncio_mode = "auto"` -- correctly avoids needing `@pytest.mark.asyncio` on every test
- `pytest-cov` available but no coverage thresholds configured
- No CI/CD pipeline config found for automated test runs

**Fixture Quality:** `/home/ip04/EtlNexus/backend/tests/conftest.py`
- Good factory functions (`make_user`, `make_team`, `make_pipeline`, `make_grant`)
- Uses `MagicMock(spec=Model)` for type safety
- `mock_session` fixture properly configures async context managers
- No database-backed fixtures (no test database, no transactions)

**Test Distribution (206 tests across 11 files):**
| File | Tests | What it covers |
|------|-------|---------------|
| test_airflow_sync_helpers.py | 54 | Pure functions: parse_writes, parse_description, task_id_to_display_name, etc. |
| test_integration.py | 31 | HTTP routing via httpx.ASGITransport: health, auth config, /me, pipelines, visibility |
| test_schemas.py | 26 | Pydantic schema validation: auth, pipeline, visibility, team DTOs |
| test_pipeline_service.py | 18 | PipelineService: list, update, detail, join suggestions, visibility |
| test_auth.py | 18 | Auth dependencies: get_current_user, require_role, require_team_membership |
| test_oidc_client.py | 16 | OIDC claims extraction: extract_groups, extract_role |
| test_user_auth_service.py | 15 | JIT provisioning: cache key, eviction, upsert, team sync |
| test_visibility_service.py | 10 | Grant CRUD: create, delete, validation |
| test_cache.py | 9 | TTLCache: set/get, expiry, clear_all |
| test_auth_schema_helpers.py | 5 | user_to_response helper |
| test_team_service.py | 4 | Team listing and detail |

### 1.2 Frontend (Vitest -- BROKEN)

**Severity: CRITICAL**

**Finding:** The frontend test infrastructure is non-functional:

1. **Vitest is NOT in `package.json`** -- neither in `dependencies` nor `devDependencies`. While vitest packages exist in `node_modules/.pnpm/`, there is no `"test"` script in package.json and no `vitest.config.ts` file.

2. **`isApiPipeline` does not exist** -- `frontend/src/test/utils.test.ts` imports `isApiPipeline` from `@/lib/utils`, but `utils.ts` only exports `cn()`. This test file will fail at import time.

3. **No vitest configuration** -- No `vitest.config.ts` and no `test` block in `vite.config.ts`.

4. **Stale field names in lineage-utils.test.ts** -- The test uses `sensor_name` and `sensor_id` fields on `TopologyBouncer`, which likely reflect pre-rename naming from the sensor-to-bouncer rename (though the type file still uses `sensor_name`).

**Impact:** All 3 frontend test files are dead code. There are effectively zero frontend tests.

---

## 2. Coverage Analysis: What Is Tested vs. What Is Not

### 2.1 Backend -- Tested Code Paths

| Layer | Tested | Untested |
|-------|--------|----------|
| **Routers (17)** | health, auth, pipelines (partial), visibility (partial) | ai, airflow, bouncers, consumers, dag_summary, lineage, resources, schema_matrix, teams, topology, usage, users |
| **Services (15)** | pipeline_service, visibility_service, user_auth_service, team_service, airflow_sync (helpers only) | ai_service, airflow_service, bouncer_service, catalog_sync_service, consumer_service, dag_summary_service, resource_service, schema_matrix_service, usage_service, airflow_sync (main sync logic) |
| **Repositories (13)** | None directly tested | All 13 repositories have zero direct tests |
| **Integrations (4)** | oidc_client (claims extraction only) | airflow_client (HTTP calls, retry, caching), iceberg_client, llm_client |
| **Auth** | get_current_user, require_role, require_team_membership, require_team_membership_or_editor_grant | Token validation internals, deactivated user path |
| **Tasks (7)** | None | All background tasks: airflow_sync_task, airflow_poll_task, catalog_sync_task, scheduler, seeds |

### 2.2 Backend -- Critical Untested Paths

#### 2.2.1 BOLA/Visibility Enforcement on Sub-Resource Endpoints
**Severity: HIGH**
**Prior Phase Finding:** Security audit identified missing visibility enforcement on sub-resource endpoints (Finding #2).

The `user_can_see_pipeline()` check is tested at the service layer (`test_pipeline_service.py::TestGetPipelineDetailForUser::test_non_visible_pipeline_returns_none`), but there are **no integration tests** verifying that the following endpoints enforce visibility:

- `GET /api/pipelines/{id}/joins` -- has inline visibility check in the router
- `GET /api/pipelines/{id}/resources` -- no visibility check found
- `GET /api/pipelines/{id}/execution-plan` -- no visibility check found
- `GET /api/pipelines/{id}/revisions` -- no visibility check found
- `POST /api/pipelines/{id}/sync` -- uses `require_team_membership` but not visibility grants

**Recommended Test:**
```python
class TestPipelineSubResourceVisibility:
    """Verify that sub-resource endpoints enforce visibility for non-admin users."""

    @pytest.mark.asyncio
    async def test_joins_endpoint_enforces_visibility(self):
        """A member who cannot see a pipeline must get 404 on /joins."""
        member = _make_member_user()
        member.team_memberships = []

        mock_service = AsyncMock()
        mock_grant_repo = AsyncMock()
        mock_grant_repo.user_can_see_pipeline.return_value = False
        mock_pipeline_repo = AsyncMock()
        mock_pipeline_repo.get_by_id.return_value = make_pipeline(
            team="Vault", team_id=uuid.uuid4()
        )

        overrides = {
            get_current_user: lambda: member,
            get_pipeline_service: lambda: mock_service,
            get_visibility_grant_repo: lambda: mock_grant_repo,
            get_pipeline_repo: lambda: mock_pipeline_repo,
        }
        async with _test_client(overrides) as client:
            response = await client.get(f"/api/pipelines/{uuid.uuid4()}/joins")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_resources_endpoint_enforces_visibility(self):
        """Resources endpoint must not leak data for non-visible pipelines."""
        # Similar pattern -- verify 404 when user cannot see the pipeline
        pass

    @pytest.mark.asyncio
    async def test_revisions_endpoint_enforces_visibility(self):
        """Revisions endpoint must not leak data for non-visible pipelines."""
        pass
```

#### 2.2.2 AI Chat Schema Validation (Literal role)
**Severity: MEDIUM**
**Prior Phase Finding:** `AIChatMessage.role` now validates as `Literal["user", "assistant"]`.

No test verifies that invalid roles are rejected by the Pydantic schema.

**Recommended Test:**
```python
class TestAIChatSchema:
    def test_valid_user_role_accepted(self):
        msg = AIChatMessage(role="user", content="hello")
        assert msg.role == "user"

    def test_valid_assistant_role_accepted(self):
        msg = AIChatMessage(role="assistant", content="response")
        assert msg.role == "assistant"

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            AIChatMessage(role="system", content="prompt injection")

    def test_empty_role_rejected(self):
        with pytest.raises(ValidationError):
            AIChatMessage(role="", content="test")

    def test_content_max_length_enforced(self):
        with pytest.raises(ValidationError):
            AIChatMessage(role="user", content="x" * 10_001)

    def test_message_max_length_enforced(self):
        with pytest.raises(ValidationError):
            AIChatRequest(message="x" * 5_001)

    def test_history_max_length_enforced(self):
        history = [AIChatMessage(role="user", content="x")] * 51
        with pytest.raises(ValidationError):
            AIChatRequest(message="hello", history=history)
```

#### 2.2.3 No Tests for `get_task_id_map()` (Replaced `get_all()`)
**Severity: MEDIUM**
**Prior Phase Finding:** `get_all()` was replaced with `get_task_id_map()` across multiple services.

The `get_task_id_map()` method on `PipelineRepository` returns `dict[str, SimpleNamespace]` instead of full ORM objects. This is called by 5 services (`ai_service`, `bouncer_service`, `consumer_service`, `usage_service`) and 1 router (`topology`). No test verifies:
- The method returns the correct shape (`SimpleNamespace` with `.id`, `.name`, `.task_id`, `.status`)
- Services correctly consume the lightweight objects instead of full ORM objects
- Edge case: empty pipeline table

#### 2.2.4 `asyncio.gather` Batching in DagSummaryService
**Severity: MEDIUM**
**Prior Phase Finding:** DagSummary queries now use `asyncio.gather` for batching.

`DagSummaryService._build_dag_summaries()` performs N sequential `resource_repo.get_dag_run_stats()` and `resource_repo.get_latest_runs_by_dag()` calls inside a loop (one per DAG). Despite the mention of `asyncio.gather`, this service has **zero tests**. The N+1 query pattern and potential for partial failures in gathered coroutines need test coverage.

#### 2.2.5 BouncerService BFS Topology Traversal
**Severity: MEDIUM**

`BouncerService.get_bouncer_topology()` implements a BFS graph traversal algorithm with union/intersection modes. This complex algorithmic logic has **zero tests**. Edge cases that need testing:
- Cycles in the DAG task graph (should not infinite-loop)
- Intersection mode with non-overlapping bouncer reachability sets (should return empty)
- Bouncer with no downstream tasks
- Deduplication by `task_id` across multiple DAGs

#### 2.2.6 ResourceService._parse_memory_gb
**Severity: LOW**

A pure function that parses `"8g"` -> `8.0`, `"512m"` -> `0.5`. No tests despite being used for capacity bar calculations. Edge cases: invalid strings, no unit suffix, terabyte unit.

**Recommended Test:**
```python
class TestParseMemoryGb:
    def test_gigabytes(self):
        assert ResourceService._parse_memory_gb("8g") == 8.0

    def test_megabytes(self):
        assert ResourceService._parse_memory_gb("512m") == 0.5

    def test_terabytes(self):
        assert ResourceService._parse_memory_gb("2t") == 2048.0

    def test_no_unit_defaults_to_gb(self):
        assert ResourceService._parse_memory_gb("4") == 4.0

    def test_invalid_string_returns_zero(self):
        assert ResourceService._parse_memory_gb("invalid") == 0

    def test_float_value(self):
        assert ResourceService._parse_memory_gb("1.5g") == 1.5

    def test_whitespace_handling(self):
        assert ResourceService._parse_memory_gb("  8g  ") == 8.0
```

### 2.3 Frontend -- Untested Code Paths

**Everything is untested.** The 3 test files are non-functional. Priority areas that need tests:

| Priority | Area | Why |
|----------|------|-----|
| **P0** | Fix test infrastructure | Vitest + test script + config must work before anything else |
| **P1** | `permissions.ts` (`isAdmin`) | Security-critical logic: role checks |
| **P1** | Auth hooks (`use-auth.ts`) | Token handling, user state management |
| **P1** | API client error handling (`client.ts`) | 401/403 redirect behavior |
| **P2** | Zustand stores | State management correctness |
| **P2** | Utility functions | `status-config.ts`, lineage utils |
| **P3** | Component rendering | Major views: PipelineRegistry, BentoWorkspace, AdminView |

---

## 3. Test Quality Assessment

### 3.1 Strengths

1. **Good assertion depth** -- Tests verify both positive and negative paths (e.g., `test_wrong_role_raises_403`, `test_returns_none_when_not_found`). Most tests have 2-4 meaningful assertions.

2. **Behavioral tests, not implementation tests** -- The test suite focuses on input/output behavior rather than mocking internal call sequences. For example, `test_search_query_bypasses_cache` verifies the observable behavior (DB called twice) rather than checking internal cache state.

3. **Clean factory fixtures** -- The `conftest.py` factories (`make_user`, `make_pipeline`, etc.) are well-designed, support keyword customization, and use `MagicMock(spec=Model)` for type safety.

4. **Integration test design** -- `test_integration.py` uses `httpx.ASGITransport` to test the full FastAPI stack (routing, middleware, serialization) without a live server, which is the correct approach for API integration testing.

5. **Cache behavior tested** -- Tests verify cache hit/miss, expiry, and invalidation (pipeline_list_cache, provision cache). The `clear_cache` autouse fixture prevents cross-test contamination.

6. **Edge case coverage on pure functions** -- The `test_airflow_sync_helpers.py` (54 tests) thoroughly covers log parsing, name conversion, team extraction, and parameter unwrapping with boundary inputs (None, empty string, malformed data).

### 3.2 Weaknesses

1. **Heavy reliance on mock objects** -- All service tests use `AsyncMock` for repository dependencies. While this is appropriate for unit tests, there are **zero tests against a real database**, meaning SQL query correctness, transaction behavior, and constraint enforcement are untested.

2. **Integration tests mock the service layer** -- `test_integration.py` overrides `get_pipeline_service` with a mock, which means the integration tests do not exercise the actual service logic. They test routing + serialization, not the full request-to-database path.

3. **No negative path tests for data integrity** -- No tests verify database constraint violations (e.g., duplicate grants, referential integrity on `pipeline_id`/`team_id`).

4. **Missing `@pytest.mark.asyncio` but works due to `asyncio_mode = "auto"`** -- This is correct configuration, but 4 test classes in `test_auth.py` don't use `@pytest.mark.asyncio` explicitly. Works fine with `auto` mode but would break if config changed.

### 3.3 Mock Quality Issues

**Severity: MEDIUM**

In `test_visibility_service.py::TestListGrants`:
```python
async def test_delegates_to_repo(self, service, grant_repo):
    grants = [make_grant(), make_grant()]
    grant_repo.get_all.return_value = grants
    result = await service.list_grants()
    assert len(result) == 2
```

The `list_grants()` service method actually returns a tuple `(grants, total)`, but the test mocks `get_all` returning a list. This test verifies mock wiring, not actual behavior. The assertion `len(result) == 2` would pass whether result is a list of 2 or a tuple of 2 elements.

---

## 4. Test Pyramid Analysis

```
                    /\
                   /  \          E2E Tests: 0
                  /    \         (No Playwright, Cypress, or similar)
                 /------\
                /        \       Integration Tests: ~31
               /  httpx   \      (HTTP routing + auth + serialization)
              /  ASGITrans \     (No real DB, services mocked)
             /------------\
            /              \     Unit Tests: ~175
           / Pure functions  \   (Services with mocked repos,
          / Schema validation \   schema validation, cache,
         / Auth dependencies   \  auth deps, OIDC extraction)
        /____________________\
```

**Verdict: Inverted pyramid with missing middle**

The test suite is dominated by unit tests with mocked dependencies (good) but lacks:
- **True integration tests** that exercise the service + repository + database stack
- **Any E2E tests** that verify complete user flows
- **Any frontend tests** at all

The existing "integration tests" in `test_integration.py` are actually **API contract tests** -- they verify routing, auth enforcement, and response shapes, but mock away the business logic.

### Recommendation: Add a Real Database Test Layer

```python
# backend/tests/conftest_db.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

TEST_DB_URL = "postgresql+asyncpg://test:test@localhost:5432/etlnexus_test"

@pytest.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    async_session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()  # Clean up after each test
```

---

## 5. Security Test Gaps

### 5.1 CRITICAL: No Tests for Prompt Injection Protection
**Security Audit Finding #3:** AI chat forwards unsanitized user input to LLM.

The `AIChatMessage.role` is now validated as `Literal["user", "assistant"]`, which prevents role injection. However, there are zero tests for:
- System prompt injection via message content
- History manipulation (e.g., injecting assistant messages that override instructions)
- Content length limits enforcement
- The chat endpoint itself (POST /api/ai/chat has no integration test)

### 5.2 HIGH: No Integration Test for BOLA Fix
**Security Audit Finding #2:** Missing visibility enforcement on sub-resource endpoints.

The `user_can_see_pipeline()` call is tested at the unit level in `test_pipeline_service.py`, but there is no integration test proving that an HTTP request to `/api/pipelines/{id}` actually returns 404 (not 403) for a user who cannot see the pipeline. The security audit specifically flagged sub-resource endpoints (`/joins`, `/resources`, `/execution-plan`) that may lack visibility checks.

### 5.3 MEDIUM: No Test for Deactivated User Rejection

`get_current_user` has a check `if not user.is_active: raise HTTPException(403)`, but no test covers this path. The `test_auth.py` tests do not verify the deactivated user flow.

**Recommended Test:**
```python
@patch("app.auth.oidc_client")
@patch("app.auth.settings")
async def test_deactivated_user_raises_403(self, mock_settings, mock_oidc, mock_session):
    mock_settings.sso_enabled = True
    claims = {"sub": "deactivated-user", "email": "d@test.com"}
    mock_oidc.validate_token = AsyncMock(return_value=claims)

    from app.auth import get_current_user

    user = make_user(sub="deactivated-user")
    user.is_active = False

    with patch("app.auth.UserAuthService") as MockService:
        MockService.return_value.upsert_from_claims = AsyncMock(return_value=user)

        creds = MagicMock()
        creds.credentials = "valid-token"
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=MagicMock(), credentials=creds, session=mock_session,
            )
        assert exc_info.value.status_code == 403
```

### 5.4 MEDIUM: No Tests for Visibility Grant Constraint Validation

The `VisibilityGrant` model has a DB CHECK constraint (one of pipeline_id/source_team_id must be set). The `VisibilityService.create_grant` validates this in Python. However:
- No test verifies the router-level validation in `POST /api/visibility/grants`
- No test verifies the DB constraint catches invalid state if Python validation is bypassed

### 5.5 LOW: No Test for grant_level Enum Values at DB Level

The `grant_level` column accepts "viewer" or "editor". Pydantic validation tests exist (`test_schemas.py::TestVisibilityGrantRequest::test_invalid_grant_level`), and service-level tests exist. But no test verifies the DB CHECK constraint.

---

## 6. Performance Test Gaps

### 6.1 No Load or Stress Tests

There are no load tests (e.g., locust, k6) for any endpoint. Critical paths that should be load-tested:
- `GET /api/pipelines` with 30+ pipelines and multiple concurrent users
- `GET /api/dag-summary` which does N queries per DAG inside a loop
- Airflow sync task which makes 6 concurrent API calls per DAG

### 6.2 No Tests for Cache Effectiveness Under Concurrency

The TTLCache is a simple dict without thread/async safety. No tests verify:
- Cache behavior under concurrent reads/writes
- Whether `pipeline_list_cache.clear()` during a write races with a concurrent read
- Memory growth under sustained use (no max-size eviction in TTLCache)

### 6.3 No Tests for Airflow API Semaphore

The `_AIRFLOW_SEMAPHORE = asyncio.Semaphore(6)` limits concurrent Airflow API calls. No test verifies this actually limits concurrency or prevents connection pool exhaustion.

---

## 7. Stale/Broken Test Issues

### 7.1 CRITICAL: Frontend `utils.test.ts` References Non-Existent Function
**File:** `/home/ip04/EtlNexus/frontend/src/test/utils.test.ts`

The test imports `isApiPipeline` from `@/lib/utils`, but `utils.ts` only exports `cn()`. The function was either removed or moved during a refactor, leaving this test as dead code.

### 7.2 MEDIUM: Frontend `lineage-utils.test.ts` Uses Pre-Rename Field Names
**File:** `/home/ip04/EtlNexus/frontend/src/test/lineage-utils.test.ts`

The `makeBouncer` helper uses `sensor_name`, `sensor_id` fields. While the `TopologyBouncer` type still uses these names (confirming the rename is incomplete in types), this is a maintenance risk. The test references these old names:
```typescript
const makeBouncer = (sensor_name: string, dag_ids: string[]): TopologyBouncer => ({
    sensor_name,
    sensor_id: null,
    // ...
});
```

### 7.3 LOW: `test_airflow_sync_helpers.py` References `TrafficSensor`
**File:** `/home/ip04/EtlNexus/backend/tests/test_airflow_sync_helpers.py`, lines 260, 264

Test data uses `"TrafficSensor"` as a bouncer name, which is a valid test input for a display-name parser. Not a bug, but potentially confusing post-rename.

---

## 8. Missing Test Categories

### 8.1 Contract Tests for API Responses

No tests verify that API response shapes match the TypeScript types defined in `frontend/src/types/`. If a backend schema changes (e.g., adding a required field), the frontend would break silently.

**Recommendation:** Add OpenAPI schema snapshot tests or use a shared schema validation approach.

### 8.2 Migration Tests

No tests verify that Alembic migrations (28 total) apply cleanly on a fresh database or that upgrade + downgrade paths work correctly.

### 8.3 Configuration Validation Tests

No tests verify that `Settings` (pydantic-settings) properly validates environment variables or that missing required vars produce clear error messages.

### 8.4 Error Handler Tests

The custom `http_exception_handler` in `main.py` is partially tested (one test in `test_integration.py`), but the `validation_exception_handler` for Pydantic errors is not tested.

---

## 9. Prioritized Recommendations

### P0 -- Must Fix (Blocking)

| # | Item | Effort | Impact |
|---|------|--------|--------|
| 1 | **Fix frontend test infrastructure**: Add vitest to devDependencies, add `"test": "vitest run"` script, create `vitest.config.ts` | 1h | Unblocks all frontend testing |
| 2 | **Fix or remove `utils.test.ts`**: Either restore `isApiPipeline` to `utils.ts` or delete the test | 15m | Dead code is misleading |
| 3 | **Add AI chat schema validation tests**: Test `Literal["user", "assistant"]` role rejection, content length limits | 1h | Security: prompt injection defense |

### P1 -- High Priority

| # | Item | Effort | Impact |
|---|------|--------|--------|
| 4 | **Add BOLA integration tests**: Verify visibility enforcement on sub-resource endpoints (`/joins`, `/resources`, `/execution-plan`, `/revisions`) | 3h | Security: prevents data leakage |
| 5 | **Add deactivated user test**: Verify `is_active=False` returns 403 | 30m | Security: account deactivation |
| 6 | **Add BouncerService topology tests**: BFS traversal, union/intersection, cycles, empty results | 3h | Algorithmic correctness |
| 7 | **Add ResourceService tests**: `_parse_memory_gb`, `_compute_capacity`, `get_execution_plan` | 2h | Data integrity |
| 8 | **Add AI service tests**: `chat()` with mocked LLM client, `get_join_insight()` edge cases | 2h | Feature correctness |

### P2 -- Medium Priority

| # | Item | Effort | Impact |
|---|------|--------|--------|
| 9 | **Add database integration tests**: Set up test DB with fixtures, test repository queries | 8h | Query correctness |
| 10 | **Add frontend permissions tests**: `isAdmin`, auth guard behavior | 2h | Security |
| 11 | **Add DagSummaryService tests**: Verify summary aggregation logic | 2h | Data accuracy |
| 12 | **Add CatalogSyncService tests**: Verify field upsert logic | 2h | Sync correctness |
| 13 | **Add coverage reporting**: Configure `pytest-cov` with minimum thresholds | 1h | Visibility |
| 14 | **Add POST /api/visibility/grants validation tests**: Verify router-level 400 responses | 1h | API correctness |

### P3 -- Nice to Have

| # | Item | Effort | Impact |
|---|------|--------|--------|
| 15 | Add Airflow client retry/fallback tests | 3h | Resilience |
| 16 | Add frontend component tests (React Testing Library) | 8h | UI correctness |
| 17 | Add E2E tests (Playwright) | 16h | User flow validation |
| 18 | Add load tests (k6/locust) | 4h | Performance baseline |
| 19 | Add API contract/snapshot tests | 4h | Frontend-backend compatibility |
| 20 | Add migration upgrade/downgrade tests | 4h | Schema evolution safety |

---

## 10. Summary of Key Metrics

| Metric | Value |
|--------|-------|
| Backend test files | 11 (+ conftest.py) |
| Backend test count | 206 (all passing) |
| Backend test run time | 1.23s |
| Frontend test files | 3 (all non-functional) |
| Frontend test count | 0 effective |
| Services with tests | 5 of 15 (33%) |
| Routers with integration tests | 5 of 17 (29%) |
| Repositories with tests | 0 of 13 (0%) |
| Integration clients with tests | 1 of 4 (25%, partial) |
| Background tasks with tests | 0 of 7 (0%) |
| Security-critical paths tested | ~40% |
| E2E tests | 0 |
| Coverage enforcement | None |
