import type { LucideIcon } from "lucide-react";
import {
  Zap,
  Database,
  LayoutGrid,
  Package,
  Network,
  BarChart3,
  Radio,
  Sparkles,
  Shield,
  CheckCircle2,
} from "lucide-react";
import type { TabType } from "@/lib/constants";

export type PanelPosition = "center" | "right" | "bottom-left" | "bottom-right";

export interface OnboardingStep {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  icon: LucideIcon;
  iconBg: string;
  iconBorder: string;
  iconText: string;
  dotColor: string;
  spotlightTarget?: TabType;
  sectionTarget?: string;
  navigateTo?: TabType;
  panelPosition: PanelPosition;
  adminOnly?: boolean;
  airflowOnly?: boolean;  // shown only when the Airflow integration is enabled
  features?: string[];
  isWelcome?: boolean;
  isFinal?: boolean;
}

const ALL_STEPS: OnboardingStep[] = [
  {
    id: "welcome",
    title: "Welcome to ETL Nexus",
    subtitle: "INITIALIZING COMMAND CENTER",
    description:
      "You are now connected to the Data Architecture Command Center. This briefing will walk you through the control surfaces available to you as an operator. ETL Nexus discovers, maps, and monitors your entire data pipeline ecosystem \u2014 all sourced live from Airflow.",
    icon: Zap,
    iconBg: "bg-indigo-500/10",
    iconBorder: "border-indigo-500/20",
    iconText: "text-indigo-400",
    dotColor: "bg-indigo-400/60",
    panelPosition: "center",
    isWelcome: true,
    features: [
      "Live pipeline discovery from Airflow",
      "Team-based access and visibility",
      "AI-powered architecture analysis",
      "Real-time DAG health monitoring",
    ],
  },
  {
    id: "catalog",
    title: "Pipeline Registry",
    subtitle: "MODULE: ETL_CATALOG",
    description:
      "Your primary command surface. Browse all discovered ETL pipelines with real-time Airflow status indicators. Search by name, description, or field name. Filter by team, DAG, or execution status.",
    icon: Database,
    iconBg: "bg-indigo-500/10",
    iconBorder: "border-indigo-500/20",
    iconText: "text-indigo-400",
    dotColor: "bg-indigo-400/60",
    spotlightTarget: "catalog",
    sectionTarget: "pipeline-registry",
    navigateTo: "catalog",
    panelPosition: "right",
    features: [
      "Searchable master list with infinite scroll",
      "Team badges and Airflow status indicators",
      "Multi-dimension filtering (team, DAG, status)",
      "Click any pipeline to open the Bento Workspace",
    ],
  },
  {
    id: "workspace",
    title: "Bento Workspace",
    subtitle: "MODULE: DETAIL_VIEW",
    description:
      "The operational detail view for any selected pipeline. A bento-box layout surfaces everything about a pipeline in one view: lineage topology, schema structure, resource performance, execution plans, and consumption snippets.",
    icon: LayoutGrid,
    iconBg: "bg-violet-500/10",
    iconBorder: "border-violet-500/20",
    iconText: "text-violet-400",
    dotColor: "bg-violet-400/60",
    sectionTarget: "bento-workspace",
    navigateTo: "catalog",
    panelPosition: "bottom-left",
    features: [
      "Pipeline lineage and DAG topology",
      "Schema structure with field details",
      "Resource allocation vs actual usage",
      "Spark execution plan inspector",
      "1-click consume code snippets",
      "AI-powered join intelligence",
    ],
  },
  {
    id: "data-products",
    title: "Data Products",
    subtitle: "MODULE: DATA_PRODUCTS",
    description:
      "Curated, published datasets promoted from pipelines. Browse data products grouped by category, search and filter by team, network, or tag, and open any product to inspect its schema, lineage, and consumption snippets.",
    icon: Package,
    iconBg: "bg-sky-500/10",
    iconBorder: "border-sky-500/20",
    iconText: "text-sky-400",
    dotColor: "bg-sky-400/60",
    spotlightTarget: "data-products",
    sectionTarget: "data-products-registry",
    navigateTo: "data-products",
    panelPosition: "right",
    features: [
      "Category-grouped data product registry",
      "Search + team / network / tag filters",
      "Promote a pipeline to a data product",
      "Per-product schema, lineage, and consume snippets",
    ],
  },
  {
    id: "matrix",
    title: "Global Schema Matrix",
    subtitle: "MODULE: FIELD_FREQUENCY",
    description:
      "Cross-pipeline field frequency analysis. See which fields appear across multiple pipelines, identify entity relationships, and discover implicit connections in your data architecture.",
    icon: Network,
    iconBg: "bg-cyan-500/10",
    iconBorder: "border-cyan-500/20",
    iconText: "text-cyan-400",
    dotColor: "bg-cyan-400/60",
    spotlightTarget: "matrix",
    sectionTarget: "schema-matrix",
    navigateTo: "matrix",
    panelPosition: "bottom-right",
    features: [
      "Field frequency across all pipelines",
      "Entity mapping and relationship discovery",
      "Virtualized infinite-scroll for large schemas",
    ],
  },
  {
    id: "dags",
    airflowOnly: true,
    title: "DAG Operations Dashboard",
    subtitle: "MODULE: DAG_OVERVIEW",
    description:
      "Monitor all Airflow DAGs from a single view. See aggregate health metrics, per-DAG task breakdowns, success/failure rates, and schedule information. Identify operational issues before they cascade.",
    icon: BarChart3,
    iconBg: "bg-amber-500/10",
    iconBorder: "border-amber-500/20",
    iconText: "text-amber-400",
    dotColor: "bg-amber-400/60",
    spotlightTarget: "dags",
    sectionTarget: "dag-dashboard",
    navigateTo: "dags",
    panelPosition: "bottom-right",
    features: [
      "Aggregate health across all DAGs",
      "Per-DAG task status breakdown",
      "Schedule and timing information",
      "Direct links to Airflow UI",
    ],
  },
  {
    id: "bouncers",
    airflowOnly: true,
    title: "Bouncer Monitoring",
    subtitle: "MODULE: BOUNCER_WATCH",
    description:
      "Track Airflow bouncers across your ecosystem. Filter by team, view bouncer topologies, and monitor the watchers that keep your pipelines triggered on time.",
    icon: Radio,
    iconBg: "bg-teal-500/10",
    iconBorder: "border-teal-500/20",
    iconText: "text-teal-400",
    dotColor: "bg-teal-400/60",
    spotlightTarget: "bouncers",
    sectionTarget: "bouncers-view",
    navigateTo: "bouncers",
    panelPosition: "bottom-right",
    features: [
      "Team-filtered bouncer overview",
      "Bouncer topology visualization",
      "Status monitoring for all bouncer types",
    ],
  },
  {
    id: "ai",
    title: "AI Architect Terminal",
    subtitle: "MODULE: AI_TERMINAL",
    description:
      "A goal-oriented natural language interface to your entire data catalog. Ask the AI Architect to design joins, find related pipelines, suggest transformations, or explain pipeline relationships.",
    icon: Sparkles,
    iconBg: "bg-purple-500/10",
    iconBorder: "border-purple-500/20",
    iconText: "text-purple-400",
    dotColor: "bg-purple-400/60",
    spotlightTarget: "ai",
    sectionTarget: "ai-terminal",
    navigateTo: "ai",
    panelPosition: "bottom-right",
    features: [
      "Natural language queries against the catalog",
      "Join path recommendations",
      "Pipeline relationship analysis",
      "Full schema and lineage context",
    ],
  },
  {
    id: "admin-panel",
    title: "Access Control Panel",
    subtitle: "MODULE: ADMIN_RBAC",
    description:
      "As an administrator, you have access to the Access Control panel. Manage users, teams, and visibility grants. Control which teams can see which pipelines through per-pipeline or per-source-team grants.",
    icon: Shield,
    iconBg: "bg-rose-500/10",
    iconBorder: "border-rose-500/20",
    iconText: "text-rose-400",
    dotColor: "bg-rose-400/60",
    spotlightTarget: "admin",
    sectionTarget: "admin-panel",
    navigateTo: "admin",
    panelPosition: "bottom-right",
    adminOnly: true,
    features: [
      "User management with role assignment (admin, member, viewer)",
      "Team overview and membership",
      "Visibility grant management",
      "Per-pipeline and per-team grant types with viewer/editor levels",
    ],
  },
  {
    id: "ready",
    title: "Mission Ready",
    subtitle: "BRIEFING COMPLETE",
    description:
      "You are now briefed on all systems. The command center is fully operational. Start by exploring the ETL Catalog \u2014 select any pipeline to dive into its workspace.",
    icon: CheckCircle2,
    iconBg: "bg-emerald-500/10",
    iconBorder: "border-emerald-500/20",
    iconText: "text-emerald-400",
    dotColor: "bg-emerald-400/60",
    navigateTo: "catalog",
    panelPosition: "center",
    isFinal: true,
  },
];

export function getOnboardingSteps(
  isUserAdmin: boolean,
  activateAirflow: boolean,
): OnboardingStep[] {
  return ALL_STEPS.filter(
    (step) =>
      (!step.adminOnly || isUserAdmin) &&
      (!step.airflowOnly || activateAirflow),
  );
}
