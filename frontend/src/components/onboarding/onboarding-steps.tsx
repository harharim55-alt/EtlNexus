import type { LucideIcon } from "lucide-react";
import {
  Zap,
  Package,
  Network,
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
      "You are now connected to the Data Products catalog. This briefing walks you through the control surfaces available to you. Data products are discovered and described here, with schemas sourced live from Spark Connect.",
    icon: Zap,
    iconBg: "bg-indigo-500/10",
    iconBorder: "border-indigo-500/20",
    iconText: "text-indigo-400",
    dotColor: "bg-indigo-400/60",
    panelPosition: "center",
    isWelcome: true,
    features: [
      "Catalog of published data products",
      "Auto-fetched schema + consume snippet",
      "Team-based access and editing",
      "AI-powered architecture analysis",
    ],
  },
  {
    id: "data-products",
    title: "Data Products",
    subtitle: "MODULE: DATA_PRODUCTS",
    description:
      "Your primary command surface. Browse data products grouped by team, filter by team or schedule, and open any product to inspect its description, documentation, schema (data structure) and import & consume snippet. Create a new product with the + button.",
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
      "Team-grouped product registry",
      "Filter by team + schedule",
      "New Data Product: name, description, documentation, schedule",
      "Schema + consume auto-fetched; both manually editable",
    ],
  },
  {
    id: "matrix",
    title: "Field Matrix",
    subtitle: "MODULE: FIELD_FREQUENCY",
    description:
      "Cross-product field frequency analysis. See which fields appear across multiple data products and discover implicit connections in your data.",
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
      "Field frequency across all products",
      "Entity mapping and relationship discovery",
    ],
  },
  {
    id: "ai",
    title: "AI Architect Terminal",
    subtitle: "MODULE: AI_TERMINAL",
    description:
      "A goal-oriented natural language interface to your entire catalog. Ask the AI Architect to find related products, design joins, or explain relationships.",
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
      "Full schema context",
    ],
  },
  {
    id: "admin-panel",
    title: "Access Control Panel",
    subtitle: "MODULE: ADMIN_RBAC",
    description:
      "As an administrator (team leader), you have access to the Access Control panel. Manage user roles, browse teams, and manage your team's membership — add users by username and remove members (you can't remove yourself). Roles come from Keycloak: admin, member, viewer.",
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
      "User management with role assignment",
      "Team overview",
      "Add/remove your team's members by username",
    ],
  },
  {
    id: "ready",
    title: "Mission Ready",
    subtitle: "BRIEFING COMPLETE",
    description:
      "You are now briefed on all systems. Start by exploring the Data Products catalog — select any product to dive into its details.",
    icon: CheckCircle2,
    iconBg: "bg-emerald-500/10",
    iconBorder: "border-emerald-500/20",
    iconText: "text-emerald-400",
    dotColor: "bg-emerald-400/60",
    navigateTo: "data-products",
    panelPosition: "center",
    isFinal: true,
  },
];

export function getOnboardingSteps(isUserAdmin: boolean): OnboardingStep[] {
  return ALL_STEPS.filter((step) => !step.adminOnly || isUserAdmin);
}
