const state = {
  rows: [],
  filteredRows: [],
  activeIndex: null,
};

const rowList = document.querySelector("#rowList");
const search = document.querySelector("#search");
const decisionFilter = document.querySelector("#decisionFilter");
const decisionStrip = document.querySelector("#decisionStrip");
const currentPane = document.querySelector("#currentPane");
const draftPane = document.querySelector("#draftPane");
const metrics = document.querySelector("#metrics");

function valueOrDash(value) {
  return value && String(value).trim() ? value : "-";
}

function citationRange(citations = {}) {
  const bylawStart = citations.bylaw_page_start;
  const bylawEnd = citations.bylaw_page_end;
  const pdfStart = citations.pdf_page_start;
  const pdfEnd = citations.pdf_page_end;
  const bylaw = bylawStart ? `bylaw page ${bylawStart}${bylawEnd && bylawEnd !== bylawStart ? `-${bylawEnd}` : ""}` : "";
  const pdf = pdfStart ? `PDF page ${pdfStart}${pdfEnd && pdfEnd !== pdfStart ? `-${pdfEnd}` : ""}` : "";
  return [bylaw, pdf].filter(Boolean).join("; ");
}

function renderMetrics() {
  const decisions = new Map();
  for (const row of state.rows) {
    decisions.set(row.review_decision, (decisions.get(row.review_decision) || 0) + 1);
  }
  metrics.innerHTML = [
    `<span class="metric">${state.rows.length} rows</span>`,
    ...[...decisions.entries()].map(([decision, count]) => `<span class="metric">${valueOrDash(decision)}: ${count}</span>`),
  ].join("");
}

function populateDecisionFilter() {
  const preferredDecisions = ["needs_review", "accepted", "rejected"];
  const decisions = [
    ...preferredDecisions,
    ...[...new Set(state.rows.map((row) => row.review_decision).filter(Boolean))]
      .filter((decision) => !preferredDecisions.includes(decision))
      .sort(),
  ];
  decisionFilter.innerHTML = '<option value="">All decisions</option>';
  for (const decision of decisions) {
    const option = document.createElement("option");
    option.value = decision;
    option.textContent = decision;
    decisionFilter.append(option);
  }
}

function filterRows() {
  const query = search.value.trim().toLowerCase();
  const decision = decisionFilter.value;
  state.filteredRows = state.rows.filter((row) => {
    const haystack = [
      row.review_decision,
      row.candidate_topic,
      row.db_equivalence_type,
      row.current_section_label,
      row.current_section_title,
      row.draft_section_label,
      row.draft_section_title,
      row.reviewer_notes,
    ]
      .join(" ")
      .toLowerCase();
    return (!decision || row.review_decision === decision) && (!query || haystack.includes(query));
  });
  renderRowList();
}

function syncRows(rows) {
  state.rows = rows;
  renderMetrics();
  populateDecisionFilter();
  filterRows();
}

function renderRowList() {
  rowList.innerHTML = "";
  if (state.filteredRows.length === 0) {
    rowList.innerHTML = '<div class="empty">No rows match the current filter.</div>';
    return;
  }

  for (const row of state.filteredRows) {
    const button = document.createElement("button");
    button.className = `row-item${row.row_index === state.activeIndex ? " active" : ""}`;
    button.type = "button";
    button.innerHTML = `
      <div class="row-title">${row.current_section_label} ${row.current_section_title}</div>
      <div class="row-subtitle">${row.draft_section_label} ${row.draft_section_title}</div>
      <div class="row-meta">
        <span class="pill">${valueOrDash(row.review_decision)}</span>
        <span class="pill">${valueOrDash(row.db_equivalence_type)}</span>
        <span class="pill">text ${valueOrDash(row.text_similarity)}</span>
      </div>
    `;
    button.addEventListener("click", () => loadDetail(row.row_index));
    rowList.append(button);
  }
}

function renderDecision(row) {
  decisionStrip.innerHTML = `
    <div class="decision-grid">
      <div class="field"><span>Decision</span><strong>${valueOrDash(row.review_decision)}</strong></div>
      <div class="field"><span>Database status</span><strong>${valueOrDash(row.db_review_status)}</strong></div>
      <div class="field"><span>Equivalence type</span><strong>${valueOrDash(row.db_equivalence_type)}</strong></div>
      <div class="field"><span>Title similarity</span><strong>${valueOrDash(row.title_similarity)}</strong></div>
      <div class="field"><span>Text similarity</span><strong>${valueOrDash(row.text_similarity)}</strong></div>
    </div>
    <div class="review-actions">
      <button class="decision-button accept" type="button" data-decision="accepted">Approve</button>
      <button class="decision-button reject" type="button" data-decision="rejected">Reject</button>
    </div>
    <p class="notes">${valueOrDash(row.reviewer_notes)}</p>
  `;
  for (const button of decisionStrip.querySelectorAll("[data-decision]")) {
    button.addEventListener("click", () => saveDecision(row, button.dataset.decision));
  }
}

function renderPane(element, label, section) {
  if (!section) {
    element.innerHTML = `<div class="empty">${label} section could not be loaded.</div>`;
    return;
  }
  const clauses = section.clauses ?? [];
  const tables = section.tables ?? [];
  element.innerHTML = `
    <div class="pane-header">
      <div class="pane-kicker">${label}</div>
      <h2 class="pane-title">${section.label} ${section.title}</h2>
      <div class="source-line">${section.filePath}</div>
      <div class="source-line">${citationRange(section.citations)}</div>
    </div>
    <div class="clause-list">
      ${clauses
        .map(
          (clause) => `
            <div class="clause">
              <div class="clause-text"><span class="clause-label">${valueOrDash(clause.label)}</span>${valueOrDash(clause.text)}</div>
              <div class="source-line">${citationRange(clause.citations)}</div>
            </div>
          `,
        )
        .join("")}
      ${tables
        .map(
          (table) => `
            <div class="clause">
              <div class="clause-text"><span class="clause-label">${valueOrDash(table.title)}</span></div>
              ${(table.rows ?? [])
                .map(
                  (row) => `
                    <div class="source-line">${(row.cells ?? [])
                      .map((cell) => valueOrDash(cell.text))
                      .filter((value) => value !== "-")
                      .join(" | ")}</div>
                  `,
                )
                .join("")}
            </div>
          `,
        )
        .join("")}
      ${clauses.length === 0 && tables.length === 0 ? '<div class="empty">No clause or table text is available for this section.</div>' : ""}
    </div>
  `;
}

async function loadDetail(rowIndex) {
  state.activeIndex = rowIndex;
  renderRowList();
  const response = await fetch(`/api/section-equivalence/${rowIndex}`);
  if (!response.ok) {
    throw new Error(`Unable to load row ${rowIndex}`);
  }
  const detail = await response.json();
  renderDecision(detail.row);
  renderPane(currentPane, "Current", detail.currentSection);
  renderPane(draftPane, "Draft", detail.draftSection);
}

async function saveDecision(row, decision) {
  const response = await fetch(`/api/section-equivalence/${row.section_equivalence_id}/decision`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ decision }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `Unable to save ${decision} decision`);
  }
  const detail = await response.json();
  syncRows(detail.rows);
  state.activeIndex = detail.row.row_index;
  renderRowList();
  renderDecision(detail.row);
  renderPane(currentPane, "Current", detail.currentSection);
  renderPane(draftPane, "Draft", detail.draftSection);
}

async function init() {
  const response = await fetch("/api/section-equivalence");
  const payload = await response.json();
  syncRows(payload.rows);
  if (state.filteredRows.length > 0) {
    await loadDetail(state.filteredRows[0].row_index);
  }
}

search.addEventListener("input", filterRows);
decisionFilter.addEventListener("change", filterRows);

init().catch((error) => {
  decisionStrip.innerHTML = `<div class="empty">${error.message}</div>`;
});
