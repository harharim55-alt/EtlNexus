# Phase 2: Security & Performance Review

**Date:** 2026-03-13
**Target:** Entire EtlNexus codebase

---

## Security Findings

### Critical (5)

1. **SEC-01: Deactivated User Bypass via `get_current_user_optional`** (CVSS 9.1, CWE-863)
   - File: `backend/app/auth.py` (lines 66-95)
   - `except HTTPException` catches 403 (deactivated) and returns `None` — deactivated users become anonymous
   - Not currently used in any router, but exported as the optional auth dependency
   - Fix: Only catch `HTTPException` with `status_code == 401`

2. **SEC-02: SSO Role Not Updated on Login — Privilege Persistence** (CVSS 8.8, CWE-269)
   - File: `backend/app/repositories/user_repo.py` (lines 56-75)
   - `upsert_from_sso` excludes `role` from the `ON CONFLICT DO UPDATE` set
   - A user demoted in Keycloak retains their old role indefinitely
   - Fix: Add `role` to the update set, or add a `role_source` column for dual management

3. **SEC-03: Broken Object-Level Authorization (BOLA) on 8+ Endpoints** (CVSS 8.6, CWE-639)
   - Files: `routers/lineage.py`, `resources.py`, `topology.py`, `pipelines.py` (revisions), `consumers.py`, `usage.py`, `ai.py`
   - Any authenticated user can access any pipeline's sub-resources (lineage, resources, execution plans, topology, consumers, usage, AI joins) by UUID — no visibility check
   - Fix: Create `require_pipeline_visibility()` dependency and apply to all sub-resource endpoints

4. **SEC-04: No Rate Limiting on Any Endpoint** (CVSS 7.5, CWE-770)
   - File: `main.py` (application-wide)
   - AI chat, pipeline sync, all data endpoints have zero rate limiting
   - Attacker can exhaust LLM budget, enumerate pipelines, or cause upstream Airflow outage
   - Fix: Add `slowapi` with per-user limits (10/min AI, 5/min sync, 100/min general)

5. **SEC-05: AI Chat Prompt Injection via Unvalidated Input** (CVSS 8.1, CWE-77)
   - Files: `services/ai_service.py`, `schemas/ai.py`
   - `AIChatMessage.role` accepts arbitrary strings — attacker can inject `"system"` messages
   - No length limits on message or history
   - Fix: `role: Literal["user", "assistant"]`, `content: str = Field(max_length=10000)`, `history: list = Field(max_length=50)`

### High (7)

6. **SEC-06: CORS allows all methods/headers with credentials** (CVSS 7.4)
   - Fix: Restrict to `["GET","POST","PATCH","DELETE","OPTIONS"]` and `["Authorization","Content-Type"]`

7. **SEC-07: Airflow credentials hardcoded as defaults** (CVSS 7.2)
   - Fix: Remove defaults, add startup validation, require in prod compose

8. **SEC-08: Airflow Fernet key empty, web secret hardcoded, config exposed** (CVSS 7.5)
   - Fix: Generate unique keys, disable `EXPOSE_CONFIG`

9. **SEC-09: Keycloak SSL disabled, brute force unprotected** (CVSS 7.3)
   - Fix: `sslRequired: "external"`, `bruteForceProtected: true`, disable Direct Access Grants

10. **SEC-10: Missing Content-Security-Policy and HSTS headers** (CVSS 6.1)
    - Fix: Add CSP, HSTS, Permissions-Policy to nginx.conf

11. **SEC-11: Health endpoint exposes internal service topology** (CVSS 5.3)
    - Fix: Split into public liveness and admin-only detailed health

12. **SEC-12: Schema matrix and DAG summary leak data across team boundaries** (CVSS 6.5)
    - Fix: Pass user context and filter through `list_visible()`

### Medium (8)

13. `PipelineUpdateRequest` has no length limits on description/documentation
14. `DEBUG=true` enabled by default in `.env` and `.env.example`
15. Keycloak dev users have weak identical passwords (`"password"`)
16. LLM client creates new HTTP client per request (amplifies DoS risk)
17. Frontend auth config endpoint exposes issuer URL and client ID
18. Docker compose exposes internal service ports to host network
19. No CSRF defense-in-depth (Bearer auth provides inherent protection)
20. Nginx proxy has no `client_max_body_size` limit

### Low (6)

21. Production compose serves HTTP only (no TLS termination)
22. Security headers missing on cached asset responses (nginx `add_header` override)
23. General exception handler may leak info in edge cases
24. UUID enumeration timing side-channel (negligible with 128-bit UUIDs)
25. Frontend token stored in memory only (secure, but XSS-accessible without CSP)
26. No backend integration tests for auth-protected endpoint lifecycle

### Positive Security Observations

- JWT RS256 validation with JWKS rotation and rate-limited refresh
- Parameterized SQL queries throughout — no injection vectors found
- LIKE injection prevention with proper escape function
- Database CHECK constraints on roles and grant levels
- Atomic user provisioning with `ON CONFLICT DO UPDATE`
- Non-root Docker containers with multi-stage builds
- Markdown XSS protection via `rehype-sanitize`
- Admin self-protection (cannot demote self or deactivate last admin)
- `.env` files properly gitignored and never committed
- Production compose uses `${VAR:?}` for required secrets

---

## Performance Findings

### Critical (4)

1. **PERF-01: Synchronous Spark blocks async event loop** — 30-135s total backend freeze during catalog sync
   - File: `integrations/iceberg_client.py`, `services/catalog_sync_service.py`
   - Fix: Run Spark operations in thread executor (`asyncio.to_thread()`)

2. **PERF-02: `get_all()` pipeline loading on every request (7 services)**
   - Files: `topology_service.py` (2x), `consumer_service.py`, `usage_service.py`, `ai_service.py`, `airflow_service.py`, `sensor_service.py`
   - Fix: Add targeted `get_pipelines_by_task_ids()` repo method; collect relevant IDs first

3. **PERF-03: BFS uses `list.pop(0)` — O(n^2) (5 locations)**
   - Fix: `collections.deque.popleft()` — trivial change, O(1)

4. **PERF-04: LLM client creates new HTTP connection per request** — +50-200ms per AI call
   - Fix: Persistent `httpx.AsyncClient` with connection pooling

### High (5)

5. **PERF-05: N+1 queries in `DagSummaryService`** — 3-5 sequential queries per DAG in a loop
   - Fix: Batch with `GROUP BY dag_id` aggregate query

6. **PERF-06: Missing composite indexes on `pipeline_run_history`**
   - Fix: Add `(pipeline_id, start_date)`, `(dag_id, start_date)`, `(pipeline_id, status)` indexes

7. **PERF-07: TTL cache with no maximum size** — unbounded memory growth
   - Fix: Add `max_size` with LRU eviction or use `cachetools.TTLCache`

8. **PERF-08: Shared DB connection pool for API + background tasks** — pool exhaustion risk
   - Fix: Separate `api_engine` and `task_engine` with dedicated pools

9. **PERF-09: `get_all_entries()` loads entire `dag_tasks` table**
   - Fix: Filter to relevant DAGs only

### Medium (8)

10. AI rebuilds catalog context per message (redundant DB load)
11. Airflow poll loads all bouncer ORM objects when only names needed
12. PipelineRegistry fetches heavyweight DagSummary for client-side filtering
13. No pagination on topology/consumer/usage/bouncer-topology/dag-summary endpoints
14. Redundant pipeline loading in auth middleware
15. `delete_stale` builds large NOT IN clause
16. Chat history grows unbounded in Zustand store
17. No response compression (GZip) middleware on FastAPI

### Low (8)

18. No debouncing on pipeline search input
19. `pool_pre_ping=True` adds 0.5ms per connection checkout
20. All bento workspace cards render eagerly (6-8 concurrent API calls)
21. Fixed retry strategy with no backoff in Airflow client
22. Single-worker production uvicorn (no multi-process)
23. Missing composite index on lineage_edges for upsert lookup
24. Vite manual chunks could be more granular
25. Expired cache entries not proactively cleaned

---

## Critical Issues for Phase 3 Context

### Testing Requirements from Security Findings
1. **Auth integration tests needed** — deactivated user bypass, role persistence, BOLA on sub-resource endpoints
2. **Visibility enforcement tests** — schema matrix, DAG summary, all pipeline sub-resources must respect team boundaries
3. **Input validation tests** — AI chat role injection, field length limits on pipeline updates
4. **Rate limiting tests** — verify limits are enforced on sensitive endpoints

### Testing Requirements from Performance Findings
1. **Load/stress tests** — verify behavior under concurrent sync + API traffic
2. **Connection pool monitoring** — ensure no exhaustion during background tasks
3. **BFS correctness tests** — verify deque refactor maintains correct traversal order
