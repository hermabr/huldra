import { test, expect } from "@playwright/test";

test.describe("Experiments Page", () => {
  test("should load experiments page", async ({ page }) => {
    await page.goto("/experiments");

    // Check page loaded - use exact match to avoid matching "No experiments found"
    await expect(
      page.getByRole("heading", { name: "Experiments", exact: true })
    ).toBeVisible();
    await expect(
      page.getByText("Browse and filter all Huldra experiments")
    ).toBeVisible();
  });

  test("should display filter controls", async ({ page }) => {
    await page.goto("/experiments");

    // Check filter inputs exist
    await expect(page.getByPlaceholder("Filter by namespace...")).toBeVisible();
    await expect(page.getByRole("combobox").first()).toBeVisible();
  });

  test("should show results count", async ({ page }) => {
    await page.goto("/experiments");

    // Wait for experiments to load
    await expect(page.getByText(/Showing \d+ of \d+ experiments/)).toBeVisible({
      timeout: 10000,
    });
  });

  test("should filter by result status", async ({ page }) => {
    await page.goto("/experiments");

    // Wait for page to load - use exact match
    await expect(
      page.getByRole("heading", { name: "Experiments", exact: true })
    ).toBeVisible();

    // Wait for initial data to load
    await expect(page.getByText(/Showing \d+ of \d+ experiments/)).toBeVisible({
      timeout: 10000,
    });

    // Select success filter (first dropdown is result status)
    const resultStatusSelect = page.getByRole("combobox").first();
    await resultStatusSelect.selectOption("success");

    // Wait for filter to apply - the results count should update
    await page.waitForTimeout(500);
  });

  test("should filter by namespace", async ({ page }) => {
    await page.goto("/experiments");

    // Enter namespace filter
    const namespaceInput = page.getByPlaceholder("Filter by namespace...");
    await namespaceInput.fill("my_project");

    // Should trigger a filter (wait for URL update)
    await page.waitForTimeout(500); // debounce
  });

  test("should handle empty results gracefully", async ({ page }) => {
    // Filter with unlikely namespace
    await page.goto("/experiments?namespace=nonexistent_namespace_xyz");

    // Should show empty state with zero results count
    await expect(page.getByText("Showing 0 of 0 experiments")).toBeVisible({
      timeout: 10000,
    });
  });
});

