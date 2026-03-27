# Phase 4: Best Practices & Standards

**PR #4:** Add SSO authentication, team RBAC, admin panel, and pipeline filters
**Date:** 2026-03-12

---

## Framework & Language Findings

### Critical

| ID | Issue |
|---|---|
| BP-01 | **`python-jose` is unmaintained** (last release 2022, known CVEs). Replace with `PyJWT[crypto]>=2.8.0`. API change is small: `jose.jwt` → `jwt`, `JWTError` → `PyJWTError`, JWK handling via `PyJWK` objects. |

### High

| ID | Issue |
|---|---|
| BP-02 | **`datetime.utcnow()` deprecated in Python 3.12** (PEP 587). 7 call sites across `pipeline_repo.py`, `user_repo.py`, `resource_repo.py`. Use `datetime.now(timezone.utc)` instead. |
| BP-03 | **APScheduler version constraint too loose** — `>=3.10.0` could pull in 4.x (completely different API). Pin to `>=3.10.0,<4.0.0`. |
| BP-04 | **SQLAlchemy models use `default=func.now()` instead of `server_default`** — timestamps generated at Python time, not DB time. Clock drift risk. All 15+ timestamp columns affected across new models. |
| BP-05 | **Raw `dict` body in users router** — bypasses FastAPI validation, OpenAPI schema generation, type safety. (Same as CQ-02/SEC-04.) |

### Medium

| ID | Issue |
|---|---|
| BP-06 | `typing.Optional`/`Union` used in ~20 files instead of PEP 604 `X | None` syntax (Python 3.12 native). |
| BP-07 | `useAuth()` fragile coupling — `SsoLogoutButton` calls `useAuth()` which requires OIDC provider. Currently correct (only rendered when SSO enabled) but fragile if refactored. |
| BP-08 | `next-themes` dependency (designed for Next.js) likely unused in an always-dark app. Only referenced by auto-generated shadcn `sonner.tsx`. |
| BP-09 | Pydantic response schemas use `str` for UUID fields — Pydantic v2 has native `uuid.UUID` support with auto JSON serialization. |
| BP-10 | `VisibilityGrantRequest` accepts UUIDs as `str` then manually converts with `uuid.UUID()` in router. Use `uuid.UUID` in schema for automatic validation. |
| BP-11 | TanStack Query `queryFn` calls Zustand `setUser()` as side effect. Anti-pattern — should use `useEffect` to sync. (Same as CQ-13.) |
| BP-12 | `TeamService.get_team_pipelines` full table scan. (Same as CQ-05/PERF-02.) |
| BP-13 | `grant_level` and `user.role` typed as `str` — should be `Literal["viewer", "editor"]` / `Literal["admin", "member", "viewer"]` for compile-time safety. (Same as CQ-07/SEC-06.) |

### Low

| ID | Issue |
|---|---|
| BP-14 | Zustand store could use `devtools` middleware for development debugging. |
| BP-15 | `VisibilityGrantResponse.created_at` is manually converted to ISO string — Pydantic v2 auto-serializes `datetime`. |
| BP-16 | `AdminUser` type duplicates `UserInfo` from auth types. |
| BP-17 | Docker frontend build does not pin Node version. |
| BP-18 | `from_attributes = True` on input-only schemas (harmless but misleading). |
| BP-19 | Keycloak container missing healthcheck in docker-compose. |
| BP-20 | Sidebar hardcodes `http://localhost:8080` for Airflow link — not configurable for production. |

### Positive Observations

The codebase correctly implements: SQLAlchemy 2.0 async patterns (`Mapped[T]`, `select()`, `selectinload()`), FastAPI three-layer DI, Pydantic v2 `model_config` dict-style, React 19 hooks, TanStack Query v5 object-form, Zustand 5 selectors, React `lazy()` + `Suspense` code splitting, OIDC dual-issuer handling.

---

## CI/CD & DevOps Findings

### Critical

| ID | Issue |
|---|---|
| OPS-01 | **No CI/CD pipeline exists.** No `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`. Every merge to `main` is unvalidated — no linting, type checking, test execution, security scanning, or build verification. |
| OPS-02 | **Zero test coverage.** No test framework dependencies, no test files, no test configuration. (Same as TEST-01.) |
| OPS-06 | **10 of 15 routers lack authentication.** (Same as SEC-01, included here for ops completeness.) |

### High

| ID | Issue |
|---|---|
| OPS-03 | **No security scanning** — no SAST (Bandit/Semgrep), SCA (pip-audit/Snyk), or container scanning (Trivy). `python-jose>=3.3.0` is unpinned with CVEs. |
| OPS-04 | **No deployment automation or strategy** — prod compose has 3 services, no blue-green/canary, no orchestrator. Backend runs migrations inline before starting. |
| OPS-05 | **Migrations run at application startup** — `CMD` chains `alembic upgrade head && uvicorn`. Multi-replica race condition on migrations. Failed migration blocks the app entirely. |
| OPS-06-rollback | **No rollback plan** — migrations have `downgrade()` but no documented procedure, no automation, no version tagging. Migration 018 downgrade deletes user-level grants (data-destructive). |
| OPS-08 | **Hardcoded credentials throughout** — docker-compose, realm JSON, .env.example all contain real default passwords. |
| OPS-09 | **Production compose missing critical services** — no Keycloak, no Airflow. No docs on external service requirements. |
| OPS-11 | **No monitoring/observability** — no Prometheus, Sentry, OpenTelemetry. Plain-text logging only. No request ID middleware. No metrics for auth failures, JWKS refreshes, or DB query latency. |
| OPS-14 | **No operational documentation** — no runbooks, no incident response procedures. |

### Medium

| ID | Issue |
|---|---|
| OPS-07 | No `.dockerignore` files — builds copy `.env`, `.venv/`, `node_modules/` into context. |
| OPS-12 | Health check returns 200 even when DB is down (unhealthy in body only). Should return 503. |
| OPS-13 | No Keycloak health monitoring — OIDC init failure is silent, no retry/backoff. |
| OPS-15 | No graceful degradation for SSO outages — Keycloak down = entire app unusable. No runtime SSO toggle. |
| OPS-16 | No environment parity — dev (12 services, SSO=true) vs prod (3 services, SSO unknown). No staging. |
| OPS-17 | Secret management is ENV-file only — no Docker secrets, no vault integration. |
| OPS-18 | Frontend OIDC configuration baked into JS bundle — changing Keycloak URL requires rebuild. |
| OPS-19 | Process-local cache not shared across workers. (Same as PERF-23.) |
| OPS-20 | Containers run without security hardening — no `cap_drop`, `read_only`, or `security_opt`. |
| OPS-21 | Docker images use unpinned tags — `iceberg-rest:latest`, `alpine:latest`. |
| OPS-23 | No rate limiting — AI chat endpoint can be abused for LLM cost amplification. |

### Low

| ID | Issue |
|---|---|
| OPS-10 | Backend port not exposed in prod compose — correctly handled by nginx proxy. (Positive finding.) |
| OPS-22 | Frontend nginx missing `Content-Security-Policy` and `Strict-Transport-Security` headers. |

---

## Counts

- **Best Practices:** 1 Critical, 4 High, 8 Medium, 7 Low = **20 findings**
- **CI/CD & DevOps:** 3 Critical, 8 High, 11 Medium, 2 Low = **24 findings**
