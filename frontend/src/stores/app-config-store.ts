import { create } from "zustand";

// Runtime branding + client tuning delivered by the backend via /api/auth/config
// (APP_NAME / APP_OWNER / AI_REQUEST_TIMEOUT_SECONDS). Defaults below are the
// fallback used before config loads or when the endpoint is unreachable.
const DEFAULT_APP_NAME = "ETL Nexus";
const DEFAULT_AI_TIMEOUT_MS = 300_000;

interface AppConfigState {
  appName: string;
  appOwner: string;
  aiRequestTimeoutMs: number;
  setBranding: (appName?: string, appOwner?: string) => void;
  setAiRequestTimeoutMs: (ms: number) => void;
}

export const useAppConfigStore = create<AppConfigState>((set) => ({
  appName: DEFAULT_APP_NAME,
  appOwner: "",
  aiRequestTimeoutMs: DEFAULT_AI_TIMEOUT_MS,
  setBranding: (appName, appOwner) =>
    set({
      ...(appName ? { appName } : {}),
      ...(appOwner !== undefined ? { appOwner } : {}),
    }),
  setAiRequestTimeoutMs: (ms) => set({ aiRequestTimeoutMs: ms > 0 ? ms : DEFAULT_AI_TIMEOUT_MS }),
}));
