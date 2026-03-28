# Production Deployment Guide

How to deploy EtlNexus in a production environment with Keycloak SSO, external Airflow, and PostgreSQL.

---

## Prerequisites

- Docker and Docker Compose (v2+)
- External PostgreSQL 16+ (or use the bundled container)
- External Keycloak 24+ (or any OIDC provider)
- External Apache Airflow 2.7+ with REST API enabled
- External Iceberg REST catalog (optional — for schema browsing)
- DNS entries for frontend and Keycloak

---

## 1. Container Architecture

EtlNexus deploys **5 containers** in production:

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `backend-api` | `backend/Dockerfile` | 8000 | FastAPI API server (2 replicas, `SCHEDULER_ENABLED=false`) |
| `backend-scheduler` | `backend/Dockerfile` | — | Background tasks only (1 replica, `SCHEDULER_ENABLED=true`) |
| `frontend` | `frontend/Dockerfile` | 80 | Nginx serving React SPA + API reverse proxy |
| `db` | `postgres:16-alpine` | 5432 | PostgreSQL with tuned params (shared_buffers=256MB) |
| `db-backup` | `postgres:16-alpine` | — | Automated pg_dump cron (default: daily at 2am, 30-day retention) |

Airflow, Keycloak, Iceberg, and LLM are external.

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

---

## 2. Environment Configuration

Create `.env.prod` from `.env.example`. Every variable is documented below.

### Database

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://etlnexus:STRONG_PASS@db.internal:5432/etlnexus` | Must use `asyncpg` driver |
| `POSTGRES_PASSWORD` | Yes | (strong password) | Must match the password in `DATABASE_URL` |

The backend auto-runs Alembic migrations on startup. Ensure the database user has `CREATE TABLE` / `ALTER TABLE` permissions.

### Airflow Integration

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `AIRFLOW_BASE_URL` | Yes | `https://airflow.company.com/api/v1` | Must include `/api/v1` suffix |
| `AIRFLOW_USERNAME` | Yes | `etlnexus-svc` | Create a dedicated service account |
| `AIRFLOW_PASSWORD` | Yes | (strong password) | HTTP Basic Auth |
| `AIRFLOW_POLL_INTERVAL_MINUTES` | No | `20` | How often to sync pipeline metadata |

The service account needs read access to: DAGs, DAG runs, task instances, task logs, DAG source code.

### SSO / OIDC (Keycloak)

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `SSO_ENABLED` | Yes | `true` | **Must be `true` in production** |
| `SSO_ISSUER_URL` | Yes | `https://keycloak.company.com/realms/etlnexus` | Backend-to-Keycloak URL (for JWKS fetch) |
| `SSO_PUBLIC_ISSUER_URL` | Yes | `https://keycloak.company.com/realms/etlnexus` | Browser-to-Keycloak URL (for OIDC redirects) |
| `SSO_CLIENT_ID` | Yes | `etlnexus-app` | Must match Keycloak client ID |
| `SSO_AUDIENCE` | Yes | `etlnexus-app` | JWT `aud` claim to validate |
| `SSO_GROUPS_CLAIM` | No | `groups` | JWT claim containing group names |
| `SSO_ROLE_CLAIM` | No | `realm_access.roles` | JWT claim path for role extraction |
| `SSO_ADMIN_ROLE` | No | `admin` | Role value that maps to admin |

**Split-DNS note:** In Docker/Kubernetes, the backend may reach Keycloak via an internal hostname while browsers use a public URL. Set `SSO_ISSUER_URL` to the internal URL and `SSO_PUBLIC_ISSUER_URL` to the public URL. The backend validates the JWT `iss` claim against **both** URLs.

### Keycloak Production Setup

The dev realm config (`dev/keycloak/etlnexus-realm.json`) is **not suitable for production**. In your production Keycloak:

1. **Create a realm** (e.g., `etlnexus`)
2. **Create an OIDC client** with:
   - Client ID: `etlnexus-app`
   - Client authentication: **Off** (public client for SPA)
   - Valid redirect URIs: `https://etlnexus.company.com/*`
   - Valid post logout redirect URIs: `https://etlnexus.company.com/*`
   - Web origins: `https://etlnexus.company.com`
   - Standard flow enabled: **On**
   - Direct access grants: **Off** (disable for production)
3. **Configure client scopes** to include `groups` in the token:
   - Add a `groups` mapper (type: Group Membership) to the client scope
   - Set "Full group path" to **Off** (EtlNexus expects bare group names)
4. **Create groups** matching your team names: `Dagger`, `Vault`, `Prism`, `Relay`, `Oasis`
5. **Assign realm roles**: `admin`, `member`, `viewer` — assign to users as needed
6. **Enable SSL** — set SSL required to `external requests` or `all requests`
7. **Set strong admin credentials** and disable the default admin account

### Iceberg Catalog

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `ICEBERG_CATALOG_URI` | No | `http://iceberg-rest.internal:8181` | Leave empty to disable schema browsing |
| `ICEBERG_NAMESPACE_PREFIX` | No | `dagger` | Only tables under this namespace are synced |

### AI / LLM

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `LLM_API_BASE_URL` | No | `https://api.openai.com/v1` | Any OpenAPI-compatible endpoint |
| `LLM_API_KEY` | No | `sk-...` | API key for the LLM service |
| `LLM_MODEL` | No | `gpt-4` | Model identifier |
| `LLM_MAX_TOKENS` | No | `1024` | Max response tokens |

Leave `LLM_API_BASE_URL` empty to disable the AI Architect terminal.

### Application

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `CORS_ORIGINS` | Yes | `["https://etlnexus.company.com"]` | JSON array of allowed origins |
| `DEBUG` | No | `false` | **Must be `false` in production** |
| `SCHEDULER_ENABLED` | Yes | `false` (API) / `true` (scheduler) | Controls whether APScheduler background tasks run in this process |
| `DEPLOYMENT_ENV` | No | `production` | Environment label (`development`, `staging`, `production`) |
| `TRUSTED_PROXY_DEPTH` | No | `1` | Number of trusted reverse proxy hops for `X-Forwarded-For` |
| `LOG_FORMAT` | No | `auto` | Log output format (`auto`, `json`, `text`) |

**Split-container architecture:** The same backend Docker image is used for both `backend-api` and `backend-scheduler`. Set `SCHEDULER_ENABLED=false` on the API replicas (which handle HTTP traffic) and `SCHEDULER_ENABLED=true` on the single scheduler replica (which runs APScheduler background tasks). This ensures background sync jobs run exactly once, even when multiple API replicas are deployed.

### Spark Cluster Capacity

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `SPARK_MAX_DRIVER_MEMORY_GB` | No | `16` | Cluster-wide driver memory cap |
| `SPARK_MAX_EXECUTOR_MEMORY_GB` | No | `64` | Cluster-wide executor memory cap |
| `SPARK_MAX_EXECUTOR_CORES` | No | `32` | Cluster-wide executor core cap |
| `SPARK_MAX_TOTAL_EXECUTORS` | No | `20` | Cluster-wide executor count cap |

These values are used for capacity utilization display only — they do not enforce Spark limits.

### Oasis Prod (External Usage Metrics)

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `OASIS_PROD_DATABASE_URL` | No | `postgresql+asyncpg://oasis-prod.internal:5432/oasis_prod` | Connection to the production observation database for live read metrics |
| `OASIS_PROD_USERNAME` | No | (service account) | Database username for the Oasis Prod connection |
| `OASIS_PROD_PASSWORD` | No | (strong password) | Database password for the Oasis Prod connection |
| `OASIS_PROD_POOL_SIZE` | No | `5` | Connection pool size for the Oasis Prod database |
| `OASIS_PROD_MAX_OVERFLOW` | No | `3` | Max overflow connections for the Oasis Prod database |

Leave `OASIS_PROD_DATABASE_URL` empty to disable live usage metrics. When disabled, usage counts in the Usage Card will show zeros. This is an optional read-only connection to an external observation database and has no impact on core functionality.

---

## 3. Database Migrations

Migrations run automatically on backend startup. For manual control:

```bash
# Inside the backend container
alembic upgrade head

# Check current migration
alembic current

# Rollback one step
alembic downgrade -1
```

The migration history (001-032) includes:
- Core tables: pipelines, fields, lineage, statuses, resources, run history, bouncers, DAG tasks, usages
- Auth tables (015-019): users, teams, user_teams, visibility_grants, grant levels
- Constraints (020): CHECK constraints on roles and grant levels
- Indexes (021, 025): Partial composite indexes for visibility, GIN trigram for full-text search
- Unique constraint (022): Deduplication constraint on visibility grants
- Timestamps (023-024, 030): Timezone-aware datetime standardization
- Revisions (027): Pipeline description/documentation revision history
- Snapshots (031): Per-run field and table snapshots
- Performance (032): Additional DAG ID indexes

See `docs/DATABASE_SCHEMA.md` for full table and column reference.

---

## 4. Security Checklist

- [ ] `SSO_ENABLED=true` — never run without SSO in production
- [ ] `DEBUG=false` — prevents detailed error traces in responses
- [ ] Strong `POSTGRES_PASSWORD` — not the default `etlnexus`
- [ ] Strong `AIRFLOW_PASSWORD` — dedicated service account, not the Airflow admin
- [ ] `CORS_ORIGINS` restricted to your frontend domain only
- [ ] Keycloak direct access grants: **Off**
- [ ] Keycloak SSL required: **On**
- [ ] Database access restricted to backend container only (network policy)
- [ ] `LLM_API_KEY` stored securely (Docker secrets or vault)
- [ ] Reverse proxy with TLS termination in front of both frontend and backend
- [ ] Rate limiting on `/api/auth/` endpoints

---

## 5. Credential Rotation

### Database password
1. Update password in PostgreSQL
2. Update `DATABASE_URL` and `POSTGRES_PASSWORD` in `.env.prod`
3. Restart backend container

### Airflow credentials
1. Update `AIRFLOW_USERNAME` / `AIRFLOW_PASSWORD` in `.env.prod`
2. Restart backend container (connection pool recreated on startup)

### Keycloak
- Client is public (no client secret to rotate)
- JWKS keys are cached with a 1-hour TTL and auto-refreshed
- Key rotation in Keycloak takes effect within 1 hour (or restart backend)

---

## 6. Monitoring

### Health checks

The backend exposes dedicated health endpoints:

**`GET /api/health`** — public liveness/readiness probe (no authentication required). Returns `{"status": "ok"}` with HTTP 200 when the database is reachable, or `{"status": "unhealthy"}` with HTTP 503 when it is not. This endpoint is already configured as the Docker health check in `docker-compose.prod.yml`.

**`GET /api/health/detail`** — admin-only detailed health check. Returns connectivity status for each integration (database, Airflow, Iceberg catalog) along with version and uptime information. Requires a valid admin JWT.

```bash
# Liveness / readiness probe (no auth required)
curl -f http://backend:8000/api/health

# Detailed health (admin only)
curl -f -H "Authorization: Bearer $TOKEN" http://backend:8000/api/health/detail

# Auth config — lightweight OIDC discovery (no auth required)
curl -f http://backend:8000/api/auth/config

# Prometheus metrics (admin only)
curl -f -H "Authorization: Bearer $TOKEN" http://backend:8000/api/metrics
```

### Background tasks

Three APScheduler tasks run inside the backend process:

| Task | Interval | What it does |
|------|----------|-------------|
| Pipeline sync | 20 min | Discovers pipelines, lineage, resources, sensors from Airflow |
| Status poll | 20 min | Updates run statuses, run history, execution plans |
| Catalog sync | 2 hours | Syncs Iceberg table schemas to pipeline fields |

Check backend logs for `[apscheduler]` entries to verify tasks are running.

### Key log patterns

```
WARNING  OIDC client not initialized    — Keycloak unreachable at startup
WARNING  JWT validation failed           — Invalid or expired token
INFO     JWKS cache stale — refreshing   — Normal key rotation
INFO     sync_pipelines_from_airflow     — Pipeline sync running
```

---

## 7. Scaling Considerations

- **Backend** can be horizontally scaled — each instance maintains its own APScheduler, so use a single-writer pattern or external scheduler for background tasks to avoid duplicate work
- **Frontend** is a static SPA served by Nginx — scale freely behind a load balancer
- **Database** — the visibility query uses OR'd subqueries; the partial composite indexes (migration 021) are critical for performance at scale
- **JIT provisioning cache** is in-process (30s TTL) — each backend instance maintains its own cache, which is acceptable for typical deployments

### Database Connection Pool

Each backend process opens its own connection pool. The total maximum connections across all processes is:

```
total_max = num_processes × (DB_POOL_SIZE + DB_MAX_OVERFLOW)
```

With the default production layout (2 API replicas + 1 scheduler replica):

```
3 × (20 + 10) = 90 connections
```

PostgreSQL's default `max_connections=200` accommodates this comfortably.

**Recommended per-replica sizing:**

| Replica type | `DB_POOL_SIZE` | `DB_MAX_OVERFLOW` | Rationale |
|--------------|----------------|-------------------|-----------|
| API (`backend-api`) | `10` | `5` | Handles concurrent HTTP requests |
| Scheduler (`backend-scheduler`) | `5` | `3` | Runs sequential background sync tasks |

If you increase the number of API replicas, recalculate the total and ensure it stays well below PostgreSQL's `max_connections`. Leave headroom for direct admin connections and monitoring tools.
