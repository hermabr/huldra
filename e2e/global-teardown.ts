import * as fs from "fs";

async function globalTeardown() {
  const dataDir = process.env.GREN_E2E_DATA_DIR ?? process.env.GREN_PATH;

  if (!dataDir) {
    return;
  }

  console.log(`Removing e2e data directory ${dataDir}...`);
  fs.rmSync(dataDir, { recursive: true, force: true });
}

export default globalTeardown;
