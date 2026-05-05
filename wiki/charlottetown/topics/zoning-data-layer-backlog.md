---
type: topic
tags:
  - charlottetown
  - backlog
  - resolver
  - visualization
updated: 2026-05-04
---

# Zoning Data Layer Backlog

Self-contained briefs for the four follow-up tasks needed to bring the
Charlottetown zoning data layer to a state that a parcel-level visualization
can sit on top of. Each section is written so an agent who has not seen the
originating conversation can pick it up cold.

Read first, in order, for context:

- [Database standup](database-standup.md) — overall data flow, source-of-truth
  artifact map, applied migrations, and tracked known issues.
- [Data-layer conventions](data-layer-conventions.md) — operating contract
  for new scripts that touch the zoning schema (versioned JSON artifacts,
  natural-key + content-hash discipline, read-only MCP boundary).
- `schema/json-schema/charlottetown-bylaw-extraction.schema.json` — the
  authoritative schema for raw + structured bylaw data.
- `schema/sql/008_zone_inheritance_resolver.sql` — the existing resolver
  views.
- `data/zoning/charlottetown/manual-corrections/override-relationships.json`
  — the curated override edges loaded into `zoning.structured_fact`.

Postgres connection defaults to the local docker container on port 54329
(see `docker-compose.yml`). Read-only inspection is fine via the configured
MCP server; mutation should go through scripts that use psycopg directly.

---

## Task 1 — Population audit (per-zone gap report)

### Goal

A reproducible, per-zone, per-bylaw report that quantifies how much of the
bylaw content is structurally captured vs. trapped in raw text. The output
should be queryable and serve as both a prioritization input ("which zones
need re-extraction first?") and a regression detector ("did the latest
import drop coverage anywhere?").

### Current state

- `zoning.coverage_gap` exists with the right shape (`gap_type`,
  `logical_bylaw_part`, `source_locator`, `expected_record_family`,
  `comparison_effect`, `status`, `notes`). Schema is from migration `001`.
- It is **empty** today. Nothing populates it.
- The structured-data layer is mostly populated after the importer fix, but
  there are known gaps the audit needs to surface — e.g. `uses` rows do not
  carry `term_id` even though the schema permits it; `map_reference` rows
  rarely fill in `postgis_*` linkage; `requirement.applicability.applies_to_use_terms`
  is sparsely populated.

### What to build

A Python script `scripts/audit-charlottetown-population.py` that:

1. For each `(document_revision_id, zone_code)` (or `(rev, document_type,
   document_label)` for non-zone documents), computes the metrics below
   from `zoning.structured_fact`, `zoning.clause`, `zoning.raw_table`,
   `zoning.raw_table_cell`, and `zoning.section`.
2. Inserts one `coverage_gap` row per `(scope, gap_type)` with a non-zero
   gap, plus a "summary" diagnostics blob in `notes`.
3. Replaces prior rows for the same `(bylaw_document_id, document_revision_id,
   gap_type, logical_bylaw_part)` so re-runs are idempotent.

Suggested `gap_type` values (text; not constrained today):

| `gap_type` | What it measures |
|---|---|
| `requirement_without_numeric_value` | requirements rows whose `numeric_value_refs` is empty or whose ids do not resolve to any active `numeric_values.numeric_value_id`. |
| `numeric_value_orphan` | numeric_values rows not referenced by any active requirement. |
| `relationship_in_text_not_extracted` | clauses whose text matches override or inheritance phrasing but no corresponding `structured_fact` exists. Reuses the regex set from `scripts/extract-charlottetown-override-candidates.py`. |
| `requirement_applicability_missing` | requirements rows where `value_payload->'applicability'->'applies_to_use_terms'` is empty AND `applies_to_zone_codes` is empty. |
| `map_reference_not_linked` | map_reference rows missing `postgis_schema` / `postgis_table` / `postgis_layer_name` / `feature_key`. |
| `use_without_term_id` | uses rows where `value_payload->>'use_term_id'` is null. |
| `raw_table_no_structured_facts` | raw_table rows that have no `structured_fact.source_record_table='raw_table'` rows pointing at them (lossy table extraction). |

Add a SQL view `zoning.v_coverage_gap_summary` that rolls the gaps up by
`(document_revision_id, gap_type)` and another that pivots by zone for the
zone-typed scopes. Place this view definition in
`schema/sql/009_coverage_gap_views.sql`.

Update `wiki/charlottetown/topics/database-standup.md` step 9 (verification)
to include `python scripts/audit-charlottetown-population.py` and a sample
roll-up query.

### Status (delivered)

Migration `schema/sql/009_coverage_gap_views.sql` and
`scripts/audit-charlottetown-population.py` are in place. The audit emits
two scopes per metric where applicable:

- **Per-revision summary** rows, `logical_bylaw_part='<family>'` (e.g.
  `requirements`), one per `(document_revision_id, gap_type)`.
- **Per-zone** rows, `logical_bylaw_part='zone:<CODE>'`, one per zone with
  a non-zero gap. These feed `zoning.v_coverage_gap_by_zone` and answer
  the "which zones to re-extract first?" prioritization question.

`numeric_value_orphan` and `map_reference_not_linked` deliberately emit
only the summary row — orphans have no requirement to attribute a zone
to, and map references are document-level.

A JSON snapshot is written to `data/zoning/charlottetown/audits/<UTC>.json`
on every run for diffability.

### Acceptance criteria

- After a fresh `import-charlottetown-zoning.py` run on the existing local
  DB, executing the audit script produces a non-zero number of
  `coverage_gap` rows and the script reports a per-revision summary on
  stdout, plus the worst-5 zones for each zone-scopable metric.
- Re-running the script with no underlying data changes does not duplicate
  rows.
- `zoning.v_coverage_gap_summary` returns one row per
  `(document_revision_id, gap_type)` with a count and a percentage where
  meaningful (e.g. requirements without numeric values / total requirements).
- `zoning.v_coverage_gap_by_zone` returns at least one row per
  `(document_revision_id, zone_code, gap_type)` where the zone has a
  non-zero gap on a zone-scopable metric.
- The wiki standup page documents how to run the audit, the two scopes,
  and what a healthy baseline looks like.

### Open decisions

1. ~~JSON snapshot under `data/zoning/charlottetown/audits/` for
   diffability across runs.~~ **Resolved: yes** — written on every run.
2. Whether the audit should fail the script with a non-zero exit code if a
   regression is detected vs. a previous baseline. Probably overkill for v1
   — start as a report.

### Effort estimate

~3 hours including the SQL view and standup wiki update.

---

## Task 2 — Override-aware resolver

### Goal

Make `v_zone_effective_uses` and `v_zone_effective_requirements` honor the
override edges loaded by
`scripts/apply-charlottetown-override-relationships.py`. Today they return
the unconditional inherited set; the 46 override facts are present in
`zoning.structured_fact` but ignored by the resolver layer.

### Current state

- Inheritance resolver: complete in `schema/sql/008_zone_inheritance_resolver.sql`.
  Walks `inherits_uses` / `inherits_regulations` edges, cycle-guarded,
  produces `v_zone_inheritance_edge` / `v_zone_inheritance_closure` /
  `v_zone_effective_uses` / `v_zone_effective_requirements`. MUC reaches
  depth 6 across both branches.
- Override edges: 46 rows in `zoning.structured_fact` with
  `fact_family='cross_references'` and `natural_key LIKE 'override|%'`,
  spread across the relationship types `notwithstanding`,
  `does_not_apply`, `exception_to`, `supersedes`, `applies_to_parcel`,
  `references_zone`. Each carries a `target_ref` and a `join_behavior`
  pulled from the schema's relationship taxonomy.
- The resolver views do not read these rows.

### What to build

A new migration `schema/sql/010_override_aware_resolver.sql` (or whatever
the next free number is) that:

1. Adds `v_zone_override_edge` — projects every override fact into a
   uniform shape: `source_zone, target_kind, target_id, relationship_type,
   join_behavior, source_clause_ref, scope`. For zone-targeted rows the
   source_zone is the row's `source_clause_ref` zone prefix or the
   `target_ref.source_ref_id` for `applies_to_parcel`. For other targets
   the source_zone is best-effort (NULL when not derivable; see Open
   decisions).
2. Replaces `v_zone_effective_uses` / `v_zone_effective_requirements` with
   override-aware variants that:
   - Auto-apply zone-targeted and clause-targeted overrides with
     `join_behavior IN ('exclude_target_values', 'override_target_values')`
     by filtering rows whose source clause matches the override's target.
   - Surface section-targeted, document-targeted, and external-source
     overrides as a parallel `applicable_overrides[]` aggregate (jsonb)
     attached to each output row, **without auto-applying them**. The
     scope field holds free-text predicates ("the lot area and frontage
     requirements") that cannot be safely interpreted in SQL.
3. Preserves provenance: existing columns (`contributing_zone`,
   `via_clause_ref`, etc.) plus the new `applicable_overrides[]` column.

### Acceptance criteria

- For zone WF, `v_zone_effective_requirements` excludes the
  finished-floor-elevation rule for parking structures / accessory
  buildings / water-related structures, because of the
  `does_not_apply` override on `zone-wf-clause-34-5-1`.
- For zone MUC (current), the closure depth and ancestor topology are
  unchanged from the pre-migration baseline (max_depth=6, 10 distinct
  ancestors). Override application does not break the inheritance walk.
- Each row in `v_zone_effective_requirements` for any zone with an
  Appendix-C `applies_to_parcel` edge surfaces the appendix reference in
  `applicable_overrides[]` even though the parcel-level override cannot be
  applied in zone-scope.
- Re-applying the migration is idempotent (`CREATE OR REPLACE VIEW`
  throughout).

### Test cases (write as SQL in the migration's smoke-test footer)

```sql
-- 1. WF FFE exception is honored
SELECT COUNT(*) AS rows_referencing_ffe
FROM zoning.v_zone_effective_requirements
WHERE root_zone='WF' AND requirement_text_raw ILIKE '%finished floor elevation%';
-- Expect 0 (excluded by override) OR rows tagged with the override applied.

-- 2. MUC topology unchanged
SELECT MAX(depth), COUNT(DISTINCT ancestor_zone)
FROM zoning.v_zone_inheritance_closure
WHERE root_zone='MUC' AND document_revision_id=1;
-- Expect (6, 10).

-- 3. Appendix C overrides are visible alongside inherited regs for affected zones
SELECT root_zone, jsonb_array_length(applicable_overrides) AS override_count
FROM zoning.v_zone_effective_requirements
WHERE root_zone IN ('C-1','DC','WF','I') AND document_revision_id=1
GROUP BY 1, applicable_overrides ORDER BY 1;
-- Expect every row for these zones to surface at least the Appendix C pointer.
```

### Open decisions

1. **Source-zone derivation for non-zone-anchored overrides.** A general-
   provisions clause's notwithstanding (e.g.
   `doc-general-provisions-clause-48-11-4 → 45.14.1`) does not name a
   zone. Two reasonable choices: treat it as document-wide (apply to every
   zone) or surface it on the section/clause-attached zones via an
   applicability resolution step. Recommend: document-wide for v1,
   surfacing in `applicable_overrides[]` only.
2. **What `override_target_values` means in SQL.** For a zone-targeted
   row, "override" can mean: replace the inherited target rows, *or* apply
   alongside as the canonical set. For v1, keep the inherited row but mark
   it with a `superseded_by_override` flag column rather than physically
   filtering. This leaves the visualization layer free to render the
   superseded rule as struck-through if it wants.
3. **Handling `references_zone` (rezoning permission, not inheritance).**
   The two RH→GC/GN edges should NOT propagate uses or regulations.
   Filter them out of the override aggregator entirely.

### Effort estimate

~1 day, mostly working through edge cases of the SQL semantics and writing
the test queries. Significantly easier than it would have been pre-PR-#5
because the override edges are already structured.

---

## Task 3 — Parcel resolver

### Goal

A function `zoning.parcel_effective_zoning(parcel_id, document_family)` (or
view + helper) that, given a parcel, returns:

1. Base zone(s) the parcel falls in via `ST_Intersects` against the
   appropriate boundary layer.
2. The flattened effective regulations from Task 2 for that zone.
3. Any parcel-specific overrides from Appendix C / draft 2.9 site-specific
   amendments.
4. Map-overlay layers the parcel intersects (height schedules, walkable
   street grade, storm surge, wetlands).

### Current state

- Spatial layers loaded: `charlottetown_parcel_map` (13,833 parcels),
  `charlottetown_civic_addresses` (14,676), `charlottetown_street_network`
  (4,598), `charlottetown_current_zoning_boundaries` (1,558),
  `charlottetown_draft_zoning_boundaries` (20),
  `charlottetown_schedule_a_wetlands` (64).
- `zone_spatial_feature` has 1,565 zone↔polygon links; both bylaws are
  100% linked except for 12 NA + 1 U polygons in the current map (these are
  intentionally unzoned — see standup wiki).
- Appendix C parcel-level rows are NOT yet structured. There are 14
  zone-coarse `applies_to_parcel` facts but no per-PID rows. Detailed
  extraction is a precondition for this task — see Task 3a below.
- The downtown and Hillsborough height schedules and the walkable-street
  grade layer are NOT yet loaded. Storm surge is unaccounted for. These
  are referenced by the bylaw and need to be loaded before the resolver
  can join them.

### Task 3a (prerequisite) — Parse Appendix C into structured facts

The file
`data/zoning/charlottetown/appendix-c-approved-site-specific-exemptions.json`
holds the raw appendix in `raw_data.pages_raw` (8 pages, ~47 distinct
PIDs across 14 zones). Each row in the source PDF table has Zone, PID(s),
Civic Address(es), Use, and Regulation override.

Build a script `scripts/extract-charlottetown-appendix-c-exemptions.py`
that:

1. Parses the page text into one record per (PID, exemption-context).
2. Writes
   `data/zoning/charlottetown/manual-corrections/appendix-c-exemptions.json`
   with `schema_version=1` and entries shaped like:
   ```json
   {
     "pid": "339994",
     "civic_address": "99 Pownal Street",
     "zone_code_at_amendment": "DMUN",
     "use_added_or_modified": "Fitness Centre",
     "regulation_override_text": "...",
     "source_page": 194
   }
   ```
3. Companion `apply-charlottetown-appendix-c-exemptions.py` promotes each
   entry to a `structured_fact` with `fact_family='cross_references'`,
   `relationship_type='applies_to_parcel'`, and a `target_ref` of
   `{"source_ref_type": "external_source", "source_ref_id":
   "parcel:<pid>"}` until a richer parcel-fact taxonomy is introduced.
4. Drops the 14 zone-coarse pointer facts from the existing
   `override-relationships.json` once per-PID rows replace them, OR keeps
   them with `confidence='superseded'` and a notes pointer. Recommend
   keeping for traceability.

### What to build (Task 3 itself, after 3a)

A SQL function `zoning.parcel_effective_zoning(parcel_id bigint,
document_family text)` returning a jsonb document with:

```json
{
  "parcel_id": ...,
  "civic_addresses": [...],
  "geometry_centroid": {...},
  "zones": [{"zone_code": "...", "zone_name": "...", "boundary_source_layer": "..."}],
  "effective_uses": [...],          // from v_zone_effective_uses, with provenance
  "effective_requirements": [...],  // from v_zone_effective_requirements
  "site_specific_exemptions": [...],// from appendix-c per-PID rows
  "applicable_overrides": [...],    // from override-aware resolver
  "map_overlays": [
    {"layer_key": "charlottetown_schedule_a_wetlands", "intersects": true, ...}
  ]
}
```

Implement as a SQL function in a new migration. Use `LATERAL` joins to keep
the function definition simple. Return `NULL` if the parcel id does not
exist. Return one row per zone in the unusual case where a parcel
straddles a zone boundary.

### Acceptance criteria

- `SELECT zoning.parcel_effective_zoning(?, 'current')` for a known
  Appendix-C parcel (e.g. PID 339994 / 99 Pownal Street) surfaces the
  Fitness Centre site-specific use in `site_specific_exemptions` and the
  base DMUN zone uses in `effective_uses`.
- Same for an unaffected parcel: `site_specific_exemptions` is empty,
  `effective_uses` reflects the base zone.
- A parcel intersecting `charlottetown_schedule_a_wetlands` has the layer
  flagged in `map_overlays`.
- Function executes in <100ms for a single parcel on the local dev DB.

### Open decisions

1. **Are downtown / Hillsborough height schedules treated as overlay
   layers or as zone-overlays modifying the underlying zone?** Probably
   overlays at v1; the bonus-height clause `doc-other-clause-2-10-2`
   already gives the structural hook.
2. **Cross-bylaw lookup:** should the function take `document_family` or
   automatically use the latest? Recommend explicit arg for clarity.

### Effort estimate

3a (Appendix C parsing): ~half day given the page text is well-structured
table content. 3 itself: ~half day. Total ~1 day.

---

## Task 4 — Visualization on resolver outputs

### Goal

A browser UI that shows, for any parcel: which zone applies, which uses
are permitted, what dimensional rules apply (with provenance back to the
clauses), what overrides are in effect, and which spatial overlays
intersect the parcel.

### Current state

- An existing web demo lives under `web/` (build in `build/`,
  `package.json` at repo root, server logic referenced in `docker-compose.yml`'s
  `web` service). It does not consume the new resolver views or the
  override edges; previous iterations were focused on raw bylaw rendering
  and current-vs-draft comparison.
- The QGIS MCP server is configured but requires the QGIS Desktop plugin
  to be running. Useful for ad-hoc cartographic work, less useful for the
  in-browser app.

### What to build

This is properly a frontend project, not a single agent task. Suggested
shape if a single agent does take it:

1. A backend endpoint `GET /api/parcel/:pid` that calls
   `zoning.parcel_effective_zoning` and returns the jsonb document
   directly.
2. A parcel search box + map (Leaflet or MapLibre) loading the parcel
   layer as vector tiles or as a simplified GeoJSON for display.
3. A side panel that renders the resolver output:
   - Tab: Permitted uses, grouped by `use_status`, with provenance
     ("inherited from R-3 via clause `zone-r-4-clause-18-1-1`").
   - Tab: Dimensional rules, table of `requirements` with units and
     comparators.
   - Tab: Overrides, listing `applicable_overrides[]` in plain English
     using the `scope` field.
   - Tab: Map overlays toggle (wetlands, schedules, etc.).
4. A current-vs-draft toggle. The existing demo already handles this
   pattern; lift the affordance.

### Open decisions

- **Frontend stack.** Existing web demo's stack (TBD; check `web/`).
  Don't pick a different framework without a reason.
- **Map renderer.** MapLibre GL is the natural choice given the spatial
  data is in PostGIS; vector tiles via pg_tileserv are a clean fit.
- **Provenance density.** How prominently to show the inheritance
  breadcrumbs vs. the overrides. Probably a collapsible "why" section per
  rule.

### Effort estimate

Out of scope for a single coding agent. Treat as a multi-day frontend
feature once Task 3 lands. Acceptance is product-shaped, not test-shaped.

---

## Task 5 — Make table-derived facts first-class in `structured_fact`

### Goal

Have the importer represent every `structured_fact` row that was
extracted from a `zoning.raw_table` with explicit table provenance:
`source_record_table='raw_table'`, `source_record_key=<table_source_id>`,
and `value_payload.raw_table_id=<bigint>`. Stop relying on the implicit
"synthetic-clause-id-by-naming-convention" pattern that table-derived
facts use today.

### Current state

The importer extracts table content (e.g. zone I's "Regulations for
Permitted Uses" table, every per-zone parking table, the
general-provisions accessory-building table) into `requirements`
`structured_fact` rows whose `source_clause_ref` is a synthetic id of
the form `<table_source_id>-row-<N>` (e.g.
`zone-i-table-regulations-for-permitted-uses-row-1`). Two consequences
that ripple through the rest of the data layer:

- **Inheritance resolver misses table-anchored zones.** The
  `owner_zone` regex in `schema/sql/008_zone_inheritance_resolver.sql`
  (and inherited by `010_override_aware_resolver.sql`) only matches
  `zone-<code>-clause-...` / `-section-...`. Table-prefixed source ids
  fall through with `owner_zone=NULL` and are filtered out, so
  `v_zone_effective_requirements` returns 0 rows for any zone whose
  requirements live exclusively in tables. Visible symptom on the
  current local DB: zone `I` has 41 requirement structured_facts but 0
  rows in the effective-requirements view. Task 2's smoke-test 3 passes
  for C-1 / DC / WF and silently drops `I` for this reason.
- **`raw_table_no_structured_facts` audit metric is brittle.** Until
  this fix lands the metric matches by synthetic clause-id prefix
  (`<table_source_id>-row-%`); see `scripts/audit-charlottetown-
  population.py`. After this fix the metric should match by
  `source_record_table='raw_table'` and `value_payload.raw_table_id`
  directly, restoring the original brief's intent.

### What to build

1. **Importer change.** Update `scripts/import-charlottetown-zoning.py`
   so that any structured_fact derived from a `raw_table` row writes:
   - `source_record_table='raw_table'`
   - `source_record_key=<table_source_id>` (the `raw_table.table_source_id`
     value, not the synthetic clause id)
   - `value_payload.raw_table_id=<raw_table.raw_table_id>`
   - `value_payload.raw_table_row_index=<integer>` (the row inside the
     table, so the existing per-row granularity is preserved).
   The `source_clause_ref` field can stay populated with the synthetic
   id for back-compat, but the canonical link is the explicit triple
   above.
2. **Inheritance regex update.** In
   `schema/sql/008_zone_inheritance_resolver.sql` (and the duplicated
   pattern in `010_override_aware_resolver.sql`), extend the
   `owner_zone` regex to accept `table` as a third anchor type:
   `^zone-([a-z0-9-]+?)-(?:clause|section|table)`. With Task 5's
   importer change in place this is the path zone-I-style requirements
   take into the resolver.
3. **Audit metric simplification.** Once table-derived facts carry
   `source_record_table='raw_table'`, restore
   `metric_raw_table_no_structured_facts` in
   `scripts/audit-charlottetown-population.py` to match by
   `source_record_table='raw_table'` / `raw_table_id` directly. Drop
   the synthetic-prefix workaround and its inline comment.
4. **Data backfill.** Re-running `import-charlottetown-zoning.py` on
   the existing artifacts re-derives every `structured_fact` from
   source JSON, so the natural-key + content-hash importer machinery
   will refresh the affected rows in place. Add a verification query
   in `wiki/charlottetown/topics/database-standup.md` step 9 confirming
   `(SELECT COUNT(*) FROM zoning.structured_fact WHERE
   source_record_table='raw_table')` is non-zero post-import.

### Acceptance criteria

- After re-import: every `raw_table` row referenced by at least one
  `structured_fact` (currently 82/86 on rev 1, 47/49 on rev 2) has a
  matching SF row with `source_record_table='raw_table'` and a
  populated `value_payload.raw_table_id`.
- `zoning.v_zone_effective_requirements` returns ≥1 row for zone `I` on
  revision 1 (today: 0). Task 2's smoke-test 3 passes for `I`.
- `scripts/audit-charlottetown-population.py` reports
  `raw_table_no_structured_facts` with the same numeric gap (4 on rev 1,
  2 on rev 2) using the simplified `source_record_table='raw_table'`
  match — i.e. the count is robust to the change in matching method.
- `wiki/charlottetown/topics/database-standup.md` step 9 documents the
  `source_record_table='raw_table'` smoke check.

### Open decisions

1. **Whether to retire the synthetic `*-row-<N>` clause ids entirely.**
   Some downstream queries may grep on them. Recommend: keep them in
   `value_payload.source_clause_ref` for back-compat, but treat the
   `(source_record_table, source_record_key, raw_table_row_index)`
   triple as canonical going forward.
2. **Whether to split the inheritance-regex update into a separate
   `011_*.sql` migration or fold it into Task 5's importer change.**
   Folding keeps the change atomic; splitting makes the resolver
   improvement reviewable on its own. Recommend: separate
   `011_table_anchored_inheritance.sql` so the SQL change can land
   independently of the importer change.

### Effort estimate

~half day: importer change is small (single helper that constructs the
table-derived SF row), regex update is a one-line patch with an
accompanying smoke query, audit metric simplification is mechanical.
Most of the time is verifying nothing else in the codebase relies on
table-derived rows having `source_record_table='clause'`.

---

## Sources

- `schema/json-schema/charlottetown-bylaw-extraction.schema.json`
- `schema/sql/001_zoning_schema.sql`
- `schema/sql/008_zone_inheritance_resolver.sql`
- `data/normalized/code-tables/relationship_type.seed.json`
- `data/zoning/charlottetown/manual-corrections/override-relationships.json`
- `data/zoning/charlottetown/manual-corrections/section-equivalence-decisions.json`
- `data/zoning/charlottetown/appendix-c-approved-site-specific-exemptions.json`
- `scripts/import-charlottetown-zoning.py`
- `scripts/extract-charlottetown-override-candidates.py`
- `scripts/apply-charlottetown-override-relationships.py`
- [Database standup](database-standup.md)
