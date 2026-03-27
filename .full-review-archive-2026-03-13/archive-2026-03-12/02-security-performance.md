# Phase 2: Security & Performance Review

**PR #4:** Add SSO authentication, team RBAC, admin panel, and pipeline filters
**Date:** 2026-03-12

---

## Security Findings

### Critical

| ID | CVSS | CWE | Issue |
|---|---|---|---|
| SEC-01 | 9.1 | CWE-862 | **10 of 15 routers lack authentication.** Only `pipelines`, `teams`, `auth`, `users`, `visibility` have `get_current_user` dependency. The remaining 10 (topology, lineage, consumers, resources, sensors, usage, schema_matrix, ai, dag_summary, airflow) accept unauthenticated requests. This renders the entire RBAC/visibility system bypassable — any anonymous caller can access pipeline topology, resource configs, AI terminal, and trigger Airflow sync. |
| SEC-02 | 8.7 | CWE-285 | **Unconstrained role injection from JWT claims.** `extract_role()` in `oidc_client.py` returns whatever string appears in the JWT `realm_access.roles` claim without allowlist validation. No CHECK constraint on `User.role` column. An IdP misconfiguration adding `"admin"` to default role composites would grant every user admin access. |
| SEC-03 | 8.2 | CWE-636 | **Silent OIDC init failure.** When Keycloak is down at startup, `initialize()` logs a warning and returns. `validate_token()` never checks `_initialized` — produces misleading "Unknown signing key" errors. `_is_jwks_stale()` is dead code (never called). No health check, no circuit breaker. |

### High

| ID | CVSS | CWE | Issue |
|---|---|---|---|
| SEC-04 | 7.5 | CWE-20 | **Raw `dict` body on role update** (`users.py:41`). Bypasses FastAPI validation, OpenAPI docs, accepts arbitrarily large payloads. |
| SEC-05 | 6.5 | CWE-799 | **No duplicate grant prevention.** No unique constraint on `visibility_grants`. Unlimited duplicate grants can be created, polluting audit trail and degrading query performance. |
| SEC-06 | 6.3 | CWE-20 | **Unvalidated `grant_level`** at schema layer (`str` not `Literal`) and DB layer (no CHECK constraint). Defense only at router level. |
| SEC-07 | 6.5 | CWE-862 | **Pipeline detail endpoint does not enforce visibility.** `GET /api/pipelines/{id}` authenticates but does not check visibility grants — any authenticated user can access any pipeline by UUID (BOLA). |
| SEC-08 | 7.2 | CWE-269 | **Self-privilege escalation via admin role update.** No self-demotion guard, no last-admin protection. An admin can demote all other admins. |

### Medium

| ID | CVSS | CWE | Issue |
|---|---|---|---|
| SEC-09 | 5.3 | CWE-324 | JWKS cache never proactively refreshed — `_is_jwks_stale()` is dead code. Stale/revoked keys persist indefinitely. |
| SEC-10 | 5.9 | CWE-319 | Keycloak realm config: `sslRequired: "none"`, `directAccessGrantsEnabled: true`. Dev-only but could be misused in production. |
| SEC-11 | 5.4 | CWE-942 | CORS `allow_methods=["*"]`, `allow_headers=["*"]` with `allow_credentials=True`. Overly permissive. |
| SEC-12 | 5.5 | CWE-798 | Default admin user backdoor when `sso_enabled=False` — no credential check, full admin privileges. Defaults to off, dangerous if `.env` misconfigured. |
| SEC-13 | 5.0 | CWE-798 | Hardcoded credentials in `docker-compose.yml`, `etlnexus-realm.json`, `.env.example`. |
| SEC-14 | 5.3 | CWE-1395 | `python-jose` library unmaintained (last release 2021), known CVEs. Recommend migration to `PyJWT`. |

### Low

| ID | CVSS | CWE | Issue |
|---|---|---|---|
| SEC-15 | 3.7 | CWE-863 | Client-side `canEditPipeline` ignores editor grants (server `can_edit` is authoritative). |
| SEC-16 | 3.1 | CWE-489 | `DEBUG=true` default in `.env.example` — may log sensitive data. |
| SEC-17 | 3.1 | CWE-200 | `GET /api/auth/config` exposes issuer URL, client ID (necessary for OIDC SPA, but reveals infrastructure). |
| SEC-18 | 2.1 | CWE-532 | JWT validation failures logged at DEBUG level — invisible for security monitoring. Should be WARNING+. |
| SEC-19 | 3.7 | CWE-307 | No rate limiting on any endpoint including auth. |

---

## Performance Findings

### Critical

| ID | Issue |
|---|---|
| PERF-01 | **`list_visible` visibility query** — up to 6 OR conditions with 4 correlated subqueries against `visibility_grants`. Only single-column indexes exist (`grantee_team_id`, `grantee_user_id`). No composite indexes on `(grantee_team_id, pipeline_id)`, `(grantee_user_id, source_team_id)`, etc. This query runs on every non-admin pipeline list request (the primary UI entry point). Estimated 5-50x slower than indexed equivalent at scale. |

### High

| ID | Issue |
|---|---|
| PERF-02 | **`get_team_pipelines` full table scan** — fetches ALL pipelines via `get_all()` then filters by `team_id` in Python. `ix_pipelines_team_id` index exists but is unused. O(N) instead of O(1). |
| PERF-04 | **JIT provisioning 5+ DB round-trips per request** — every SSO request goes through `_upsert_user_from_claims`: user lookup, upsert, reload with selectinload, per-group team lookups (up to 5), membership diff, flush, expire, re-fetch. Minimum 4 queries, up to 4+2*N_groups. |

### Medium

| ID | Issue |
|---|---|
| PERF-03 | `has_editor_grant` redundant pipeline lookup — re-queries `pipeline.team_id` that the caller already has. 1 extra DB round-trip per PATCH. |
| PERF-05 | Default user re-queried on every non-SSO request — 2 queries per request for a result that never changes. |
| PERF-06 | No pagination on `list_visible` — hardcoded `limit(200)`, no `offset`. Limits scalability. |
| PERF-07 | Pipeline double-fetch on PATCH — auth dependency loads pipeline, then route handler loads it again. |
| PERF-08 | No unique constraint on grants — unbounded duplicate accumulation degrades query performance linearly. |
| PERF-10 | Pipeline list cache only works for admin/no-query — non-admin users (majority with RBAC) always hit DB. |
| PERF-12 | No caching of `get_grant_level_for_pipeline` results — deterministic result queried on every detail view. |
| PERF-13 | Sequential team lookups during SSO login — N serial `get_or_create` calls instead of 1 batch SELECT. |
| PERF-16 | JWKS refresh thundering herd — no `asyncio.Lock`, concurrent unknown-kid requests all fetch independently. |
| PERF-17 | `update_metadata` calls `session.commit()` directly — breaks transaction boundary convention. Non-rollbackable. |
| PERF-20 | `setUser` Zustand setter called inside TanStack Query `queryFn` — causes unnecessary re-render cascades. |
| PERF-23 | Process-local pipeline cache — not shared across workers in multi-worker deployment. |
| PERF-24 | `get_join_suggestions` loads all pipelines with all fields for O(N*M) pairwise comparison in Python. |

### Low

| ID | Issue |
|---|---|
| PERF-09 | JWKS cache never TTL-expires — revoked keys persist. |
| PERF-11 | Sequential team queries during Airflow sync — 31 queries reducible to ~6. |
| PERF-14 | Admin view fires 3 queries eagerly regardless of active sub-tab. |
| PERF-15 | Full pipeline list fetched for admin name lookup — over-fetching. |
| PERF-18 | Race condition on concurrent first SSO login — IntegrityError on unique constraint → 500. |
| PERF-19 | Unmemoized maps in `GrantsPanel` — negligible at current scale. |
| PERF-21 | `oidc-client-ts` (~45KB) always in initial bundle even when SSO disabled. |
| PERF-25 | Connection pool (20+10) may be strained by high per-request query count. |

---

## Critical Issues for Phase 3 Context

1. **SEC-01 (unauthenticated routers)** — Testing must verify all endpoints require auth when SSO enabled.
2. **SEC-07 (BOLA on pipeline detail)** — Testing must cover direct object access by non-authorized users.
3. **SEC-02 (role injection)** — Testing must validate role allowlist enforcement.
4. **SEC-08 (self-demotion)** — Testing must cover admin edge cases (last admin, self-role-change).
5. **SEC-05/PERF-08 (duplicate grants)** — Testing must verify idempotent grant creation.
6. **PERF-01 (visibility query)** — Documentation should describe indexing strategy for visibility_grants.
7. **PERF-04 (JIT provisioning)** — Documentation should describe the per-request overhead and caching strategy.

---

## Counts

- **Security:** 3 Critical, 5 High, 6 Medium, 5 Low = **19 findings**
- **Performance:** 1 Critical, 2 High, 14 Medium, 8 Low = **25 findings**
