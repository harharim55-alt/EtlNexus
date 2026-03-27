# Phase 2: Security & Performance Review

**Date:** 2026-03-13
**Target:** Entire EtlNexus codebase (post tech-debt remediation)

---

## Security Findings

### High (5)

1. **SSO Role not updated on login — split-brain between Keycloak and app** (CVSS 7.5, CWE-269)
   - File: `user_repo.py` lines 43-83
   - ON CONFLICT excludes `role` from update — Keycloak role changes silently ignored for existing users
   - No documented authority for who controls roles
   - Fix: Either sync role from SSO on every login, or add `role_managed_by` field

2. **Missing visibility enforcement on sub-resource endpoints** (CVSS 7.1, CWE-862)
   - Affected: lineage, resources, execution-plan, topology, consumers, usage — all accept pipeline_id without visibility check
   - Any authenticated user can access any pipeline's sub-resources by UUID
   - Fix: Create reusable `require_pipeline_visibility` dependency

3. **AI chat prompt injection via unvalidated input** (CVSS 7.0, CWE-77)
   - Files: `schemas/ai.py`, `services/ai_service.py`
   - No `role` validation (allows "system" injection), no length limits, catalog context includes all pipelines regardless of user visibility
   - Fix: `role: Literal["user", "assistant"]`, `Field(max_length=...)`, filter catalog by user visibility

4. **No HTTPS/HSTS in production configuration** (CVSS 7.4, CWE-319)
   - Production serves HTTP only on port 80, no TLS termination, no HSTS header
   - Fix: Add TLS to nginx or deploy behind TLS-terminating proxy

5. **Keycloak brute force protection disabled** (CVSS 7.3, CWE-307)
   - `bruteForceProtected: false`, `sslRequired: "none"`, Direct Access Grants enabled
   - Fix: Enable brute force protection, set `sslRequired: "external"`, disable ROPC flow

### Medium (8)

6. Rate limiting only on 2 of 20+ endpoints (AI joins endpoint has no limit despite triggering LLM)
7. Deactivated user can still auth within JWT lifetime (no Keycloak session revocation)
8. SSO disabled mode grants full admin with no credential check (`sso_enabled` defaults False)
9. CORS allows wildcard methods/headers with credentials
10. OpenAPI/Swagger docs exposed in production
11. Keycloak Direct Access Grants enabled (deprecated ROPC flow)
12. No request body size limits in nginx or Pydantic schemas
13. Security headers missing from nginx cached asset locations

### Low (6)

14. Debug mode enabled in `.env.example`
15. Default credentials in docker-compose and Keycloak realm
16. Airflow web server exposes configuration
17. Missing Permissions-Policy header
18. Pipeline revision `getattr` on field_name (validated at API level, low risk)
19. Empty Fernet key in Airflow configuration

### Positive Security Observations

- Consistent auth enforcement on all endpoints (except health + auth config)
- JWT RS256 with JWKS rotation, dual-issuer, rate-limited refresh
- ORM parameterization throughout — no SQL injection vectors
- LIKE escape function for search queries
- Iceberg SQL identifier validation
- Markdown XSS protection via rehype-sanitize
- Non-root Docker containers with multi-stage builds
- Admin self-demotion guard and last-admin protection
- `.env` files properly gitignored
- Production DB password enforcement (`${VAR:?}`)
- Comprehensive auth test suite
- Rate limiting infrastructure in place (SlowAPI)

---

## Performance Findings

### Critical (4)

1. **N+1 queries in DagSummaryService** — 4 sequential DB queries per DAG in a loop (~24 queries per request)
   - File: `dag_summary_service.py` lines 90-116
   - Fix: Batch repo methods with `GROUP BY dag_id` or `asyncio.gather`

2. **`get_all()` loads all pipelines per request across 6+ services** — TopologyService (2x), ConsumerService, UsageService, BouncerService, AIService, AirflowService
   - Fix: Shared `PipelineIndex` singleton refreshed on sync, or targeted `WHERE task_id IN (...)`

3. **Synchronous Spark blocks async event loop** — all requests stall during catalog sync (~30s+)
   - File: `iceberg_client.py`
   - Fix: `loop.run_in_executor()` with dedicated thread pool

4. **BFS uses `list.pop(0)` — O(n^2)** in 4-6 locations
   - Fix: `collections.deque.popleft()` — trivial change

### High (6)

5. LLM client creates new HTTP connection per request (+50-200ms)
6. AI join insight loads all pipelines+fields in Python despite existing SQL query
7. `get_all()` called independently by 3+ services within milliseconds (no shared caching)
8. `useBouncerTopology` hook mutates queryKey array via `.sort()` — causes unnecessary refetches
9. In-process caching prevents horizontal scaling (no Redis)
10. Background tasks (APScheduler) coupled to web process — duplicate syncs with multiple workers

### Medium (9)

11. All DagTasks loaded into memory for bouncer topology
12. AI chat history grows unbounded in Zustand store
13. TTL cache has no max-size eviction
14. Missing composite indexes on `pipeline_run_history`
15. Missing index on `lineage_edges` for upsert lookup
16. Cache not invalidated on pipeline update (stale data up to 60s)
17. TTL cache not thread-safe (acceptable for single-thread asyncio)
18. 7+ parallel requests on pipeline select (BentoWorkspace)
19. Single backend container in production (no horizontal scaling)

### Low (5)

20. No index on `dag_tasks.sensor_name`
21. Connection pool sizing hardcoded
22. `get_all_dags()` called twice in single-pipeline sync
23. Missing `refetchOnWindowFocus: false` on hooks
24. Rate limiting not differentiated per-endpoint

---

## Critical Issues for Phase 3 Context

### Testing Requirements from Security
1. Integration tests for visibility enforcement on all sub-resource endpoints
2. Tests for AI chat input validation (role injection, length limits)
3. Tests for SSO role sync behavior (new user, existing user, role change)
4. Tests for deactivated user blocking through full request lifecycle

### Testing Requirements from Performance
1. Load tests for concurrent pipeline selection (multiple `get_all()` calls)
2. Verify BFS correctness after deque refactor
3. Test catalog sync doesn't block API requests (after thread executor fix)
4. Verify DagSummary batched queries produce same results
