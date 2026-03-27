# Phase 2: Security & Performance Review

## Security Findings

### Critical

**SEC-C1. No Authentication or Authorization on Any API Endpoint** (CVSS 9.8, CWE-306)
- **Location:** All files in `backend/app/routers/`
- Every API endpoint is publicly accessible. State-mutating endpoints (`POST /api/pipelines/{id}/sync`, `POST /api/ai/chat`) have no identity verification.
- **Impact:** Any network-reachable actor can read the catalog, trigger syncs, query the AI endpoint (consuming LLM credits), and map internal infrastructure.
- **Fix:** Implement OAuth 2.0 / JWT auth middleware with RBAC (at minimum: read-only viewers vs sync-capable users).

**SEC-C2. Airflow Credentials Hardcoded and Transmitted Over Plaintext HTTP** (CVSS 9.1, CWE-319/798)
- **Location:** `backend/app/config.py:10-11`, `backend/app/integrations/airflow_client.py:44`
- Default `admin:admin` credentials in settings. `airflow_base_url` defaults to `http://` — credentials sent in cleartext via HTTP Basic Auth.
- **Fix:** Remove hardcoded defaults (make required), enforce HTTPS URL validation for non-localhost, migrate to token-based auth.

**SEC-C3. LLM Prompt Injection via Unrestricted User Input** (CVSS 8.6, CWE-77)
- **Location:** `backend/app/services/ai_service.py:24-34`, `backend/app/schemas/ai.py:5`
- Arbitrary user messages injected into LLM prompt with full catalog context. The `role` field in `AIChatMessage` accepts any string including `system`, allowing system prompt override. No input length limits.
- **Fix:** Constrain `role` to `Literal["user", "assistant"]`, add `max_length=4000` on message, `max_length=20` on history list.

### High

**SEC-H1. SQL LIKE Wildcard Injection** (CVSS 7.5, CWE-943)
- **Location:** `backend/app/repositories/pipeline_repo.py:39-40`
- `f"%{query}%"` doesn't escape `%` and `_` metacharacters. Search for `%` matches every row.
- **Fix:** Escape LIKE metacharacters; use `ilike(pattern, escape="\\")`.

**SEC-H2. CORS Misconfiguration — Wildcard Methods/Headers with Credentials** (CVSS 7.4, CWE-942)
- **Location:** `backend/app/main.py:90-96`
- `allow_methods=["*"]`, `allow_headers=["*"]` with `allow_credentials=True`. Permits DELETE/PUT/PATCH methods the app doesn't use.
- **Fix:** Restrict to `allow_methods=["GET", "POST"]`, `allow_headers=["Content-Type", "Authorization"]`.

**SEC-H3. No Rate Limiting on Any Endpoint** (CVSS 7.5, CWE-770)
- **Location:** All `backend/app/routers/`
- AI chat consumes LLM credits; sync triggers 30-50 Airflow API calls; search hits DB.
- **Fix:** Add `slowapi` rate limiting — `10/minute` on AI, `2/minute` on sync, `60/minute` on search.

**SEC-H4. Race Condition in Concurrent Startup Tasks** (CVSS 6.8, CWE-362)
- **Location:** `backend/app/main.py:66-67`
- Two `asyncio.create_task()` calls launch concurrent DB mutations on same tables. Plus scheduler catch-up at 5 min can overlap.
- **Fix:** Serialize startup — await sync before poll. Add `asyncio.Lock` around sync function.

**SEC-H5. Airflow Configuration Exposure in Docker Compose** (CVSS 7.1, CWE-200)
- **Location:** `docker-compose.yml:107`
- `EXPOSE_CONFIG: "true"` exposes full Airflow config (DB strings, secret keys) via web UI. Empty Fernet key disables encryption. Hardcoded `etlnexus-dev-key` secret.
- **Fix:** Set `EXPOSE_CONFIG: "false"`, generate proper Fernet key and secret key.

### Medium

**SEC-M1.** Debug mode enabled by default in `.env.example` — may leak sensitive data in logs. (CWE-489)
**SEC-M2.** Database credentials hardcoded in `docker-compose.yml` — `etlnexus:etlnexus`, exposed port 5432. (CWE-798)
**SEC-M3.** Missing security headers on FastAPI backend — no HSTS, CSP, X-Frame-Options on direct access. (CWE-693)
**SEC-M4.** Unvalidated `full_table_name` passed to `spark.table()` in Iceberg client. (CWE-20)
**SEC-M5.** Unbound `asyncio.create_task` without error handling — startup failures silently swallowed. (CWE-755)
**SEC-M6.** Health endpoint exposes internal service connectivity to unauthenticated callers. (CWE-200)
**SEC-M7.** Unbounded query parameters — no min length on search, no upper bound on `limit`. (CWE-770)
**SEC-M8.** Production Docker Compose serves HTTP without TLS — no HTTPS, no HSTS. (CWE-319)

### Low

**SEC-L1.** Module-level singleton clients initialized at import time — configuration frozen. (CWE-665)
**SEC-L2.** LLM error messages leak internal details ("LLM API error: {status}"). (CWE-209)
**SEC-L3.** Deprecated `datetime.utcnow()` — potential timezone comparison bugs. (CWE-682)
**SEC-L4.** `etl_name` path parameter not validated — accepts `../`, long strings. (CWE-22)
**SEC-L5.** No Content-Security-Policy on frontend nginx. (CWE-1021)

### Informational

- `.env` file present with dev credentials on disk (verify `.gitignore` coverage)
- No automated security testing in CI/CD (no SAST, DAST, dependency scanning)
- No request/response audit logging for incident investigation
- Database connection pool (30 max) exhaustible without rate limiting
- PySpark 3.5.1 pinned — review for transitive Java dependency CVEs (Log4j, Netty)

---

## Performance Findings

### Critical

**PERF-C1. N+1 Query in FieldFrequencyRepository**
- **File:** `backend/app/repositories/field_frequency_repo.py:11-47`
- Executes separate DB query per shared field name (50-100+ queries per request).
- **Fix:** Single query with `array_agg`. Reduces 50-100 queries → 1. Latency: ~200-500ms → ~10-30ms.

**PERF-C2. Serial Airflow API Calls Without Connection Reuse**
- **File:** `backend/app/integrations/airflow_client.py:49-67`
- New `httpx.AsyncClient` (TCP connection) per request. ~49 sequential requests during sync, ~67 during poll.
- **Fix:** Persistent `AsyncClient` with connection pool + `asyncio.gather` parallelization. Sync: ~10s → ~3s.

### High

**PERF-H1. Repeated `get_all()` Full-Table Scans**
- **Files:** `topology.py:53`, `consumer_service.py:30`, `usage_service.py:40`, `pipeline_service.py:79`, `airflow_service.py:42`
- BentoWorkspace load triggers 4 separate full-table reads of all pipelines.
- **Fix:** Targeted `get_by_task_ids()` queries. Reduces data by ~80%.

**PERF-H2. Health Endpoint Makes Live Airflow HTTP Call**
- **File:** `backend/app/routers/health.py:21`
- Docker healthcheck every 30s makes real HTTP request. If Airflow is slow → backend marked unhealthy.
- **Fix:** Use cached `is_connected` flag (already done for Iceberg). Latency: 200-500ms → <5ms.

**PERF-H3. `sync_single_pipeline` Triggers 30-50 Sequential HTTP Requests**
- **File:** `backend/app/services/airflow_sync_service.py:274-501`
- Scans ALL DAGs sequentially to find the task, then fetches 5 runs per DAG with instances.
- **Fix:** Use cached `dag_tasks` table to skip full scan + parallelize.

**PERF-H4. No Application-Level Caching for Read-Heavy Pipeline Data**
- Pipeline data changes only every 20-min sync cycle but hits DB on every request.
- **Fix:** In-memory TTL cache (30s) or leverage TanStack Query's `staleTime` + eliminate redundant `get_all()`.

**PERF-H5. APScheduler Runs in Every Worker**
- **File:** `backend/app/main.py:70-72`
- Multi-worker deployment: each worker starts its own scheduler → 4x Airflow API calls, DB conflicts.
- **Fix:** Separate scheduler container or `workers=1` (viable for I/O-bound app).

**PERF-H6. Single AirflowClient Singleton Per Process**
- **File:** `backend/app/integrations/airflow_client.py:178`
- In-memory TTL cache not shared across workers → cache misses, redundant API calls.
- **Fix:** Accept per-worker caching or use Redis for shared cache if rate limits are a concern.

### Medium

**PERF-M1.** Missing composite DB indexes on `lineage_edges(source_table, target_table, edge_type)` and covering index for `pipeline_run_history` stats query.
**PERF-M2.** `delete_stale()` loads full `dag_tasks` table for O(N) individual DELETEs.
**PERF-M3.** No pagination on list endpoints — unbounded response size.
**PERF-M4.** Blocking PySpark/JVM calls on asyncio event loop — blocks all request handling during catalog sync.
**PERF-M5.** Unbounded TTL cache growth — stale entries never evicted proactively.
**PERF-M6.** Pipeline list loaded into memory 4x per BentoWorkspace load (~240-600KB).
**PERF-M7.** Join suggestions recomputed on every request (O(N×M) pipeline×field comparison).
**PERF-M8.** Schema matrix not cached — hits N+1 query every time (changes only every 2 hours).
**PERF-M9.** Race between startup sync tasks — poll may complete before pipelines exist.
**PERF-M10.** ResourcePerformanceCard missing `useMemo` — IIFE recomputes on every render.
**PERF-M11.** Zustand store selectors in PipelineRegistry cause full re-render per keystroke.
**PERF-M12.** DagNetworkCard duplicates topology query (TanStack deduplicates but unnecessary subscription).
**PERF-M13.** Long-lived SparkSession holds ~512MB driver memory for entire process lifetime.
**PERF-M14.** No rate limiting on sync endpoint — Airflow API abuse possible.

### Low

**PERF-L1.** Connection pool sizing adequate for single instance, needs PgBouncer for horizontal scaling.
**PERF-L2.** Background task sessions accumulate large identity maps before commit.
**PERF-L3.** TTL cache not thread-safe (no actual risk with asyncio).
**PERF-L4.** Catch-up sync may overlap with scheduled sync (idempotent, wastes API calls).
**PERF-L5.** Missing debounce on pipeline search — API call per keystroke.
**PERF-L6.** Bundle splitting opportunities — PipelineRegistry not lazy-loaded, `sonner` in main chunk.
**PERF-L7.** Unused `next-themes` dependency adds ~3KB gzipped.
**PERF-L8.** No response compression (gzip/brotli) on backend or production nginx.

---

## Critical Issues for Phase 3 Context

The following findings affect testing and documentation requirements:

1. **No authentication (SEC-C1)** — testing strategy must plan for auth integration; all current tests (if any) assume unauthenticated access
2. **LLM prompt injection (SEC-C3)** — requires dedicated security test cases for input validation
3. **Race conditions (SEC-H4)** — needs integration tests for concurrent startup scenarios
4. **N+1 queries (PERF-C1, PERF-H1)** — performance test suite needed to catch query regressions
5. **No rate limiting (SEC-H3)** — load/stress testing needed to validate resource limits
6. **Missing security headers (SEC-M3)** — needs compliance verification tests
7. **Frontend re-render issues (PERF-M10, PERF-M11)** — React profiling tests needed
8. **Blocking Spark calls (PERF-M4)** — integration test for event loop blocking during sync
