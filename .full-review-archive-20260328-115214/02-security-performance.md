# Phase 2: Security & Performance Review

## Security Findings

### Critical (4)

1. **SEC-01: Broken Access Control on Sub-Resource Endpoints (IDOR)** (CVSS 8.6, CWE-862) — All sub-resource endpoints (`/lineage`, `/topology`, `/resources`, `/runs`, `/execution-plan`, `/revisions`) and name-keyed endpoints (`/usage/{name}`, `/consumers/{name}`) authenticate callers but never verify authorization for the specific pipeline. Any authenticated user with a UUID can access full data for pipelines they shouldn't see, completely undermining team-based RBAC.
   - Files: `routers/lineage.py`, `topology.py`, `resources.py`, `usage.py`, `consumers.py`, `pipelines.py` (revisions)
   - Fix: Create reusable `require_pipeline_visibility()` dependency and apply to all sub-resource endpoints

2. **SEC-02: Unauthenticated Metrics Endpoint** (CVSS 7.5, CWE-306) — `/api/metrics` serves Prometheus data (endpoint paths, request counts, error rates, timing) with no authentication. `include_in_schema=False` only hides from OpenAPI docs.
   - File: `routers/metrics.py:45`
   - Fix: Add `Depends(require_role("admin"))` or restrict by source IP

3. **SEC-03: Join Suggestions Cache Ignores Visibility** (CVSS 8.1, CWE-732) — Cached by `pipeline_id` only. Admin's unfiltered result served to non-admin users for 60s TTL.
   - File: `services/pipeline_service.py:283-339`
   - Fix: Include user context in cache key; filter results by visibility

4. **SEC-04: Hardcoded Default Credentials** (CVSS 9.1, CWE-798) — `config.py` defaults Airflow to `admin/admin`. Docker Compose uses `admin/admin` for Airflow, Keycloak, weak PostgreSQL password. Empty Fernet key = plaintext connection passwords.
   - Files: `config.py:14-15`, `docker-compose.yml:11,131-142,209-210`
   - Fix: Remove defaults for secrets; add startup validation; use Docker secrets

### High (5)

5. **SEC-05: Frontend `sed` Injection** (CVSS 7.2, CWE-78) — `docker-entrypoint.sh` interpolates `VITE_AIRFLOW_URL` into sed replacement without validation. Compromised env var → arbitrary JS injection in production assets.
   - File: `frontend/docker-entrypoint.sh:1-9`
   - Fix: Validate URL format or use runtime config.js approach

6. **SEC-06: OpenAPI Docs Exposed in Production** (CVSS 5.3, CWE-200) — `/api/docs`, `/api/redoc`, `/api/openapi.json` unconditionally enabled, revealing full API schema.
   - File: `main.py:101-108`
   - Fix: Disable when `settings.debug` is False

7. **SEC-07: Exception Detail Leakage** (CVSS 5.4, CWE-209) — `/api/airflow/sync-all` passes raw `str(e)` to HTTP response, potentially leaking connection strings, SQL errors, internal paths.
   - File: `routers/airflow.py:76-82`
   - Fix: Return generic error message; log details server-side

8. **SEC-08: Auth Bypass When SSO Disabled** (CVSS 8.1, CWE-287) — Default `sso_enabled=False` means zero authentication; all requests treated as admin. Any prod deployment forgetting `SSO_ENABLED=true` is fully open.
   - Files: `auth.py:50-51`, `user_auth_service.py:163-185`
   - Fix: Fail-fast startup guard for non-debug deployments without SSO

9. **SEC-09: Airflow Credentials Over HTTP** (CVSS 7.4, CWE-319/918) — Basic Auth sent in cleartext. No URL scheme validation = SSRF surface via `AIRFLOW_BASE_URL`.
   - File: `integrations/airflow_client.py:36-56`
   - Fix: Validate HTTPS in production; consider API tokens

### Medium (7)

10. **SEC-10: Rate Limiting IP Confusion Behind Proxy** (CVSS 5.3, CWE-770) — `slowapi` uses `get_remote_address` which sees Docker bridge IP, not real client IP, behind nginx.
11. **SEC-11: Topology Cache Ignores User Context** (CVSS 5.0, CWE-732) — Cache keyed by `pipeline_id:dag_id` only; will bypass visibility even after SEC-01 is fixed.
12. **SEC-12: AI Chat Prompt Injection** (CVSS 5.3, CWE-74) — User input passed directly to LLM with full catalog context (including pipelines user shouldn't see).
13. **SEC-13: Missing Security Headers on Cached Assets** (CVSS 4.3, CWE-693) — nginx `add_header` in `location /assets/` replaces parent-level CSP/HSTS/X-Frame-Options headers.
14. **SEC-14: CORS Misconfiguration Risk** (CVSS 5.4, CWE-942) — `allow_credentials=True` with env-configurable origins; no validation prevents wildcard.
15. **SEC-15: Production HTTP Only (No TLS)** (CVSS 5.9, CWE-319) — nginx listens on port 80 only; JWT tokens transmitted in cleartext.
16. **SEC-16: Database Connection Without SSL** (CVSS 4.8, CWE-319) — No SSL parameters on `create_async_engine`; credentials and data in cleartext.

### Low (6)

17. **SEC-17:** Airflow `EXPOSE_CONFIG: true` in dev compose
18. **SEC-18:** Health endpoint reveals infrastructure service status to unauthenticated users
19. **SEC-19:** No password complexity enforcement for service accounts
20. **SEC-20:** No explicit `client_max_body_size` in nginx; no `max_length` on documentation field
21. **SEC-21:** Iceberg seed container runs as root with `chmod 777`
22. **SEC-22:** No CSRF tokens (mitigated by Bearer token pattern — document as security invariant)

### Positive Security Observations

- Pydantic input validation on all endpoints with type constraints and bounds
- SQLAlchemy parameterized queries prevent SQL injection; Iceberg validates identifiers
- Non-root Docker containers in production
- Proper OIDC/JWKS JWT validation with key rotation and dual-issuer support
- Admin self-protection (prevents self-demotion, last-admin removal)
- Structured audit logging for security-relevant operations
- Markdown sanitization with `rehype-sanitize` whitelist
- Request ID tracing with UUID v4 `X-Request-ID`
- Generic error responses in global exception handler
- Dependency pinning with `uv.lock` and `pnpm-lock.yaml`

---

## Performance Findings

### Critical (3)

1. **IcebergClient Blocks Async Event Loop** — Synchronous PySpark `spark.sql().collect()` freezes all request handling during catalog sync. Every 2 hours, the event loop is completely blocked.
   - File: `integrations/iceberg_client.py:73-159`
   - Fix: Wrap in `asyncio.to_thread()`

2. **O(n^2) BFS from `list.pop(0)`** — 6 BFS loops use Python list `pop(0)` (O(n) per dequeue), turning O(V+E) into O(V^2+E). At 500+ tasks per DAG, this is 250,000 shifts vs 500 popleft operations.
   - Files: `services/graph_builder.py:48,96,151,203`, `services/bouncer_service.py:107,106`
   - Fix: `collections.deque.popleft()`

3. **Topology Loads ALL Pipelines Per Request** — `get_all()` with eager-loaded relationships on every topology request. A lightweight cached `get_task_id_map()` already exists but is unused here.
   - File: `services/topology_service.py:73,229`
   - Fix: Use existing `get_task_id_map()`

### High (7)

4. **Bouncer Service Loads Entire dag_tasks Table** — `get_all_entries()` is a full `SELECT *` with no filter.
   - File: `services/bouncer_service.py:71`
   - Fix: Filter by relevant DAG IDs at DB level

5. **Unbounded Metrics Dictionaries — Memory Leak** — `defaultdict` dictionaries grow monotonically without eviction.
   - File: `routers/metrics.py:14-16`
   - Fix: Add max-entries guard or use `prometheus_client`

6. **AirflowClient Retries Without Backoff** — Immediate retry on all errors (including 4xx). During partial outage, hammers Airflow with 50-100 duplicate requests.
   - File: `integrations/airflow_client.py:51-68`
   - Fix: Exponential backoff; skip retries on 4xx

7. **In-Memory Cache Prevents Horizontal Scaling** — Module-level TTLCache; `clear_all()` only clears local process.
   - File: `cache.py:41-49`
   - Fix: Document constraint; plan Redis migration

8. **Single Backend Instance Architecture** — One uvicorn process handles all HTTP requests AND background sync tasks.
   - File: `docker-compose.prod.yml:27-33`
   - Fix: Separate scheduler; plan multi-worker deployment

9. **Poll Task Loads All Pipelines + Bouncers** — Two full table scans every 20 minutes.
   - File: `services/airflow_service.py:56,77`
   - Fix: Use lightweight `get_task_id_map()`

10. **Recharts Bundle Not Isolated** — ~180KB gzipped in the BentoWorkspace chunk rather than its own cached chunk.
    - File: `vite.config.ts`
    - Fix: Add `vendor-charts` manual chunk

### Medium (8)

11. **Sequential Upserts in Sync** — O(n) sequential DB roundtrips during pipeline sync (100+ pipelines = 300+ roundtrips).
12. **Missing Index on `pipeline_run_history.dag_id`** — Several queries filter on `dag_id` without an index.
13. **Sequential Log Fetch in Single-Pipeline Sync** — Direct `await` per DAG instead of `asyncio.gather()`.
14. **N+1 in Catalog Sync** — Individual `SELECT WHERE task_id = :id` per Iceberg table instead of bulk `IN` query.
15. **O(N*E) Hover Computation in UpstreamTopologyModal** — Linear edge scan per node on every hover event.
16. **React-Markdown Bundle Size** — 7 markdown packages (~120KB gzipped) in a single chunk.
17. **PostgreSQL Memory Tuning** — Default 128MB `shared_buffers` with 1GB container limit.
18. **Scheduler Lock Check Non-Atomic** — TOCTOU between `locked()` and `async with` (mitigated by single-threaded event loop).

### Low (5)

19. **TTLCache Never Evicts Expired Entries Proactively** — Entries set but never get'd remain until `clear()`.
20. **AirflowSyncService Intermediate Data Structures** — All fetched data in memory simultaneously.
21. **Zustand Store Selector Granularity** — Actually correct pattern (positive finding).
22. **TopologySvgEdges Re-renders Without Memoization** — SVG paths recalculated on parent re-renders.
23. **Nginx Proxy Without Connection Limits** — No `limit_conn` or `limit_req` for `/api/`.

### Positive Performance Observations

- GIN trigram indexes for ILIKE search on pipelines and fields
- Composite indexes on run_history and visibility_grants
- React.lazy() code splitting for all secondary views
- Virtual scrolling with @tanstack/react-virtual
- Connection pooling for httpx and PostgreSQL
- TTL caching with sync-cycle invalidation
- Semaphore-limited concurrent Airflow API calls
- Vite manual chunks for vendor libraries

---

## Critical Issues for Phase 3 Context

### Testing Requirements from Security Findings
- Integration tests verifying visibility enforcement on ALL sub-resource endpoints
- Test that non-admin users cannot access pipelines outside their team via sub-resource URLs
- Test cache behavior with different user contexts (admin then non-admin)
- Test that metrics endpoint requires authentication
- Test SSO-disabled startup guard in non-debug mode
- Test rate limiting behind reverse proxy

### Testing Requirements from Performance Findings
- Load tests for topology endpoint with growing pipeline counts
- Benchmarks for BFS algorithms with large DAGs (500+ tasks)
- Memory profiling for long-running processes (metrics accumulation)
- Event loop blocking detection during catalog sync

### Documentation Requirements
- Single-process cache assumption must be documented
- Security invariant: Bearer tokens only (no cookies) for CSRF protection
- Production deployment checklist: SSO, TLS, credential rotation, OpenAPI disabled
- Horizontal scaling prerequisites (Redis, scheduler separation)
