# Phase 1: Code Quality & Architecture Review

**PR #4:** Add SSO authentication, team RBAC, admin panel, and pipeline filters
**Date:** 2026-03-12

---

## Code Quality Findings

### Critical

| ID | File | Issue |
|---|---|---|
| CQ-01 | `auth.py:317-345` | `_get_or_create_default_user` does not use `selectinload(team_memberships)`. The SSO-disabled path returns a `User` with unloaded relationships. Downstream access to `user.team_memberships` in `require_team_membership` risks `MissingGreenlet` with async SQLAlchemy. Currently mitigated because the default admin has no teams, but architecturally fragile. |
| CQ-02 | `users.py:38` | `update_user_role` accepts raw `dict` body — bypasses FastAPI validation, OpenAPI docs, and type safety. Only endpoint in the codebase using this pattern. |

### High

| ID | File | Issue |
|---|---|---|
| CQ-03 | `visibility_grant_repo.py:118-215` | `has_editor_grant` and `get_grant_level_for_pipeline` share ~90% identical query-building logic (4 OR-condition patterns). Should extract shared `_build_grant_conditions` helper. |
| CQ-04 | `visibility_grant_repo.py:128-130` | `has_editor_grant` performs a redundant pipeline lookup (`SELECT team_id WHERE id=`) that its caller (`require_team_membership_or_editor_grant`) already has. |
| CQ-05 | `team_service.py:27-30` | `get_team_pipelines` fetches ALL pipelines via `get_all()` then filters in Python. Should use SQL `WHERE team_id =` clause. |
| CQ-06 | `users.py`, `auth.py`, `teams.py` | User-to-response ORM-to-Pydantic conversion duplicated across 3 files with identical `isinstance(ut, UserTeam)` guards. |
| CQ-07 | `schemas/visibility.py:11` | `grant_level: str` accepts any string. Should use `Literal["viewer", "editor"]` for schema-level validation and OpenAPI docs. |

### Medium

| ID | File | Issue |
|---|---|---|
| CQ-08 | `auth.py` (6 locations) | Deferred imports inside function bodies. No actual circular dependency exists — these can be top-level. |
| CQ-09 | `user_repo.py:58,66`, `pipeline_repo.py:87,133` | `datetime.utcnow()` deprecated in Python 3.12. Use `datetime.now(timezone.utc)`. |
| CQ-10 | `pipeline_repo.py:137-225` | `list_visible` generates up to 6 OR conditions with 4 correlated subqueries. No pagination (hardcoded `limit(200)`). Missing composite indexes on `visibility_grants`. |
| CQ-11 | `permissions.ts:7-15` | `canEditPipeline` checks only team membership, ignores editor-level grants. Server-side `can_edit` is authoritative. |
| CQ-12 | `AuthGuard.tsx` | `SSOGuard` calls `useAuth()` which requires OIDC provider. Safe as currently wired, but fragile if reused outside `AuthBootstrap`. |
| CQ-13 | `use-auth.ts:11` | Zustand `setUser()` called inside TanStack Query `queryFn` — side effect during query lifecycle. Should use `useEffect` to sync. |
| CQ-14 | `GrantsPanel.tsx:66-67` | `teamMap` and `pipelineMap` created on every render, not memoized (unlike `UsersPanel` which uses `useMemo`). |
| CQ-15 | `routers/visibility.py:28` | `source_team_name` always returned as `None`. Frontend falls back to `teamMap` lookup. |
| CQ-16 | `models/pipeline.py:23-26` | Denormalized `team` (string) alongside `team_id` (FK). No consistency guarantee on team rename. |

### Low

| ID | File | Issue |
|---|---|---|
| CQ-17 | Sidebar, UsersPanel, TeamsPanel | `UserInitials` component duplicated 3x with minor size differences. |
| CQ-18 | UsersPanel, TeamsPanel, GrantsPanel | Grant level badge styling (editor vs viewer ternary) duplicated 3x. |
| CQ-19 | `AdminView.tsx:18-20` | All 3 admin queries fire eagerly regardless of active sub-tab. |
| CQ-20 | UsersPanel, TeamsPanel | `ROLE_STYLES` map exact duplicate. |
| CQ-21 | `api/auth.ts:9-14` | Manual `Authorization` header duplicates the interceptor. Exists to handle timing race during initial SSO flow. |
| CQ-22 | `topology.py` | Topology endpoints lack `get_current_user` dependency — accessible without auth when SSO enabled. |
| CQ-23 | migrations 017-018 | 017 creates `grantee_team_id` as NOT NULL, 018 immediately alters to nullable. Can be squashed. |
| CQ-24 | `visibility_grant.py:45` | `grant_level` column has no DB-level CHECK constraint. |

---

## Architecture Findings

### High

| ID | Category | Issue |
|---|---|---|
| AR-01 | Component Boundaries | `auth.py` bypasses the service layer — directly instantiates 4 repository classes, contains full user upsert + team sync business logic (`_upsert_user_from_claims`, 66 lines). Should extract `AuthorizationService`. |
| AR-02 | API Design | `PATCH /api/users/{user_id}/role` accepts raw `dict` body (same as CQ-02). |
| AR-03 | Security | OIDC initialization failure silently swallowed. If Keycloak is down at startup, `validate_token()` gives misleading "Unknown signing key" errors instead of indicating the root cause. `_initialized` flag never checked before validation. |

### Medium

| ID | Category | Issue |
|---|---|---|
| AR-04 | Component Boundaries | `PipelineService.list_pipelines` receives full ORM `User` model — couples service to auth context. Should accept `user_id`, `team_ids`, `is_admin` primitives. |
| AR-05 | Dependency Mgmt | Deferred imports in `auth.py` mask the dependency graph (symptom of AR-01). |
| AR-06 | Dependency Mgmt | `AirflowSyncService.__init__` constructs 6 repositories internally from raw session — bypasses DI pattern in `dependencies.py`. |
| AR-07 | Dependency Mgmt | Users router directly instantiates `UserRepository` instead of going through a `UserService`. No `get_user_repo` factory in `dependencies.py`. |
| AR-08 | API Design | `can_edit` authorization logic computed inline in the pipelines router (20 lines) — should be in `PipelineService` or `AuthorizationService`. |
| AR-09 | API Design | No duplicate grant prevention — same grant can be created multiple times. No unique constraint. |
| AR-10 | Data Model | Denormalized `team` string + `team_id` FK on pipelines (same as CQ-16). Stale on team rename. |
| AR-11 | Data Model | `grant_level` String(20) with no CHECK constraint (same as CQ-24). |
| AR-12 | Data Model | `User.role` String(50) with no CHECK constraint. JIT provisioning sets role from JWT claims without validation. |
| AR-13 | Design Patterns | `list_visible` visibility query — up to 6 correlated subqueries without covering indexes (same as CQ-10). |
| AR-14 | Consistency | `pipeline_repo.update_metadata` calls `session.commit()` directly, breaking the convention where repos use `flush()` and `get_db_session` commits. |
| AR-15 | Consistency | No DI factory for `UserRepository` — only repo without one in `dependencies.py`. |
| AR-16 | Consistency | JIT provisioning depends on route handler success to commit. If handler raises, user/team changes roll back. Acceptable but undocumented. |
| AR-17 | Consistency | Admin tab client-side gated only (`isAdmin` check in Sidebar). Backend endpoints enforce auth, but admin UI is visible if frontend state is manipulated. Acceptable defense-in-depth. |
| AR-18 | Security | `canEditPipeline` client-side ignores editor grants (same as CQ-11). Latent bug if used outside BentoHeader flow. |

### Low

| ID | Category | Issue |
|---|---|---|
| AR-19 | Component Boundaries | User-to-response mapping duplicated in `auth.py` and `users.py` (same as CQ-06). |
| AR-20 | API Design | `source_team_name` always `None` in grant responses (same as CQ-15). |
| AR-21 | Data Model | Migrations 017+018 could be squashed (same as CQ-23). |
| AR-22 | Design Patterns | `_is_jwks_stale()` method exists but is never called — dead code. |

---

## Critical Issues for Phase 2 Context

These findings from Phase 1 should inform the Security & Performance review:

1. **OIDC init failure handling (AR-03)** — Security: silent failure masks auth system unavailability. Needs deeper security assessment of what happens when Keycloak is down.
2. **Topology endpoints lack auth (CQ-22)** — Security: unauthenticated access to pipeline topology data.
3. **No duplicate grant prevention (AR-09)** — Security: could allow grant accumulation or confusion attacks.
4. **User.role from JWT without validation (AR-12)** — Security: IdP misconfiguration could inject arbitrary roles.
5. **Visibility query complexity (CQ-10/AR-13)** — Performance: 6 correlated subqueries without covering indexes on every pipeline list request for non-admin users.
6. **Team pipelines full scan (CQ-05)** — Performance: O(N) pipeline fetch for each team detail request.
7. **`update_metadata` direct commit (AR-14)** — Correctness: transaction boundary violation.
8. **Raw dict body on role update (CQ-02/AR-02)** — Security: bypasses request validation.

---

## Counts

- **Code Quality:** 2 Critical, 5 High, 8 Medium, 8 Low = **23 findings**
- **Architecture:** 3 High, 15 Medium, 4 Low = **22 findings**
- **Deduplicated total:** ~30 unique findings (several overlap between CQ and AR)
