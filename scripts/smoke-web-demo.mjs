#!/usr/bin/env node

const baseUrl = process.env.WEB_SMOKE_BASE_URL || "http://localhost:3000";
const samplePid = process.env.WEB_SMOKE_PID || "";
const requireSourceAssets = process.env.WEB_SMOKE_REQUIRE_SOURCE_ASSETS !== "false";

const checks = [
  {
    name: "portal route",
    path: "/",
    expectText: ["Municipal portal", "Charlottetown municipal portal", "/api/portal/context", "View preset"],
  },
  {
    name: "parcel lookup alias",
    path: "/parcel-lookup",
    expectText: ["Parcel lookup", "address-results"],
  },
  {
    name: "parcel map explorer route",
    path: samplePid ? `/map-explorer?pid=${encodeURIComponent(samplePid)}` : "/map-explorer",
    expectText: ["Map Explorer", "logo-island-needle.svg", "/api/parcels/", "/api/buildings/osm.geojson", "/parcel-3d"],
  },
  {
    name: "parcel 3D route",
    path: samplePid ? `/parcel-3d?pid=${encodeURIComponent(samplePid)}` : "/parcel-3d",
    expectText: ["Parcel 3D", "logo-island-needle.svg", "/3d-context", "three", "Terrain"],
  },
  {
    name: "city view route",
    path: "/city-view",
    expectText: ["City View Map", "logo-island-needle.svg", "/api/parcels.geojson", "/api/parcels/point", "/api/buildings/osm.geojson"],
  },
  {
    name: "zoning comparison route",
    path: samplePid ? `/zoning-comparison?pid=${encodeURIComponent(samplePid)}` : "/zoning-comparison",
    expectText: ["Zoning Comparison", "logo-island-needle.svg", "/api/zoning-comparison/"],
  },
  {
    name: "provisions comparison route",
    path: "/provisions-comparison",
    expectText: ["Provisions Comparison", "logo-island-needle.svg", "/api/provisions-comparison"],
  },
  {
    name: "business items stub route",
    path: "/business-items",
    expectText: ["Business items", "Page contract", "planned: /api/business-items"],
  },
  {
    name: "published budget visualization route",
    path: "/budgets",
    expectText: ["Budget contents", "Contextual facts", "Financial observations", "/api/budgets/structure", "FactContent", "observationColumnKey"],
  },
  {
    name: "operating overview route",
    path: "/budgets/operating",
    expectText: ["Operating overview", "City-wide operating statements", "periodHeading", "ObservationTable"],
  },
  {
    name: "capital overview route",
    path: "/budgets/capital",
    expectText: ["Capital overview", "City and utility capital summaries", "capital-page-111-capital"],
  },
  {
    name: "contextual fact explorer route",
    path: "/budgets/facts",
    expectText: ["Contextual facts", "source wording and citations", "/api/budgets/facts"],
  },
  {
    name: "financial observation explorer route",
    path: "/budgets/observations",
    expectText: ["Financial observations", "reported numeric or textual values", "/api/budgets/observations"],
  },
  {
    name: "lab tools route",
    path: "/lab",
    expectText: ["Lab tools", "Demo-only lab area", "/api/parcels/:pid/3d-context"],
  },
  {
    name: "portal context API contract",
    path: "/api/portal/context?role=staff&route=/documents",
    expectJson: (payload) =>
      payload.municipality?.id === "charlottetown" &&
      payload.theme?.stylesheet === "/themes/charlottetown.css" &&
      payload.rolePreset === "staff" &&
      payload.route === "/documents" &&
      Array.isArray(payload.availableActions),
  },
  {
    name: "budget municipality pagination API contract",
    path: "/api/budgets/municipalities?limit=1&cursor=0",
    expectJson: (payload) => Array.isArray(payload.data) && payload.pagination?.limit === 1 && payload.pagination?.cursor === "0",
  },
  {
    name: "budget observation warning API contract",
    path: "/api/budgets/observations/13067?municipality=charlottetown",
    expectJson: (payload) => payload.data?.observation_id === "13067" && Array.isArray(payload.data?.citations) && payload.warnings?.some((warning) => warning.issue_key === "reconciliation:debt_total:balance"),
  },
  {
    name: "budget editions API contract",
    path: "/api/budgets/editions?municipality=charlottetown&limit=10",
    expectJson: (payload) =>
      Array.isArray(payload.data) &&
      payload.data.length === 3 &&
      payload.data.every((edition) => edition.document_id && edition.fiscal_period_label && edition.document_observation_count > 0),
  },
  {
    name: "budget structure contract",
    path: "/api/budgets/structure?municipality=charlottetown&document=9",
    expectJson: (payload) =>
      Array.isArray(payload.data) &&
      payload.data.some((section) => section.section_key === "operating-budget") &&
      payload.data.some((section) => section.section_key === "capital-budget") &&
      payload.data.filter((section) => section.section_key.startsWith("appendix.")).length === 3,
  },
  {
    name: "appendix descendant observation contract",
    path: "/api/budgets/observations?municipality=charlottetown&document=9&section=appendices&limit=200",
    expectJson: (payload) =>
      Array.isArray(payload.data) &&
      payload.data.length === 158 &&
      payload.data.every((observation) => observation.section_key.startsWith("appendix.")),
  },
  {
    name: "contextual facts document filter contract",
    path: "/api/budgets/facts?municipality=charlottetown&document=8&limit=20",
    expectJson: (payload) =>
      Array.isArray(payload.data) &&
      payload.data.length === 20 &&
      payload.data.every((fact) => Number(fact.edition_document_id) === 8 && fact.title),
  },
  {
    name: "structured contextual fact contract",
    path: "/api/budgets/facts?municipality=charlottetown&document=9&q=Budgeting%20Process&limit=10",
    expectJson: (payload) => {
      const fact = payload.data?.find((row) => row.source_pages?.includes(9));
      const blocks = fact?.content_json?.blocks || [];
      return blocks.some((block) => block.type === "heading" && block.text === "The Budgeting Process") &&
        blocks.some((block) => block.type === "unordered_list" && block.items?.length === 4) &&
        blocks.some((block) => block.type === "ordered_list" && block.items?.length === 3) &&
        blocks.filter((block) => block.type === "paragraph").every((block) => !block.text.includes("\n"));
    },
  },
  {
    name: "contextual department filter contract",
    path: "/api/budgets/facts?municipality=charlottetown&document=8&department=public-works&limit=100",
    expectJson: (payload) =>
      Array.isArray(payload.data) &&
      payload.data.length > 0 &&
      payload.data.every((fact) => fact.organization_unit_key === "public-works"),
  },
  {
    name: "financial observation department filter contract",
    path: "/api/budgets/observations?municipality=charlottetown&document=8&department=public-works&limit=100",
    expectJson: (payload) =>
      Array.isArray(payload.data) &&
      payload.data.length > 0 &&
      payload.data.every((observation) => observation.effective_organization_unit_key === "public-works"),
  },
  {
    name: "financial observation project filter contract",
    path: "/api/budgets/observations?municipality=charlottetown&document=8&project=street-resurfacing&limit=100",
    expectJson: (payload) =>
      Array.isArray(payload.data) &&
      payload.data.length > 0 &&
      payload.data.every((observation) => observation.project_key === "street-resurfacing"),
  },
  {
    name: "budget unknown filter rejection",
    path: "/api/budgets/periods?municipality=charlottetown&unsupported=test",
    expectStatus: 400,
    expectJson: (payload) => /Unsupported budget filter/.test(payload.error || ""),
  },
  {
    name: "published projects API contract",
    path: "/api/projects?municipality=charlottetown&limit=2&cursor=0",
    expectJson: (payload) =>
      Array.isArray(payload.data) &&
      payload.data.length === 2 &&
      payload.data.every((project) => project.project_key && Array.isArray(project.periods)) &&
      payload.pagination?.limit === 2,
  },
  {
    name: "budget exact-identity comparison API contract",
    path: "/api/budgets/compare?municipality=charlottetown&prior_period=2025-2026-budget&current_period=2026-2027-budget&basis=nominal&limit=2",
    expectJson: (payload) =>
      Array.isArray(payload.data) &&
      payload.data.length === 2 &&
      payload.data.every((row) => row.prior_observation_id && row.current_observation_id && row.numeric_change !== undefined) &&
      payload.warnings?.includes("exact_identity_matches_only") &&
      payload.coverage?.current_observation_count > 0 &&
      payload.coverage?.matched_observation_count === 440,
  },
  {
    name: "budget comparison invalid entity rejection",
    path: "/api/budgets/compare?municipality=charlottetown&prior_period=2025-2026-budget&current_period=2026-2027-budget&entity=bad",
    expectStatus: 400,
    expectJson: (payload) => /positive integer/.test(payload.error || ""),
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
  {
    name: "Buildings GeoJSON API contract",
    path: "/api/buildings/osm.geojson?bbox=-63.20,46.20,-63.05,46.30&limit=1",
    expectJson: (payload) => payload.type === "FeatureCollection" && Array.isArray(payload.features) && payload.metadata?.source === "zoning.v_charlottetown_buildings",
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
      name: "parcel restriction buffers API contract",
      path: `/api/parcels/${encodeURIComponent(samplePid)}/restriction-buffers`,
      expectJson: (payload) => payload.pid && payload.current?.type === "FeatureCollection" && payload.draft?.type === "FeatureCollection" && payload.metadata?.source,
    },
    {
      name: "parcel 3D context API contract",
      path: `/api/parcels/${encodeURIComponent(samplePid)}/3d-context?radiusM=250`,
      expectJson: (payload) =>
        payload.pid &&
        payload.parcels?.type === "FeatureCollection" &&
        payload.buildings?.type === "FeatureCollection" &&
        payload.roads?.type === "FeatureCollection" &&
        payload.terrain?.status &&
        payload.metadata?.radiusM === 250 &&
        payload.metadata?.terrainStatus === payload.terrain.status,
    },
    {
      name: "zoning comparison API contract",
      path: `/api/zoning-comparison/${encodeURIComponent(samplePid)}`,
      expectJson: (payload) => payload.pid && Array.isArray(payload.rows) && payload.citations,
    },
  );
}

if (requireSourceAssets) {
  checks.push({
    name: "published budget source page render",
    path: "/api/budgets/sources/9/pages/1?municipality=charlottetown",
    expectContentType: "image/png",
  });
}

checks.push({
  name: "provisions comparison API contract",
  path: "/api/provisions-comparison",
  expectJson: (payload) => Array.isArray(payload.parts) && payload.summary?.parts === 9 && payload.parts[0]?.partNumber === "PART 1",
});

async function runCheck(check) {
  const url = new URL(check.path, baseUrl);
  const response = await fetch(url);
  if (check.expectStatus && response.status !== check.expectStatus) {
    throw new Error(`${check.name}: ${url} returned HTTP ${response.status}, expected ${check.expectStatus}`);
  }
  if (!check.expectStatus && !response.ok) {
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

  if (check.expectContentType) {
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.startsWith(check.expectContentType) || (await response.arrayBuffer()).byteLength < 1000) {
      throw new Error(`${check.name}: expected non-empty ${check.expectContentType}`);
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
