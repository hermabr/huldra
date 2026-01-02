import { test, expect } from "@playwright/test";

test.describe("API Endpoints", () => {
  test("health endpoint returns healthy", async ({ request }) => {
    const response = await request.get("/api/health");
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.status).toBe("healthy");
    expect(data.version).toBeDefined();
  });

  test("experiments endpoint returns list", async ({ request }) => {
    const response = await request.get("/api/experiments");
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.experiments).toBeDefined();
    expect(Array.isArray(data.experiments)).toBe(true);
    expect(typeof data.total).toBe("number");
  });

  test("experiments endpoint supports filtering", async ({ request }) => {
    const response = await request.get(
      "/api/experiments?result_status=success&limit=5"
    );
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.experiments).toBeDefined();
    expect(data.experiments.length).toBeLessThanOrEqual(5);
  });

  test("stats endpoint returns statistics", async ({ request }) => {
    const response = await request.get("/api/stats");
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(typeof data.total).toBe("number");
    expect(typeof data.running_count).toBe("number");
    expect(typeof data.success_count).toBe("number");
    expect(typeof data.failed_count).toBe("number");
    expect(Array.isArray(data.by_result_status)).toBe(true);
  });

  test("nonexistent experiment returns 404", async ({ request }) => {
    const response = await request.get(
      "/api/experiments/nonexistent.namespace/fakehash123"
    );
    expect(response.status()).toBe(404);
  });
});


