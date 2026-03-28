import { useState, useRef, useEffect } from "react";
import { Calendar } from "lucide-react";
import {
  useDateRangeStore,
  type DatePreset,
} from "@/stores/date-range-store";

const PRESETS: { label: string; value: Exclude<DatePreset, "custom"> }[] = [
  { label: "24h", value: "24h" },
  { label: "7d", value: "7d" },
  { label: "30d", value: "30d" },
  { label: "90d", value: "90d" },
];

const ACTIVE =
  "text-indigo-300 bg-indigo-500/15 border-indigo-500/30 shadow-[0_0_8px_rgba(99,102,241,0.12)]";
const INACTIVE =
  "text-text-muted bg-hover-bg border-border hover:border-border-prominent hover:text-text-secondary";

export function DateRangePicker() {
  const { preset, dateFrom, dateTo, setPreset, setCustomRange } =
    useDateRangeStore();
  const [showCustom, setShowCustom] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Local state for custom inputs
  const [localFrom, setLocalFrom] = useState("");
  const [localTo, setLocalTo] = useState("");

  // Sync local state when store changes
  useEffect(() => {
    if (preset === "custom") {
      setLocalFrom(toLocalInput(dateFrom));
      setLocalTo(toLocalInput(dateTo));
    }
  }, [preset, dateFrom, dateTo]);

  // Close popover on outside click
  useEffect(() => {
    if (!showCustom) return;
    function handleClick(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setShowCustom(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showCustom]);

  function handleApplyCustom() {
    if (localFrom && localTo) {
      setCustomRange(
        new Date(localFrom).toISOString(),
        new Date(localTo).toISOString(),
      );
      setShowCustom(false);
    }
  }

  return (
    <div className="flex items-center gap-1 relative">
      {PRESETS.map((p) => (
        <button
          key={p.value}
          type="button"
          onClick={() => {
            setPreset(p.value);
            setShowCustom(false);
          }}
          className={`text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer ${
            preset === p.value ? ACTIVE : INACTIVE
          }`}
        >
          {p.label}
        </button>
      ))}
      <button
        type="button"
        onClick={() => setShowCustom(!showCustom)}
        className={`text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer inline-flex items-center gap-1 ${
          preset === "custom" ? ACTIVE : INACTIVE
        }`}
      >
        <Calendar className="w-2.5 h-2.5" />
        Custom
      </button>

      {showCustom && (
        <div
          ref={popoverRef}
          className="absolute top-full right-0 mt-2 z-50 bg-card border border-border-prominent rounded-xl p-3 shadow-xl min-w-[280px]"
        >
          <div className="flex flex-col gap-2">
            <label className="text-[9px] font-mono uppercase tracking-widest text-text-muted">
              From
            </label>
            <input
              type="datetime-local"
              value={localFrom}
              onChange={(e) => setLocalFrom(e.target.value)}
              className="bg-hover-bg border border-border-prominent rounded-lg px-3 py-1.5 text-xs font-mono text-foreground focus:outline-none focus:border-indigo-500/50 [color-scheme:dark]"
            />
            <label className="text-[9px] font-mono uppercase tracking-widest text-text-muted">
              To
            </label>
            <input
              type="datetime-local"
              value={localTo}
              onChange={(e) => setLocalTo(e.target.value)}
              className="bg-hover-bg border border-border-prominent rounded-lg px-3 py-1.5 text-xs font-mono text-foreground focus:outline-none focus:border-indigo-500/50 [color-scheme:dark]"
            />
            <button
              type="button"
              onClick={handleApplyCustom}
              disabled={!localFrom || !localTo}
              className="mt-1 text-[10px] font-mono px-3 py-1.5 rounded-lg bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Apply
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/** Convert ISO string to datetime-local input value. */
function toLocalInput(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
