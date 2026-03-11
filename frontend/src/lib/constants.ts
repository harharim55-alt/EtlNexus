export const TABS = {
  CATALOG: "catalog",
  MATRIX: "matrix",
  DAGS: "dags",
  SENSORS: "sensors",
  AI: "ai",
} as const;

export type TabType = (typeof TABS)[keyof typeof TABS];
