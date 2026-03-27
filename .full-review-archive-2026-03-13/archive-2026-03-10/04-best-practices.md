# Phase 4: Best Practices & Standards

## Framework & Language Findings

### High

**BP-H1. `datetime.utcnow()` Deprecated Since Python 3.12**
- **Files:** `backend/app/repositories/pipeline_repo.py:86`, `backend/app/repositories/resource_repo.py:117`
- Returns naive datetime. Rest of codebase uses `datetime.now(timezone.utc)`.
- **Fix:** Replace with `datetime.now(timezone.utc)` and standardize a `utc_now_naive()` utility.

**BP-H2. New httpx.AsyncClient Per Request (No Connection Pooling)**
- **Files:** `backend/app/integrations/airflow_client.py:53,145`, `backend/app/integrations/llm_client.py:50`
- Every API call creates/destroys a client. Hundreds of connections during sync.
- **Fix:** Persistent `AsyncClient` with connection pool limits; close during shutdown.

**BP-H3. Serial Airflow API Calls (No asyncio.gather)**
- **Files:** `backend/app/services/airflow_sync_service.py:59-148`, `backend/app/services/airflow_service.py:63-145`
- ~150+ sequential HTTP calls. With 100ms each, sync takes ~15s.
- **Fix:** `asyncio.gather` for independent per-DAG operations. Add `Semaphore` for rate limiting.

**BP-H4. N+1 Query in FieldFrequencyRepository**
- **File:** `backend/app/repositories/field_frequency_repo.py:26-34`
- Separate query per shared field name. 21 queries instead of 2.
- **Fix:** Single query with subquery + Python-side grouping.

**BP-H5. Fire-and-Forget `asyncio.create_task` Without Error Handling**
- **File:** `backend/app/main.py:66-67`
- Startup failures silently swallowed. No retry, no alerting.
- **Fix:** Wrap in error-logging helper or store task references with done callbacks.

**BP-H6. LLM Prompt Injection via Unconstrained `role` Field**
- **File:** `backend/app/schemas/ai.py:5`
- `role: str` accepts `"system"`, allowing prompt override.
- **Fix:** `role: Literal["user", "assistant"]`.

### Medium

**BP-M1.** Naive `datetime.now()` without timezone in `scheduler.py:25` and `seed_usage_data.py:77`.
**BP-M2.** `"use client"` directive in `sonner.tsx` and `scroll-area.tsx` — Next.js artifact in Vite project.
**BP-M3.** `next-themes` dependency — Next.js-specific, unused in Vite project. Adds unnecessary bundle weight.
**BP-M4.** Timezone stripping anti-pattern — `datetime.now(timezone.utc).replace(tzinfo=None)` in 8+ locations across sync services.
**BP-M5.** `delete_stale` loads all `DagTask` rows into memory for Python-side comparison.
**BP-M6.** Topology endpoint loads all pipelines per request.
**BP-M7.** PipelineListItem uses non-semantic `div` with `onClick` — not keyboard-accessible (WCAG 4.1.2 violation).
**BP-M8.** CORS allows all methods and headers — only GET/POST used.

### Low

**BP-L1.** `from typing import Optional` in `topology.py` — rest of codebase uses `X | None`.
**BP-L2.** APScheduler version constraint `>=3.10.0` could pull in breaking 4.x — pin to `<4.0.0`.
**BP-L3.** Duplicated `_parse_datetime`, `_parse_resource_actual`, `_to_task_id` across services.
**BP-L4.** Redundant circular import workarounds in model files — `__init__.py` handles registration.
**BP-L5.** IIFE inside JSX in ResourcePerformanceCard — anti-pattern, prevents React optimization.
**BP-L6.** `tsconfig.json` targets ES2020 — could use ES2023 for `toReversed()`, `findLast()`.
**BP-L7.** Zustand destructuring triggers extra re-renders in PipelineRegistry.
**BP-L8.** Duplicate `staleTime: 30_000` in `use-pipelines.ts` matches global default.
**BP-L9.** Unstable React key (array index) in ResourcePerformanceCard run history chart.
**BP-L10.** Missing Vite `build.target` — defaults to conservative es2020.
**BP-L11.** PySpark exact version pin `==3.5.1` prevents patch-level security fixes.
**BP-L12.** `shadcn` listed as runtime dependency — should be devDependency or removed.
**BP-L13.** `tw-animate-css` may be unused — only standard Tailwind animate classes used.

---

## CI/CD & DevOps Findings

### Critical

**OPS-C1. No CI/CD Pipeline Exists**
- No `.github/workflows/`, `.gitlab-ci.yml`, or any CI config. Code merges to `main` with zero automated gates.
- **Fix:** GitHub Actions workflow: lint (`ruff check`), type-check (`pnpm tsc --noEmit`), build verification, `pip-audit`, `pnpm audit`.

**OPS-C2. Zero Test Coverage — No Test Framework Installed**
- No pytest, no vitest, no test files anywhere. `.gitignore` references `.pytest_cache` but nothing generates it.
- **Fix:** Add pytest + vitest. Gate PRs on test passage.

**OPS-C3. No Metrics Collection or APM**
- No Prometheus, Datadog, OpenTelemetry, Sentry, or any observability. Zero visibility into latency, error rates, throughput.
- **Fix:** `prometheus-fastapi-instrumentator` for HTTP metrics, OpenTelemetry for distributed tracing, custom APScheduler metrics.

**OPS-C4. No Database Backup Strategy**
- No `pg_dump`, no WAL archiving, no point-in-time recovery. Data lives in Docker volume — `docker compose down -v` deletes everything.
- **Fix:** Automated `pg_dump` on schedule, external storage (S3/GCS), WAL archiving, documented restore procedure.

**OPS-C5. No Authentication on Any Endpoint** (also SEC-C1)
- Every API endpoint publicly accessible. AI chat consumes LLM tokens with no access control.

### High

**OPS-H1. No Deployment Strategy — Manual Docker Compose Only**
- Single `docker compose up -d` with no orchestration. No blue-green, canary, or rolling updates. No rollback procedure.
- **Fix:** Container orchestrator (Docker Swarm or K8s) for rolling updates. Separate migration from app startup.

**OPS-H2. No Image Registry or Versioning**
- Both compose files use `build:` with local context. No tagged images. Rollback means rebuilding from git.
- **Fix:** Push to GHCR/ECR/Docker Hub with git SHA tags. Reference `image:` in prod compose.

**OPS-H3. Migrations Coupled to Application Start**
- `backend/Dockerfile:28`: `alembic upgrade head && exec uvicorn ...`
- Multi-replica: all replicas race to run migrations. If migration fails, app never starts.
- **Fix:** Extract migration into init container with `service_completed_successfully` dependency.

**OPS-H4. Health Endpoint Cascading Failure**
- `/api/health` makes live HTTP call to Airflow. Docker healthcheck every 30s. Airflow down → backend marked unhealthy → orchestrator restarts.
- **Fix:** Split into `/health/live` (DB only, fast) and `/health/ready` (includes external checks).

**OPS-H5. No Runbooks, Alerting, or Incident Response**
- No alerting rules, no PagerDuty/OpsGenie, no documented recovery procedures.
- **Fix:** Runbooks for: DB connection loss, Airflow unavailable, migration failure, disk full. Alert on health check failures and error rate spikes.

**OPS-H6. APScheduler Runs in Every Worker Process**
- Each uvicorn worker starts its own scheduler → duplicate sync jobs, DB write conflicts.
- **Fix:** Separate scheduler container or `workers=1` (viable for I/O-bound app).

**OPS-H7. No TLS Termination in Production**
- Frontend nginx serves port 80 (HTTP). No HTTPS, no TLS certs, no HSTS.
- **Fix:** TLS-terminating reverse proxy (Traefik/Caddy) or nginx with Let's Encrypt.

**OPS-H8. Hardcoded Credentials in Dev Compose**
- `docker-compose.yml`: `admin/admin` for Airflow, `etlnexus/etlnexus` for DB.
- Acceptable for dev but must be documented as dev-only. Add pre-commit hook blocking `.env` commits.

### Medium

**OPS-M1.** No linting or formatting enforcement — no `ruff`, `eslint`, `prettier`, no pre-commit hooks.
**OPS-M2.** No `.dockerignore` files — build context includes `.venv/`, `node_modules/`, potentially `.env`.
**OPS-M3.** Unpinned base image tags — `python:3.12-slim`, `nginx:alpine`, `postgres:16-alpine` are mutable.
**OPS-M4.** Logging is stdout-only, unstructured text — no JSON, no request IDs, no correlation.
**OPS-M5.** `EXPOSE_CONFIG=true` in dev Airflow — exposes full config including connection strings.
**OPS-M6.** Debug mode enabled by default in `.env.example`.
**OPS-M7.** CORS allows all methods and headers (also BP-M8).
**OPS-M8.** Secrets in plain-text env vars visible in `docker inspect`.

### Low

**OPS-L1.** Unpinned `pnpm@latest` in frontend Dockerfile — non-reproducible builds.
**OPS-L2.** Database pool configuration not environment-tunable.
**OPS-L3.** Iceberg REST image uses `latest` tag.

### Positive Findings
- Production compose properly uses required variable substitution (`${VAR:?error}`)
- Production compose has memory limits on all services
- Docker log rotation configured (50m/5 files)
- Backend port not exposed in production (traffic through nginx only)
- Infrastructure configs are version-controlled
