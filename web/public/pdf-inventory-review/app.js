const documentKey = "ctown-budget-2026-2027";
const apiRoot = `/api/internal/pdf-inventory-review/documents/${documentKey}`;
const representativePages = [10, 18, 19, 20, 21, 22, 23, 24, 87, 88, 89, 90, 91, 92, 105, 110, 111, 112, 149, 151, 152, 153];
const blockTypes = [
  ["title", "Title"], ["formatted_text", "Formatted Text"], ["table", "Table"],
  ["chart", "Graph/Chart"], ["other_visual", "Diagram/Other Visual"], ["map", "Map"],
  ["table_of_contents", "Table of Contents"], ["header", "Header"], ["footer", "Footer"],
  ["page_number", "Page Number"], ["divider", "Divider"], ["signature", "Signature"],
];
const regionTypes = {
  formatted_text: [["paragraph", "Paragraph"], ["bullet_list", "Bullet List"], ["sorted_list", "Sorted List"]],
  table: [["table_header", "Table Header"], ["column_label", "Column Label"], ["row_label", "Row Label"], ["cell", "Cell"], ["subtotal", "Sub-Total"], ["total", "Total"]],
};
const relationshipLabels = { graph_source_table: "Graph/chart source", table_continuation: "Table continuation", overview_detail: "Overview to detail" };

const state = {
  document: null, artifact: null, pages: [], activePage: 1, pageEvidence: null,
  blockPage: null, selectedBlockKey: null, zoom: 1, embeddedWords: null, ocrWords: null,
  saving: false, drawMode: false, drawTarget: "block", pointerEdit: null, pendingBlockKey: null,
  internalBlockKey: null, selectedRegionKey: null, linkSource: null,
};

const ids = [
  "validation-status", "editing-status", "page-coverage", "document-title", "source-path", "page-count",
  "block-count", "financial-count", "review-page-count", "artifact-hash", "page-input",
  "representative-pages", "thumbnail-list", "previous-page", "next-page", "active-page-label",
  "zoom-out", "zoom-in", "zoom-label", "fit-page", "blocks-toggle", "embedded-toggle", "draw-block",
  "ocr-toggle", "page-canvas", "canvas-status", "page-sheet", "page-image", "blocks-overlay",
  "embedded-overlay", "ocr-overlay", "inspector-title", "page-disposition", "page-key",
  "page-dimensions", "page-rotation", "embedded-count", "ocr-status", "review-status",
  "ocr-notice", "ocr-notice-copy", "block-summary", "block-list", "block-detail", "block-key",
  "block-type", "block-family", "block-order", "block-confidence", "block-review", "block-excerpt",
  "block-editor", "block-type-select", "block-financial", "save-block-type", "delete-block",
  "new-block-type", "new-block-financial", "edit-reason", "edit-internal", "region-editor",
  "exit-internal", "region-summary", "region-list", "region-type-select", "save-region-type",
  "draw-region", "delete-region", "relationship-type", "link-source-status", "set-link-source",
  "save-link", "relationship-list",
  "render-hash", "thumbnail-hash", "embedded-hash", "ocr-hash", "source-citation", "error-banner",
];
const elements = Object.fromEntries(ids.map((id) => [id, document.getElementById(id)]));

function formatHash(value) { return value ? `${value.slice(0, 12)}:${value.slice(-8)}` : "Not applicable"; }
function human(value) { return value ? value.replaceAll("_", " ") : "Not applicable"; }
function showError(message) { elements["error-banner"].textContent = message; elements["error-banner"].hidden = false; }
function clearError() { elements["error-banner"].hidden = true; }
async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `Request failed with HTTP ${response.status}.`);
  return payload;
}
async function sendCommand(command) {
  if (!state.document?.write_enabled || state.saving) return;
  const reason = elements["edit-reason"].value.trim();
  if (!reason) { showError("A review reason is required."); return; }
  state.saving = true; document.body.classList.add("saving"); clearError();
  try {
    const response = await fetch(`${apiRoot}/commands`, {
      method: "POST", cache: "no-store", headers: { "content-type": "application/json" },
      body: JSON.stringify({
        ...command, document_key: documentKey,
        expected_artifact_sha256: state.document.block_artifact_sha256, reason,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `Command failed with HTTP ${response.status}.`);
    state.pendingBlockKey = command.action === "delete" ? null : payload.affected_keys?.find((key) => key.includes(":p")) || state.selectedBlockKey;
    state.selectedRegionKey = command.action === "delete_region" ? null : payload.affected_keys?.find((key) => key.includes("region-")) || state.selectedRegionKey;
    await initialize();
  } catch (error) {
    showError(error.message); renderBlockInventory();
  } finally {
    state.saving = false; document.body.classList.remove("saving");
  }
}
function populateTypeOptions(select) {
  select.replaceChildren(...blockTypes.map(([value, label]) => {
    const option = document.createElement("option"); option.value = value; option.textContent = label; return option;
  }));
}
function currentPage() { return state.pages.find((page) => page.page_number === state.activePage); }
function setUrlPage(pageNumber) { const url = new URL(location.href); url.searchParams.set("page", String(pageNumber)); history.replaceState(null, "", url); }

function renderRepresentativePages() {
  elements["representative-pages"].replaceChildren(...representativePages.map((pageNumber) => {
    const button = document.createElement("button");
    button.type = "button"; button.className = "representative-link"; button.textContent = String(pageNumber);
    button.title = `Open representative source control page ${pageNumber}`;
    button.addEventListener("click", () => selectPage(pageNumber));
    return button;
  }));
}

function renderThumbnails() {
  const fragment = document.createDocumentFragment();
  for (const page of state.pages) {
    const button = document.createElement("button");
    button.type = "button"; button.className = "thumbnail-card"; button.dataset.pageNumber = String(page.page_number);
    button.setAttribute("aria-label", `Open PDF page ${page.page_number}`);
    const image = document.createElement("img"); image.loading = "lazy"; image.alt = ""; image.src = page.assets.thumbnail; image.width = 68; image.height = 88;
    const meta = document.createElement("span"); meta.className = "thumbnail-meta";
    const label = document.createElement("span"); label.className = "thumbnail-page"; label.textContent = `Page ${page.page_number}`;
    const count = document.createElement("span"); count.className = "thumbnail-count"; count.textContent = `${page.block_count} blocks · ${page.financial_block_count} financial`;
    meta.append(label, count);
    if (page.block_inventory_status === "needs_review") { const badge = document.createElement("span"); badge.className = "thumbnail-ocr"; badge.textContent = "Review"; meta.append(badge); }
    button.append(image, meta); button.addEventListener("click", () => selectPage(page.page_number)); fragment.append(button);
  }
  elements["thumbnail-list"].replaceChildren(fragment);
}

function updateSelectedThumbnail() {
  for (const card of elements["thumbnail-list"].querySelectorAll(".thumbnail-card")) {
    const selected = Number(card.dataset.pageNumber) === state.activePage;
    card.classList.toggle("selected", selected); card.setAttribute("aria-current", selected ? "page" : "false");
    if (!selected) continue;
    const container = elements["thumbnail-list"];
    if (getComputedStyle(container).display === "flex") card.scrollIntoView({ block: "nearest", inline: "nearest" });
    else if (card.offsetTop < container.scrollTop || card.offsetTop + card.offsetHeight > container.scrollTop + container.clientHeight) card.scrollIntoView({ block: "nearest" });
  }
}

function positionBox(node, bbox) {
  node.style.left = `${bbox.x0 * 100}%`; node.style.top = `${bbox.y0 * 100}%`;
  node.style.width = `${(bbox.x1 - bbox.x0) * 100}%`; node.style.height = `${(bbox.y1 - bbox.y0) * 100}%`;
}

function positionRegionBox(node, bbox, parent) {
  node.style.left = `${((bbox.x0 - parent.x0) / (parent.x1 - parent.x0)) * 100}%`;
  node.style.top = `${((bbox.y0 - parent.y0) / (parent.y1 - parent.y0)) * 100}%`;
  node.style.width = `${((bbox.x1 - bbox.x0) / (parent.x1 - parent.x0)) * 100}%`;
  node.style.height = `${((bbox.y1 - bbox.y0) / (parent.y1 - parent.y0)) * 100}%`;
}

function currentBlock() { return state.blockPage?.blocks.find((block) => block.block_key === state.selectedBlockKey) || null; }
function currentRegion() { return currentBlock()?.regions.find((region) => region.region_key === state.selectedRegionKey) || null; }

function selectBlock(blockKey) {
  state.selectedBlockKey = blockKey;
  const block = state.blockPage?.blocks.find((candidate) => candidate.block_key === blockKey);
  if (!block?.regions.some((region) => region.region_key === state.selectedRegionKey)) state.selectedRegionKey = null;
  for (const node of document.querySelectorAll("[data-block-key]")) node.classList.toggle("selected", node.dataset.blockKey === blockKey);
  if (!block) { elements["block-detail"].hidden = true; elements["block-editor"].hidden = true; elements["region-editor"].hidden = true; renderRelationships(); return; }
  elements["block-detail"].hidden = false;
  elements["block-key"].textContent = block.block_key; elements["block-type"].textContent = human(block.block_type);
  elements["block-family"].textContent = human(block.table_family_candidate); elements["block-order"].textContent = String(block.reading_order);
  elements["block-confidence"].textContent = `${block.confidence.level} · ${Math.round(block.confidence.score * 100)}%`;
  elements["block-review"].textContent = human(block.review.status); elements["block-excerpt"].textContent = block.evidence[0]?.text_excerpt || "No text evidence";
  const internal = state.internalBlockKey === block.block_key;
  elements["block-editor"].hidden = !state.document?.write_enabled || internal;
  elements["region-editor"].hidden = !internal;
  elements["edit-internal"].hidden = !regionTypes[block.block_type];
  elements["block-type-select"].value = block.block_type;
  elements["block-financial"].checked = block.financial_candidate;
  if (internal) renderRegions(block);
  renderRelationships();
}

function selectRegion(regionKey) {
  state.selectedRegionKey = regionKey;
  for (const node of document.querySelectorAll("[data-region-key]")) node.classList.toggle("selected", node.dataset.regionKey === regionKey);
  const region = currentRegion();
  if (region) elements["region-type-select"].value = region.region_type;
  elements["save-region-type"].disabled = !region;
  elements["delete-region"].disabled = !region;
  renderRelationships();
}

function populateRegionOptions(block) {
  elements["region-type-select"].replaceChildren(...(regionTypes[block.block_type] || []).map(([value, label]) => {
    const option = document.createElement("option"); option.value = value; option.textContent = label; return option;
  }));
}

function renderRegions(block) {
  populateRegionOptions(block);
  elements["region-summary"].textContent = `${block.regions.length} internal regions`;
  const list = document.createDocumentFragment();
  for (const region of block.regions) {
    const item = document.createElement("button"); item.type = "button"; item.className = "block-list-item";
    item.dataset.regionKey = region.region_key; item.textContent = human(region.region_type);
    item.addEventListener("click", () => selectRegion(region.region_key)); list.append(item);
  }
  elements["region-list"].replaceChildren(list);
  const selected = block.regions.some((region) => region.region_key === state.selectedRegionKey) ? state.selectedRegionKey : block.regions[0]?.region_key || null;
  selectRegion(selected);
}

function selectedEndpoint() {
  return state.selectedBlockKey ? { block_key: state.selectedBlockKey, region_key: state.selectedRegionKey || null } : null;
}

function renderRelationships() {
  const selected = selectedEndpoint();
  elements["link-source-status"].textContent = state.linkSource ? `Source: ${state.linkSource.region_key || state.linkSource.block_key}` : "No link source selected.";
  elements["save-link"].disabled = !state.linkSource || !selected || (state.linkSource.block_key === selected.block_key && state.linkSource.region_key === selected.region_key);
  const fragment = document.createDocumentFragment();
  for (const relationship of state.blockPage?.relationships || []) {
    if (selected && relationship.source.block_key !== selected.block_key && relationship.target.block_key !== selected.block_key) continue;
    const row = document.createElement("div"); row.className = "relationship-item";
    const text = document.createElement("span"); text.textContent = `${relationshipLabels[relationship.relationship_type]}: ${relationship.source.region_key || relationship.source.block_key} -> ${relationship.target.region_key || relationship.target.block_key}`;
    const remove = document.createElement("button"); remove.type = "button"; remove.textContent = "Unlink";
    remove.addEventListener("click", () => sendCommand({ action: "unlink", relationship_key: relationship.relationship_key }));
    row.append(text, remove); fragment.append(row);
  }
  elements["relationship-list"].replaceChildren(fragment);
}

function renderBlockInventory() {
  const page = state.blockPage;
  const blocks = page?.blocks || [];
  elements["block-summary"].textContent = page ? `${blocks.length} candidates · ${human(page.disposition.status)} · ${state.document?.write_enabled ? "editing enabled" : "read-only"}` : "No inventory loaded";
  const overlayFragment = document.createDocumentFragment(); const listFragment = document.createDocumentFragment();
  for (const block of blocks) {
    const internal = state.internalBlockKey === block.block_key;
    const overlay = document.createElement(internal ? "div" : "button"); if (!internal) overlay.type = "button"; overlay.className = `block-box block-${block.block_type}${internal ? " internal-parent" : ""}`;
    overlay.dataset.blockKey = block.block_key; overlay.setAttribute("aria-label", `Inspect ${human(block.block_type)} block ${block.reading_order}`); positionBox(overlay, block.bbox);
    const label = document.createElement("span"); label.className = "block-label"; label.textContent = `${block.reading_order} ${human(block.block_type)}`; overlay.append(label);
    if (state.document?.write_enabled && !internal) {
      for (const edge of ["n", "ne", "e", "se", "s", "sw", "w", "nw"]) {
        const handle = document.createElement("i"); handle.className = `resize-handle resize-${edge}`; handle.dataset.edge = edge;
        handle.addEventListener("pointerdown", (event) => startResize(event, block)); overlay.append(handle);
      }
    }
    if (internal) {
      const surface = document.createElement("div"); surface.className = "internal-edit-surface"; surface.addEventListener("pointerdown", (event) => beginRegionDraw(event, block));
      for (const region of block.regions) {
        const regionBox = document.createElement("button"); regionBox.type = "button"; regionBox.className = "region-box"; regionBox.dataset.regionKey = region.region_key; positionRegionBox(regionBox, region.bbox, block.bbox);
        const regionLabel = document.createElement("span"); regionLabel.className = "region-label"; regionLabel.textContent = human(region.region_type); regionBox.append(regionLabel);
        for (const edge of ["n", "ne", "e", "se", "s", "sw", "w", "nw"]) {
          const handle = document.createElement("i"); handle.className = `resize-handle resize-${edge}`; handle.dataset.edge = edge; handle.addEventListener("pointerdown", (event) => startRegionResize(event, block, region)); regionBox.append(handle);
        }
        regionBox.addEventListener("click", (event) => { event.stopPropagation(); selectRegion(region.region_key); }); surface.append(regionBox);
      }
      overlay.append(surface);
    } else overlay.addEventListener("click", () => selectBlock(block.block_key));
    overlayFragment.append(overlay);
    const item = document.createElement("button"); item.type = "button"; item.className = "block-list-item"; item.dataset.blockKey = block.block_key;
    item.textContent = `${block.reading_order}. ${human(block.block_type)}${block.financial_candidate ? " · financial" : ""}`; item.addEventListener("click", () => selectBlock(block.block_key)); listFragment.append(item);
  }
  elements["blocks-overlay"].replaceChildren(overlayFragment); elements["block-list"].replaceChildren(listFragment);
  elements["blocks-overlay"].hidden = !elements["blocks-toggle"].checked;
  const target = state.pendingBlockKey && blocks.some((block) => block.block_key === state.pendingBlockKey)
    ? state.pendingBlockKey : state.selectedBlockKey && blocks.some((block) => block.block_key === state.selectedBlockKey)
      ? state.selectedBlockKey : blocks[0]?.block_key || null;
  state.pendingBlockKey = null; selectBlock(target);
}

function pointerPosition(event) {
  const rect = elements["blocks-overlay"].getBoundingClientRect();
  return {
    x: Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)),
    y: Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height)),
  };
}

function startResize(event, block) {
  if (!state.document?.write_enabled || state.saving) return;
  event.preventDefault(); event.stopPropagation(); selectBlock(block.block_key);
  state.pointerEdit = { mode: "resize", edge: event.currentTarget.dataset.edge, blockKey: block.block_key, bbox: { ...block.bbox } };
}

function startRegionResize(event, block, region) {
  if (!state.document?.write_enabled || state.saving) return;
  event.preventDefault(); event.stopPropagation(); selectRegion(region.region_key);
  state.pointerEdit = { mode: "region_resize", edge: event.currentTarget.dataset.edge, blockKey: block.block_key, regionKey: region.region_key, parent: { ...block.bbox }, bbox: { ...region.bbox } };
}

function beginRegionDraw(event, block) {
  if (!state.drawMode || state.drawTarget !== "region" || state.saving || event.target !== event.currentTarget) return;
  event.preventDefault(); event.stopPropagation();
  const start = pointerPosition(event); const preview = document.createElement("div"); preview.className = "draw-preview";
  elements["blocks-overlay"].append(preview); state.pointerEdit = { mode: "region_draw", blockKey: block.block_key, parent: { ...block.bbox }, start, preview, bbox: { x0: start.x, y0: start.y, x1: start.x, y1: start.y } };
}

function beginDraw(event) {
  if (!state.drawMode || state.drawTarget !== "block" || state.saving || event.target !== elements["blocks-overlay"]) return;
  event.preventDefault();
  const start = pointerPosition(event); const preview = document.createElement("div"); preview.className = "draw-preview";
  elements["blocks-overlay"].append(preview); state.pointerEdit = { mode: "draw", start, preview, bbox: { x0: start.x, y0: start.y, x1: start.x, y1: start.y } };
}

function movePointerEdit(event) {
  if (!state.pointerEdit) return;
  event.preventDefault(); const point = pointerPosition(event); const edit = state.pointerEdit;
  if (edit.mode === "draw" || edit.mode === "region_draw") {
    if (edit.parent) {
      point.x = Math.min(edit.parent.x1, Math.max(edit.parent.x0, point.x));
      point.y = Math.min(edit.parent.y1, Math.max(edit.parent.y0, point.y));
    }
    edit.bbox = { x0: Math.min(edit.start.x, point.x), y0: Math.min(edit.start.y, point.y), x1: Math.max(edit.start.x, point.x), y1: Math.max(edit.start.y, point.y) };
    positionBox(edit.preview, edit.bbox); return;
  }
  const box = { ...edit.bbox }; const minimum = .005;
  if (edit.parent) {
    point.x = Math.min(edit.parent.x1, Math.max(edit.parent.x0, point.x));
    point.y = Math.min(edit.parent.y1, Math.max(edit.parent.y0, point.y));
  }
  if (edit.edge.includes("w")) box.x0 = Math.min(point.x, box.x1 - minimum);
  if (edit.edge.includes("e")) box.x1 = Math.max(point.x, box.x0 + minimum);
  if (edit.edge.includes("n")) box.y0 = Math.min(point.y, box.y1 - minimum);
  if (edit.edge.includes("s")) box.y1 = Math.max(point.y, box.y0 + minimum);
  edit.next = box;
  if (edit.mode === "region_resize") {
    const region = elements["blocks-overlay"].querySelector(`[data-region-key="${CSS.escape(edit.regionKey)}"]`); if (region) positionRegionBox(region, box, edit.parent);
  } else {
    const overlay = elements["blocks-overlay"].querySelector(`[data-block-key="${CSS.escape(edit.blockKey)}"]`); if (overlay) positionBox(overlay, box);
  }
}

async function finishPointerEdit() {
  const edit = state.pointerEdit; if (!edit) return; state.pointerEdit = null;
  if (edit.mode === "resize") {
    if (edit.next && JSON.stringify(edit.next) !== JSON.stringify(edit.bbox)) await sendCommand({ action: "resize", block_key: edit.blockKey, bbox: edit.next });
    return;
  }
  if (edit.mode === "region_resize") {
    if (edit.next && JSON.stringify(edit.next) !== JSON.stringify(edit.bbox)) await sendCommand({ action: "resize_region", block_key: edit.blockKey, region_key: edit.regionKey, bbox: edit.next });
    return;
  }
  edit.preview.remove(); toggleDrawMode(false);
  if (edit.bbox.x1 - edit.bbox.x0 < .005 || edit.bbox.y1 - edit.bbox.y0 < .005) return;
  if (edit.mode === "region_draw") {
    await sendCommand({ action: "create_region", block_key: edit.blockKey, bbox: edit.bbox, region_type: elements["region-type-select"].value });
    return;
  }
  await sendCommand({
    action: "create", page_number: state.activePage, bbox: edit.bbox,
    block_type: elements["new-block-type"].value, financial_candidate: elements["new-block-financial"].checked,
  });
}

function toggleDrawMode(force, target = state.drawTarget) {
  state.drawMode = typeof force === "boolean" ? force : !state.drawMode;
  state.drawTarget = target;
  elements["blocks-overlay"].classList.toggle("draw-mode", state.drawMode);
  elements["draw-block"].classList.toggle("selected", state.drawMode && state.drawTarget === "block");
  elements["draw-region"].classList.toggle("selected", state.drawMode && state.drawTarget === "region");
  elements["draw-block"].textContent = state.drawMode && state.drawTarget === "block" ? "Cancel drawing" : "Draw new box";
  elements["draw-region"].textContent = state.drawMode && state.drawTarget === "region" ? "Cancel drawing" : "Draw region";
}

function renderWordOverlay(container, words) {
  const fragment = document.createDocumentFragment();
  for (const word of words || []) { const box = document.createElement("span"); box.className = "word-box"; positionBox(box, word.bbox); box.title = word.text; fragment.append(box); }
  container.replaceChildren(fragment);
}

async function loadWordEvidence(type) {
  const page = currentPage(); if (!page) return;
  const property = type === "embedded" ? "embeddedWords" : "ocrWords";
  const toggle = elements[type === "embedded" ? "embedded-toggle" : "ocr-toggle"];
  const overlay = elements[type === "embedded" ? "embedded-overlay" : "ocr-overlay"];
  if (!toggle.checked) { overlay.replaceChildren(); return; }
  if (type === "ocr" && !page.assets.ocr_words) return;
  if (!state[property]) state[property] = await fetchJson(type === "embedded" ? page.assets.embedded_words : page.assets.ocr_words);
  renderWordOverlay(overlay, state[property].words);
}

function updateZoom(delta = 0, reset = false) {
  state.zoom = reset ? 1 : Math.min(2.5, Math.max(.5, state.zoom + delta));
  elements["page-sheet"].style.width = `${state.zoom * 100}%`; elements["page-sheet"].style.maxWidth = `${state.zoom * 900}px`;
  elements["zoom-label"].textContent = `${Math.round(state.zoom * 100)}%`; elements["zoom-out"].disabled = state.zoom <= .5; elements["zoom-in"].disabled = state.zoom >= 2.5;
}

function renderInspector(page, evidence) {
  elements["inspector-title"].textContent = `Page ${page.page_number}`; elements["page-disposition"].textContent = human(page.block_inventory_status);
  elements["page-disposition"].className = `status-badge ${page.block_inventory_status}`; elements["page-key"].textContent = page.page_key;
  elements["page-dimensions"].textContent = `${page.width_pt} × ${page.height_pt} pt`; elements["page-rotation"].textContent = `${page.rotation}°`;
  elements["embedded-count"].textContent = String(page.embedded_word_count); elements["review-status"].textContent = human(page.review.status);
  elements["render-hash"].textContent = evidence.render.sha256; elements["thumbnail-hash"].textContent = evidence.thumbnail.sha256;
  elements["embedded-hash"].textContent = evidence.embedded_text.sha256; elements["ocr-hash"].textContent = evidence.ocr.sha256 || "Not applicable";
  elements["ocr-toggle"].disabled = page.ocr_status !== "completed";
  elements["ocr-status"].textContent = page.ocr_status === "completed" ? `${page.ocr_word_count} words · ${(page.ocr_mean_confidence * 100).toFixed(1)}% mean confidence` : human(page.ocr_status);
  elements["ocr-notice"].hidden = page.ocr_status !== "completed";
  elements["ocr-notice-copy"].textContent = page.ocr_status === "completed" ? `Only ${page.embedded_word_count} embedded words were available. Tesseract supplied ${page.ocr_word_count} OCR words at ${(page.ocr_mean_confidence * 100).toFixed(1)}% mean confidence.` : "";
  elements["source-citation"].textContent = `${state.artifact.source.repo_relpath}, PDF page ${page.page_number}`; elements["source-citation"].href = page.assets.render;
}

async function selectPage(pageNumber) {
  if (!state.pages.length) return;
  const bounded = Math.min(state.pages.length, Math.max(1, Number(pageNumber) || 1));
  if (bounded !== state.activePage) { state.internalBlockKey = null; state.selectedRegionKey = null; }
  state.activePage = bounded; state.embeddedWords = null; state.ocrWords = null; state.blockPage = null; state.selectedBlockKey = null; toggleDrawMode(false); clearError(); setUrlPage(bounded); updateSelectedThumbnail();
  elements["page-input"].value = String(bounded); elements["active-page-label"].textContent = `Page ${bounded} of ${state.pages.length}`;
  elements["previous-page"].disabled = bounded === 1; elements["next-page"].disabled = bounded === state.pages.length;
  elements["canvas-status"].hidden = false; elements["canvas-status"].textContent = `Loading PDF page ${bounded}`; elements["page-sheet"].hidden = true;
  elements["embedded-overlay"].replaceChildren(); elements["ocr-overlay"].replaceChildren(); elements["blocks-overlay"].replaceChildren(); elements["ocr-toggle"].checked = false;
  try {
    const payload = await fetchJson(`${apiRoot}/pages/${bounded}`); if (state.activePage !== bounded) return;
    state.pageEvidence = payload.evidence; state.blockPage = payload.block_inventory; renderInspector(payload.page, payload.evidence); renderBlockInventory();
    elements["page-image"].alt = `Rendered source PDF page ${bounded}`; elements["page-image"].src = payload.page.assets.render; await elements["page-image"].decode();
    if (state.activePage !== bounded) return; elements["canvas-status"].hidden = true; elements["page-sheet"].hidden = false;
    if (elements["embedded-toggle"].checked) await loadWordEvidence("embedded");
  } catch (error) { elements["canvas-status"].hidden = false; elements["canvas-status"].textContent = "Source page is unavailable."; showError(error.message); }
}

async function initialize() {
  try {
    const [documentsPayload, artifactPayload, pagesPayload] = await Promise.all([fetchJson("/api/internal/pdf-inventory-review/documents"), fetchJson(`${apiRoot}/artifacts`), fetchJson(`${apiRoot}/pages`)]);
    state.document = documentsPayload.documents[0]; state.artifact = artifactPayload.artifact; state.pages = pagesPayload.pages;
    elements["validation-status"].textContent = "Stages 0–1 validated"; elements["validation-status"].className = "status-badge valid";
    elements["editing-status"].textContent = state.document.write_enabled ? "Editing enabled" : "Editing disabled";
    elements["editing-status"].className = `status-badge ${state.document.write_enabled ? "valid" : "pending"}`;
    elements["draw-block"].hidden = !state.document.write_enabled;
    elements["page-coverage"].textContent = `Stage 1 · ${state.document.page_count - state.document.block_review_page_count}/${state.document.page_count} pages inventoried`;
    elements["document-title"].textContent = state.document.title; elements["source-path"].textContent = state.artifact.source.repo_relpath;
    elements["page-count"].textContent = String(state.document.page_count); elements["block-count"].textContent = String(state.document.block_count);
    elements["financial-count"].textContent = String(state.document.financial_block_count); elements["review-page-count"].textContent = String(state.document.block_review_page_count);
    elements["artifact-hash"].textContent = formatHash(state.document.block_artifact_sha256); elements["artifact-hash"].title = state.document.block_artifact_sha256;
    renderRepresentativePages(); renderThumbnails(); const requested = Number(new URL(location.href).searchParams.get("page")); await selectPage(Number.isInteger(requested) && requested > 0 ? requested : 1);
  } catch (error) { elements["validation-status"].textContent = "Evidence unavailable"; elements["validation-status"].className = "status-badge error"; elements["canvas-status"].textContent = "Staged evidence could not be loaded."; showError(error.message); }
}

elements["previous-page"].addEventListener("click", () => selectPage(state.activePage - 1)); elements["next-page"].addEventListener("click", () => selectPage(state.activePage + 1));
elements["page-input"].addEventListener("change", (event) => selectPage(event.target.value)); elements["zoom-out"].addEventListener("click", () => updateZoom(-.25));
elements["zoom-in"].addEventListener("click", () => updateZoom(.25)); elements["fit-page"].addEventListener("click", () => updateZoom(0, true));
elements["blocks-toggle"].addEventListener("change", () => { elements["blocks-overlay"].hidden = !elements["blocks-toggle"].checked; });
elements["embedded-toggle"].addEventListener("change", () => loadWordEvidence("embedded").catch((error) => showError(error.message)));
elements["ocr-toggle"].addEventListener("change", () => loadWordEvidence("ocr").catch((error) => showError(error.message)));
elements["draw-block"].addEventListener("click", () => toggleDrawMode(undefined, "block"));
elements["blocks-overlay"].addEventListener("pointerdown", beginDraw);
document.addEventListener("pointermove", movePointerEdit, { passive: false });
document.addEventListener("pointerup", () => finishPointerEdit().catch((error) => showError(error.message)));
elements["save-block-type"].addEventListener("click", () => {
  if (!state.selectedBlockKey) return;
  sendCommand({ action: "set_type", block_key: state.selectedBlockKey, block_type: elements["block-type-select"].value, financial_candidate: elements["block-financial"].checked });
});
elements["delete-block"].addEventListener("click", () => {
  if (!state.selectedBlockKey) return;
  if (window.confirm("Delete the selected Stage 1 box? The review event will remain in the audit history.")) sendCommand({ action: "delete", block_key: state.selectedBlockKey });
});
elements["edit-internal"].addEventListener("click", () => {
  const block = currentBlock(); if (!block || !regionTypes[block.block_type]) return;
  state.internalBlockKey = block.block_key; state.selectedRegionKey = block.regions[0]?.region_key || null; toggleDrawMode(false); renderBlockInventory();
});
elements["exit-internal"].addEventListener("click", () => {
  state.internalBlockKey = null; state.selectedRegionKey = null; toggleDrawMode(false); renderBlockInventory();
});
elements["draw-region"].addEventListener("click", () => toggleDrawMode(undefined, "region"));
elements["save-region-type"].addEventListener("click", () => {
  const block = currentBlock(); const region = currentRegion(); if (!block || !region) return;
  sendCommand({ action: "set_region_type", block_key: block.block_key, region_key: region.region_key, region_type: elements["region-type-select"].value });
});
elements["delete-region"].addEventListener("click", () => {
  const block = currentBlock(); const region = currentRegion(); if (!block || !region) return;
  if (window.confirm("Delete the selected internal region?")) sendCommand({ action: "delete_region", block_key: block.block_key, region_key: region.region_key });
});
elements["set-link-source"].addEventListener("click", () => { state.linkSource = selectedEndpoint(); renderRelationships(); });
elements["save-link"].addEventListener("click", () => {
  const target = selectedEndpoint(); if (!state.linkSource || !target) return;
  sendCommand({ action: "link", relationship_type: elements["relationship-type"].value, source: state.linkSource, target }).then(() => { state.linkSource = null; renderRelationships(); });
});
elements["new-block-type"].addEventListener("change", () => {
  elements["new-block-financial"].checked = elements["new-block-type"].value === "table";
});
document.addEventListener("keydown", (event) => {
  if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;
  if (event.key === "ArrowLeft") selectPage(state.activePage - 1); else if (event.key === "ArrowRight") selectPage(state.activePage + 1);
  else if (event.key === "+" || event.key === "=") updateZoom(.25); else if (event.key === "-") updateZoom(-.25);
  else if (event.key.toLowerCase() === "b") elements["blocks-toggle"].click(); else if (event.key.toLowerCase() === "e") elements["embedded-toggle"].click();
  else if (event.key.toLowerCase() === "o" && !elements["ocr-toggle"].disabled) elements["ocr-toggle"].click();
});
populateTypeOptions(elements["block-type-select"]); populateTypeOptions(elements["new-block-type"]);
elements["new-block-type"].value = "title"; elements["new-block-financial"].checked = false;
updateZoom(0, true); initialize();
