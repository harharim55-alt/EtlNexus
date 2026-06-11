export const TABS = {
  DATA_PRODUCTS: "data-products",
  MATRIX: "matrix",
  AI: "ai",
  ADMIN: "admin",
} as const;

export type TabType = (typeof TABS)[keyof typeof TABS];
