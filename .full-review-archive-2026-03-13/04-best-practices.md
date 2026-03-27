# Phase 4: Best Practices & Standards

**Date:** 2026-03-13

---

## Framework & Language Findings

### High (3)

1. **Three coexisting service construction patterns** — PipelineService uses proper DI, AirflowService self-constructs repos, AirflowSyncService uses optional params with fallback, CatalogSyncService bypasses repos entirely
2. **AirflowService/AirflowSyncService overlap** — duplicate static methods, both contain run-history logic
3. **Phantom `slowapi` dependency** — `rate_limit.py` imports slowapi but the package is not in `pyproject.toml`, not imported in `main.py`, and the limiter is never attached to the app. Dead code.

### Medium (6)

4. 5 repositories use SELECT-then-INSERT instead of PostgreSQL `ON CONFLICT`
5. `CatalogSyncService` directly executes SQLAlchemy queries instead of using repos
6. TypedDicts defined but not used as parameter types in repos (still accept untyped `dict`)
7. Health endpoint returns HTTP 200 even when database is down (breaks Docker healthcheck)
8. All 4 integration clients are module-level singletons bypassing DI
9. Production Dockerfile runs uvicorn with single worker

### Strengths

- SQLAlchemy models use modern `Mapped` type annotations
- Frontend is exemplary: TanStack Query v5, Zustand v5, lazy loading, virtual scrolling
- TypeScript config is strict with all modern checks
- Vite build has proper chunk splitting
- Pydantic v2 with `from_attributes` used correctly
- Dependencies are current across both stacks

---

## CI/CD & DevOps Findings

### Critical (1)

1. **No CI/CD pipeline exists** — no GitHub Actions, no test gates, no security scanning, no build automation

### High (4)

2. No deployment strategy — single container, no rollback, inline migrations at startup
3. No monitoring/observability — no Prometheus, no tracing, no alerting, no Sentry
4. No incident response capability — no backups, no runbooks, no rollback procedures
5. Weak secret management — dead rate limiter, in-process cache blocks scaling, no prod config template

### Medium (3)

6. No `.dockerignore` files — build contexts include `.venv/`, `node_modules/`, `.git/`
7. No `.env.prod.example` template
8. Keycloak production config missing (dev config has `sslRequired: "none"`, weak passwords)

### Low (2)

9. No container registry with tagged/versioned images
10. Frontend builds bake environment at build time (no runtime config injection)
