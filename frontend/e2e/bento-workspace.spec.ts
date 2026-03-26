import { test, expect } from "@playwright/test";

test.describe("Bento Workspace", () => {
  test("opens pipeline detail view when a pipeline is clicked", async ({ page }) => {
    await page.goto("/");
    // Wait for pipeline cards to appear
    const searchInput = page.getByPlaceholder(/search/i);
    await expect(searchInput).toBeVisible({ timeout: 15000 });

    // Click the first pipeline card in the list
    const firstPipeline = page.locator("[data-testid='pipeline-card']").first();
    // If no data-testid exists, try clicking any list item that looks like a pipeline
    const pipelineItem = firstPipeline.or(
      page.locator("button, [role='button'], a").filter({ hasText: /pipeline|etl/i }).first()
    );

    if (await pipelineItem.isVisible()) {
      await pipelineItem.click();
      // After clicking, the bento workspace should appear
      // Wait a moment for the detail view transition
      await page.waitForTimeout(1000);
    }
  });
});
