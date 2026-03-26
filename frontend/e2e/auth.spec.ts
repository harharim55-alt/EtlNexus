import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test("loads the app and authenticates with default user (SSO disabled)", async ({ page }) => {
    await page.goto("/");
    // App should load without login screen when SSO is disabled
    await expect(page).not.toHaveURL(/.*login.*/);
    // Should see the main layout
    await expect(page.locator("body")).toBeVisible();
  });

  test("health check endpoint responds", async ({ request }) => {
    const response = await request.get("/api/health");
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.status).toBeDefined();
  });
});
