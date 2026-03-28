# EtlNexus Best Practices & Modernization Review

**Date:** 2026-03-27
**Scope:** Full-stack review of backend (Python 3.12, FastAPI, SQLAlchemy 2.0, APScheduler) and frontend (TypeScript, React 19, Vite 6, TanStack Query v5, Zustand 5, Tailwind CSS v4)

---

## Table of Contents

1. [Backend: Python & FastAPI](#1-backend-python--fastapi)
2. [Backend: SQLAlchemy & Database](#2-backend-sqlalchemy--database)
3. [Backend: Dependency Injection & Architecture](#3-backend-dependency-injection--architecture)
4. [Backend: APScheduler & Background Tasks](#4-backend-apscheduler--background-tasks)
5. [Frontend: TypeScript & React](#5-frontend-typescript--react)
6. [Frontend: TanStack Query & Zustand](#6-frontend-tanstack-query--zustand)
7. [Frontend: Build & Configuration](#7-frontend-build--configuration)
8. [Infrastructure: Docker & Deployment](#8-infrastructure-docker--deployment)
9. [Package Management & Dependencies](#9-package-management--dependencies)
10. [Cross-Cutting Concerns](#10-cross-cutting-concerns)

---

## 1. Backend: Python & FastAPI

### 1.1 `datetime.fromisoformat` Z-suffix workaround is unnecessary on Python 3.12

**Severity: Medium**

Four call sites use `datetime.fromisoformat(date_str.replace("Z", "+00:00"))`. Python 3.11+ natively handles the `Z` suffix in `fromisoformat`.

**Current pattern:**
```python
datetime.fromisoformat(date_str.replace("Z", "+00:00"))
```

**Recommended pattern (Python 3.11+):**
```python
datetime.fromisoformat(date_str)
```

**Files:**
- `backend/app/integrations/airflow_client.py:238`
- `backend/app/services/airflow_service.py:234`
- `backend/app/services/airflow_sync_service.py:217`
- `backend/app/services/sync/task_classifier.py:108`

**Fix:** Remove all `.replace("Z", "+00:00")` calls. `fromisoformat` on Python 3.12 handles ISO 8601 `Z` suffix natively.

---

### 1.2 No use of `typing.Annotated` for FastAPI dependency injection

**Severity: Medium**

FastAPI 0.95+ (current: >=0.115) recommends `Annotated[Type, Depends(...)]` over `param: Type = Depends(...)`. The `Annotated` pattern is the modern standard, improves readability, enables reuse, and avoids default-value mutation pitfalls.

**Current pattern (all routers):**
```python
async def list_pipelines(
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
):
```

**Recommended pattern:**
```python
from typing import Annotated

CurrentUser = Annotated[User, Depends(get_current_user)]
PipelineSvc = Annotated[PipelineService, Depends(get_pipeline_service)]

async def list_pipelines(
    user: CurrentUser,
    service: PipelineSvc,
):
```

**Fix:** Define reusable `Annotated` type aliases in `dependencies.py` and use them across all 40+ route handlers. This is a non-breaking, incremental change.

---

### 1.3 No `StrEnum` or `Literal` types for role/status/grant_level

**Severity: Low**

String-based enums like `role IN ('admin', 'member', 'viewer')` and `grant_level IN ('viewer', 'editor')` are enforced only at the DB level via CHECK constraints and at the Pydantic schema level via `str`. Python 3.11+ `StrEnum` or `Literal` types would catch invalid values at the application layer.

**Current pattern:**
```python
role: Mapped[str] = mapped_column(String(50), default="member")
```

**Recommended pattern:**
```python
from enum import StrEnum

class UserRole(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

# In Pydantic schemas:
role: Literal["admin", "member", "viewer"] = "member"
```

**Fix:** Define `StrEnum` classes (or `Literal` unions) for `UserRole`, `GrantLevel`, `AirflowStatus`, `EdgeType`, `ChangeSource`. Use in both ORM models and Pydantic schemas.

---

### 1.4 Custom domain exceptions defined but barely used

**Severity: Medium**

`backend/app/exceptions.py` defines six domain-specific exceptions (`AirflowConnectionError`, `AirflowSyncError`, `PipelineNotFoundError`, `IcebergCatalogError`, `AuthorizationError`), but the codebase has 30+ `except Exception` blocks that catch generically instead of using these.

**Current pattern:**
```python
except Exception:
    logger.exception("Scheduled pipeline sync failed")
```

**Recommended pattern:**
```python
except AirflowConnectionError:
    logger.warning("Airflow unreachable, will retry next cycle")
except AirflowSyncError:
    logger.exception("Pipeline sync data error")
except Exception:
    logger.exception("Unexpected error during sync")
```

**Fix:** Replace bare `except Exception` blocks in sync/poll/catalog tasks and integration clients with domain-specific exception handling. Raise domain exceptions from `airflow_client.py` and `iceberg_client.py`.

---

### 1.5 TTLCache uses `Any` type parameter despite PEP 695 generic syntax

**Severity: Low**

`cache.py` defines `class TTLCache[T]` using Python 3.12 PEP 695 generic syntax (good), but all module-level instances use `TTLCache[Any]`, negating the type safety benefit.

**Current pattern:**
```python
pipeline_list_cache: TTLCache[Any] = TTLCache(ttl=settings.cache_ttl_short)
```

**Recommended pattern:**
```python
pipeline_list_cache: TTLCache[PipelineListResponse] = TTLCache(ttl=settings.cache_ttl_short)
topology_cache: TTLCache[TopologyGraph] = TTLCache(ttl=settings.cache_ttl_short)
```

**Fix:** Parameterize each cache with its actual stored type.

---

## 2. Backend: SQLAlchemy & Database

### 2.1 Auto-commit on all requests including reads (GET endpoints)

**Severity: High**

`get_db_session()` unconditionally calls `await session.commit()` after every request, even for pure-read (GET) endpoints. This is unnecessary overhead and semantically incorrect -- reads should not trigger commits.

**Current pattern (`database.py`):**
```python
async def get_db_session():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Recommended pattern:**
```python
async def get_db_session():
    async with async_session_factory() as session:
        yield session
        # No auto-commit -- let callers commit explicitly for writes

async def get_db_session_with_commit():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Alternative (more idiomatic):** Use a single dependency but only commit when the session is dirty:

```python
async def get_db_session():
    async with async_session_factory() as session:
        try:
            yield session
            if session.dirty or session.new or session.deleted:
                await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Fix:** Either split into read/write session dependencies, or check `session.dirty` before committing. This eliminates ~35 unnecessary commits per read-only request cycle.

---

### 2.2 `DeclarativeBase` without `MappedAsDataclass` consideration

**Severity: Low**

All ORM models use `class Base(DeclarativeBase)`. SQLAlchemy 2.0 also supports `MappedAsDataclass` which auto-generates `__init__`, `__repr__`, and `__eq__` -- useful for models frequently constructed in code (like `PipelineField`, `LineageEdge`).

**Current pattern:**
```python
class Base(DeclarativeBase):
    pass
```

**Recommended pattern (for suitable models):**
```python
from sqlalchemy.orm import MappedAsDataclass, DeclarativeBase

class Base(MappedAsDataclass, DeclarativeBase):
    pass
```

**Note:** This is a significant migration. Not all models are suitable (e.g., those with complex defaults). Evaluate per-model.

---

### 2.3 Alembic env.py uses star import for model registration

**Severity: Low**

`from app.models import * # noqa: F401, F403` is functional but uncontrolled. If a new model file is added without updating `__init__.py`, Alembic will miss it silently.

**Current pattern:**
```python
from app.models import *  # noqa: F401, F403
```

**Recommended pattern:**
```python
from app.models import (  # noqa: F401
    AirflowRunStatus, Bouncer, DagTask, LineageEdge, Pipeline,
    PipelineField, PipelineRevision, PipelineUsage,
    PipelineResourceConfig, PipelineRunHistory, Team, User,
    UserTeam, VisibilityGrant,
)
```

**Fix:** Explicit imports ensure new models are noticed during PR review. The `__init__.py` already lists all models explicitly -- mirror that list.

---

## 3. Backend: Dependency Injection & Architecture

### 3.1 TopologyService and AirflowService bypass FastAPI DI -- construct repos internally

**Severity: High**

`TopologyService.__init__` takes a raw `AsyncSession` and constructs all four repositories internally. `AirflowService` does the same. This bypasses FastAPI's DI system, making these services untestable without a real database.

**Current pattern (`topology_service.py`):**
```python
class TopologyService:
    def __init__(self, session: AsyncSession):
        self.pipeline_repo = PipelineRepository(session)
        self.dag_task_repo = DagTaskRepository(session)
        self.bouncer_repo = BouncerRepository(session)
        self.resource_repo = ResourceRepository(session)
```

**Current pattern (`routers/topology.py`):**
```python
service = TopologyService(session)
```

**Recommended pattern:**
```python
# dependencies.py
def get_topology_service(
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
    dag_task_repo: DagTaskRepository = Depends(get_dag_task_repo),
    bouncer_repo: BouncerRepository = Depends(get_bouncer_repo),
    resource_repo: ResourceRepository = Depends(get_resource_repo),
) -> TopologyService:
    return TopologyService(pipeline_repo, dag_task_repo, bouncer_repo, resource_repo)

# topology_service.py
class TopologyService:
    def __init__(self, pipeline_repo, dag_task_repo, bouncer_repo, resource_repo):
        self.pipeline_repo = pipeline_repo
        ...
```

**Fix:** Refactor `TopologyService` and `AirflowService` to accept repos via constructor, add DI factory in `dependencies.py`, and inject into route handlers.

---

### 3.2 AirflowSyncService optional repo parameters with fallback construction

**Severity: Medium**

`AirflowSyncService.__init__` accepts seven optional repo parameters, each with a `or Repository(session)` fallback. This dual-path construction is confusing -- sometimes repos come from DI, sometimes they are internally created.

**Current pattern:**
```python
class AirflowSyncService:
    def __init__(
        self,
        session: AsyncSession,
        pipeline_repo: PipelineRepository | None = None,
        lineage_repo: LineageRepository | None = None,
        # ... 5 more
    ):
        self.pipeline_repo = pipeline_repo or PipelineRepository(session)
```

**Recommended pattern:** Make all repos required parameters. The DI factory in `dependencies.py` already passes them explicitly. For the background task path, construct them explicitly:

```python
class AirflowSyncService:
    def __init__(
        self,
        session: AsyncSession,
        pipeline_repo: PipelineRepository,
        lineage_repo: LineageRepository,
        # ... all required
    ):
```

---

### 3.3 TopologyService loads all pipelines into memory for lookups

**Severity: Medium**

`build_pipeline_topology` and `build_upstream_topology` both call `await self.pipeline_repo.get_all()` which loads all pipeline objects with `selectinload(Pipeline.airflow_status)`. This is used only to build a `{task_id: pipeline}` lookup map. The existing `get_task_id_map()` method in `PipelineRepository` returns a lightweight cached alternative.

**Current pattern:**
```python
all_pipelines = await self.pipeline_repo.get_all()
task_id_to_pipeline = {p.task_id: p for p in all_pipelines if p.task_id}
```

**Recommended pattern:**
```python
task_id_to_pipeline = await self.pipeline_repo.get_task_id_map()
```

**Fix:** Replace both `get_all()` calls in `TopologyService` with `get_task_id_map()`. This uses the cached, lightweight query that already exists.

---

## 4. Backend: APScheduler & Background Tasks

### 4.1 APScheduler 3.x is in maintenance mode -- APScheduler 4 is the modern version

**Severity: Medium**

`pyproject.toml` pins `apscheduler>=3.10.0,<4.0.0`. APScheduler 4.x has been stable since mid-2024 and is the actively developed version with native async support, persistent job stores, and a cleaner API. APScheduler 3.x is in maintenance mode.

**Current pattern:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler()
scheduler.add_job(_guarded_sync, "interval", minutes=20, ...)
```

**Recommended pattern (APScheduler 4):**
```python
from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger

async with AsyncScheduler() as scheduler:
    await scheduler.add_schedule(
        _guarded_sync, IntervalTrigger(minutes=20), id="airflow_sync"
    )
    await scheduler.run_until_stopped()
```

**Fix:** Evaluate APScheduler 4 migration. The current usage is simple enough that migration would be straightforward. The main benefit is native async-first design and active development.

---

### 4.2 Sync lock check is racy

**Severity: Low**

`_guarded_sync()` checks `_sync_lock.locked()` before `async with _sync_lock:`. Between the check and the acquire, another coroutine could acquire the lock. This is a minor issue since the worst case is a log message being skipped, not a concurrent execution.

**Current pattern:**
```python
async def _guarded_sync() -> None:
    if _sync_lock.locked():
        logger.info("Skipping sync — another sync is already running")
        return
    async with _sync_lock:
        ...
```

**Recommended pattern:** Use non-blocking acquire:
```python
async def _guarded_sync() -> None:
    acquired = _sync_lock.acquire(blocking=False)  # not available on asyncio.Lock
```

Since `asyncio.Lock` does not support non-blocking acquire, use a pattern with a flag:
```python
async def _guarded_sync() -> None:
    if _sync_lock.locked():
        logger.info("Skipping sync — another sync is already running")
        return
    async with _sync_lock:
        ...  # The pattern is acceptable -- the race window is negligible in practice
```

**Verdict:** The current pattern is pragmatically fine for this use case. Document the known race window.

---

## 5. Frontend: TypeScript & React

### 5.1 No URL-based routing -- all navigation is in-memory state

**Severity: High**

The entire app uses `useNavigationStore` (Zustand) to track the active tab. There is no URL router (React Router, TanStack Router, etc.). This means:

- Users cannot bookmark or share direct links to specific tabs or pipelines
- Browser back/forward buttons do not work
- Deep linking to a specific pipeline detail view is impossible
- SSO redirects lose the user's navigation context

**Current pattern (`App.tsx`):**
```tsx
const activeTab = useNavigationStore((s) => s.activeTab);
// ... conditional rendering based on activeTab
{activeTab === "catalog" && <PipelineRegistry />}
{activeTab === "matrix" && <SchemaMatrixView />}
```

**Recommended pattern:** Adopt TanStack Router (type-safe, modern) or React Router v7:

```tsx
import { createBrowserRouter, RouterProvider } from "react-router-dom";

const router = createBrowserRouter([
  { path: "/", element: <AppShell />, children: [
    { index: true, element: <PipelineRegistry /> },
    { path: "pipelines/:id", element: <BentoWorkspace /> },
    { path: "matrix", element: <SchemaMatrixView /> },
    { path: "dags", element: <DagSummaryView /> },
    { path: "admin", element: <AdminView /> },
  ]},
]);
```

**Fix:** This is a significant refactor but high-value. TanStack Router would pair well with the existing TanStack Query setup. Implement incrementally -- start with top-level tab routes, then add pipeline detail routes.

---

### 5.2 No use of React 19 features

**Severity: Medium**

The project targets React 19 (`"react": "^19.0.0"`) but does not use any React 19-specific features:

- **`use()` hook** for reading context/promises in render -- could simplify some Suspense patterns
- **`useActionState`** (formerly `useFormState`) for form submission state management
- **`useOptimistic`** for optimistic UI updates (e.g., pipeline description edits)
- **Server Components** are not applicable (Vite SPA), but **Actions** are
- **`ref` as a prop** (no more `forwardRef`) -- the codebase already avoids `forwardRef`, which is good

**Recommended adoption (useOptimistic):**
```tsx
function EditableDescription({ description, onSave }) {
  const [optimisticDesc, setOptimisticDesc] = useOptimistic(description);

  async function handleSave(newDesc: string) {
    setOptimisticDesc(newDesc);
    await onSave(newDesc);
  }
  // render optimisticDesc instead of waiting for server response
}
```

**Fix:** Evaluate `useOptimistic` for the pipeline update flow and `useActionState` for the admin forms. These are incremental adoptions.

---

### 5.3 `tsconfig.json` targets ES2020 -- should target ES2023+

**Severity: Low**

`"target": "ES2020"` and `"lib": ["ES2020", ...]` are conservative. Since the project uses Vite (which handles transpilation) and modern browsers, targeting ES2023 or ESNext provides access to features like `Array.findLast()`, `Object.groupBy()`, and `using` declarations in type checking.

**Current:**
```json
"target": "ES2020",
"lib": ["ES2020", "DOM", "DOM.Iterable"]
```

**Recommended:**
```json
"target": "ES2023",
"lib": ["ES2023", "DOM", "DOM.Iterable"]
```

**Fix:** Update `tsconfig.json`. Vite handles the actual transpilation to the browser target, so this only affects TypeScript's type checking and available built-in types.

---

### 5.4 `ErrorBoundary` uses class component -- could use library

**Severity: Low**

`ErrorBoundary.tsx` uses a class component (required for `componentDidCatch`). While React 19 still requires class components for error boundaries, libraries like `react-error-boundary` provide a cleaner API with `useErrorBoundary` hook.

**Verdict:** The current implementation is fine. This is cosmetic. Monitor React 19.x for potential `use()` based error boundary support.

---

## 6. Frontend: TanStack Query & Zustand

### 6.1 Conflicting Axios response interceptors for retry logic

**Severity: High**

`api/client.ts` registers two response error interceptors:

1. **First interceptor (lines 20-36):** Retries 502/503/504 up to 2 times with 1s delay
2. **Second interceptor (lines 38-74):** Handles 401 with token refresh, and also catches 503

These interceptors chain sequentially. A 503 error will:
1. Be retried twice by interceptor 1 (with 1s delays)
2. If still failing, be caught by interceptor 2 (which just logs a warning and rejects)

A 401 error will:
1. Pass through interceptor 1 (not a 5xx, so not retried)
2. Be caught by interceptor 2 (which waits 2s for token refresh)

The 503 dual-handling is redundant but harmless. The real issue is that the retry interceptor uses `_retryCount` on the config object, and the auth interceptor uses `_retry` -- different flags, no coordination.

**Fix:** Consolidate into a single response interceptor with clear precedence:
```typescript
apiClient.interceptors.response.use(undefined, async (error) => {
  const config = error.config;
  const status = error.response?.status;

  // 1. Auth errors -- handle first (no retry)
  if (status === 401 && !config?._authRetried) {
    config._authRetried = true;
    // ... token refresh logic
  }

  // 2. Transient server errors -- retry
  if (config && (!status || status >= 500)) {
    config._retryCount = config._retryCount ?? 0;
    if (config._retryCount < 2) {
      config._retryCount += 1;
      await new Promise(r => setTimeout(r, 1000));
      return apiClient(config);
    }
  }

  return Promise.reject(error);
});
```

---

### 6.2 Zustand stores use `Set<string>` which is not serializable

**Severity: Low**

`pipeline-store.ts` uses `Set<string>` for filter state (`teamFilters`, `dagFilters`, `statusFilters`). While Zustand handles this correctly at runtime, Sets are not JSON-serializable, which prevents using Zustand's `persist` middleware if URL-based state or localStorage persistence is ever needed.

**Current pattern:**
```typescript
teamFilters: new Set<string>(),
```

**Recommended pattern (if persistence is needed):**
```typescript
teamFilters: [] as string[],
// or keep Set but add a custom serializer to persist middleware
```

**Verdict:** Acceptable for now since persist middleware is not in use. Flag for future routing integration.

---

### 6.3 TanStack Query patterns are idiomatic and well-structured

**Severity: N/A (Positive finding)**

The hooks layer (`frontend/src/hooks/`) follows TanStack Query v5 best practices:
- `useInfiniteQuery` with proper `initialPageParam` and `getNextPageParam` for pagination
- `keepPreviousData` (renamed from v4's `keepPreviousData` option to `placeholderData` -- correctly used)
- `useMutation` with proper `onSuccess` invalidation chains
- Separate `queryKey` arrays with proper dependencies
- `staleTime` configured per-query based on data volatility

---

### 6.4 Zustand stores are lean and well-separated

**Severity: N/A (Positive finding)**

Each store has a single responsibility and no cross-store imports (except `pipeline-store.ts` correctly calling `useRunSelectorStore.getState().clearRun()`). The `create<State>()` pattern is the current Zustand v5 standard.

---

## 7. Frontend: Build & Configuration

### 7.1 Vite config is well-optimized with manual chunking

**Severity: N/A (Positive finding)**

`vite.config.ts` correctly:
- Uses `@tailwindcss/vite` plugin (Tailwind v4 standard)
- Defines `manualChunks` for vendor splitting (react, query, UI)
- Sets up dev proxy to backend
- Uses path aliases matching `tsconfig.json`

---

### 7.2 Missing Vite build target configuration

**Severity: Low**

No explicit `build.target` is set in `vite.config.ts`. Vite defaults to `['es2020', 'edge88', 'firefox78', 'chrome87', 'safari14']`. For a corporate internal tool, a more modern target could enable smaller bundles:

```typescript
build: {
  target: 'es2022',  // or 'esnext' for bleeding edge
  // ... existing config
}
```

---

### 7.3 Source maps disabled in production build

**Severity: Low**

`sourcemap: false` in `vite.config.ts` is fine for production, but consider `sourcemap: 'hidden'` to generate source maps for error tracking (e.g., Sentry) without exposing them to browsers.

---

## 8. Infrastructure: Docker & Deployment

### 8.1 Frontend Dockerfile uses `node:20-alpine` -- should be Node 22

**Severity: Medium**

Node.js 20 enters maintenance mode in October 2026 and EOL in April 2027. Node 22 is the current active LTS.

**Current:**
```dockerfile
FROM node:20-alpine AS dev
```

**Recommended:**
```dockerfile
FROM node:22-alpine AS dev
```

---

### 8.2 Production docker-compose lacks backend port exposure

**Severity: N/A (Positive finding -- secure by default)**

`docker-compose.prod.yml` does not expose `backend:8000` directly. The frontend Nginx container proxies `/api/` to the backend via Docker networking. This is correct for production.

---

### 8.3 Dev docker-compose frontend uses `target: production` -- rebuilds entire prod image on watch

**Severity: Medium**

`docker-compose.yml` builds the frontend with `target: production`, which runs the full build pipeline and serves via Nginx. Combined with `develop.watch` that triggers `action: rebuild` on any source file change, this means every code change rebuilds the entire Docker image.

**Current:**
```yaml
frontend:
  build:
    target: production
  develop:
    watch:
      - action: rebuild
        path: ./frontend/src
```

**Recommended:** Use `target: dev` for local development with Vite's HMR:
```yaml
frontend:
  build:
    target: dev
  command: pnpm dev --host 0.0.0.0
  develop:
    watch:
      - action: sync
        path: ./frontend/src
        target: /app/src
```

---

### 8.4 Backend Dockerfile copies all files including potential secrets

**Severity: Low**

`COPY . .` in the backend Dockerfile copies everything. While a `.dockerignore` likely exists, verify it excludes `.env`, `.env.prod`, credentials, and test fixtures.

**Fix:** Verify `.dockerignore` exists and contains:
```
.env*
.git
__pycache__
*.pyc
tests/
```

---

## 9. Package Management & Dependencies

### 9.1 PySpark pinned to exact version 3.5.1

**Severity: Low**

`pyspark==3.5.1` is an exact pin while all other dependencies use minimum-version ranges. PySpark 3.5.x has had patch releases with bug fixes. Consider `pyspark>=3.5.1,<3.6`.

---

### 9.2 `slowapi` rate limiter is in maintenance mode

**Severity: Low**

`slowapi` (last release: 2023) wraps `limits` and has not been updated for recent FastAPI versions. FastAPI's ecosystem has matured -- consider `fastapi-limiter` or implementing rate limiting directly with `limits` library + middleware.

**Verdict:** No urgent action needed. The integration is minimal (one file, `rate_limit.py`). Monitor for deprecation.

---

### 9.3 Frontend dependencies are current and well-maintained

**Severity: N/A (Positive finding)**

All major frontend dependencies are at recent versions:
- React 19.0, TanStack Query 5.90, Zustand 5.0, Vite 6.0
- TypeScript 5.7, Tailwind CSS 4.2
- Playwright 1.58 for E2E testing

---

## 10. Cross-Cutting Concerns

### 10.1 O(n^2) BFS using `list.pop(0)` instead of `collections.deque`

**Severity: High**

Five BFS implementations in `graph_builder.py` and `bouncer_service.py` use `queue.pop(0)` on a Python `list`. `list.pop(0)` is O(n) because it shifts all remaining elements, making the overall BFS O(n^2). `collections.deque.popleft()` is O(1).

**Current pattern (5 occurrences in `graph_builder.py`):**
```python
queue: list[str] = [root_task_id]
while queue:
    tid = queue.pop(0)
```

**Recommended pattern:**
```python
from collections import deque

queue: deque[str] = deque([root_task_id])
while queue:
    tid = queue.popleft()
```

**Files:**
- `backend/app/services/graph_builder.py` lines 48, 96, 151, 204
- `backend/app/services/bouncer_service.py` line 107

**Fix:** Replace `list` with `deque` in all five BFS functions. This is a trivial, zero-risk change.

---

### 10.2 IcebergClient uses synchronous Spark calls in async context

**Severity: High**

`IcebergClient` methods (`list_tables_in_namespace`, `get_table_schema`, `get_all_schemas`) make synchronous PySpark/JVM calls (e.g., `spark.sql(...).collect()`, `spark.table(...).schema`) that block the asyncio event loop. These are called from `CatalogSyncService.sync_from_catalog()` which is an async method.

**Current pattern:**
```python
async def sync_from_catalog(self) -> int:
    schemas = iceberg_client.get_all_schemas()  # Blocks event loop!
```

**Recommended pattern:**
```python
import asyncio

async def sync_from_catalog(self) -> int:
    schemas = await asyncio.to_thread(iceberg_client.get_all_schemas)
```

**Fix:** Wrap all synchronous `IcebergClient` calls with `asyncio.to_thread()` to offload blocking JVM operations to the thread pool. The `IcebergClient` itself should remain synchronous (PySpark is not async-aware), but the callers must use `to_thread`.

---

### 10.3 In-memory TTL cache not safe for multi-process deployment

**Severity: Medium**

The `TTLCache` in `cache.py` is a plain in-memory dict. In production with multiple Uvicorn workers (`--workers N`), each process has an independent cache, leading to inconsistent reads and wasted memory. Currently, the prod Dockerfile runs a single worker (`exec uv run uvicorn ... --host 0.0.0.0 --port 8000`), so this is not an active issue.

**Recommendation:** Document that multi-worker deployment requires migrating to Redis or shared cache. Alternatively, add `--workers 1` explicitly to the production command to make the single-worker assumption explicit.

---

### 10.4 CSP header in nginx.conf blocks Keycloak SSO

**Severity: Medium**

The Content-Security-Policy header in `nginx.conf` restricts `connect-src` to `'self'`:

```
connect-src 'self'
```

When SSO is enabled, the frontend needs to connect to the Keycloak server (different origin). This would block OIDC token requests and JWKS fetching from the browser.

**Fix:** Add the Keycloak origin to `connect-src`:
```
connect-src 'self' ${SSO_ISSUER_URL}
```

Or use the `docker-entrypoint.sh` to inject the CSP dynamically based on environment variables.

---

### 10.5 `@fontsource-variable/geist` imported but `body` uses Inter

**Severity: Low**

`index.css` imports `@fontsource-variable/geist` but sets the body font to `"Inter", system-ui, ...`. Either switch to Geist or remove the import to reduce bundle size.

---

## Summary

| Severity | Count | Key Items |
|----------|-------|-----------|
| **Critical** | 0 | |
| **High** | 5 | Auto-commit on reads, DI bypass in TopologyService/AirflowService, conflicting Axios interceptors, O(n^2) BFS, sync Spark in async context |
| **Medium** | 8 | Annotated DI, domain exceptions unused, APScheduler 3.x, Node 20, dev frontend rebuild, CSP blocks SSO, datetime Z workaround, AirflowSyncService optional repos |
| **Low** | 8 | StrEnum adoption, TTLCache typing, tsconfig target, source maps, PySpark pin, slowapi maintenance, Alembic star import, font import mismatch |

### Recommended Priority

1. **Immediate wins (low effort, high impact):** BFS `deque` fix, remove `.replace("Z", "+00:00")`, wrap IcebergClient with `asyncio.to_thread`
2. **Architecture improvements:** Fix auto-commit on reads, refactor TopologyService/AirflowService DI, consolidate Axios interceptors
3. **Modernization (incremental):** `Annotated` DI types, URL-based routing, `StrEnum` adoption, APScheduler 4 migration
4. **Infrastructure:** Upgrade to Node 22, fix dev docker-compose frontend target, fix CSP for SSO
