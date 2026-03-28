import {
  FileText,
  User,
  Calendar,
  Clock,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { formatRelativeTime, formatFreshness } from "@/lib/format";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";

/* ── Props ─────────────────────────────────────────────────────────── */

interface HeaderActionsProps {
  lastUpdatedBy: string | null;
  lastUpdatedAt: string | null;
  executionDate: string | null;
  dagId: string | null;
  taskId: string | null;
  airflowUrl: string;
  isSyncing: boolean;
  onSync: () => void;
  onOpenDocs: () => void;
}

/* ── Component ─────────────────────────────────────────────────────── */

export function HeaderActions({
  lastUpdatedBy,
  lastUpdatedAt,
  executionDate,
  dagId,
  taskId,
  airflowUrl,
  isSyncing,
  onSync,
  onOpenDocs,
}: HeaderActionsProps) {
  const fresh = executionDate ? formatFreshness(executionDate) : null;

  return (
    <div className="flex items-center gap-2 shrink-0">
      {fresh && fresh.label !== "never" && (
        <span
          className={`hidden xl:flex items-center gap-1.5 text-[11px] font-mono bg-hover-bg px-2.5 py-1.5 rounded-lg border border-border ${fresh.className}`}
          title="Last Airflow run"
        >
          <Clock className="size-3" />
          {fresh.label}
        </span>
      )}
      {lastUpdatedBy && (
        <span
          className="hidden xl:flex items-center gap-1.5 text-[11px] text-text-muted font-mono bg-hover-bg px-2.5 py-1.5 rounded-lg border border-border"
          title="Last updated by"
        >
          <User className="size-3 text-text-faint" />
          {lastUpdatedBy}
        </span>
      )}
      {lastUpdatedAt && (
        <span
          className="hidden xl:flex items-center gap-1.5 text-[11px] text-text-muted font-mono bg-hover-bg px-2.5 py-1.5 rounded-lg border border-border"
          title="Last updated"
        >
          <Calendar className="size-3 text-text-faint" />
          {formatRelativeTime(lastUpdatedAt)}
        </span>
      )}

      {/* Docs icon-button */}
      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              variant="outline"
              size="icon-sm"
              onClick={onOpenDocs}
              className="border-border-prominent bg-hover-bg text-text-secondary hover:text-indigo-400 hover:bg-indigo-500/10 hover:border-indigo-500/20 transition-all duration-200"
            />
          }
        >
          <FileText className="size-3.5" />
        </TooltipTrigger>
        <TooltipContent side="bottom">
          Open Documentation
        </TooltipContent>
      </Tooltip>

      {/* Open in Airflow */}
      {dagId && taskId && (
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  window.open(
                    `${airflowUrl}/dags/${dagId}/grid?task_id=${taskId}`,
                    "_blank",
                    "noopener,noreferrer",
                  )
                }
                className="border-border-prominent bg-hover-bg text-text-secondary hover:text-amber-400 hover:bg-amber-500/10 hover:border-amber-500/20 transition-all duration-200"
              />
            }
          >
            <ExternalLink className="size-3.5" />
            <span className="text-xs">Airflow</span>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            Open in Airflow ({dagId})
          </TooltipContent>
        </Tooltip>
      )}

      {/* Sync button */}
      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              variant="outline"
              size="sm"
              disabled={isSyncing}
              onClick={onSync}
              className="border-border-prominent bg-hover-bg text-text-secondary hover:text-foreground hover:bg-hover-bg-strong transition-all duration-200"
            />
          }
        >
          <RefreshCw
            className={`size-3.5 ${isSyncing ? "animate-spin" : ""}`}
          />
          <span className="text-xs">
            {isSyncing ? "Syncing\u2026" : "Sync"}
          </span>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          Refresh this pipeline from Airflow
        </TooltipContent>
      </Tooltip>
    </div>
  );
}
