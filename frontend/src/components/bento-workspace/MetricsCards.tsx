interface MetricsCardsProps {
  rowsPerDay: string | null;
  schedule: string | null;
}

export function MetricsCards({ rowsPerDay, schedule }: MetricsCardsProps) {
  return (
    <div className="col-span-12 lg:col-span-4 grid grid-rows-2 gap-6">
      <div className="bg-[#18181b] border border-white/5 rounded-2xl p-5 flex flex-col justify-center">
        <div className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-1">
          Volume Rate
        </div>
        <div className="flex items-end gap-2">
          <span className="text-2xl font-semibold text-white tracking-tight">
            {rowsPerDay ?? "—"}
          </span>
          <span className="text-sm text-slate-500 mb-1">rows/day</span>
        </div>
      </div>
      <div className="bg-[#18181b] border border-white/5 rounded-2xl p-5 flex flex-col justify-center">
        <div className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-1">
          Schedule
        </div>
        <div className="text-lg font-medium text-white">
          {schedule ?? "—"}
        </div>
      </div>
    </div>
  );
}
