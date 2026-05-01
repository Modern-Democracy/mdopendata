#!/usr/bin/env node

const baseUrl = process.env.WEB_SMOKE_BASE_URL || "http://localhost:3000";
const samplePid = process.env.WEB_SMOKE_PID || "";

const checks = [
  {
    name: "parcel lookup route",
    path: "/",
    expectText: ["Parcel lookup", "logo-island-needle.svg", "/api/addresses"],
  },
  {
    name: "parcel lookup alias",
    path: "/parcel-lookup",
    expectText: ["Parcel lookup", "address-results"],
  },
  {
    name: "parcel map explorer route",
    path: samplePid ? `/map-explorer?pid=${encodeURIComponent(samplePid)}` : "/map-explorer",
    expectText: ["Map Explorer", "logo-island-needle.svg", "/api/parcels/"],
  },
  {
    name: "city view route",
    path: "/city-view",
    expectText: ["City View Map", "logo-island-needle.svg", "/api/parcels.geojson", "/api/parcels/point"],
  },
  {
    name: "zoning comparison route",
    path: samplePid ? `/zoning-comparison?pid=${encodeURIComponent(samplePid)}` : "/zoning-comparison",
    expectText: ["Zoning Comparison", "logo-island-needle.svg", "/api/zoning-comparison/"],
  },
  {
    name: "address API contract",
    path: "/api/addresses?q=university&limit=1",
    expectJson: (payload) => Array.isArray(payload.rows) && Boolean(payload.source),
  },
  {
    name: "parcel GeoJSON API contract",
    path: "/api/parcels.geojson?bbox=-63.20,46.20,-63.05,46.30&limit=1",
    expectJson: (payload) => payload.type === "FeatureCollection" && Array.isArray(payload.features) && Boolean(payload.metadata?.source),
  },
  {
    name: "current zoning GeoJSON API contract",
    path: "/api/zoning/current.geojson?bbox=-63.20,46.20,-63.05,46.30&limit=1",
    expectJson: (payload) => payload.type === "FeatureCollection" && Array.isArray(payload.features) && Boolean(payload.metadata?.source),
  },
  {
    name: "draft zoning GeoJSON API contract",
    path: "/api/zoning/draft.geojson?bbox=-63.20,46.20,-63.05,46.30&limit=1",
    expectJson: (payload) => payload.type === "FeatureCollection" && Array.isArray(payload.features) && Boolean(payload.metadata?.source),
  },
];

if (samplePid) {
  checks.push(
    {
      name: "selected parcel API contract",
      path: `/api/parcels/${encodeURIComponent(samplePid)}`,
      expectJson: (payload) => payload.pid && payload.parcel && payload.zones && payload.source,
    },
    {
      name: "zoning comparison API contract",
      path: `/api/zoning-comparison/${encodeURIComponent(samplePid)}`,
      expectJson: (payload) => payload.pid && Array.isArray(payload.rows) && payload.citations,
    },
  );
}

async function runCheck(check) {
  const url = new URL(check.path, baseUrl);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${check.name}: ${url} returned HTTP ${response.status}`);
  }

  if (check.expectText) {
    const text = await response.text();
    const missing = check.expectText.filter((fragment) => !text.includes(fragment));
    if (missing.length) {
      throw new Error(`${check.name}: missing text ${missing.join(", ")}`);
    }
    return;
  }

  const payload = await response.json();
  if (!check.expectJson(payload)) {
    throw new Error(`${check.name}: JSON contract check failed`);
  }
}

const failures = [];
for (const check of checks) {
  try {
    await runCheck(check);
    console.log(`ok - ${check.name}`);
  } catch (error) {
    failures.push(error);
    console.error(`not ok - ${error.message}`);
  }
}

if (failures.length) {
  process.exitCode = 1;
}
