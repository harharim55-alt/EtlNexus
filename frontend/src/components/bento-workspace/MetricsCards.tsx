interface MetricsCardsProps {
  rowsPerDay: string | null;
  schedule: string | null;
}

export function MetricsCards({ rowsPerDay, schedule }: MetricsCardsProps) {
  return (
    <div className="col-span-12 lg:col-span-4 grid grid-rows-2 gap-6">
      <div className="bg-card border border-border rounded-2xl p-5 flex flex-col justify-center">
        <div className="text-[11px] font-mono uppercase tracking-widest text-text-muted mb-1">
          Volume Rate
        </div>
        <div className="flex items-end gap-2">
          <span className="text-2xl font-semibold text-foreground tracking-tight">
            {rowsPerDay ?? "—"}
          </span>
          <span className="text-sm text-text-muted mb-1">rows/day</span>
        </div>
      </div>
      <div className="bg-card border border-border rounded-2xl p-5 flex flex-col justify-center">
        <div className="text-[11px] font-mono uppercase tracking-widest text-text-muted mb-1">
          Schedule
        </div>
        <div className="text-lg font-medium text-foreground">
          {schedule ?? "—"}
        </div>
      </div>
    </div>
  );
}
