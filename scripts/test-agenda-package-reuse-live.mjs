#!/usr/bin/env node

import { spawn } from "node:child_process";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function availablePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => resolve(address.port));
    });
  });
}

async function waitForServer(baseUrl, child) {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    if (child.exitCode !== null) {
      throw new Error(`Server exited with ${child.exitCode}.`);
    }
    try {
      const response = await fetch(`${baseUrl}/healthz`);
      if (response.ok) return;
    } catch {
      // Continue until the bounded startup deadline.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("Server did not start.");
}

async function stopServer(child) {
  if (child.exitCode !== null) return;
  child.kill();
  await Promise.race([
    new Promise((resolve) => child.once("exit", resolve)),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]);
}

async function preview(baseUrl, packageKey) {
  const response = await fetch(
    `${baseUrl}/api/document-ingestion/packages/${packageKey}/reuse-preview`,
    { method: "POST" },
  );
  const payload = await response.json();
  assert(
    response.ok,
    `${packageKey} returned ${response.status}: ${JSON.stringify(payload)}`,
  );
  return payload;
}

const port = await availablePort();
const child = spawn(process.execPath, ["web/server.js"], {
  cwd: root,
  env: {
    ...process.env,
    REPO_ROOT: root,
    HOST: "127.0.0.1",
    PORT: String(port),
    PGHOST: process.env.PGHOST || "127.0.0.1",
    PGPORT: process.env.PGPORT || "54329",
    PGDATABASE: process.env.PGDATABASE || "mdopendata",
    PGUSER: process.env.PGUSER || "mdopendata",
    PGPASSWORD: process.env.PGPASSWORD || "mdopendata_dev",
    AGENDA_PACKAGE_REUSE_PROFILE:
      "data/document-ingestion/profiles/charlottetown-council-public-meeting/v1/profile.json",
  },
  stdio: ["ignore", "pipe", "pipe"],
  windowsHide: true,
});
let diagnostics = "";
child.stdout.on("data", (chunk) => { diagnostics += chunk.toString(); });
child.stderr.on("data", (chunk) => { diagnostics += chunk.toString(); });
const baseUrl = `http://127.0.0.1:${port}`;

try {
  await waitForServer(baseUrl, child);
  const positive = await preview(
    baseUrl,
    "agenda-package-73d48c77694d443e5351089c",
  );
  assert(positive.status === "needs_review", "Positive package status is incorrect.");
  assert(positive.documents?.length === 5, "Positive package document count is incorrect.");
  assert(
    positive.documents.every((item) => item.fit_class === "exact"),
    "Positive package contains a non-exact document.",
  );
  assert(
    positive.coverage?.assigned_pages === 6
      && positive.coverage?.unknown_pages === 0
      && positive.coverage?.conflicting_pages === 0
      && positive.coverage?.omitted_pages === 0,
    "Positive package coverage is incomplete.",
  );

  const negative = await preview(
    baseUrl,
    "agenda-package-d529b04147218eaf379ab063",
  );
  assert(negative.status === "blocked", "Negative package must remain blocked.");
  assert(
    negative.coverage?.total_pages === 453
      && negative.coverage?.omitted_pages === 0,
    "Negative package accounting is incomplete.",
  );
  assert(
    negative.documents.every(
      (item) => item.policy_evaluation?.outcome !== "auto_approved",
    ),
    "Negative package contains an automatic approval.",
  );
  console.log(JSON.stringify({
    positive: {
      status: positive.status,
      documents: positive.documents.length,
      coverage: positive.coverage,
    },
    negative: {
      status: negative.status,
      documents: negative.documents.length,
      coverage: negative.coverage,
    },
  }, null, 2));
} catch (error) {
  error.message = `${error.message}\n${diagnostics}`;
  throw error;
} finally {
  await stopServer(child);
}
