import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const require = createRequire(import.meta.url);

function loadPlaywright() {
  try {
    return require("playwright");
  } catch (error) {
    throw new Error(
      "Playwright is not resolvable. Set NODE_PATH to the main install, for example C:\\Users\\19029\\node_modules.",
      { cause: error },
    );
  }
}

function argValue(name, fallback) {
  const prefix = `--${name}=`;
  const match = process.argv.find((arg) => arg.startsWith(prefix));
  return match ? match.slice(prefix.length) : fallback;
}

const pgadminUrl = argValue("pgadmin-url", process.env.PGADMIN_URL ?? "http://127.0.0.1:5050");
const email = argValue("email", process.env.PGADMIN_EMAIL ?? process.env.PGADMIN_DEFAULT_EMAIL);
const password = argValue("password", process.env.PGADMIN_PASSWORD ?? process.env.PGADMIN_DEFAULT_PASSWORD);
const databasePassword = argValue("database-password", process.env.PGPASSWORD ?? "mdopendata_dev");
const serverName = argValue("server", process.env.PGADMIN_SERVER_NAME ?? "mdopendata PostGIS");
const schemaName = argValue("schema", process.env.PGADMIN_ERD_SCHEMA ?? "zoning");
const outputPath = path.resolve(argValue("output", "wiki/shared/assets/zoning-schema-erd.png"));
const headless = argValue("headless", process.env.PGADMIN_ERD_HEADLESS ?? "true") !== "false";

if (!email || !password) {
  throw new Error("PGADMIN_EMAIL and PGADMIN_PASSWORD, or matching --email and --password arguments, are required.");
}

const { chromium } = loadPlaywright();

async function connectServer(page) {
  await page.getByText("Servers", { exact: true }).dblclick();
  await page.waitForTimeout(500);
  await page.getByText(serverName, { exact: true }).dblclick({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(500);

  const passwordInputs = page.locator('input[type="password"]');
  if (await passwordInputs.count()) {
    await passwordInputs.fill(databasePassword);
    await page.locator(".MuiDialog-root button").filter({ hasText: "OK" }).click();
    await page.waitForTimeout(5000);
  }
}

async function openGeneratedErd(page) {
  await page.getByText(schemaName, { exact: true }).click();
  await page.waitForTimeout(500);
  await page.evaluate(() => {
    window.pgAdmin.Tools.ERD.showErdTool(null, window.pgAdmin.Browser.tree.selected(), true);
  });
  await page.waitForTimeout(15000);
  const frame = page.frames().find((candidate) => candidate.url().includes("/erd/panel/"));
  if (!frame) {
    throw new Error("pgAdmin ERD frame was not created.");
  }
  return frame;
}

async function main() {
  const browser = await chromium.launch({ headless });
  const page = await browser.newPage({
    acceptDownloads: true,
    viewport: { width: 2400, height: 1800 },
  });

  try {
    await page.goto(`${pgadminUrl.replace(/\/$/, "")}/login`, { waitUntil: "networkidle" });
    await page.locator('input[name="email"]').fill(email);
    await page.locator('input[name="password"]').fill(password);
    await page.getByRole("button", { name: "Login" }).click();
    await page.waitForURL("**/browser/**", { timeout: 10000 });
    await page.waitForTimeout(1500);

    await connectServer(page);
    const frame = await openGeneratedErd(page);
    await frame.getByLabel("Zoom to Fit").click();
    await page.waitForTimeout(1500);

    await mkdir(path.dirname(outputPath), { recursive: true });
    const downloadPromise = page.waitForEvent("download", { timeout: 30000 });
    await frame.getByLabel("Download image").click();
    const download = await downloadPromise;
    await download.saveAs(outputPath);
    console.log(JSON.stringify({ path: outputPath, suggestedFilename: download.suggestedFilename() }, null, 2));
  } finally {
    await browser.close();
  }
}

await main();
