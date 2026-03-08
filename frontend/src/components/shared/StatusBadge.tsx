interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, size = "sm" }: StatusBadgeProps) {
  const isSuccess = status === "success";
  const isFailed = status === "failed";

  if (size === "sm") {
    return (
      <div
        className={`w-2 h-2 rounded-full shrink-0 ${
          isSuccess
            ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"
            : isFailed
              ? "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)] animate-pulse"
              : "bg-slate-500"
        }`}
      />
    );
  }

  return (
    <span
      className={`text-[10px] font-mono uppercase tracking-widest px-2 py-1 rounded border ${
        isSuccess
          ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
          : isFailed
            ? "text-rose-400 bg-rose-500/10 border-rose-500/20"
            : "text-slate-400 bg-slate-500/10 border-slate-500/20"
      }`}
    >
      {isSuccess
        ? "Airflow: Success"
        : isFailed
          ? "Airflow: Failed"
          : "Airflow: Unknown"}
    </span>
  );
}
