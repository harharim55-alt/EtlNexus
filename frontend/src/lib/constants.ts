export const TABS = {
  CATALOG: "catalog",
  MATRIX: "matrix",
  AI: "ai",
} as const;

export type TabType = (typeof TABS)[keyof typeof TABS];
