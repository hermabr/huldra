/**
 * Global setup for Playwright e2e tests.
 *
 * This script runs before all tests to generate test data using the
 * Python data generation script. It creates realistic Gren experiments
 * with various states and dependencies.
 *
 * For faster iteration, data is only regenerated if:
 * - The data directory doesn't exist
 * - The REGENERATE_DATA env var is set
 * - Running in CI
 */

import { execSync } from "child_process";
import * as fs from "fs";
import * as path from "path";

async function globalSetup() {
  const projectRoot = path.resolve(__dirname, "..");
  const e2eDir = __dirname;
  const dataDir = path.join(projectRoot, "data-gren");

  // Check if we should regenerate data
  const forceRegenerate = process.env.REGENERATE_DATA === "1" || process.env.CI;
  const dataExists = fs.existsSync(dataDir);

  if (dataExists && !forceRegenerate) {
    console.log("✅ Using existing test data (set REGENERATE_DATA=1 to force regeneration)");
    return;
  }

  console.log("🔧 Generating test data for e2e tests...");

  try {
    // Run the data generation script with --clean to ensure fresh data
    execSync(`uv run python ${path.join(e2eDir, "generate_data.py")} --clean`, {
      cwd: projectRoot,
      stdio: "inherit",
      env: {
        ...process.env,
        // Ensure we use the project's data-gren directory
        GREN_PATH: dataDir,
      },
    });
    console.log("✅ Test data generated successfully");
  } catch (error) {
    console.error("❌ Failed to generate test data:", error);
    throw error;
  }
}

export default globalSetup;
