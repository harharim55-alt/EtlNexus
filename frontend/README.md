# EtlNexus Frontend

A dark-themed data architecture command center for discovering, understanding, and utilizing ETL pipelines. The frontend provides a "bento-box" UI with a master-detail layout, pipeline lineage visualization, schema browsing, join intelligence, and an AI architect terminal.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Pages and Views](#pages-and-views)
4. [Component Hierarchy](#component-hierarchy)
5. [State Management](#state-management)
6. [API Layer](#api-layer)
7. [Styling](#styling)
8. [Testing](#testing)
9. [Development](#development)
10. [Key Conventions](#key-conventions)

---

## Overview

**Stack:** React 19, TypeScript, Vite, pnpm, Tailwind CSS v4, shadcn/ui (base-ui variant), TanStack Query v5, Zustand v5, Axios, Lucide icons, oidc-client-ts, react-oidc-context.

The application is a single-page app with a fixed vertical sidebar that switches between six views via a tab system. All views are code-split with `React.lazy` and `Suspense`. A global `ErrorBoundary` wraps the entire tree to catch unhandled render errors.

Authentication supports two modes:
- **SSO disabled** (default for local dev): a synthetic `default-admin` user is injected into the auth store and all requests proceed without a token.
- **SSO enabled** (docker-compose): Keycloak OIDC via `react-oidc-context` with automatic silent renewal.

The backend's REST API is consumed exclusively through TanStack Query hooks (server state) and an Axios client. No Redux. Client-only UI state (selected pipeline, filters, chat history, onboarding step, etc.) lives in Zustand stores.

---

## Architecture

```
                         ┌────────────────────────────────────────────────┐
                         │                    React Tree                   │
                         │                                                  │
                         │  ErrorBoundary                                   │
                         │  └─ QueryClientProvider (TanStack Query)         │
                         │     └─ TooltipProvider                           │
                         │        └─ AuthBootstrap                          │
                         │           └─ [OidcAuthProvider?]                 │
                         │              └─ AuthGuard / SSOGuard             │
                         │                 └─ AppContent                    │
                         │                    ├─ AppShell (Sidebar)         │
                         │                    └─ [Active View via lazy()]   │
                         │                       └─ OnboardingOverlay       │
                         └────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────────────────────┐
  │                          State Layers                                  │
  │                                                                        │
  │  TanStack Query (server state)        Zustand (client UI state)       │
  │  ─────────────────────────────        ──────────────────────────       │
  │  • Automatic caching & staleTime      • navigation-store (activeTab)  │
  │  • Infinite scroll / pagination       • pipeline-store (selection,    │
  │  • Background refetch every 5 min       filters, search)              │
  │  • Optimistic invalidation on         • auth-store (user, token,      │
  │    mutations                            ssoEnabled)                   │
  │  • 30s global staleTime              • date-range-store (preset,      │
  │  • retry: 2, no window focus refetch   dateFrom, dateTo)              │
  │                                       • bouncer-store (selection,     │
  │                                         topologyMode)                 │
  │                                       • ai-store (messages, typing)   │
  │                                       • onboarding-store (step,       │
  │                                         direction, localStorage)      │
  └────────────────────────────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────────────────────┐
  │                          API Layer                                     │
  │                                                                        │
  │  src/api/client.ts  (Axios, baseURL=/api, timeout=30s)                │
  │  ├─ Request interceptor: attach Bearer token from auth-store           │
  │  ├─ Response interceptor 1: retry 502/503/504 up to 2x with 1s delay  │
  │  └─ Response interceptor 2: on 401, wait 2s for silent token renewal  │
  │       then retry; if token unchanged, trigger OIDC signout            │
  │                                                                        │
  │  src/api/*.ts  (one file per domain, typed with src/types/*.ts)       │
  └────────────────────────────────────────────────────────────────────────┘
```

### Application Bootstrap Sequence

1. `main.tsx` creates the `QueryClient` with global defaults (30s staleTime, 2 retries, no window-focus refetch) and mounts `<App>`.
2. `App` wraps everything in `AuthBootstrap`, which calls `GET /api/auth/config` on mount.
3. If SSO is disabled (or the config endpoint is unavailable), a default admin user is set into the auth store immediately and children render without an OIDC provider.
4. If SSO is enabled, `OidcAuthProvider` is injected and `SSOGuard` manages the OIDC redirect flow, token syncing, and user info fetching via `useCurrentUser`.
5. Once authenticated, `AppContent` renders `AppShell` (sidebar) and the active tab view.
6. `OnboardingOverlay` is always present in the tree — it renders a full-screen overlay only when `useOnboardingStore.isActive` is true.

---

## Pages and Views

All views are lazy-loaded and gated by `activeTab` from `useNavigationStore`. The `catalog` tab renders both the registry list and the workspace detail panel side-by-side.

### Pipeline Registry (`catalog`)

The master list of all ETL pipelines discovered from Airflow. Implemented in `PipelineRegistry` with four sub-components: `PipelineSearch` (controlled text input), `PipelineFilters` (team/DAG/status facets), `PipelineListItem` (individual row with status dot, team badge, schedule), and a virtualized scroll container powered by `@tanstack/react-virtual`. Data loads via `usePipelines`, which uses an infinite query (page size 50) that re-fetches every 5 minutes and preserves previous data during navigation. Typing in the search box debounces naturally through TanStack Query's `keepPreviousData`. When a pipeline is selected, its ID is set in `usePipelineStore` and the Bento Workspace renders to the right.

### Bento Workspace (`catalog`, detail panel)

The detail view that renders to the right of the registry list when a pipeline is selected. Implemented in `BentoWorkspace`, which reads `selectedPipelineId` from `usePipelineStore`, fetches the pipeline via `usePipelineDetail`, then renders a 12-column CSS grid of cards. The layout differs by pipeline type:

- **ETL pipelines**: `BentoHeader` (editable name/description, team badge, metadata pills, docs button) → `LineageTopology` (DAG-level upstream lineage with a separate `UpstreamTopologyModal`) → `MetricsCards` (rows/day, schedule) → `ResourcePerformanceCard` (Spark allocation vs actual) → `TransformInspectorCard` (Spark execution plan tree) → `SchemaViewer` + `UsageCard` → `JoinIntelligence` + `ConsumeSnippet`.
- **API pipelines**: `LineageTopology` full-width → `UsageCard` + `ConsumeSnippet` side by side (no resource, execution plan, schema, or join cards).

The `DocumentationModal` opens as a full-screen overlay from `BentoHeader` with edit/preview toggle, GFM markdown rendering via `react-markdown` + `rehype-sanitize`, syntax highlighting, and a revision history panel.

### Global Schema Matrix (`matrix`)

A cross-pipeline field frequency table rendered by `SchemaMatrixView`. Data loads via `useSchemaMatrix`, an infinite query (page size 100) that loads additional pages as the user scrolls. The visible rows use `@tanstack/react-virtual` for DOM recycling. Each `FieldFrequencyRow` shows a field name and the pipelines it appears in as colored pills.

### DAG Summary (`dags`)

A dashboard of per-DAG health cards rendered by `DagSummaryView`. Data loads via `useDagSummary` which re-fetches every 5 minutes and respects the global date-range filter. An `AggregateBar` shows overall success/failure distribution across all DAGs. Each `DagCard` shows the DAG name, schedule, task-level status dots via `TaskStatusDots`, and a success rate percentage. A `DateRangePicker` in the header controls the time window for all data in this view.

### Bouncers (`bouncers`)

Root data ingestion tasks (renamed from sensors). `BouncersView` renders a filterable list of `BouncerCard` components alongside a `BouncerTopology` visualization. Data loads via `useBouncers` and `useBouncerTopology`. `useBouncerStore` manages the multi-selection of bouncers and the topology display mode (union: show all pipelines fed by any selected bouncer; intersection: show only pipelines fed by all selected bouncers). Filtered by team via `TeamFilter`.

### AI Architect Terminal (`ai`)

A terminal-style chat interface rendered by `AIArchitectView`. The UI is composed of `TerminalHeader`, a scrollable message list of `ChatMessage` components, a `TypingIndicator`, and `ChatInput`. Chat history is persisted in `useAIStore` for the session lifetime. Sending a message calls `useAIChat`, a TanStack mutation that posts to `POST /api/ai/chat` with the full message history for context. On success the assistant reply is appended to the store; on error a fallback message is shown.

### Admin Panel (`admin`)

Visible only to users with `role === "admin"`. `AdminView` contains three tabs rendered as separate panels:

- `UsersPanel`: paginated user list with inline role selector and active/inactive toggle, powered by `useAdminUsers`, `useUpdateUserRole`, and `useUpdateUserActive`.
- `TeamsPanel`: team list with membership counts, powered by `useAdminTeams` and `useTeamDetail`.
- `GrantsPanel`: visibility grant list with create/revoke controls, powered by `useAdminGrants`, `useCreateGrant`, and `useDeleteGrant`. Grants can be scoped to a specific pipeline or to an entire source team, with `viewer` or `editor` access level.

### Onboarding Overlay

A guided tour rendered by `OnboardingOverlay` as a full-screen overlay with animated step transitions. Steps are defined in `onboarding-steps.tsx` (8 steps for non-admins, 9 for admins). Each step may spotlight a sidebar nav icon (`SidebarSpotlight`), a section within the main content area (`SectionSpotlight`), or neither (centered panel). A `SpotlightConnector` draws a visual line between the overlay panel and the target element. Progress and completion state persist in `localStorage` via `useOnboardingStore` using a version key to allow re-triggering on schema changes. The tour can be restarted from the sidebar's help icon.

---

## Component Hierarchy

```
src/components/
├── layout/
│   ├── AppShell.tsx            — full-height flex container: Sidebar + main
│   ├── Sidebar.tsx             — 80px icon nav, Airflow status dot, user avatar, SSO logout
│   └── NavIcon.tsx             — individual sidebar icon button with tooltip
│
├── auth/
│   ├── AuthProvider.tsx        — AuthBootstrap: fetches /api/auth/config, conditionally mounts OidcAuthProvider
│   ├── AuthGuard.tsx           — gates children behind authentication; SSOGuard for OIDC flow
│   └── LoginPage.tsx           — full-screen login prompt when OIDC not yet authenticated
│
├── pipeline-registry/
│   ├── PipelineRegistry.tsx    — container: composes search + filters + virtual list
│   ├── PipelineSearch.tsx      — search input bound to pipeline-store.searchQuery
│   ├── PipelineFilters.tsx     — collapsible team/DAG/status filter facets
│   └── PipelineListItem.tsx    — single row: status dot, name, team badge, schedule
│
├── bento-workspace/
│   ├── BentoWorkspace.tsx      — root: reads selectedPipelineId, renders appropriate layout
│   ├── BentoHeader.tsx         — pipeline name (inline edit), description, team badge, metadata pills, docs button
│   ├── LineageTopology.tsx     — reads/writes lineage cards + DAG-level topology
│   ├── MetricsCards.tsx        — rows/day + schedule metric cards
│   ├── SchemaViewer.tsx        — field list with data types and ordinal positions
│   ├── ConsumeSnippet.tsx      — tabbed PySpark/Trino/Python consume code snippets
│   ├── JoinIntelligence.tsx    — schema-match join suggestions + AI join insight cards
│   ├── UsageCard.tsx           — pipeline usage statistics and consumer downstream list
│   ├── ResourcePerformanceCard.tsx — Spark allocation vs actual usage chart
│   ├── TransformInspectorCard.tsx  — execution plan tree with run selector
│   ├── UpstreamTopologyModal.tsx   — modal showing full upstream lineage graph
│   ├── DocumentationModal.tsx      — full-screen markdown editor/preview with revision history
│   ├── RevisionHistoryPanel.tsx    — description/documentation change history with restore
│   ├── documentation/
│   │   ├── doc-toolbar.tsx         — edit/preview toggle toolbar
│   │   ├── doc-cheatsheet.tsx      — markdown syntax cheatsheet panel
│   │   └── markdown-components.tsx — custom react-markdown renderers with rehype-sanitize
│   ├── execution-plan/
│   │   ├── PlanTree.tsx            — recursive CSS-tree of execution plan nodes
│   │   ├── PlanNodeCard.tsx        — individual node card: type, label, metrics
│   │   ├── PlanRunSelector.tsx     — dropdown to select a historical run
│   │   ├── PlanFormatters.tsx      — display helpers for plan node types
│   │   ├── plan-constants.ts       — node type → color/icon mappings
│   │   └── plan-parsers.ts         — JSON → plan tree parsing utilities
│   ├── lineage/
│   │   ├── LineageNodes.tsx        — individual lineage graph nodes
│   │   ├── LineageSections.tsx     — reads_from / writes_to section renderers
│   │   ├── DagGroupSection.tsx     — DAG-level task groupings in topology
│   │   ├── DependencySection.tsx   — upstream dependency display
│   │   ├── lineage-utils.ts        — edge-drawing helpers and layout calculations
│   │   └── hooks/useEdgeDrawing.ts — SVG edge drawing hook for topology canvas
│   ├── resource-performance/
│   │   ├── ResourceSections.tsx    — allocated vs actual resource comparison panels
│   │   └── resource-utils.ts       — GB/MB formatting and resource diff calculations
│   └── hooks/                  — bento-workspace-specific hooks (currently useEdgeDrawing)
│
├── schema-matrix/
│   ├── SchemaMatrixView.tsx    — full view: header, infinite virtual list
│   └── FieldFrequencyRow.tsx   — single field row with pipeline occurrence pills
│
├── dag-summary/
│   ├── DagSummaryView.tsx      — full view: header with DateRangePicker, AggregateBar, DAG grid
│   ├── DagCard.tsx             — per-DAG health card: name, schedule, task dots, success rate
│   ├── AggregateBar.tsx        — stacked bar of overall status distribution
│   └── TaskStatusDots.tsx      — row of colored status indicator dots for task runs
│
├── bouncers/
│   ├── BouncersView.tsx        — full view: TeamFilter, bouncer grid, topology panel
│   ├── BouncerCard.tsx         — individual bouncer card: name, team badge, downstream count
│   ├── BouncerTopology.tsx     — force-directed graph of bouncer → pipeline topology
│   └── TeamFilter.tsx          — team selector for bouncer filtering
│
├── ai-terminal/
│   ├── AIArchitectView.tsx     — full view: header, message list, input
│   ├── ChatMessage.tsx         — single message bubble (user / assistant)
│   ├── ChatInput.tsx           — textarea with send button
│   ├── TerminalHeader.tsx      — terminal title bar with clear history button
│   └── TypingIndicator.tsx     — animated dots shown while assistant is responding
│
├── admin/
│   ├── AdminView.tsx           — tab container for Users / Teams / Grants
│   ├── UsersPanel.tsx          — paginated user list with role and active controls
│   ├── TeamsPanel.tsx          — team list with member counts and detail drawer
│   └── GrantsPanel.tsx         — visibility grant list with create/revoke form
│
├── onboarding/
│   ├── OnboardingOverlay.tsx   — full-screen animated tour overlay
│   ├── SidebarSpotlight.tsx    — highlights a sidebar icon during a tour step
│   ├── SectionSpotlight.tsx    — highlights a content section during a tour step
│   ├── SpotlightConnector.tsx  — SVG line connecting the panel to the spotlight target
│   └── onboarding-steps.tsx    — step definitions with icon, text, and spotlight targets
│
├── shared/
│   ├── ErrorBoundary.tsx       — React class error boundary wrapping the app root
│   ├── ErrorState.tsx          — error card with message and optional retry callback
│   ├── EmptyState.tsx          — empty content placeholder with icon and message
│   ├── LoadingState.tsx        — spinner/skeleton for async loading states
│   ├── StatusBadge.tsx         — colored badge displaying a pipeline status label
│   ├── CopyButton.tsx          — clipboard copy button with toast confirmation
│   ├── DateRangePicker.tsx     — preset selector (24h/7d/30d/90d/custom) bound to date-range-store
│   └── UserInitials.tsx        — avatar circle showing initials derived from display_name
│
└── ui/                         — shadcn/ui primitives (base-ui variant)
    ├── badge.tsx
    ├── button.tsx
    ├── card.tsx
    ├── input.tsx
    ├── scroll-area.tsx
    ├── separator.tsx
    ├── skeleton.tsx
    ├── sonner.tsx
    └── tooltip.tsx
```

---

## State Management

### Zustand Stores

All stores live in `src/stores/` and use Zustand v5. None use persistence middleware except `onboarding-store`, which reads and writes `localStorage` directly.

| Store | File | Purpose | Key State |
|---|---|---|---|
| `useNavigationStore` | `navigation-store.ts` | Active sidebar tab | `activeTab: TabType` (catalog/matrix/dags/bouncers/ai/admin) |
| `usePipelineStore` | `pipeline-store.ts` | Pipeline registry UI state | `selectedPipelineId`, `selectedDagId`, `searchQuery`, `filtersOpen`, `teamFilters`, `dagFilters`, `statusFilters` |
| `useAuthStore` | `auth-store.ts` | Auth session state | `user: UserInfo`, `token`, `isAuthenticated`, `ssoEnabled`, `oidcSignout` |
| `useDateRangeStore` | `date-range-store.ts` | Global date filter for time-series data | `preset: DatePreset` (24h/7d/30d/90d/custom), `dateFrom`, `dateTo`. Exports `useDateParams()` helper that returns `undefined` when preset is the default 30d (so backend uses its own fallback and cache hits are preserved). |
| `useBouncerStore` | `bouncer-store.ts` | Bouncer selection and topology settings | `selectedBouncers: string[]`, `teamFilter`, `topologyMode: "union" \| "intersection"` |
| `useAIStore` | `ai-store.ts` | AI terminal session | `messages: ChatMessage[]`, `isTyping`. Chat history persists for the browser session but is cleared on `clearHistory()`. |
| `useOnboardingStore` | `onboarding-store.ts` | Guided tour state | `isActive`, `isExiting`, `currentStep`, `hasCompleted` (from localStorage), `direction`. Uses `ONBOARDING_VERSION = 1` as the localStorage key so version bumps re-trigger the tour. |

### TanStack Query Hooks

All hooks live in `src/hooks/`. The global `QueryClient` is configured with `staleTime: 30_000`, `retry: 2`, and `refetchOnWindowFocus: false`. Individual hooks may override these.

| Hook | File | Query type | Endpoint | Cache key | Notes |
|---|---|---|---|---|---|
| `usePipelines` | `use-pipelines.ts` | infinite | `GET /pipelines` | `["pipelines", searchQuery, dateParams]` | Page size 50, refetch every 5 min, keepPreviousData |
| `usePipelineDetail` | `use-pipeline-detail.ts` | query | `GET /pipelines/{id}` | `["pipeline", pipelineId]` | staleTime 60s |
| `useJoinSuggestions` | `use-join-suggestions.ts` | query | `GET /pipelines/{id}/joins` | `["join-suggestions", pipelineId]` | |
| `useSyncPipeline` | `use-sync-pipeline.ts` | mutation | `POST /pipelines/{id}/sync` | — | Invalidates pipeline, pipelines, airflow-statuses, resource-metrics, lineage, topology |
| `useUpdatePipeline` | `use-update-pipeline.ts` | mutation | `PATCH /pipelines/{id}` | — | Invalidates pipeline, pipelines, revisions |
| `useRevisions` | `use-revisions.ts` | query | `GET /pipelines/{id}/revisions` | `["revisions", pipelineId, field]` | |
| `useRestoreRevision` | `use-revisions.ts` | mutation | `POST /pipelines/{id}/revisions/{revisionId}/restore` | — | Invalidates pipeline, revisions, pipelines |
| `useLineage` | `use-lineage.ts` | query | `GET /pipelines/{id}/lineage` | `["lineage", pipelineId]` | staleTime 5 min |
| `useTopology` | `use-topology.ts` | query | `GET /pipelines/{id}/topology` | `["topology", pipelineId, dagId]` | staleTime 2 min |
| `useUpstreamTopology` | `use-upstream-topology.ts` | query | `GET /pipelines/{id}/topology/upstream` | `["upstream-topology", pipelineId, dagId]` | staleTime 2 min |
| `useResourceMetrics` | `use-resource-metrics.ts` | query | `GET /pipelines/{id}/resources` | `["resource-metrics", pipelineId, dateParams]` | Date-range aware |
| `useExecutionPlan` | `use-execution-plan.ts` | query | `GET /pipelines/{id}/execution-plan` | `["execution-plan", pipelineId, dagRunId]` | `retry: false` — returns 404 when no plan exists |
| `useExecutionPlanRuns` | `use-execution-plan.ts` | infinite | `GET /pipelines/{id}/execution-plan/runs` | `["execution-plan-runs", pipelineId]` | Page size 20, keepPreviousData |
| `usePipelineUsage` | `use-pipeline-usage.ts` | query | `GET /api/usage/{etlName}` | `["pipeline-usage", etlName, dateParams]` | Date-range aware; keyed by `etl_name` not `id` |
| `usePipelineConsumers` | `use-pipeline-consumers.ts` | query | `GET /api/consumers/{etlName}` | `["pipeline-consumers", etlName]` | |
| `useAirflowStatuses` | `use-airflow-status.ts` | query | `GET /airflow/statuses` | `["airflow-statuses"]` | Refetch every 5 min |
| `useDagSummary` | `use-dag-summary.ts` | query | `GET /dag-summary` | `["dag-summary", dateParams]` | Date-range aware, refetch every 5 min |
| `useBouncers` | `use-bouncers.ts` | query | `GET /bouncers` | `["bouncers", team]` | Refetch every 5 min |
| `useBouncerTopology` | `use-bouncers.ts` | query | `GET /bouncers/topology` | `["bouncer-topology", ...bouncerNames, mode]` | Only fires when `bouncerNames.length > 0`; staleTime 30s, refetch every 60s |
| `useSchemaMatrix` | `use-schema-matrix.ts` | infinite | `GET /schema-matrix` | `["schema-matrix"]` | Page size 100 |
| `useAIChat` | `use-ai-chat.ts` | mutation | `POST /ai/chat` | — | Bridges useAIStore ↔ TanStack mutation |
| `useCurrentUser` | `use-auth.ts` | query | `GET /auth/me` | `["auth", "me", token]` | retry: 1; result synced to useAuthStore via useEffect |
| `useAdminUsers` | `use-admin.ts` | infinite | `GET /users` | `["admin-users"]` | Page size 100, staleTime 2 min |
| `useAdminTeams` | `use-admin.ts` | query | `GET /teams` | `["admin-teams"]` | staleTime 2 min |
| `useTeamDetail` | `use-admin.ts` | query | `GET /teams/{id}` | `["admin-team-detail", teamId]` | staleTime 2 min |
| `useAdminGrants` | `use-admin.ts` | infinite | `GET /visibility/grants` | `["admin-grants"]` | Page size 100, staleTime 2 min |
| `useUpdateUserRole` | `use-admin.ts` | mutation | `PATCH /users/{id}/role` | — | Invalidates admin-users |
| `useUpdateUserActive` | `use-admin.ts` | mutation | `PATCH /users/{id}/active` | — | Invalidates admin-users |
| `useCreateGrant` | `use-admin.ts` | mutation | `POST /visibility/grants` | — | Invalidates admin-grants |
| `useDeleteGrant` | `use-admin.ts` | mutation | `DELETE /visibility/grants/{id}` | — | Invalidates admin-grants |

---

## API Layer

### Client Configuration

`src/api/client.ts` creates an Axios instance with:

```
baseURL: VITE_API_BASE_URL || "/api"
timeout: 30_000 ms
Content-Type: application/json
```

### Interceptors

Three interceptors run in order on every request/response cycle:

**Request — bearer token injection**
Reads `token` from `useAuthStore.getState()` and appends `Authorization: Bearer <token>` to every request. When SSO is disabled, the token is `"no-sso"` and the header is omitted.

**Response — transient error retry**
Retries requests that fail with HTTP 502, 503, or 504 (gateway/upstream errors) up to 2 times with a 1-second delay between attempts. Network errors (no `status`) are also retried.

**Response — 401 token refresh**
On a 401 response (and only when SSO is enabled), the interceptor waits 2 seconds for the OIDC library's automatic silent renewal to complete. If the token in the auth store has changed, the original request is retried with the new token. If the token is unchanged (genuine auth failure), `logout()` is called on the auth store and `oidcSignout()` is invoked to redirect the user through the Keycloak logout flow.

### API Modules

Each file in `src/api/` covers one domain and imports from `src/types/` for strict typing:

| File | Domain | Key functions |
|---|---|---|
| `pipelines.ts` | Pipeline CRUD | `fetchPipelines`, `fetchPipelineDetail`, `fetchJoinSuggestions`, `syncPipeline`, `updatePipeline`, `fetchRevisions`, `restoreRevision` |
| `lineage.ts` | Lineage edges | `fetchLineage` |
| `topology.ts` | DAG topology | `fetchTopology`, `fetchUpstreamTopology` |
| `resources.ts` | Spark resource metrics | `fetchResourceMetrics` |
| `execution-plan.ts` | Execution plan tree | `fetchExecutionPlan`, `fetchExecutionPlanRuns` |
| `usage.ts` | Pipeline usage stats | `fetchPipelineUsage` |
| `consumer.ts` | Downstream consumers | `fetchPipelineConsumers` |
| `airflow.ts` | Airflow connection status | `fetchAllAirflowStatuses` |
| `dag-summary.ts` | DAG health summary | `fetchDagSummary` |
| `bouncer.ts` | Bouncer list and topology | `fetchBouncers`, `fetchBouncerTopology` |
| `schema-matrix.ts` | Cross-pipeline field frequency | `fetchSchemaMatrix` |
| `ai.ts` | AI chat | `sendAIMessage` |
| `auth.ts` | Auth config and user info | `fetchAuthConfig`, `fetchMe` |
| `admin.ts` | Users, teams, grants | `fetchUsers`, `updateUserRole`, `updateUserActive`, `fetchTeams`, `fetchTeamDetail`, `fetchGrants`, `createGrant`, `deleteGrant` |

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `/api` | Backend API base URL |
| `VITE_AIRFLOW_URL` | `http://localhost:8080` | Airflow UI URL for the sidebar status link |

---

## Styling

### Theme

The application is always dark. There is no light mode toggle.

| Token | Value | Usage |
|---|---|---|
| Background | `#09090b` | Root background (`bg-[#09090b]`), sidebar, login page |
| Card surface | `#18181b` | All card and panel backgrounds |
| Accent | `indigo-500` | Active nav icons, selection highlights, primary buttons |
| Text primary | `slate-300` | Body text |
| Text muted | `slate-600` | Placeholder, disabled, secondary text |
| Border | `white/5` | Subtle dividers between panels |

### Tailwind CSS v4

Uses `@tailwindcss/vite` as the Vite plugin (not the PostCSS approach). Configuration is in `src/index.css` using the `@import "tailwindcss"` directive. Arbitrary values (`bg-[#09090b]`, `shadow-[0_0_8px_...]`) are used throughout for theme colors and glow effects.

The `cn()` utility in `src/lib/utils.ts` combines `clsx` and `tailwind-merge` for safe conditional class composition.

Animation uses `tw-animate-css` for pre-built Tailwind animation classes.

### shadcn/ui (base-ui Variant)

Components in `src/components/ui/` are sourced from shadcn/ui using the `@base-ui/react` primitive layer for React 19 compatibility. Two important differences from the standard shadcn/ui variant:

- Tooltip delay prop is `delay`, not `delayDuration`. The global `TooltipProvider` in `main.tsx` uses `delay={200}`.
- `TooltipTrigger` does **not** accept `asChild`. Wrap content directly inside `TooltipTrigger` without the `asChild` prop.

### Status Colors

`src/lib/status-config.ts` exports `STATUS_CONFIG`, a record mapping Airflow task state strings to a `StatusStyle` object with Tailwind classes for dot color, glow shadow, text color, background fill, and active filter pill state. Use `getStatusStyle(status)` to retrieve a config (falls back to `"unknown"`). `STATUS_SEVERITY_ORDER` defines severity priority for selecting which status to display when multiple are present (e.g., for a glow indicator on a pipeline card).

### Font

The Geist variable font is loaded from `@fontsource-variable/geist` and applied via `font-sans`.

### Toasts

`sonner` is used for all toast notifications, mounted in `main.tsx` with `theme="dark"`. Hooks and mutations use `toast.success()` and `toast.error()` from `sonner` directly.

---

## Testing

### Test Infrastructure

- **Framework**: Vitest v4
- **DOM environment**: jsdom (configured in `vitest.config.ts`)
- **Assertion library**: `@testing-library/jest-dom` (matchers added in `src/test/setup.ts`)
- **Component rendering**: `@testing-library/react` v16
- **Path alias**: `@` → `src/` (configured in `vitest.config.ts` resolver)

### Test Distribution

210 tests across 20 test files:

| Category | Files | Tests |
|---|---|---|
| Store unit tests | `test/stores/auth-store.test.ts`, `bouncer-store.test.ts`, `date-range-store.test.ts`, `navigation-store.test.ts`, `pipeline-store.test.ts` | 116 |
| Component tests | `test/components/BentoWorkspace.test.tsx`, `ConsumeSnippet.test.tsx`, `DagCard.test.tsx`, `ErrorBoundary.test.tsx`, `ErrorState.test.tsx`, `MetricsCards.test.tsx`, `PipelineListItem.test.tsx`, `SchemaMatrixView.test.tsx`, `SchemaViewer.test.tsx` | 185 |
| Utility unit tests | `test/format.test.ts`, `test/lineage-utils.test.ts`, `test/permissions.test.ts`, `test/plan-parsers.test.ts`, `test/status-config.test.ts`, `test/utils.test.ts` | 63 |

### Running Tests

```bash
# Watch mode (default for development)
pnpm test

# Single run (CI)
pnpm test:run
```

Tests are colocated in `src/test/` mirroring the source tree. Store tests cover state transitions and selector behavior. Component tests use mock data and `QueryClientProvider` wrappers to test rendering and user interactions. Utility tests cover pure functions: `formatDuration`, lineage layout calculations, `isAdmin`, plan-tree parsing, `getStatusStyle`, `cn`, and `isApiPipeline`.

---

## Development

### Prerequisites

- Node.js 20+
- pnpm (see root `package.json` for version)
- The backend must be running on port 8000 (or configure `VITE_API_BASE_URL`)

### Commands

```bash
# Install dependencies
pnpm install

# Start Vite dev server at http://localhost:5173 with HMR
pnpm dev

# Production build (TypeScript compile + Vite bundle)
pnpm build

# Preview production build locally
pnpm preview

# TypeScript type check (no emit)
pnpm tsc --noEmit

# Run tests in watch mode
pnpm test

# Run tests once (CI)
pnpm test:run

# Add a shadcn/ui component (base-ui variant)
pnpm dlx shadcn@latest add <component>
```

### Docker Compose (Recommended for Full Stack)

```bash
# Start all services (backend, frontend, db, airflow, keycloak, iceberg)
docker compose up

# Start with file-watching auto-sync (frontend hot-reload via Vite HMR)
docker compose watch

# Stop all services
docker compose down

# Reset database and all volumes
docker compose down -v
```

### Path Aliases

The `@` alias maps to `src/`. Configured in both `vite.config.ts` and `vitest.config.ts` so it works at build time and in tests.

---

## Key Conventions

### Pipeline Type Discrimination

`pipeline_type` on the `PipelineListItem` and `PipelineDetail` types is a string discriminant. The utility function `isApiPipeline(pipeline_type)` in `src/lib/utils.ts` returns `true` when `pipeline_type === "api"`. This controls the Bento Workspace layout: API pipelines receive a simplified view without schema, resource, execution plan, or join intelligence cards.

```typescript
// src/lib/utils.ts
export function isApiPipeline(pipelineType: string | null | undefined): boolean {
  return pipelineType === "api";
}
```

### ETL vs API Pipeline Layouts

When rendering the Bento Workspace grid, always check `isApiPipeline(pipeline.pipeline_type)` before rendering ETL-only cards. API pipelines expose topology and consumption information but have no Iceberg schema, Spark resources, or execution plans.

### PascalCase Task IDs

All Airflow task IDs follow PascalCase naming (e.g., `SwitchPortCollector`, `NetworkInsightsApiDummy`). API dependencies have a `Dummy` suffix. Bouncer tasks contain the word `Bouncer` (e.g., `SwitchPortBouncer`). The backend's `_task_id_to_display_name()` converts both PascalCase and snake_case via regex splitting; the frontend receives the already-formatted `name` field and renders it directly.

### Usage Endpoints Keyed by `etl_name`

The `usePipelineUsage` and `usePipelineConsumers` hooks accept `etl_name` (a string task ID such as `SwitchPortCollector`), not the UUID pipeline `id`. Pass `pipeline.task_id ?? pipeline.name` as the key when calling these hooks. The `UsageCard` component handles this internally.

### shadcn/ui base-ui Quirks

The project uses `@base-ui/react` as the primitive layer instead of Radix UI. Two rules must be followed across all components:

1. Use `delay={200}` (not `delayDuration`) on `TooltipProvider` and individual tooltips.
2. Never add `asChild` to `TooltipTrigger` — pass the trigger element as a direct child.

Violating either rule causes runtime errors or silent rendering failures.

### `cn()` for Conditional Classes

Always use `cn()` from `src/lib/utils.ts` when composing Tailwind class strings conditionally. It runs `clsx` for conditional logic then `tailwind-merge` to resolve conflicting Tailwind utilities (e.g., two `bg-*` classes) correctly.

### Date Range Integration

Many hooks accept date parameters via `useDateParams()` from `date-range-store.ts`. This helper returns `undefined` when the active preset is `"30d"` (the default), which causes the backend to use its own 30-day fallback. This is intentional: returning `undefined` means the query key does not include date params, so all users on the default preset share the same TanStack Query cache entry.

### Global Error Handling

The root `ErrorBoundary` in `src/components/shared/ErrorBoundary.tsx` catches unhandled render errors and displays a fallback UI. Below that level, individual async states are handled by `ErrorState` and `EmptyState` components rendered from loading/error branches within each view. API errors from mutations display toast notifications via `sonner`.

### Lazy Loading

All views except `PipelineRegistry` are lazy-loaded via `React.lazy()` and wrapped in `<Suspense fallback={<TabSkeleton />}>` in `App.tsx`. The `PipelineRegistry` is eagerly loaded because it is visible on the default `catalog` tab and must render immediately on app load without a skeleton flash.

### Revision History

`useRevisions` and `useRestoreRevision` support a `field` parameter of `"description"` or `"documentation"`. Pass the field name to filter revision history to a specific field. Restoring a revision invalidates `["pipeline", pipelineId]`, `["revisions", pipelineId]`, and `["pipelines"]` so the list and detail views refresh immediately.
