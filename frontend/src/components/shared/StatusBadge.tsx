interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, size = "sm" }: StatusBadgeProps) {
  if (size === "sm") {
    const dotClass =
      status === "success"
        ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"
        : status === "failed"
          ? "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)] animate-pulse"
          : status === "upstream_failed"
            ? "bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.5)]"
            : status === "queued"
              ? "bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.4)]"
              : status === "running"
                ? "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.4)] animate-pulse"
                : "bg-slate-500";

    return <div className={`w-2 h-2 rounded-full shrink-0 ${dotClass}`} />;
  }

  const badgeConfig =
    status === "success"
      ? { cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", label: "Airflow: Success" }
      : status === "failed"
        ? { cls: "text-rose-400 bg-rose-500/10 border-rose-500/20", label: "Airflow: Failed" }
        : status === "upstream_failed"
          ? { cls: "text-orange-400 bg-orange-500/10 border-orange-500/20", label: "Airflow: Upstream Failed" }
          : status === "queued"
            ? { cls: "text-sky-400 bg-sky-500/10 border-sky-500/20", label: "Airflow: Queued" }
            : status === "running"
              ? { cls: "text-amber-400 bg-amber-500/10 border-amber-500/20", label: "Airflow: Running" }
              : { cls: "text-slate-400 bg-slate-500/10 border-slate-500/20", label: "Airflow: Unknown" };

  return (
    <span
      className={`text-[10px] font-mono uppercase tracking-widest px-2 py-1 rounded border ${badgeConfig.cls}`}
    >
      {badgeConfig.label}
    </span>
  );
}
