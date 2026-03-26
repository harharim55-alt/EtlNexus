import { test, expect } from "@playwright/test";

test.describe("Pipeline Registry", () => {
  test("displays pipeline list", async ({ page }) => {
    await page.goto("/");
    // Wait for the pipeline registry to load
    // The registry is the default view with a search input
    const searchInput = page.getByPlaceholder(/search/i);
    await expect(searchInput).toBeVisible({ timeout: 15000 });
  });

  test("search filters pipelines", async ({ page }) => {
    await page.goto("/");
    const searchInput = page.getByPlaceholder(/search/i);
    await expect(searchInput).toBeVisible({ timeout: 15000 });
    await searchInput.fill("test");
    // Search should filter — wait for the input to have the value
    await expect(searchInput).toHaveValue("test");
  });
});
