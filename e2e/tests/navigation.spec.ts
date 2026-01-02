import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test("should navigate to experiments page", async ({ page }) => {
    await page.goto("/");

    // Click on experiments link
    await page.getByRole("link", { name: "Experiments" }).click();

    // Should be on experiments page
    await expect(page).toHaveURL("/experiments");
    await expect(
      page.getByRole("heading", { name: "Experiments", exact: true })
    ).toBeVisible();
  });

  test("should navigate back to dashboard", async ({ page }) => {
    await page.goto("/experiments");

    // Click on dashboard link
    await page.getByRole("link", { name: "Dashboard" }).click();

    // Should be on dashboard
    await expect(page).toHaveURL("/");
    await expect(
      page.getByRole("heading", { name: "Dashboard" })
    ).toBeVisible();
  });

  test("should navigate via logo", async ({ page }) => {
    await page.goto("/experiments");

    // Click on Huldra logo/link
    await page.getByRole("link", { name: "Huldra" }).click();

    // Should be on dashboard
    await expect(page).toHaveURL("/");
  });
});

