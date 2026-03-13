import { getStatusStyle } from "@/lib/status-config";

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, size = "sm" }: StatusBadgeProps) {
  const cfg = getStatusStyle(status);

  if (size === "sm") {
    return <div className={`w-2 h-2 rounded-full shrink-0 ${cfg.dot} ${cfg.glow}`} />;
  }

  return (
    <span
      className={`text-[10px] font-mono uppercase tracking-widest px-2 py-1 rounded border ${cfg.text} ${cfg.bg} border-current/20`}
    >
      Airflow: {cfg.label}
    </span>
  );
}
