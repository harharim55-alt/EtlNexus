# Phase 3: Testing & Documentation Review

**Date:** 2026-03-13

---

## Test Coverage Findings

### Critical (2)

1. **No security integration tests for BOLA fix** — `require_pipeline_visibility` was added but has zero HTTP-level tests proving sub-resource endpoints enforce visibility
2. **No tests for AI chat schema validation** — `Literal["user", "assistant"]` role constraint and `max_length` limits untested

### High (4)

3. 67% of backend services untested (8 of 15: ai, bouncer, resource, dag_summary, catalog_sync, consumer, usage, schema_matrix)
4. 100% of repositories untested against real database
5. All 7 background tasks untested
6. Deactivated user rejection (`is_active=False` → 403) has no test

### Medium (5)

7. No component-level React tests
8. No Zustand store tests
9. No API client interceptor tests (retry, 401 handling)
10. Test pyramid lacks middle integration layer (services + real DB)
11. Frontend test infrastructure may be incomplete (vitest config needs verification)

### Strengths

- 206 backend tests all pass in 1.23s
- Good behavioral test design (input/output focused)
- Clean factory fixtures with `MagicMock(spec=Model)`
- Thorough pure function coverage (54 tests on sync helpers)
- Integration tests use `httpx.ASGITransport` correctly

---

## Documentation Findings

### Critical (1)

1. **Frontend types used `sensor_name`/`sensor_id` while backend returns `bouncer_name`/`bouncer_id`** — **FIXED** during this review (types + 5 component files + 1 test file updated)

### High (3)

2. CLAUDE.md says lineage comes from `op_kwargs`; it actually comes from `params` (needs/prefers)
3. README.md missing entire SSO/Teams/RBAC/Admin/Bouncer/DAG-Summary/Execution-Plan/Documentation features
4. README.md `op_kwargs` code example is inaccurate (category, schedule, needs source)

### Medium (4)

5. README says 9 migrations; there are 29
6. README says tasks share one lock; implementation uses two separate locks
7. `.env` missing variables present in `.env.example`
8. `project_plan.md` references git cloning (removed)

### Low (3)

9. Missing docstrings on bouncer topology BFS and DAG summary builder
10. No CHANGELOG or ADR documents
11. Test file has stale "sensor" references (now "bouncer" references fixed)
