// Runtime config from config.js (injected at container start), with build-time fallback
const runtimeConfig = (window as unknown as { __RUNTIME_CONFIG__?: Record<string, string> })
  .__RUNTIME_CONFIG__ ?? {};

export const AIRFLOW_URL =
  runtimeConfig.AIRFLOW_URL ?? import.meta.env.VITE_AIRFLOW_URL ?? "http://localhost:8080";
