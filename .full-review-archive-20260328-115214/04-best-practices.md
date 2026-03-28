# Phase 4: Best Practices & Standards

## Framework & Language Findings

### High (5)

1. **Auto-commit on all requests including reads** (`backend/app/database.py`) — `get_db_session()` calls `session.commit()` after every request, even GET endpoints. Sends unnecessary COMMIT to PostgreSQL. Fix: check `session.dirty` or `session.new` before committing, or split into read/write session dependencies.

2. **TopologyService and AirflowService bypass FastAPI DI** — Take raw `AsyncSession` and construct repos internally, making them untestable without a real DB and inconsistent with the 15 other services that use proper DI. Fix: inject repos via constructor and add DI factory in `dependencies.py`.

3. **O(n^2) BFS using `list.pop(0)`** — 5 BFS functions in `graph_builder.py` and `bouncer_service.py` use `list.pop(0)` (O(n) per dequeue) instead of `collections.deque.popleft()` (O(1)). Trivial mechanical fix.

4. **IcebergClient sync Spark calls block the async event loop** — `CatalogSyncService.sync_from_catalog()` calls synchronous PySpark/JVM operations without `asyncio.to_thread()`. Fix: wrap with `await asyncio.to_thread(iceberg_client.get_all_schemas)`.

5. **Conflicting Axios response interceptors** — Two separate error interceptors with overlapping retry logic (transient 5xx retry + 401 token refresh). No coordination between them. Fix: consolidate into a single interceptor with clear status-code branching.

### Medium (8)

6. **No `Annotated[Type, Depends()]` usage** — 40+ route handlers use inline `Depends()` in function signatures instead of the modern `Annotated` pattern (recommended since FastAPI 0.95+). More verbose, less reusable.

7. **Custom domain exceptions defined but unused** — 5 exception types in `exceptions.py` exist but services raise `ValueError` or return `None` instead. Dilutes both error handling patterns.

8. **APScheduler 3.x pinned** — APScheduler 4.x has been stable since mid-2024 with native async support and distributed scheduling. Current 3.x uses compatibility wrappers.

9. **No URL-based routing** — All frontend navigation via Zustand `activeTab` state. No bookmarking, deep linking, browser back/forward. Significant UX limitation.

10. **Dev frontend rebuilds entire Docker image on file changes** — `docker-compose.yml` frontend uses `target: production` which rebuilds the full prod nginx image on watch. Should use a dev stage with Vite HMR.

11. **CSP header blocks Keycloak SSO** — nginx `Content-Security-Policy` uses `default-src 'self'` without `connect-src` allowing Keycloak URLs. OIDC discovery and token requests will be blocked.

12. **`datetime.fromisoformat` Z-suffix workaround unnecessary on Python 3.12** — `.replace("Z", "+00:00")` is used in several places, but Python 3.12+ natively supports ISO 8601 "Z" suffix.

13. **AirflowSyncService optional repo parameters with fallback construction** — Creates dual construction paths (DI vs direct). Background tasks bypass DI graph entirely. Fix: dedicated factory for background task construction.

### Low (8)

14. No `StrEnum` or `Literal` for role/status/grant_level constants (string comparison risk)
15. TTLCache uses `Any` type despite Python 3.12 PEP 695 generic syntax available
16. `tsconfig.json` targets ES2020 instead of ES2023+
17. Source maps disabled in production build (harder to debug production issues)
18. PySpark pinned to exact version 3.5.1 (won't receive patch updates)
19. `slowapi` rate limiter is in maintenance mode (consider alternatives)
20. Alembic `env.py` uses star import for model registration
21. `@fontsource-variable/geist` imported but CSS `body` uses Inter font

### Positive Findings

- SQLAlchemy 2.0 `Mapped` types used correctly throughout all 14 models
- TanStack Query v5 patterns are idiomatic (infinite queries, proper cache invalidation, `keepPreviousData`)
- Zustand stores are lean and well-separated (8 stores, single responsibility each)
- Vite config has proper vendor chunk splitting with manual chunks
- Pydantic v2 `model_config` used correctly (no deprecated v1 `class Config`)
- TypeScript strict mode enabled with thorough compiler options
- No deprecated React patterns (`React.FC`, `forwardRef`, Redux)
- Modern Python 3.12 syntax throughout (union types `X | Y`, type parameter syntax)

---

## CI/CD & DevOps Findings

### Critical (3)

1. **No CI/CD Pipeline Exists** — No GitHub Actions, Jenkinsfile, GitLab CI, or any automation. Zero build automation. Tests and lint never enforced. Every code change goes to production untested. The Playwright config even has `forbidOnly: !!process.env.CI` suggesting CI was intended but never set up.

2. **No Automated Test Enforcement** — 45+ test files exist across backend and frontend but are never triggered automatically. They may have drifted into a broken state.

3. **No Deployment Strategy** — Manual `docker compose up -d`. No blue-green, no canary, no rolling updates. Every deployment causes downtime. Migration runs inline with app startup (crash-loops on failure). No rollback mechanism.

### High (8)

4. **No Linting or Type-Checking Gates** — Ruff configured in `pyproject.toml`, TypeScript strict mode enabled, but neither enforced in automation.

5. **No Container Image Registry** — Images built locally with no versioning, no tags, no audit trail. Cannot roll back to previous version.

6. **Migration Runs Inline with Application Startup** — `alembic upgrade head && exec uvicorn`. Long or failed migrations crash the container in a restart loop. Multiple replicas would race on migrations.

7. **No Rollback Capability** — No image tags, no rollback scripts, no procedures. Recovery requires identifying bad commit, rebuilding, redeploying (15-30+ min MTTR).

8. **No Alerting System** — No PagerDuty, OpsGenie, email alerts, or Slack webhooks. Failures discovered only when users report them.

9. **No TLS Termination in Production** — nginx listens on port 80 only. JWT tokens transmitted in cleartext. HSTS header is meaningless over HTTP.

10. **No Container Image Scanning** — No Trivy, Grype, or Snyk. Images include python:3.12-slim, node:20-alpine, Java JRE, PySpark — CVEs go undetected.

11. **No Staging Environment** — Only dev and prod. Migrations and features tested only against dev data.

### Medium (6)

12. **Prometheus Metrics Exist but No Collection Stack** — `/api/metrics` emits data into the void. No Prometheus server, no Grafana.

13. **No Centralized Log Aggregation** — Logs written to container stdout with 250MB rotation. No ELK, Loki, or similar.

14. **Health Check Returns 200 Even When Unhealthy** — Database failure returns `{"status": "unhealthy"}` with HTTP 200. Docker healthcheck won't detect it.

15. **Nginx Security Headers Dropped on Cached Assets** — `add_header` in `location /assets/` replaces parent-level CSP/HSTS/X-Frame-Options.

16. **In-Memory Cache Prevents Horizontal Scaling** — Module-level TTLCache; `clear_all()` only clears local process.

17. **PostgreSQL Memory Limit at 1GB with Default Configuration** — Default `shared_buffers` (128MB) with 1GB container limit and heavy queries.

### Low (3)

18. Database backups exist but no tested restore procedure; backups stored on same host
19. No `HEALTHCHECK` in backend Dockerfile (only in compose)
20. Backend Dockerfile copies all files (potential secrets exposure if `.dockerignore` incomplete)

### Positive DevOps Findings

- Infrastructure config is version-controlled (compose files, nginx, Dockerfiles, scripts in git)
- Air-gap deployment kit is well-designed (image export/import scripts, offline compose generation)
- Good config separation between dev and prod (separate compose files, required prod env vars)
- Structured JSON logging with request ID correlation and Docker log rotation
- Multi-stage Docker build with non-root user
- `.gitignore` correctly excludes `.env`, `.env.prod`, `.env.local`

### DevOps Maturity Scorecard

| Area | Maturity | Key Gap |
|------|----------|---------|
| CI/CD Pipeline | **None** | No automation exists |
| Test Automation | **Exists, not enforced** | 45+ test files never run in CI |
| Deployment Strategy | **Manual** | No rollback, no zero-downtime |
| Image Management | **Ad-hoc** | No registry, no versioning |
| Monitoring | **Partial** | Metrics endpoint exists, no collection |
| Logging | **Good** | Structured JSON, request IDs, rotation |
| Alerting | **None** | No alerting system |
| Backups | **Partial** | Automated backup, untested restore |
| Container Security | **Good** | Multi-stage, non-root, .dockerignore |
| Scalability | **Not ready** | In-memory cache, coupled scheduler |
