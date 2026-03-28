# ETL Nexus — User Guide

ETL Nexus is a data architecture command center for discovering, understanding, and consuming ETL pipelines. It gives data engineers and analysts a single place to browse pipelines, trace data lineage, inspect Spark performance, find join opportunities, and query the catalog through natural language.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
   - 1.1 [Logging In](#11-logging-in)
   - 1.2 [Application Layout](#12-application-layout)
   - 1.3 [Roles and Permissions](#13-roles-and-permissions)
2. [Pipeline Registry](#2-pipeline-registry)
   - 2.1 [Browsing the List](#21-browsing-the-list)
   - 2.2 [Searching](#22-searching)
   - 2.3 [Filtering](#23-filtering)
   - 2.4 [Pipeline Cards](#24-pipeline-cards)
3. [Bento Workspace](#3-bento-workspace)
   - 3.1 [Pipeline Header](#31-pipeline-header)
   - 3.2 [Pipeline Topology](#32-pipeline-topology)
   - 3.3 [Metrics Cards](#33-metrics-cards)
   - 3.4 [Resource Performance Card](#34-resource-performance-card)
   - 3.5 [Transform Inspector](#35-transform-inspector)
   - 3.6 [Data Structure (Schema Viewer)](#36-data-structure-schema-viewer)
   - 3.7 [Usage Card](#37-usage-card)
   - 3.8 [Join Intelligence](#38-join-intelligence)
   - 3.9 [Import and Consume Snippet](#39-import-and-consume-snippet)
   - 3.10 [Documentation Modal](#310-documentation-modal)
   - 3.11 [Upstream Topology Modal](#311-upstream-topology-modal)
4. [DAG Operations Dashboard](#4-dag-operations-dashboard)
5. [Field Frequency Matrix](#5-field-frequency-matrix)
6. [Bouncer Dashboard](#6-bouncer-dashboard)
7. [AI Architect Terminal](#7-ai-architect-terminal)
8. [Admin Panel](#8-admin-panel)
   - 8.1 [Users](#81-users)
   - 8.2 [Teams](#82-teams)
   - 8.3 [Grants](#83-grants)
9. [Key Workflows](#9-key-workflows)
   - 9.1 [Finding a Pipeline](#91-finding-a-pipeline)
   - 9.2 [Understanding Data Dependencies](#92-understanding-data-dependencies)
   - 9.3 [Checking Spark Performance](#93-checking-spark-performance)
   - 9.4 [Debugging Execution Steps](#94-debugging-execution-steps)
   - 9.5 [Finding Join Opportunities](#95-finding-join-opportunities)
   - 9.6 [Consuming a Pipeline in Code](#96-consuming-a-pipeline-in-code)
   - 9.7 [Cross-Pipeline Field Analysis](#97-cross-pipeline-field-analysis)
   - 9.8 [Exploring Bouncer Ingestion Points](#98-exploring-bouncer-ingestion-points)
   - 9.9 [AI-Powered Discovery](#99-ai-powered-discovery)
   - 9.10 [Editing Pipeline Documentation](#910-editing-pipeline-documentation)
   - 9.11 [Managing Team Access](#911-managing-team-access)
10. [Status Indicators Reference](#10-status-indicators-reference)
11. [Dependency Types Reference](#11-dependency-types-reference)
12. [Dev User Reference](#12-dev-user-reference)

---

## 1. Getting Started

### 1.1 Logging In

When SSO is enabled, the application shows a login page before granting access. Click **Sign in with SSO** to be redirected to your organization's identity provider (Keycloak). After authenticating, you are automatically returned to the application.

Your team memberships are read from your identity provider groups. No manual team assignment is required after login.

When SSO is disabled (local development mode), the application grants access automatically with a default admin user — no login step is required.

### 1.2 Application Layout

The interface is divided into two areas:

- **Left sidebar** — a narrow vertical navigation rail with icon-labelled tabs for each major section.
- **Main content area** — displays the section selected in the sidebar.

The Pipeline Registry and Bento Workspace share the main content area simultaneously: the Registry occupies a fixed-width left panel (400 px) and the Workspace fills the remaining space to the right. All other tabs occupy the full content area.

**Sidebar tabs:**

| Tab | Label | Purpose |
|-----|-------|---------|
| catalog | Pipeline Registry | Browse and search all ETL pipelines |
| dags | DAG Summary | Airflow DAG network health overview |
| matrix | Schema Matrix | Cross-pipeline field frequency |
| bouncers | Bouncers | Ingestion bouncers and their downstream pipelines |
| ai | AI Architect | Natural language catalog queries |
| admin | Admin | User, team, and access grant management (admins only) |

### 1.3 Roles and Permissions

There are three roles:

| Role | Can view pipelines | Can edit descriptions/docs | Can access Admin panel |
|------|--------------------|---------------------------|----------------------|
| **viewer** | Scoped to their teams + grants | No | No |
| **member** | Scoped to their teams + grants | Own-team pipelines only | No |
| **admin** | All pipelines | All pipelines | Yes |

Team scoping means a user sees pipelines assigned to their own team(s), pipelines with no team assigned, and any pipelines or team catalogs explicitly shared with them via visibility grants.

---

## 2. Pipeline Registry

The Pipeline Registry is a searchable, filterable master list of every ETL pipeline discovered from Airflow. It is always visible on the left side of the screen when you are in the **catalog** tab.

### 2.1 Browsing the List

Pipelines are grouped into two categories — **ETL** and **API** — and sorted alphabetically within each group. The group header shows the category name and a count of pipelines in that group.

Click any pipeline card to select it. The selected pipeline opens in the Bento Workspace to the right. If no pipeline is explicitly selected, the first pipeline in the list is selected automatically.

### 2.2 Searching

The search bar at the top of the Registry accepts free-text queries. The backend searches against:

- Pipeline name
- Pipeline description
- Field (column) names in the pipeline's schema

Type into the search bar to filter the list in real time. Clear the search bar to return to the full list.

**Tip:** Searching by a field name such as `device_id` is a fast way to find all pipelines that contain a particular column.

### 2.3 Filtering

Click the filter icon next to the search bar to open the filter drawer. Three independent filter dimensions are available:

**Team** — show only pipelines owned by one or more teams (Dagger, Vault, Prism, Relay, Oasis). Active team filters appear as indigo pills.

**Network** — show only pipelines that run on one or more Airflow DAG networks (Backbone Core, Perimeter Defense, Application Mesh, Transit Exchange, Heartbeat Probe, NOC Sentinel). Active network filters appear as teal pills.

**Status** — show only pipelines with a specific Airflow task status. Active status filters use colour-coded pills matching the status colour (green for success, red for failed, amber for running, grey for unknown).

Multiple values within the same dimension act as OR (a pipeline matches if it belongs to any of the selected teams). Filters across dimensions act as AND (a pipeline must satisfy all active dimensions).

When the filter drawer is closed and filters are active, a compact summary strip appears below the search bar showing the active selections. Click the **X** on that strip to clear all filters at once. A **Clear all** button also appears inside the open filter drawer.

The result count line (`Showing N of M`) appears whenever the active filters reduce the visible list below the total.

### 2.4 Pipeline Cards

Each card in the list displays:

- **Name** — the pipeline identifier in PascalCase (e.g., `SwitchPortCollector`)
- **Description** — a short summary of what the pipeline produces
- **Status badge** — the most recent Airflow task outcome (coloured dot with label)
- **Team tag** — the owning team in green
- **Success rate** — percentage of recent runs that succeeded

The currently selected pipeline card is highlighted with an indigo accent.

---

## 3. Bento Workspace

The Bento Workspace is the detail view for the selected pipeline. It appears to the right of the Pipeline Registry and is composed of independently scrollable cards arranged in rows.

### 3.1 Pipeline Header

The header card spans the full width of the workspace and contains:

**Left side:**
- Pipeline name (large, white)
- Airflow status badge
- Category tag (indigo, uppercase monospace)
- Team tag (green, with team icon)

**Right side:**
- Last updated by and last updated date (visible on wider screens)
- **Docs button** (file icon) — opens the Documentation Modal
- **Airflow button** (external link icon) — opens the task directly in the Airflow web UI in a new tab (only shown when DAG and task IDs are known)
- **Sync button** — triggers an immediate re-sync of this pipeline from Airflow, updating status and metadata

**Description (below the identity row):**

The pipeline description appears below the header row. If you have edit permission for this pipeline, hovering over the description reveals a pencil icon on the right. Click it to enter inline editing mode:

- A textarea replaces the description text.
- Press **Ctrl+Enter** (or **Cmd+Enter** on macOS) to save, or click **Save Changes**.
- Press **Escape** or click **Cancel** to discard edits.

Saving a description updates the record immediately and shows your username in the "last updated by" metadata.

### 3.2 Pipeline Topology

This card (occupying the left 8 columns of Row 1) shows the data flow graph centred on the current pipeline.

**Layout (left to right):**

```
[Bouncers] --> [Dependencies] --> [Current Pipeline] --> [Downstream]
```

Each column is present only when there are items to show.

**Bouncers column** — upstream Airflow bouncers that gate this pipeline's execution. Bouncer nodes are displayed in teal with a radio icon. When a pipeline runs on multiple DAGs, bouncers are grouped into collapsible DAG accordion sections. Click a bouncer node to jump to the Bouncer Dashboard with that bouncer pre-selected.

**Dependencies column** — upstream ETL pipelines that this pipeline depends on, split into two sub-sections:

- **Needs** (orange lock icon) — hard dependencies; the pipeline will not run if these fail.
- **Prefers** (blue sparkle icon) — soft dependencies; the pipeline runs even if these are not ready, but prefers their output.

When dependencies span multiple DAGs, they are grouped into collapsible accordion sections labelled by DAG name. Each section header shows a compact status summary (counts by colour).

**Current Pipeline** — a highlighted node in indigo showing the selected pipeline's task ID and status.

**Downstream column** — ETL pipelines that directly depend on the current pipeline. Also grouped by DAG when multiple DAGs are involved. Click any downstream node to navigate to that pipeline in the Registry.

**Writes To footer** — below the main graph, a row of monospace tags lists the Iceberg table paths this pipeline writes to (e.g., `catalog.iceberg.dagger.switch_port_collector`).

**DAG selector** — if a pipeline runs on more than one DAG, small pill buttons appear in the card's top-right corner labelled with the DAG IDs plus an **all** option. Selecting a specific DAG scopes the topology to that DAG's dependencies and downstream tasks.

**Full Upstream button** — opens the Upstream Topology Modal (see section 3.11).

### 3.3 Metrics Cards

Two stacked cards occupy the right 4 columns of Row 1:

- **Volume Rate** — the pipeline's average output in rows per day.
- **Schedule** — the Airflow schedule expression (e.g., `@daily`, `0 6 * * *`).

### 3.4 Resource Performance Card

This full-width card (Row 2) surfaces Spark resource allocation and actual execution data for the selected pipeline.

**Left section — Allocated Resources:**

Shows the Spark configuration for this pipeline on each DAG:

| Metric | Description |
|--------|-------------|
| Driver Memory | RAM allocated to the Spark driver |
| Executor Memory | RAM per executor |
| Cores | CPU cores per executor |
| Executors | Number of executor instances |

When the pipeline runs on multiple DAGs and has different resource configurations per DAG, each configuration is shown in a separate sub-section.

**Centre section — Duration History:**

- Average run duration (prominent, large text)
- Min / max range
- Recent run history as a proportional bar chart, colour-coded by status (green = success, red = failed, amber = running)
- Success rate across recent runs

**Right section — Cluster Capacity:**

Progress bars showing what percentage of total cluster capacity this pipeline consumes for driver memory, executor memory, and total core count. The bars shift colour as utilisation increases: green below 60 %, amber from 60–80 %, red above 80 %.

**Actual Usage sub-section:**

When recent runs have logged actual resource consumption (via `ETL_RESOURCE_ACTUAL` log markers), this section shows measured driver memory used, executor memory used, and CPU utilisation alongside the allocated amounts for comparison.

### 3.5 Transform Inspector

This full-width card (Row 2.5) displays the Spark physical execution plan from the most recent run of the pipeline.

The plan is rendered as a tree where each node represents a physical operation. Nodes are colour-coded by type:

| Type | Colour | Examples |
|------|--------|---------|
| read | Blue | Table scan, file scan |
| write | Green | Iceberg write, file write |
| shuffle | Amber | Sort-merge join, exchange |
| transform | Indigo | Filter, project, aggregate |

Each node shows:
- Operation name (e.g., `IcebergScanRelation`, `SortMergeJoin`)
- Key metrics: row counts, data size, time metrics (scan time, build time, sort time, etc.)
- For shuffle nodes: bytes shuffled and shuffle partitions

Click the expand icon in the card header to open a full-screen view of the plan tree with more visible depth.

Click any node to expand or collapse its details panel, which shows all available metrics for that operation.

**Note:** If no execution plan has been captured for a pipeline (i.e., the pipeline has not yet run with sparkMeasure enabled), this card shows a "No execution plan available" message.

### 3.6 Data Structure (Schema Viewer)

This card (left portion of Row 3) lists every output field of the selected pipeline.

Each row shows:
- Field name (monospace)
- Data type (e.g., `TIMESTAMP`, `UUID`, `VARCHAR`, `FLOAT8`, `BOOL`)

The card is scrollable and capped at 460 px height to keep it compact. Hover any row to highlight it.

**Tip:** Use the search bar in the Pipeline Registry to search by field name. Once you find the pipeline, the Schema Viewer confirms the full field list and types.

### 3.7 Usage Card

This card (below the Schema Viewer in Row 3) shows downstream consumers — pipelines and APIs that read from the current pipeline.

The current pipeline itself appears as the first row with an indigo highlight and `current` label. Each subsequent row is a downstream consumer and shows:

- Consumer name
- Type (ETL or API, with an icon)
- Airflow status dot with glow
- Access count (number of times it has been queried)

### 3.8 Join Intelligence

This card (right portion of Row 3) provides two types of join suggestions:

**Schema Matches** (database icon section) — pipelines that share field names with the current pipeline. Each match shows the pipeline name and the list of shared field names as code tags. These are detected automatically from Iceberg catalog data. Up to two top matches are shown.

**AI Insights** (sparkle icon section) — the AI Architect analyses the current pipeline's schema, description, and category to suggest semantically relevant join candidates and notes. This section may take a moment to load as it calls the LLM endpoint.

### 3.9 Import and Consume Snippet

This card (below Join Intelligence in Row 3) provides ready-to-copy code for consuming the pipeline in your own ETL or notebook.

For standard **ETL pipelines**, the snippet uses the internal catalog client:

```python
from etls import Catalog, Engine

Catalog(Engine.Spark).iceberg.dagger.pipeline_name("date").consume().as_pyspark()
```

For **API pipelines**, the snippet uses the API import pattern:

```python
from path import api

pipeline_name = pipeline_name(start_date, end_date)
```

Click the copy button in the card header to copy the full snippet to your clipboard.

### 3.10 Documentation Modal

Clicking the **Docs** button (file icon) in the Pipeline Header opens a full-screen documentation overlay for the selected pipeline.

**Viewing mode** — documentation is rendered as formatted Markdown with syntax highlighting for code blocks. A copy button appears on hover for each code block.

**Editing mode** (available to users with edit permission) — click the **Edit** button to switch to a raw Markdown editor. A toolbar provides shortcuts for common formatting: bold, italic, headings (H1–H4), lists, code blocks, tables, and horizontal rules. Click **Preview** to toggle back to the rendered view without saving. Click **Save** to persist the documentation. Press **Escape** or click the X to close without saving.

The editor supports GitHub Flavored Markdown (GFM) including tables, task lists, and strikethrough.

### 3.11 Upstream Topology Modal

Click **Full Upstream** in the Pipeline Topology card to open this modal. It renders a recursive, force-directed graph of all upstream dependencies across all DAGs — not just the direct parents.

**Node types:**

- **Current pipeline** — indigo ring
- **Bouncer** — teal with radio icon
- **Needs dependency** — orange border
- **Prefers dependency** — blue border
- **Root node** (no further parents) — grey

**Edge types:**

- Solid orange lines — needs edges
- Dashed blue lines — prefers edges
- Dashed teal lines — bouncer edges

**Filters** in the modal header let you toggle which edge types are shown. A status legend explains the status colour applied to each node dot.

Click any node in the modal to navigate the Registry to that pipeline and close the modal.

---

## 4. DAG Operations Dashboard

Navigate to the **dags** tab in the sidebar.

This view provides an operational overview of all Airflow DAG networks.

**Aggregate bar (top):** A single row summarising across all DAGs:
- Total DAGs monitored
- Total pipeline count
- Active DAG count (not paused)
- Overall success rate (colour-coded: green ≥ 90 %, amber ≥ 70 %, red below 70 %)
- 30-day run count

**Per-DAG cards:** One card per DAG network, showing:

| Field | Description |
|-------|-------------|
| DAG name | Human-readable (e.g., "Backbone Core") |
| Status indicator | Coloured dot reflecting the worst active state |
| Schedule | Cron or preset expression |
| Task count | Total tasks in the DAG |
| Pipeline count | ETL pipelines in this DAG |
| Avg / min / max duration | Run time statistics |
| Success / failed / running counts | Current task state breakdown |
| Success rate bar | Visual percentage bar |
| Task status dots | One dot per task, coloured by latest status |

Expanding a DAG card (click the chevron) shows a breakdown by task group with per-group status dots.

---

## 5. Field Frequency Matrix

Navigate to the **matrix** tab in the sidebar.

This view answers the question: "Which field names appear across multiple pipelines?"

**Columns:**

| Column | Description |
|--------|-------------|
| Field Name | The column name as it appears in Iceberg schemas |
| Frequency | Number of pipelines that contain this field |
| Pipelines | Pill list of pipeline names that share this field |

Rows are sorted by frequency (highest first). Fields that appear in only one pipeline are excluded.

**Use cases:**

- Identify join keys shared between pipelines without manually comparing schemas.
- Discover which pipelines all track a concept like `device_id`, `site_code`, or `ts` (timestamp).
- Cross-reference with the AI Architect for deeper join analysis.

---

## 6. Bouncer Dashboard

Navigate to the **bouncers** tab in the sidebar.

The Bouncer Dashboard shows data ingestion bouncers — Airflow tasks that wait for external data availability before triggering downstream ETL pipelines.

### Left panel — Bouncer Grid

Bouncer cards are displayed in a responsive grid (1–2 columns depending on screen width). Each card shows:

- Bouncer name and display name
- Team tag (colour-coded by team)
- Volume per day
- Current status dot (green / red / amber / grey)
- DAG memberships

Click a bouncer card to **select** it. Selected cards display a checkmark and an indigo ring. Multiple bouncers can be selected simultaneously.

**Team filter** — a row of team pills at the top of the left panel filters which bouncers are visible.

**Clear selection** — a button in the header clears all selected bouncers when at least one is active.

### Right panel — Bouncer Topology

The right panel shows all ETL pipelines that are downstream of the currently selected bouncer(s).

When multiple bouncers are selected, a toggle switches between:
- **Union mode** — shows pipelines reachable from *any* of the selected bouncers
- **Intersection mode** — shows only pipelines reachable from *all* of the selected bouncers

Each downstream ETL node shows:
- Pipeline display name
- Task ID
- Status dot

Click any ETL node to navigate to that pipeline in the Pipeline Registry (the bouncers tab is replaced by the catalog tab with the selected pipeline open).

**Integration with Bento Workspace:** When you click a bouncer node in the Pipeline Topology card of the Bento Workspace, the application automatically switches to the Bouncers tab with that bouncer pre-selected and its downstream topology displayed.

---

## 7. AI Architect Terminal

Navigate to the **ai** tab in the sidebar.

The AI Architect is a chat interface connected to an LLM that has been given full context about the ETL catalog — pipeline names, categories, descriptions, schemas, and relationships.

### How to use it

Type your question in the input bar at the bottom and press Enter or click Send. The AI responds in the message thread above.

**Example questions:**

- "Which pipelines track bandwidth utilization?"
- "What is the best way to join RouteTableSnapshot with BgpSessionMonitor?"
- "Show me all pipelines in the Vault team that have a `site_id` field."
- "What does DhcpLeaseSync write and who depends on it?"
- "I need daily traffic volume by prefix. Which pipeline should I use and how?"
- "Are there any pipelines that could help me build a network capacity forecast?"

### Tips

- Be specific about data domains (e.g., "DNS resolution data", "BGP session state") for more targeted answers.
- Ask follow-up questions — the conversation context is maintained within the session.
- The AI does not execute code or modify data; it is a catalog intelligence layer only.
- Chat history is preserved for the duration of your browser session. Click **Clear** in the terminal header to reset the conversation.

---

## 8. Admin Panel

Navigate to the **admin** tab. This tab is only visible to users with the `admin` role.

The Admin Panel has three sub-tabs: **Users**, **Teams**, and **Grants**.

### 8.1 Users

The Users sub-tab lists every SSO user who has logged into ETL Nexus.

**Search** — a search bar filters users by name or username.

**Expanding a user row** (click the chevron) reveals:
- Team memberships (sourced from SSO groups)
- Active visibility grants affecting this user (both grants given directly to the user and grants given to their teams)

**Changing a role** — click the current role badge to open a dropdown and select a new role. Roles are: `admin`, `member`, `viewer`. The change takes effect immediately.

**Note:** Team memberships are controlled by the identity provider (Keycloak), not by ETL Nexus. Changing a user's team requires updating their group membership in Keycloak.

### 8.2 Teams

The Teams sub-tab lists all teams registered in the system, with member counts. This is a read-only view for reference.

### 8.3 Grants

The Grants sub-tab manages visibility grants — explicit cross-team access permissions.

**Without grants**, a user sees only:
- Pipelines owned by their team(s)
- Pipelines with no team assigned

**With grants**, additional access can be given.

**Existing grants** are listed with:
- What was granted (a specific pipeline or an entire team's catalog)
- Who received the grant (a team or a specific user)
- Grant level (viewer or editor)
- A delete button (X) to revoke the grant

**Creating a new grant:**

Click **New Grant** to expand the grant creation form. Fill in four fields:

1. **Grantee type** — choose whether the grant is for a **Team** (all members of a team gain access) or a **User** (a specific individual).
2. **Grantee** — select the specific team or user from the dropdown.
3. **Grant type** — choose whether you are granting access to a specific **Pipeline** or to all pipelines belonging to a **Source Team**.
4. **Grant level** — `viewer` (read-only access) or `editor` (can edit description and documentation).

Click **Create** to save. The new grant appears in the list immediately.

**Example:** To give the Relay team editor access to all pipelines owned by the Dagger team, set grantee type = Team, grantee = Relay, grant type = Source Team, source team = Dagger, grant level = editor.

---

## 9. Key Workflows

### 9.1 Finding a Pipeline

1. Click the **catalog** tab.
2. Type a keyword into the search bar — pipeline name, a word from the description, or a field name.
3. Optionally open the filter drawer to narrow by team, DAG network, or status.
4. Click the pipeline card. The Bento Workspace opens to the right with full details.

**Tip:** If you know the team that owns the data but not the pipeline name, use the Team filter to reduce the list to a manageable set and then scan by description.

### 9.2 Understanding Data Dependencies

1. Select a pipeline in the Registry.
2. In the Bento Workspace, look at the **Pipeline Topology** card.
3. The **Dependencies column** shows direct upstream pipelines (Needs = hard, Prefers = soft).
4. Click any upstream node to navigate to that pipeline.
5. For a recursive view of all ancestors across every dependency level, click **Full Upstream** to open the Upstream Topology Modal.
6. In the modal, follow orange (Needs) and blue (Prefers) edges back to bouncer and root nodes to understand the full data lineage.

### 9.3 Checking Spark Performance

1. Select a pipeline that has run history.
2. Scroll to the **Resource Performance Card** (Row 2 of the Bento Workspace).
3. Review the **Duration History** section: average run time, min/max range, and the bar chart of recent runs coloured by outcome.
4. Check the **Cluster Capacity** section to understand how much of total cluster resources this pipeline consumes. Bars turning amber or red indicate the pipeline is resource-intensive.
5. If the pipeline has logged actual usage, compare **Allocated** vs **Actual** values to identify over- or under-provisioning.

### 9.4 Debugging Execution Steps

1. Select a pipeline that has a recent completed run.
2. Scroll to the **Transform Inspector** card (Row 2.5).
3. Read the execution plan tree top-down: blue nodes are reads, green are writes, amber are shuffles, indigo are transforms.
4. Click any node to see its detailed metrics (row counts, time breakdown, bytes shuffled).
5. Expensive shuffles (large amber nodes with high byte counts) are common performance bottlenecks — the preceding transform or join is usually the cause.
6. Click the expand icon in the card header for the full-screen plan view, which is easier to read for deep trees.

### 9.5 Finding Join Opportunities

**Method 1 — Join Intelligence card:**
1. Select a pipeline.
2. Scroll to the **Join Intelligence** card (Row 3, right side).
3. Check **Schema Matches** for pipelines sharing field names with the current pipeline.
4. Read the **AI Insights** section for semantically informed join suggestions.

**Method 2 — Schema Matrix:**
1. Navigate to the **matrix** tab.
2. Find the field name you want to join on in the left column.
3. The **Pipelines** column lists all pipelines that contain that field — these are your join candidates.

**Method 3 — AI Architect:**
1. Navigate to the **ai** tab.
2. Ask directly: "Which pipelines can I join with `{PipelineName}` on `device_id`?"

### 9.6 Consuming a Pipeline in Code

1. Select the pipeline in the Registry.
2. Scroll to the **Import and Consume Snippet** card (Row 3, right column).
3. Read the generated code snippet.
4. Click the copy button in the card header.
5. Paste the snippet into your PySpark notebook or ETL file.
6. Replace `"date"` with your actual partition value or date string.

For ETL pipelines, the pattern is:
```python
from etls import Catalog, Engine
Catalog(Engine.Spark).iceberg.dagger.<pipeline_name>("<date>").consume().as_pyspark()
```

For API pipelines:
```python
from path import api
<pipeline_name> = <pipeline_name>(start_date, end_date)
```

### 9.7 Cross-Pipeline Field Analysis

1. Navigate to the **matrix** tab.
2. Scan the **Frequency** column for high values — these fields appear in the most pipelines and are likely shared dimensions or primary keys.
3. Click the pipeline pills in the **Pipelines** column to see which specific pipelines share a field (note: clicking the pill does not navigate; use it as a reference, then find the pipeline in the Registry).
4. Use this information to plan joins or identify canonical key fields across the data platform.

### 9.8 Exploring Bouncer Ingestion Points

1. Navigate to the **bouncers** tab.
2. Browse the bouncer grid. Use the team filter pills to narrow to bouncers owned by a specific team.
3. Click one or more bouncer cards to select them (checkmark appears).
4. The right panel shows the Bouncer Topology: all ETL pipelines triggered by the selected bouncer(s).
5. Use the **Union / Intersection** toggle to change multi-bouncer mode.
6. Click any ETL node in the topology to jump to that pipeline's Bento Workspace.

**Alternative entry point:** In the Pipeline Topology card of the Bento Workspace, bouncers appear in the leftmost column. Click any bouncer node there to jump directly to the Bouncers tab with that bouncer pre-selected.

### 9.9 AI-Powered Discovery

1. Navigate to the **ai** tab.
2. Describe what you need in natural language. Some effective patterns:
   - **Goal-oriented:** "I want to build a dashboard showing BGP route stability over the past 30 days. Which pipelines should I use?"
   - **Field-oriented:** "Which pipeline contains the most granular per-interface traffic counters?"
   - **Lineage-oriented:** "What is upstream of the `NetworkCapacityForecast` pipeline?"
   - **Comparison:** "What is the difference between `BandwidthUtilization` and `InterfaceTrafficSummary`?"
3. Read the response and ask follow-up questions as needed.
4. Use pipeline names from AI responses to navigate directly in the Pipeline Registry.

### 9.10 Editing Pipeline Documentation

1. Select a pipeline you have edit permission for (members can edit their own team's pipelines; admins can edit any pipeline).
2. **Short description:** Hover over the description text in the Pipeline Header. A pencil icon appears on the right. Click it to edit inline. Press Ctrl+Enter to save or Escape to cancel.
3. **Full documentation:** Click the **Docs** button (file icon) in the Pipeline Header to open the Documentation Modal. Click **Edit** to enter edit mode. Write Markdown documentation using the toolbar shortcuts or by typing directly. Click **Save** when done.

Changes are saved immediately. The "last updated by" metadata in the Pipeline Header updates to reflect your username.

### 9.11 Managing Team Access

_Requires admin role._

**To share a single pipeline with another team:**
1. Navigate to the **admin** tab and click **Grants**.
2. Click **New Grant**.
3. Set grantee type to **Team**, select the receiving team.
4. Set grant type to **Pipeline**, select the specific pipeline.
5. Set grant level to **viewer** (read-only) or **editor** (can edit description/docs).
6. Click **Create**.

**To share all pipelines from one team with another:**
1. Same as above, but set grant type to **Source Team** and select the source team.

**To give a specific user access to a pipeline (regardless of their team):**
1. Same process, but set grantee type to **User** and select the user.

**To revoke a grant:**
1. Navigate to **admin > Grants**.
2. Find the grant in the list.
3. Click the **X** button on that row.

---

## 10. Status Indicators Reference

Status dots and badges appear throughout the application. All follow a consistent colour system:

| Status | Colour | Meaning |
|--------|--------|---------|
| success | Green (emerald) with glow | Last run completed successfully |
| failed | Red (rose) with glow | Last run ended in failure |
| upstream_failed | Orange | A dependency failed; this task was skipped |
| running | Amber, pulsing | Task is currently executing |
| queued | Sky blue | Task is waiting to be picked up by a worker |
| unknown | Grey | No run history or status not yet fetched |

---

## 11. Dependency Types Reference

Two types of upstream dependency exist, visible in the Pipeline Topology card and the Upstream Topology Modal:

| Type | Icon | Colour | Meaning |
|------|------|--------|---------|
| Needs | Lock | Orange | Hard dependency. The pipeline will not start if any `Needs` dependency has not succeeded. |
| Prefers | Sparkles | Blue/sky | Soft dependency. The pipeline starts regardless of this dependency's outcome, but prefers its data to be ready. |

In practice:
- Use **Needs** when your analysis requires the upstream data to be complete and correct.
- Use **Prefers** when the upstream data enriches your output but its absence is acceptable.

---

## 12. Dev User Reference

The following users are pre-configured for development and testing:

| Username | Password | Role | Teams |
|----------|----------|------|-------|
| alice | password | admin | Dagger |
| bob | password | member | Vault, Prism |
| charlie | password | member | Relay |
| diana | password | member | Oasis |

These accounts exist in the local Keycloak instance. Alice can see all pipelines and the Admin panel. Bob, Charlie, and Diana see only pipelines belonging to their respective teams (plus unassigned pipelines and any explicit grants).

To test cross-team visibility grants, log in as Alice, create a grant in the Admin panel giving Bob's team access to a Dagger pipeline, then log in as Bob to verify it appears in his Pipeline Registry.
