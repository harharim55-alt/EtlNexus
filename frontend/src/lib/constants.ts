export const TABS = {
  CATALOG: "catalog",
  MATRIX: "matrix",
  DAGS: "dags",
  SENSORS: "sensors",
  AI: "ai",
  ADMIN: "admin",
} as const;

export type TabType = (typeof TABS)[keyof typeof TABS];
