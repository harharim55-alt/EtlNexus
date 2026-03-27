# Phase 3: Testing & Documentation Review

**PR #4:** Add SSO authentication, team RBAC, admin panel, and pipeline filters
**Date:** 2026-03-12

---

## Test Coverage Findings

### Executive Summary

**This PR introduces zero tests.** No test files, no test framework dependencies, no test configuration, no CI pipeline. The PR adds a complete SSO/OIDC authentication system, RBAC with visibility grants, admin endpoints, and team-scoped filtering — all entirely untested.

### Critical

| ID | Issue | Relates To |
|---|---|---|
| TEST-01 | **No test infrastructure exists.** No pytest, vitest, httpx, or any test framework in backend or frontend dependencies. No `conftest.py`, `vitest.config.ts`, no `tests/` directories. Structurally impossible to run automated tests. | All |
| TEST-02 | **Authentication system untested.** `auth.py` (345 lines) and `oidc_client.py` (267 lines) have zero coverage. No tests for JWT validation, JIT provisioning, `extract_role` allowlist (SEC-02), `extract_groups`, token expiry, default user bypass (SEC-12). | SEC-02, SEC-03, SEC-12 |
| TEST-03 | **Visibility/RBAC authorization untested.** `list_visible` (6 OR conditions, 4 subqueries) has no test coverage. Pipeline detail BOLA (SEC-07) — any authenticated user can access any pipeline by UUID — is undetected. No tests for grant resolution precedence. | SEC-07, PERF-01 |
| TEST-04 | **10 unauthenticated routers undetected.** No parametrized test verifying all endpoints require auth when SSO enabled. SEC-01 (the most severe security finding) would be caught by a single test file. | SEC-01 |

### High

| ID | Issue | Relates To |
|---|---|---|
| TEST-05 | **Admin privilege escalation untested.** No tests for self-demotion, last-admin guard, raw `dict` body on role update. | SEC-08, SEC-04 |
| TEST-06 | **Duplicate grant creation untested.** No tests verifying idempotent grant creation or unique constraint enforcement. | SEC-05, PERF-08 |
| TEST-07 | **Concurrent JIT provisioning race untested.** Two simultaneous first logins for the same SSO user would hit IntegrityError → 500. | PERF-04, PERF-18 |
| TEST-11 | **No integration tests.** No FastAPI TestClient tests for the full request lifecycle (HTTP → auth → service → repo → DB). | All |

### Medium

| ID | Issue | Relates To |
|---|---|---|
| TEST-08 | Grant level validation only tested at router (if at all) — no schema or DB layer tests. | SEC-06 |
| TEST-09 | Client-side `canEditPipeline` diverges from server `can_edit` — no frontend unit tests. | SEC-15 |
| TEST-10 | OIDC init failure → misleading "Unknown signing key" errors — untested. | SEC-03 |
| TEST-12 | No frontend component tests (AuthGuard, AdminView, permissions logic). | — |
| TEST-13 | No performance benchmarks for the visibility query. | PERF-01 |

### Low

| ID | Issue |
|---|---|
| TEST-14 | No migration tests (CHECK constraints, FK cascades, downgrade paths). |

### Recommended Test Priority

1. **TEST-04** — Parametrized auth enforcement for all 15+ endpoints (~20 test cases, catches SEC-01)
2. **TEST-03** — Visibility query + pipeline detail BOLA (~15 test cases, catches SEC-07)
3. **TEST-02** — Auth unit tests: role extraction, token validation, default user (~20 test cases)
4. **TEST-05** — Admin role edge cases (~5 test cases)
5. **TEST-06** — Duplicate grant idempotency (~5 test cases)

**Estimated effort to reach minimum merge threshold: 15-20 engineering hours.**

---

## Documentation Findings

### Critical

| ID | Issue |
|---|---|
| DOC-14 | **No architecture documentation for SSO/RBAC.** The visibility model has 4 grant types × 2 levels + team membership + admin bypass + unassigned fallback. Only discoverable by reading `list_visible` and `can_edit` logic across 3 files. No ADR, no diagram, no design doc. |
| DOC-15 | **CLAUDE.md is stale and inaccurate.** Multiple statements contradict the implementation: references to git-based pipeline discovery (removed), missing Keycloak/OIDC in tech stack, "git-seed" docker service doesn't exist, no mention of SSO/teams/RBAC/visibility. This is the primary AI assistant instruction source. |
| DOC-22 | CLAUDE.md line 37: "Pipeline lineage derived from git repository" — actually from Airflow. |
| DOC-23 | CLAUDE.md line 30: Technology Stack lists "Git (code reading via cloned repos)" — removed. |

### High

| ID | Issue |
|---|---|
| DOC-01 | Default admin backdoor (`sso_enabled=False`) lacks prominent security warning. Only in function docstring, not flagged as production risk. |
| DOC-02 | Silent OIDC init failure path undocumented — no comment about degraded state consequences. |
| DOC-03 | `list_visible` (most complex RBAC query) has single-line docstring. No docs on the 6 visibility conditions, performance implications, or required indexes. |
| DOC-09 | Pipeline router endpoints (most-used API) have no docstrings — OpenAPI shows empty descriptions. |
| DOC-10 | `update_user_role` raw `dict` body → OpenAPI shows unconstrained JSON. No field descriptions. |
| DOC-16 | **No production deployment guide.** Keycloak realm config is dev-only (SSL off, direct access grants). No docs on production SSO setup, credential rotation, split-DNS issuer URLs, or required DB indexes. |
| DOC-17 | Auth layer bypassing service layer (AR-01) is undocumented — no ADR or comment explaining the architectural choice. |
| DOC-20 | **No project-level README.md.** 182 files, no README. |
| DOC-21 | No Keycloak documentation — dev users/passwords/groups only discoverable by reading realm JSON. |
| DOC-24-26 | CLAUDE.md backend architecture section references deleted files (Git client, AST parser, git pull task). |
| DOC-27 | `.env.example` has `DEBUG=true` as default — should be `false` with warning. |
| DOC-31 | **No changelog or migration guide.** 5 new migrations, new Keycloak dependency, 9 new env vars, pipeline visibility behavior change — no upgrade documentation. |

### Medium

| ID | Issue |
|---|---|
| DOC-04 | `has_editor_grant` / `get_grant_level_for_pipeline` duplication undocumented. |
| DOC-05 | Deferred imports in auth.py lack rationale comments. |
| DOC-06 | Inline `can_edit` computation (20 lines in router) has minimal documentation of precedence order. |
| DOC-11 | `grant_level: str` in schema → OpenAPI shows unconstrained string. |
| DOC-12 | No field descriptions on auth schemas (role valid values, etc.). |
| DOC-18 | JIT provisioning rollback behavior (AR-16) undocumented. |
| DOC-19 | Dual-issuer rationale only partially explained (Docker networking scenario). |
| DOC-28 | `SSO_ENABLED` default discrepancy between .env.example (true) and config.py (false) undocumented. |
| DOC-29 | Missing `grant_level` CHECK constraint not mentioned in model docstring. |
| DOC-30 | CLAUDE.md docker compose comment references non-existent "git-seed" service. |
| DOC-32 | Migrations 017+018 immediate modify pattern not explained. |

### Low

| ID | Issue |
|---|---|
| DOC-07 | No JSDoc on frontend auth components (AuthBootstrap, SSOGuard interaction). |
| DOC-08 | `canEditPipeline` lacks comment noting it's a client-side approximation. |
| DOC-13 | No OpenAPI request/response examples on grant schemas. |
| DOC-33 | Migration 019 `server_default="viewer"` behavior for existing rows undocumented. |

---

## Counts

- **Testing:** 4 Critical, 4 High, 5 Medium, 1 Low = **14 findings**
- **Documentation:** 3 Critical (+2 sub), 10 High, 10 Medium, 3 Low = **26 findings** (some overlap with Phase 1-2 findings)
