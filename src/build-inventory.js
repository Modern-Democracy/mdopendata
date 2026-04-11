const fs = require("fs");
const path = require("path");

const root = process.cwd();
const includeExt = new Set([".pdf", ".gif", ".png", ".jpg", ".jpeg", ".tif", ".tiff"]);
const skipDirs = new Set([
  ".git",
  "node_modules",
  "data",
  ".python",
  ".venv",
  ".qgis-mcp-packages",
  "qgis_mcp_vendor",
  ".docker-local"
]);

function classify(relPath) {
  const normalized = relPath.replace(/\\/g, "/").toLowerCase();

  if (normalized.includes("/zoning and development bylaw")) {
    return { domain: "land_use_regulation", kind: "bylaw_text" };
  }
  if (normalized.includes("/zoning map")) {
    return { domain: "land_use_regulation", kind: "zoning_map" };
  }
  if (normalized.includes("/official plan")) {
    return { domain: "policy", kind: "official_plan_text" };
  }
  if (
    normalized.includes("municipal planning strategy") ||
    normalized.includes("/halifaxmps")
  ) {
    return { domain: "policy", kind: "official_plan_text" };
  }
  if (normalized.includes("/future land use map")) {
    return { domain: "policy", kind: "future_land_use_map" };
  }
  if (normalized.includes("/wards")) {
    return { domain: "municipal_geography", kind: "ward_map" };
  }
  if (normalized.includes("/neighborhood")) {
    return { domain: "municipal_geography", kind: "neighborhood_map" };
  }
  if (normalized.includes("truck")) {
    return { domain: "transportation", kind: "truck_route_map" };
  }
  if (normalized.includes("cycling")) {
    return { domain: "transportation", kind: "cycling_map" };
  }
  if (normalized.includes("park")) {
    return { domain: "parks", kind: "parks_map" };
  }
  if (normalized.includes("street map")) {
    return { domain: "transportation", kind: "street_map" };
  }

  return { domain: "unclassified", kind: "unknown" };
}

function extractionHints(kind, ext) {
  const hints = [];

  if (ext === ".pdf") {
    hints.push("attempt_text_extraction");
    hints.push("attempt_vector_layer_extraction");
  } else {
    hints.push("ocr_required");
  }

  if (kind.endsWith("_map") || kind === "street_map") {
    hints.push("georeference_needed");
    hints.push("legend_parsing_needed");
  }

  if (kind.endsWith("_text") || kind === "bylaw_text") {
    hints.push("section_and_table_parsing_needed");
    hints.push("citation_capture_required");
  }

  return hints;
}

function walk(dir, results = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (!skipDirs.has(entry.name)) {
        walk(path.join(dir, entry.name), results);
      }
      continue;
    }

    const fullPath = path.join(dir, entry.name);
    const relPath = path.relative(root, fullPath);
    const ext = path.extname(entry.name).toLowerCase();
    const normalizedRelPath = relPath.replace(/\\/g, "/").toLowerCase();

    if (!includeExt.has(ext)) {
      continue;
    }
    if (normalizedRelPath.startsWith("maps/qgis-")) {
      continue;
    }

    const { domain, kind } = classify(relPath);
    results.push({
      source_id: relPath.replace(/\\/g, "/"),
      path: relPath.replace(/\\/g, "/"),
      filename: entry.name,
      extension: ext,
      bytes: fs.statSync(fullPath).size,
      domain,
      kind,
      extraction_hints: extractionHints(kind, ext)
    });
  }

  return results;
}

const sources = walk(root).sort((a, b) => a.path.localeCompare(b.path));
const outputDir = path.join(root, "data", "manifest");
fs.mkdirSync(outputDir, { recursive: true });

const payload = {
  generated_at: new Date().toISOString(),
  root,
  source_count: sources.length,
  sources
};

const outputPath = path.join(outputDir, "sources.json");
fs.writeFileSync(outputPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");

console.log(`Wrote ${sources.length} sources to ${outputPath}`);
