import {
  Database,
  HardDrive,
  ArrowRightLeft,
  Activity,
} from "lucide-react";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export const NODE_STYLES: Record<
  ExecutionPlanNode["type"],
  {
    bg: string;
    border: string;
    text: string;
    icon: typeof Database;
  }
> = {
  read: {
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
    text: "text-blue-400",
    icon: Database,
  },
  write: {
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
    text: "text-emerald-400",
    icon: HardDrive,
  },
  shuffle: {
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    text: "text-amber-400",
    icon: ArrowRightLeft,
  },
  transform: {
    bg: "bg-indigo-500/10",
    border: "border-indigo-500/30",
    text: "text-indigo-400",
    icon: Activity,
  },
};

// Metrics that get prominent display with ⏱ icon
export const TIME_KEYS = new Set([
  "scan time",
  "build time",
  "stream time",
  "sort time",
  "agg time",
  "plan time",
  "metadata",
]);

// Metrics to hide (low-value noise for cards)
export const HIDDEN_KEYS = new Set(["data files", "files"]);
