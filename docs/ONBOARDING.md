# Developer Onboarding Guide

Welcome to EtlNexus — a data architecture command center for discovering, understanding, and utilizing ETL pipelines. This guide covers everything a new team needs to start building features.

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  Frontend (React 19 + Vite)                                          │
│  ┌───────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────┐    │
│  │ Zustand   │  │ TanStack     │  │ Axios API   │  │ shadcn/ui  │    │
│  │ (UI state)│  │ Query (data) │  │ (HTTP layer)│  │ (base-ui)  │    │
│  └───────────┘  └──────────────┘  └─────────────┘  └────────────┘    │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ REST API
┌────────────────────────────▼────────────────────────────────────────────┐
│  Backend (FastAPI + async SQLAlchemy)                                   │
│                                                                         │
│  Router (HTTP) ──► Service (business logic) ──► Repository (SQL)        │
│                                                                         │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐       │
│  │ Auth/RBAC │  │ APScheduler  │  │ Integrations │  │ Redis     │       │
│  │ (JWT+SSO) │  │ (bg tasks)   │  │ (Airflow,    │  │ (cache    │       │
│  │           │  │              │  │  Iceberg,LLM)│  │  bus)     │       │
│  └───────────┘  └──────────────┘  └──────────────┘  └───────────┘       │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  PostgreSQL 16  │
                    └─────────────────┘
```

### Backend Layer Pattern

Every feature follows: **Router → Service → Repository**

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Router | `backend/app/routers/` | HTTP endpoints, request validation, auth dependencies |
| Service | `backend/app/services/` | Business logic, orchestration, caching |
| Repository | `backend/app/repositories/` | Async SQLAlchemy queries, data access |
| Model | `backend/app/models/` | ORM table definitions |
| Schema | `backend/app/schemas/` | Pydantic request/response DTOs |

### Frontend Layer Pattern

Every feature follows: **Type → API → Hook → Component**

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Type | `frontend/src/types/` | TypeScript interfaces mirroring Pydantic schemas |
| API | `frontend/src/api/` | Axios functions per domain |
| Hook | `frontend/src/hooks/` | TanStack Query wrappers (server state) |
| Store | `frontend/src/stores/` | Zustand stores (client-only UI state) |
| Component | `frontend/src/components/` | React components organized by feature |

---

## 2. Running the System

### Full Stack (all integrations)

```bash
docker compose up        # Start everything
docker compose watch     # Start with hot-reload file watching
```

Services: `db`, `redis`, `backend`, `frontend`, `airflow-*`, `keycloak`, `iceberg-*`

### Limited Mode (no Airflow, no Keycloak, no Iceberg)

You only need three containers. Create a `.env` file:

```env
# .env (minimal)
DATABASE_URL=postgresql+asyncpg://etlnexus:etlnexus@db:5432/etlnexus
SSO_ENABLED=false
SCHEDULER_ENABLED=false
SPARK_CONNECT_URL=
REDIS_URL=
OASIS_PROD_DATABASE_URL=
LLM_API_BASE_URL=
DEPLOYMENT_ENV=development
```

Then run only the core services:

```bash
docker compose up db backend frontend
```

The app starts and is fully functional:
- `SSO_ENABLED=false` → all requests get default admin user (no Keycloak needed)
- `SCHEDULER_ENABLED=false` → no background sync jobs attempt to reach Airflow/Spark Connect
- Empty `SPARK_CONNECT_URL` → catalog sync no-ops
- Empty `REDIS_URL` → falls back to in-memory caching (fine for single instance)

### Backend Only (local development)

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Only (local development)

```bash
cd frontend
pnpm install
pnpm dev    # http://localhost:5173
```

---

## 3. Authentication & Authorization

### Roles

| Role | Access |
|------|--------|
| `admin` | Full system access, bypasses all checks |
| `member` | Team-scoped access, can edit own team's pipelines |
| `viewer` | Read-only within team scope |

### How Auth Works

**SSO Enabled (production):**
1. Frontend uses `react-oidc-context` to authenticate via Keycloak
2. Backend validates JWT via `get_current_user` dependency
3. User is JIT-provisioned on first login (user + teams synced from JWT claims)
4. Role extracted from configurable JWT claim path

**SSO Disabled (development):**
- All requests return a default admin user with `is_beta=true`
- No token validation, no Keycloak required

### Backend Auth Dependencies

Use these in route definitions to gate access:

```python
from app.auth import get_current_user, require_role, require_feature_flag
from app.auth import require_team_membership_or_editor_grant

# Any authenticated user
@router.get("/pipelines")
async def list(user: User = Depends(get_current_user)): ...

# Admin only
@router.delete("/pipelines/{id}", dependencies=[Depends(require_role("admin"))])

# Team member or editor grant holder
@router.patch("/pipelines/{id}",
    dependencies=[Depends(require_team_membership_or_editor_grant("pipeline_id"))])

# Feature flag gate (admins bypass)
@router.get("/beta-feature", dependencies=[Depends(require_feature_flag("my_flag"))])
```

### Pipeline Visibility

Non-admin users can see:
1. Pipelines owned by their team (`team_id` matches)
2. Unassigned pipelines (`team_id IS NULL`)
3. Pipelines/teams granted via `visibility_grants` table

The `can_edit` field on `PipelineDetail` is resolved server-side and consumed by frontend components.

---

## 4. Feature Flags

Feature flags allow gradual rollout of features to specific users.

### Database Model

```
feature_flags table:
  id        UUID PRIMARY KEY
  name      VARCHAR UNIQUE   -- e.g., "dag_dashboard"
  enabled   BOOLEAN          -- global on/off
  beta_only BOOLEAN          -- if true, requires user.is_beta=true
```

### Access Logic

```
User wants to access feature X:
  1. Is user admin? → ALLOW (admins bypass everything)
  2. Is flag enabled? → if not, DENY
  3. Is flag beta_only? → if yes, check user.is_beta
  4. All checks pass → ALLOW
```

### Backend: Gate an Endpoint

```python
@router.get("/my-feature", dependencies=[Depends(require_feature_flag("my_feature"))])
async def my_feature_endpoint(...): ...
```

### Frontend: Gate a UI Element

```tsx
import { useFeatureFlagCheck } from "@/hooks/use-feature-flags";
import { isAdmin } from "@/lib/permissions";
import { useAuthStore } from "@/stores/auth-store";

function MyComponent() {
  const user = useAuthStore((s) => s.user);
  const { data: flag } = useFeatureFlagCheck("my_feature");

  // Show if admin OR if feature flag accessible to this user
  const showFeature = isAdmin(user) || flag?.accessible;

  return showFeature ? <MyFeatureUI /> : null;
}
```

### Managing Flags

- **Create/update flags:** `PUT /api/feature-flags/{id}` (admin only)
- **Toggle user beta access:** `PATCH /api/users/{id}/beta` (admin only)
- **Admin panel UI:** UsersPanel has a flask icon to toggle beta per user

### Current Flags

| Flag Name | Purpose | Default State |
|-----------|---------|---------------|
| `dag_dashboard` | DAG Summary tab visibility | `enabled=false, beta_only=true` |
| `bouncer_dashboard` | Bouncers tab visibility | `enabled=false, beta_only=true` |

---

## 5. Gating UI Features by Role

### Pattern 1: Admin-Only Content

```tsx
import { isAdmin } from "@/lib/permissions";
import { useAuthStore } from "@/stores/auth-store";

function MyPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div>
      <PublicContent />
      {isAdmin(user) && <AdminOnlySection />}
    </div>
  );
}
```

**Real example** — Admin tab in `App.tsx`:
```tsx
{activeTab === "admin" && isAdmin(user) && (
  <Suspense fallback={<TabSkeleton />}>
    <AdminView />
  </Suspense>
)}
```

### Pattern 2: Feature-Flag-Gated Tabs

**Real example** — Sidebar.tsx:
```tsx
const { data: dagFlag } = useFeatureFlagCheck("dag_dashboard");
const { data: bouncerFlag } = useFeatureFlagCheck("bouncer_dashboard");
const showDags = isAdmin(user) || dagFlag?.accessible;
const showBouncers = isAdmin(user) || bouncerFlag?.accessible;

{showDags && (
  <NavIcon icon={<BarChart3 />} tooltip="DAG Summary" ... />
)}
```

### Pattern 3: Edit Permissions via `can_edit`

The backend resolves whether the current user can edit a pipeline (based on team membership or editor grants). The frontend receives this as a boolean and passes it through:

```tsx
// In BentoWorkspace.tsx
<BentoHeader pipeline={pipeline} canEdit={pipeline.can_edit} />
<SchemaViewer pipeline={pipeline} canEdit={pipeline.can_edit} />
<DocumentationPreview pipeline={pipeline} canEdit={pipeline.can_edit} />

// Inside a component:
function SchemaViewer({ canEdit }: { canEdit: boolean }) {
  return (
    <div>
      <SchemaTable />
      {canEdit && <EditSchemaButton />}
    </div>
  );
}
```

---

## 6. Showing/Hiding Bento Workspace Sections

The bento workspace (`BentoWorkspace.tsx`) renders a **12-column CSS grid** of cards. Each card can be conditionally rendered.

### Current Conditional Logic

```tsx
// 1. By pipeline property
{pipeline.topology_enabled && (
  <LineageTopology pipelineId={pipeline.id} />
)}

// 2. By pipeline type (API vs ETL)
{isApiPipeline(pipeline.pipeline_type) ? (
  <>{/* API layout: SchemaViewer + UsageCard */}</>
) : (
  <>{/* ETL layout: ResourcePerformance + TransformInspector + SchemaViewer + UsageCard */}</>
)}

// 3. By edit permission
{canEdit && <PipelineSettingsModal />}
```

### Adding a Role-Gated Bento Card

**Step 1:** Create the component:

```tsx
// frontend/src/components/bento-workspace/MyAdminCard.tsx
interface MyAdminCardProps {
  pipelineId: string;
}

export function MyAdminCard({ pipelineId }: MyAdminCardProps) {
  return (
    <div className="col-span-12 bg-card border border-border rounded-2xl p-5">
      <h3 className="text-sm font-medium text-foreground mb-3">Admin Insights</h3>
      {/* Card content */}
    </div>
  );
}
```

**Step 2:** Add to BentoWorkspace with role check:

```tsx
import { useAuthStore } from "@/stores/auth-store";
import { isAdmin } from "@/lib/permissions";
import { MyAdminCard } from "./MyAdminCard";

function BentoWorkspace() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="grid grid-cols-12 gap-6">
      {/* ... existing cards ... */}

      {/* Admin-only card */}
      {isAdmin(user) && (
        <MyAdminCard pipelineId={pipeline.id} />
      )}
    </div>
  );
}
```

**Step 3 (optional):** Gate with feature flag instead of role:

```tsx
const { data: myFlag } = useFeatureFlagCheck("my_new_feature");
const showMyCard = isAdmin(user) || myFlag?.accessible;

{showMyCard && <MyAdminCard pipelineId={pipeline.id} />}
```

### Grid Layout Rules

| Span | CSS Class | Use Case |
|------|-----------|----------|
| Full width | `col-span-12` | Topology, documentation |
| 7/5 split | `col-span-12 lg:col-span-7` + `lg:col-span-5` | Schema + Usage |
| Half/half | `col-span-12 lg:col-span-6` | Equal two-column |
| Always mobile-first | Base `col-span-12` + `lg:` breakpoint | Responsive |

---

## 7. Adding a New Feature (End-to-End Checklist)

### Backend

1. **Model** — `backend/app/models/my_entity.py` (SQLAlchemy ORM)
2. **Migration** — `uv run alembic revision --autogenerate -m "add my_entity"`
3. **Repository** — `backend/app/repositories/my_entity_repo.py` (async queries)
4. **Schema** — `backend/app/schemas/my_entity.py` (Pydantic DTOs)
5. **Service** — `backend/app/services/my_entity_service.py` (business logic)
6. **Router** — `backend/app/routers/my_entity.py` (endpoints under `/api/`)
7. **Register** — Add to `backend/app/models/__init__.py`, `backend/app/main.py` (include_router), `backend/app/dependencies.py` (DI factories)

### Frontend

1. **Type** — `frontend/src/types/my-entity.ts` (mirrors Pydantic schema)
2. **API** — `frontend/src/api/my-entity.ts` (Axios CRUD functions)
3. **Hook** — `frontend/src/hooks/use-my-entity.ts` (TanStack Query wrapper)
4. **Component** — `frontend/src/components/my-feature/MyComponent.tsx`
5. **Wire up** — Import into workspace, registry, or App.tsx

### Feature-Flagging It

1. Insert row: `INSERT INTO feature_flags (name, enabled, beta_only) VALUES ('my_feature', false, true);`
2. Backend: Add `dependencies=[Depends(require_feature_flag("my_feature"))]` to router
3. Frontend: Use `useFeatureFlagCheck("my_feature")` to conditionally render
4. Enable for beta testers first, then flip `enabled=true, beta_only=false` for GA

---

## 8. Deploying Without Airflow (Limited Capacity)

When you don't have Airflow, Iceberg, or other external integrations, the system runs in "manual mode" — pipelines and schemas are created via the API instead of being discovered automatically.

### Configuration

```env
SCHEDULER_ENABLED=false      # No background sync jobs
SSO_ENABLED=false            # Or true with real Keycloak
SPARK_CONNECT_URL=           # Empty = no catalog sync
AIRFLOW_BASE_URL=http://localhost:8080/api/v1  # Can point anywhere, won't be called
```

### What Happens

- App starts normally, logs "SSO disabled" warning
- No startup sync runs (no Airflow health check wait)
- No scheduled jobs (no pipeline discovery, no status polling)
- Database starts empty — you populate it via API

### Creating Data Manually

**Create a data product (pipeline without Airflow backing):**
```bash
curl -X POST http://localhost:8000/api/data-products \
  -H "Content-Type: application/json" \
  -d '{"name": "My Pipeline", "description": "Daily customer sync", "schedule_type": "daily"}'
```

**Set schema manually:**
```bash
curl -X PUT http://localhost:8000/api/pipelines/{id}/fields \
  -H "Content-Type: application/json" \
  -d '{"fields": [
    {"name": "customer_id", "data_type": "bigint", "ordinal_position": 0},
    {"name": "email", "data_type": "string", "ordinal_position": 1}
  ]}'
```

**Set manual lineage (writes_to/reads_from):**
```bash
curl -X PATCH http://localhost:8000/api/pipelines/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "writes_to_manual": ["warehouse.customers", "warehouse.audit_log"],
    "reads_from_manual": ["staging.raw_customers"]
  }'
```

### Sync Safety

When you later connect Airflow/Iceberg, the system respects manual overrides:
- `schema_manually_edited=true` → catalog sync skips that pipeline
- `writes_to_manual` set → airflow sync won't regenerate writes_to edges
- `is_data_product=true` → pipeline won't be overwritten by Airflow discovery

### Minimal Docker Compose

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: etlnexus
      POSTGRES_PASSWORD: etlnexus
      POSTGRES_DB: etlnexus
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://etlnexus:etlnexus@db:5432/etlnexus
      SSO_ENABLED: "false"
      SCHEDULER_ENABLED: "false"
      SPARK_CONNECT_URL: ""
      REDIS_URL: ""
    ports:
      - "8000:8000"
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "5173:80"
    depends_on:
      - backend
```

---

## 9. Key Files Reference

| Purpose | File |
|---------|------|
| All config options | `backend/app/config.py` |
| Auth dependencies (role gates, feature flags) | `backend/app/auth.py` |
| Dependency injection factories | `backend/app/dependencies.py` |
| Router registration | `backend/app/main.py` |
| Frontend permission helpers | `frontend/src/lib/permissions.ts` |
| Feature flag hook | `frontend/src/hooks/use-feature-flags.ts` |
| Tab gating (sidebar) | `frontend/src/components/layout/Sidebar.tsx` |
| Tab routing | `frontend/src/App.tsx` |
| Bento workspace layout | `frontend/src/components/bento-workspace/BentoWorkspace.tsx` |
| Pipeline types | `frontend/src/types/pipeline.ts` |
| Auth store | `frontend/src/stores/auth-store.ts` |
| Navigation store | `frontend/src/stores/navigation-store.ts` |
| Pipeline store (filters) | `frontend/src/stores/pipeline-store.ts` |
| Docker dev setup | `docker-compose.yml` |
| Docker prod setup | `docker-compose.prod.yml` |
| Offline image import | `etlnexus-images/import-images.sh` |

---

## 10. Common Patterns Quick Reference

### Adding a new tab to the sidebar

1. Add constant in `frontend/src/lib/constants.ts`:
   ```ts
   export const TABS = { ..., MY_TAB: "my-tab" };
   ```
2. Add to valid tabs in `frontend/src/stores/navigation-store.ts`
3. Add NavIcon in `frontend/src/components/layout/Sidebar.tsx` (with optional feature-flag gate)
4. Add tab rendering in `frontend/src/App.tsx`

### Adding a new API endpoint

1. Create router: `backend/app/routers/my_thing.py`
2. Register: `app.include_router(my_thing.router)` in `main.py`
3. Frontend API: `frontend/src/api/my-thing.ts`
4. Frontend hook: `frontend/src/hooks/use-my-thing.ts`

### Requiring authentication on an endpoint

All endpoints already require auth via `get_current_user`. The only exceptions are:
- `GET /health` (liveness probe)
- `GET /api/auth/config` (SSO configuration for frontend bootstrap)
