import { create } from "zustand";

export type DatePreset = "24h" | "7d" | "30d" | "90d" | "custom";

const PRESET_MS: Record<Exclude<DatePreset, "custom">, number> = {
  "24h": 24 * 60 * 60 * 1000,
  "7d": 7 * 24 * 60 * 60 * 1000,
  "30d": 30 * 24 * 60 * 60 * 1000,
  "90d": 90 * 24 * 60 * 60 * 1000,
};

function computeRange(preset: Exclude<DatePreset, "custom">) {
  const now = new Date();
  return {
    dateFrom: new Date(now.getTime() - PRESET_MS[preset]).toISOString(),
    dateTo: now.toISOString(),
  };
}

interface DateRangeState {
  preset: DatePreset;
  dateFrom: string;
  dateTo: string;
  setPreset: (preset: Exclude<DatePreset, "custom">) => void;
  setCustomRange: (from: string, to: string) => void;
}

export const useDateRangeStore = create<DateRangeState>((set) => {
  const initial = computeRange("30d");
  return {
    preset: "30d",
    dateFrom: initial.dateFrom,
    dateTo: initial.dateTo,
    setPreset: (preset) => {
      const range = computeRange(preset);
      set({ preset, ...range });
    },
    setCustomRange: (from, to) => {
      set({ preset: "custom", dateFrom: from, dateTo: to });
    },
  };
});

/**
 * Returns { date_from, date_to } query params when the user has changed
 * from the default 30d preset. Returns undefined for the default so the
 * backend uses its own 30-day fallback and caching works optimally.
 */
export function useDateParams(): Record<string, string> | undefined {
  const { preset, dateFrom, dateTo } = useDateRangeStore();
  if (preset === "30d") return undefined;
  return { date_from: dateFrom, date_to: dateTo };
}

/** Human-readable label for the active period (e.g., "24h", "7d"). */
export function usePeriodLabel(): string {
  return useDateRangeStore((s) => s.preset === "custom" ? "custom" : s.preset);
}
