import { test, expect } from "@playwright/test";

test.describe("Dashboard Home Page", () => {
  test("should load the dashboard", async ({ page }) => {
    await page.goto("/");

    // Check that the page title is visible
    await expect(
      page.getByRole("heading", { name: "Dashboard" })
    ).toBeVisible();
  });

  test("should display API health status", async ({ page }) => {
    await page.goto("/");

    // Wait for the API status to load
    await expect(page.getByText("API Status:")).toBeVisible();
    await expect(page.getByText("Healthy")).toBeVisible();
  });

  test("should display stats cards", async ({ page }) => {
    await page.goto("/");

    // Check that stats cards are visible
    await expect(page.getByText("Total Experiments")).toBeVisible();
    await expect(page.getByText("Running")).toBeVisible();
    await expect(page.getByText("Successful")).toBeVisible();
    await expect(page.getByText("Failed")).toBeVisible();
  });

  test("should have working navigation", async ({ page }) => {
    await page.goto("/");

    // Check navigation links exist
    await expect(page.getByRole("link", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Experiments" })).toBeVisible();
  });

  test("should show version number", async ({ page }) => {
    await page.goto("/");

    // Wait for the version to load
    await expect(page.getByText(/v\d+\.\d+\.\d+/)).toBeVisible();
  });
});


