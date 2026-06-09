import {
  Settings,
  User,
  Calendar,
  Clock,
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
  onOpenSettings?: () => void;
  canEdit?: boolean;
}

/* ── Component ─────────────────────────────────────────────────────── */

export function HeaderActions({
  lastUpdatedBy,
  lastUpdatedAt,
  executionDate,
  onOpenSettings,
  canEdit,
}: HeaderActionsProps) {
  const fresh = executionDate ? formatFreshness(executionDate) : null;

  return (
    <div className="flex items-center gap-2 shrink-0">
      {fresh && fresh.label !== "never" && (
        <span
          className={`hidden xl:flex items-center gap-1.5 text-[11px] font-mono bg-hover-bg px-2.5 py-1.5 rounded-lg border border-border ${fresh.className}`}
          title="Last run"
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

      {/* Settings */}
      {canEdit && onOpenSettings && (
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="outline"
                size="icon-sm"
                onClick={onOpenSettings}
                className="border-border-prominent bg-hover-bg text-text-secondary hover:text-foreground hover:bg-hover-bg-strong transition-all duration-200"
              />
            }
          >
            <Settings className="size-3.5" />
          </TooltipTrigger>
          <TooltipContent side="bottom">
            Settings
          </TooltipContent>
        </Tooltip>
      )}
    </div>
  );
}
