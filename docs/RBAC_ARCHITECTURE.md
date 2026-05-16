# RBAC & Visibility Architecture

How EtlNexus enforces who can see and edit which pipelines.

---

## Overview

EtlNexus uses a team-scoped visibility model layered on top of three global roles. The system combines:

- **Global roles** (admin / member / viewer) from Keycloak `realm_access.roles`
- **Team membership** synced from Keycloak groups on every login
- **Visibility grants** created by admins to share pipelines across team boundaries

---

## Global Roles

| Role | Pipeline visibility | Edit pipelines | Manage grants | Manage users |
|------|-------------------|----------------|--------------|--------------|
| `admin` | All pipelines (bypasses visibility filter) | All pipelines | Yes | Yes |
| `member` | Own teams + unassigned + granted | Own teams + editor grants | No | No |
| `viewer` | Own teams + unassigned + granted | No | No | No |

Roles are validated at three layers:
1. **JWT extraction** — `extract_role()` validates against allowlist `{"admin", "member", "viewer"}`, defaulting to `"member"`
2. **Database CHECK constraint** — `ck_users_role` enforces `role IN ('admin', 'member', 'viewer')`
3. **Pydantic schema** — `RoleUpdateRequest.role` typed as `Literal["admin", "member", "viewer"]`

---

## Pipeline Visibility

The `list_visible()` query in `PipelineRepository` determines which pipelines appear in a user's registry. For non-admin users, a pipeline is visible if **any** of these conditions is true:

### Condition 1: Unassigned pipeline
```
pipeline.team_id IS NULL
```
Pipelines not yet assigned to any team are visible to everyone.

### Condition 2: Team ownership
```
pipeline.team_id IN user_team_ids
```
The user belongs to the team that owns the pipeline.

### Condition 3: Pipeline grant to user's team
```
EXISTS (visibility_grants WHERE
    grantee_team_id IN user_team_ids
    AND pipeline_id = pipeline.id)
```
An admin granted one of the user's teams access to this specific pipeline.

### Condition 4: Source-team grant to user's team
```
pipeline.team_id IN (SELECT source_team_id FROM visibility_grants WHERE
    grantee_team_id IN user_team_ids
    AND source_team_id IS NOT NULL)
```
An admin granted one of the user's teams access to **all** pipelines owned by the pipeline's team.

### Condition 5: Pipeline grant to specific user
```
EXISTS (visibility_grants WHERE
    grantee_user_id = user.id
    AND pipeline_id = pipeline.id)
```

### Condition 6: Source-team grant to specific user
```
EXISTS (visibility_grants WHERE
    grantee_user_id = user.id
    AND source_team_id = pipeline.team_id)
```

These 6 conditions are OR'd together. Admins bypass the filter entirely and see all pipelines.

The same logic is mirrored in `user_can_see_pipeline()` for single-pipeline detail requests (returns 404, not 403, to prevent UUID enumeration).

---

## Visibility Grants

### Structure

Each grant has two dimensions:

**Target** (what is being shared) — exactly one must be set:
- `pipeline_id` — share a specific pipeline
- `source_team_id` — share all pipelines owned by a team

**Recipient** (who receives access) — exactly one must be set:
- `grantee_team_id` — grant to an entire team
- `grantee_user_id` — grant to a specific user

This produces 4 grant type combinations:

| Target | Recipient | Meaning |
|--------|-----------|---------|
| `pipeline_id` | `grantee_team_id` | Team X can see pipeline P |
| `pipeline_id` | `grantee_user_id` | User Y can see pipeline P |
| `source_team_id` | `grantee_team_id` | Team X can see all of Team Z's pipelines |
| `source_team_id` | `grantee_user_id` | User Y can see all of Team Z's pipelines |

### Grant Levels

Each grant carries a `grant_level`:
- `viewer` — can see the pipeline but not edit
- `editor` — can see and edit the pipeline

Validated by:
- CHECK constraint `ck_visibility_grants_grant_level` on the DB column
- `Literal["viewer", "editor"]` in both `VisibilityGrantRequest` and `VisibilityGrantResponse`

### Constraints

- **Mutual exclusivity** — two CHECK constraints enforce exactly-one semantics for target and recipient
- **Uniqueness** — a composite unique constraint `uq_visibility_grant_target_grantee` on `(grantee_team_id, grantee_user_id, pipeline_id, source_team_id)` prevents duplicate grants
- **Upsert behavior** — creating a grant with the same target+recipient combo updates the `grant_level` instead of inserting a duplicate

### Database Indexes

Four partial composite indexes optimize the visibility query:

| Index | Columns | WHERE clause |
|-------|---------|-------------|
| `ix_vg_team_pipeline` | `(grantee_team_id, pipeline_id)` | `pipeline_id IS NOT NULL` |
| `ix_vg_team_source` | `(grantee_team_id, source_team_id)` | `source_team_id IS NOT NULL` |
| `ix_vg_user_pipeline` | `(grantee_user_id, pipeline_id)` | `pipeline_id IS NOT NULL` |
| `ix_vg_user_source` | `(grantee_user_id, source_team_id)` | `source_team_id IS NOT NULL` |

---

## Edit Rights

A user can edit a pipeline (PATCH `/api/pipelines/{id}`) if any of these is true:

1. User has the `admin` role
2. Pipeline is unassigned (`team_id IS NULL`)
3. User is a member of the pipeline's team
4. User has an `editor`-level visibility grant for the pipeline (direct or via source-team grant)

This is enforced by the `require_team_membership_or_editor_grant` dependency, which checks conditions 1-4 and returns HTTP 403 on failure.

The `can_edit` boolean is computed server-side in `GET /api/pipelines/{id}` and included in the response for frontend permission gating.

---

## Admin Safeguards

- **Self-demotion block** — admins cannot change their own role via `PATCH /api/users/{id}/role`
- **Last-admin guard** — the system prevents demoting the last remaining admin user
- **Grant management** — only admins can create, list, or delete visibility grants

---

## JIT User Provisioning

On every SSO login, the `UserAuthService.upsert_from_claims()` method:

1. Extracts `sub`, `email`, `display_name`, `role`, and `groups` from JWT claims
2. Upserts the user row (keyed by `sub`)
3. Reconciles team memberships — adds new, removes stale
4. Returns the user with `team_memberships` eagerly loaded

A 30-second in-memory cache (keyed by `sub` + claims hash) avoids repeating the full provisioning flow when the same user hits multiple endpoints within a short window.

---

## Team Assignment

Pipelines are assigned to teams automatically during Airflow sync. The sync service parses TaskGroup names from DAG source code and prefix-matches against known team names:

- `DaggerCollection` → team `Dagger`
- `VaultAnalysis` → team `Vault`

Teams that appear in Keycloak groups are created with `source="sso"`. The five teams are: **Dagger**, **Vault**, **Prism**, **Relay**, **Oasis**.
