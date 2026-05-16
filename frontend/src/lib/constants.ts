export const TABS = {
  CATALOG: "catalog",
  DATA_PRODUCTS: "data-products",
  MATRIX: "matrix",
  DAGS: "dags",
  BOUNCERS: "bouncers",
  AI: "ai",
  ADMIN: "admin",
} as const;

export type TabType = (typeof TABS)[keyof typeof TABS];
