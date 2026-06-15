export const TABS = {
  DATA_PRODUCTS: "data-products",
  TABLES: "tables",
  AI: "ai",
} as const;

export type TabType = (typeof TABS)[keyof typeof TABS];
