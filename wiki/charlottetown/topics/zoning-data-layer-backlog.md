---
type: topic
tags:
  - charlottetown
  - backlog
  - resolver
  - visualization
updated: 2026-05-05
---

# Zoning Data Layer Backlog

Self-contained briefs for the follow-up tasks needed to bring the
Charlottetown zoning data layer to a state that a parcel-level
visualization can sit on top of. Each section is written so an agent who
has not seen the originating conversation can pick it up cold.

## Status overview

| Task | Status | Key artifact(s) |
|---|---|---|
| 1 — Population audit | ✅ delivered | `schema/sql/009_coverage_gap_views.sql`, `scripts/audit-charlottetown-population.py` |
| 2 — Override-aware resolver | ✅ delivered | `schema/sql/010_override_aware_resolver.sql` |
| 3 — Parcel resolver | ✅ v1.1 delivered | `schema/sql/012_parcel_resolver.sql`, `schema/sql/013_parcel_resolver_civic_address.sql`, `scripts/extract-charlottetown-appendix-c-exemptions.py`, `scripts/apply-charlottetown-appendix-c-exemptions.py` |
| 4 — Visualization | ⏳ pending | (frontend; out of scope for a single coding agent) |
| 5 — Table-derived facts first-class | ✅ delivered | `schema/sql/011_table_anchored_inheritance.sql`, `scripts/import-charlottetown-zoning.py`, `scripts/audit-charlottetown-population.py` |
| 6 — Split current `general-provisions.json` | ⏳ pending | — |
| 7 — Stamp `applies_to_*` at extraction time | ⏳ pending | — |
| 8 — Inheritance closure `DISTINCT ON` (perf) | ✅ delivered | `schema/sql/014_inherited_reqs_distinct_on.sql` |

Cross-cutting deliverable not in the table: `propagate_group_applicability()`
in `scripts/import-charlottetown-zoning.py` (Option A from the gap-3
investigation; closes `requirement_applicability_missing` from 100% to
~24/39%, see Task 7 for the extractor-side follow-up).

Read first, in order, for context:

- [Database standup](database-standup.md) — overall data flow, source-of-truth
  artifact map, applied migrations, and tracked known issues.
- [Data-layer conventions](data-layer-conventions.md) — operating contract
  for new scripts that touch the zoning schema (versioned JSON artifacts,
  natural-key + content-hash discipline, read-only MCP boundary).
- `schema/json-schema/charlottetown-bylaw-extraction.schema.json` — the
  authoritative schema for raw + structured bylaw data.
- `schema/sql/008_zone_inheritance_resolver.sql` — the original
  inheritance resolver. Migrations 010, 011, and 013 layer on top of it
  for override semantics, table-anchored requirements, and the parcel
  resolver respectively.
- `data/zoning/charlottetown/manual-corrections/override-relationships.json`
  — the curated override edges loaded into `zoning.structured_fact`.
- `data/zoning/charlottetown/manual-corrections/appendix-c-exemptions.json`
  — per-PID Appendix C exemptions (36 high-confidence + 12 needs_review).

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

### Status (delivered)

Migration `schema/sql/010_override_aware_resolver.sql`. Added
`zoning.v_zone_override_edge` (44 edges; `references_zone` filtered out
per Open Decision #3) and `zoning.v_clause_section_lookup`. Replaced
`v_zone_effective_uses` and `v_zone_effective_requirements` with
override-aware variants exposing `applicable_overrides jsonb` (every
override targeting the row's zone/clause/section/document) and
`superseded_by_override boolean` (clause- or section-targeted overrides
with `join_behavior IN ('exclude_target_values','override_target_values')`
that hit the row's source clause). Per Open Decision #2 the views never
physically filter rows — the visualization layer chooses how to render
superseded entries.

All four smoke tests in the migration footer pass. WF FFE rule surfaces
10 applicable overrides (zone-targeted `does_not_apply` + Appendix C +
others); MUC closure topology unchanged at depth=6 / 10 ancestors;
Appendix-C zone-targeted overrides reach every requirement of affected
zones (verified for C-1, DC, WF, and — after migration 011 — I);
`v_zone_override_edge` excludes `references_zone` (0 rows; 44 other
edges remain).

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

### Status (delivered v1)

Migrations `011_table_anchored_inheritance.sql` and
`012_parcel_resolver.sql`; scripts
`scripts/extract-charlottetown-appendix-c-exemptions.py` and
`scripts/apply-charlottetown-appendix-c-exemptions.py`; data file
`data/zoning/charlottetown/manual-corrections/appendix-c-exemptions.json`.

The extractor produced 48 records (36 high-confidence, 12 needs_review).
The applier promoted the 36 high-confidence rows to
`zoning.structured_fact` with `relationship_type='applies_to_parcel'`
and a per-`(zone, pid, source_page)` natural key so multi-amendment
parcels (e.g. 199 Grafton Street has three Appendix C entries on pages
3/4/6) stay distinct. Re-runs are idempotent.

Migration 012 adds `zoning.zone_effective_payload(zone_code,
revision_id)` and `zoning.parcel_effective_zoning(pid,
document_family)`. PID 339994 returns one DMUN exemption + a payload
with 34 effective uses and 126 effective requirements; PID 342790
returns two exemptions; non-existent PIDs return NULL.

### v1.1 update — civic-address PID resolution

Migration `013_parcel_resolver_civic_address.sql` replaces
`parcel_effective_zoning()` to resolve a parcel's base zone via the
`charlottetown_civic_addresses` point layer (PID attribute) intersected
against the appropriate zoning-boundary layer, and adds map-overlay
intersects. The earlier "Appendix-C-only" v1 has been superseded.

The original four acceptance criteria now read:

1. ✓ `parcel_effective_zoning('339994')` resolves to `zones=["DMUN"]`
   with one Appendix C exemption and a DMUN payload of 34 effective
   uses + 126 effective requirements. `resolution_method` is
   `civic_address_intersect`.
2. ✓ Unaffected parcels (e.g. PID 338129 / 65 Great George Street) now
   return their base zone (`["DMUN"]`) with empty
   `site_specific_exemptions` and a populated zone payload.
3. ✓ A parcel intersecting `charlottetown_schedule_a_wetlands` (e.g.
   PID 335307) has the layer flagged in
   `map_overlays=[{"layer_key":"charlottetown_schedule_a_wetlands",
   "feature_keys":["1"]}]`. Three civic addresses currently intersect
   wetlands.
4. ✓ Performance follow-up delivered in Task 8. Migration
   `014_inherited_reqs_distinct_on.sql` de-duplicates inherited
   requirements by shortest path; C-2 current requirements now return
   245 rows / 245 distinct facts, and
   `parcel_effective_zoning('386557')` returned in 268 ms on a warm
   local dev DB run.

### Known limitations / follow-ups

- **Inheritance-closure duplication (perf): fixed in Task 8.** Migration
  `014_inherited_reqs_distinct_on.sql` adds `DISTINCT ON` shortest-path
  projection to `inherited_reqs`, reducing C-2 current requirements to
  245 rows / 245 distinct facts.
- **Cadastral PID-to-geometry mapping is missing.** `public.parcels`
  is empty and `charlottetown_parcel_map` is a polygonized derivation
  with no PID column. The civic-address resolution path is sufficient
  for v1 (14,676 civic-address points cover 11,669 distinct PIDs) but
  some parcels lack a civic address and would need a real cadastral
  layer to resolve. Track as Task 3b ("ingest PID-keyed cadastral
  parcels") if that long tail matters.
- **Overlay layers limited to wetlands.** The not-yet-loaded height
  schedules / walkable-street grade / storm surge layers will join
  through the same overlay machinery once registered with
  `expected_geometry_type IN ('POLYGON','MULTIPOLYGON')` in
  `zoning.spatial_layer`. No code change needed in the resolver.
- **12 needs_review Appendix C rows.** The PDF text-extractor
  flattened the table into multi-line cells the parser can't always
  bucket cleanly. Curator workflow: spot-check the 12 rows in
  `appendix-c-exemptions.json`, hand-correct the `civic_address` /
  `use_added_or_modified` / `regulation_override_text` fields, and
  re-run the applier with `--include-needs-review` once the rows are
  reliable.
- **Single-mashed-line rows underpopulate `use_added_or_modified`.**
  E.g. PID 339994's "Fitness Centre" lands in `civic_address` because
  the source text put PID + address + use on one line. Cosmetic, but
  worth a follow-up parser pass.

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

### Status (partial — regex sub-piece delivered)

The smallest sub-piece — extending the inheritance-resolver regex from
`(clause|section)` to `(clause|section|table)` — landed as
`schema/sql/011_table_anchored_inheritance.sql`. Concrete effects:

- `v_zone_effective_requirements` now returns 41 rows for zone I (was
  0); Task 2's smoke-test 3 passes for I as well as C-1/DC/WF.
- C-1 / DC / WF row counts also jumped (2/10/9 → 273/130/131) because
  their inherited requirements now include table-anchored ancestor
  rules. This is the "hidden Task 5↔Task 3 dependency" called out
  during planning — Task 3's parcel resolver consumes this view, so
  fixing the regex was a real prerequisite for resolver quality, not
  cosmetic cleanup.
- The audit metric `raw_table_no_structured_facts` was tightened in
  commit `e58c127` to match by synthetic clause-id prefix
  (`<table_source_id>-row-%`), reporting the real lossy-extraction
  rate (4/86 rev 1, 2/49 rev 2) instead of the spurious 100%.

The remaining sub-pieces (importer writes `source_record_table='raw_table'`
/ `raw_table_id` directly; audit metric simplified to the cleaner
match) were delivered on 2026-05-05. During implementation the importer
also stopped loading duplicate top-level `raw_data.tables_raw` entries
when the same `table_id` already exists under a section, reducing the
active raw-table baseline from 86/49 to 43/34.

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

### Status (delivered)

`scripts/import-charlottetown-zoning.py` now resolves table-row source
references to canonical raw-table provenance:

- `source_record_table='raw_table'`
- `source_record_key=<table_source_id>`
- `value_payload.source_clause_ref=<synthetic row id>` for compatibility
- `value_payload.raw_table_row_index=<row index>`
- `value_payload.raw_table_id=<active zoning.raw_table.raw_table_id>`

The importer also excludes `manual-corrections/` and `audits/` from source
artifact discovery; those directories are handled by their own apply/audit
scripts. Duplicate top-level raw-table rows are no longer loaded when the
same `table_id` is already present inside a section.

`scripts/audit-charlottetown-population.py` now computes
`raw_table_no_structured_facts` from direct `source_record_table='raw_table'`
and `value_payload.raw_table_id` links. After re-import and audit:

- Revision 1 has 41 linked raw tables out of 43 active raw tables; gap 2.
- Revision 2 has 33 linked raw tables out of 34 active raw tables; gap 1.
- Every active `source_record_table='raw_table'` structured fact has
  `raw_table_id` and `raw_table_row_index` populated.
- Zone I effective requirements remain visible at 41 rows, and Task 2's
  Appendix-C override smoke check remains true for C-1, DC, WF, and I.

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

## Task 6 — Split current `general-provisions.json` into themed parts

### Goal

Restructure `data/zoning/charlottetown/general-provisions.json` (a single
artifact carrying Parts 4 through 48 of the current bylaw, ~94 sections)
into themed sibling files mirroring the layout already used by the draft
folder. The split is a code-organization improvement (smaller artifacts,
better current↔draft section-equivalence pairing, easier incremental
re-extraction); it is **not** an applicability-coverage fix and does not
move the audit's `requirement_applicability_missing` metric.

### Current state

- **Current:** `data/zoning/charlottetown/general-provisions.json` is one
  document with `document_metadata.document_type='general_provisions'`
  and 94 entries in `raw_data.sections_raw` spanning section labels
  4.1 through 48.x. Structured-data totals: 256 numeric_values, 164
  requirements, 1 regulation_group, 4 terms, 0 uses, 4 zone_relationships.
  Loaded into the database under a single `zoning.bylaw_part` row.
- **Draft:** `data/zoning/charlottetown-draft/` already splits the same
  conceptual content into six themed files:
  - `general-provisions-buildings-structures.json`
  - `general-provisions-land-use.json`
  - `general-provisions-lots-site-design.json`
  - `general-provisions-parking.json`
  - `general-provisions-signage.json`
  - `general-provisions-subdividing-land.json`
  Plus `administration.json` and `permit-applications-processes.json`
  siblings.

The draft layout is also what `scripts/generate-charlottetown-section-
equivalence.py` works against; current↔draft pairing across the
mismatched layout currently relies on section-label heuristics.

### What to build

1. **A splitter script** (e.g. `scripts/split-charlottetown-general-
   provisions.py`) that reads the existing artifact and writes six
   themed siblings, partitioning `raw_data.sections_raw` by section-
   label range:

   | Target file | Section-label prefixes |
   |---|---|
   | `general-provisions-buildings-structures.json` | 4.x |
   | `general-provisions-land-use.json` | 5.x, 6.x (uses, mixed uses, secondary suites, garden suites, accessory uses) |
   | `general-provisions-lots-site-design.json` | 7.x (lot regulations), 8.x–9.x (yard / setback overrides not already in Part 4) |
   | `general-provisions-parking.json` | 46.x |
   | `general-provisions-signage.json` | 47.x |
   | `general-provisions-subdividing-land.json` | 48.x |

   The prefix mapping above is a starting point; finalize against the
   actual draft topic-to-section mapping by inspecting each draft file's
   `sections_raw[*].section_label_raw` ranges. Any section in the
   current document that does not fit one of the six buckets goes into
   a seventh `general-provisions-other.json` rather than getting
   silently dropped.

2. **Co-partition `structured_data` and `raw_data.tables_raw` /
   `clause_refs` / `map_references_raw`** so each themed file is
   self-contained. Concretely: for every `requirement`,
   `numeric_value`, `regulation_group`, `term`, `zone_relationship`,
   and `map_layer_reference`, look up its `source_refs[0].source_ref_id`
   (or equivalent), find which themed file owns the matching section,
   and write it there. `regulation_groups` whose `requirement_refs[]`
   span multiple themed files get flagged for review.

3. **Update `data/zoning/charlottetown/source-manifest.json`** to list
   the six (or seven) new themed files and remove the original
   `general-provisions.json` entry.

4. **Run `python scripts/import-charlottetown-zoning.py`** on the
   reorganized layout. Because the source-file natural key includes
   `repo_relpath`, the rename creates new active rows and supersedes the
   prior single-file `bylaw_part`. `structured_fact` natural keys also
   embed `repo_relpath`, so every fact is re-keyed; rows whose payload
   is unchanged keep the same content_hash but acquire a new active
   record under the new natural key.

5. **Re-run section-equivalence generation** (`scripts/generate-
   charlottetown-section-equivalence.py`) against the new layout. The
   themed-to-themed pairing should yield more confident `same_topic`
   matches than the current single-file pairing; expect a meaningful
   uplift in `accepted` candidates.

### Acceptance criteria

- The original `data/zoning/charlottetown/general-provisions.json` is
  removed and replaced by 6 (or 7 with `-other`) themed siblings, none
  of which exceeds half the size of the original.
- Every section in the original `sections_raw` is present in exactly one
  themed file. Likewise for every `requirements` / `numeric_values` /
  `terms` / `regulation_groups` / `zone_relationships` /
  `map_layer_references` entry.
- `python scripts/import-charlottetown-zoning.py` succeeds; total
  `structured_fact` count is unchanged (or differs only by entries that
  spanned themed boundaries and were reviewed).
- `scripts/audit-charlottetown-population.py` reports the same gap
  values pre- and post-split; this task should not change the audit
  metrics.
- `scripts/generate-charlottetown-section-equivalence.py` produces at
  least as many `accepted`-candidate rows as the pre-split run, ideally
  more.
- The `wiki/charlottetown/topics/database-standup.md` artifact map is
  updated to list the six themed siblings.

### Open decisions

1. **Whether to keep a `general-provisions-other.json` catch-all bucket
   or fail the split if a section doesn't map cleanly.** Recommend:
   keep the catch-all and emit a `review_flags` entry on it, so a
   human can re-classify in a follow-up rather than blocking the split.
2. **Whether the splitter is a one-shot script or part of the
   extractor.** A one-shot script is simpler and reversible; folding
   into `extract-charlottetown-zoning-bylaw.py` means future
   re-extractions inherit the layout for free. Recommend: one-shot
   first, fold into the extractor in a follow-up once the boundary
   mapping is settled.
3. **Whether to also split `definitions.json` and the appendix files
   to mirror the draft.** Out of scope for v1 — the draft's
   `definitions.json` is already a sibling of the same name, and the
   appendices have no draft analogue to align with.

### Effort estimate

~half to one day: most of the time is figuring out the section-prefix
to themed-file mapping by cross-referencing the draft layout, plus
verifying that `structured_data` co-partitioning doesn't orphan any
cross-references. The mechanical write-out is small once the mapping is
locked in.

---

## Task 7 — Stamp `applies_to_*` on requirements at extraction time

### Goal

Push the `applicability.applies_to_zone_codes` /
`applies_to_use_terms` fields onto each `requirement` (and
`other_requirement`) at extraction time so the on-disk JSON artifacts
under `data/zoning/charlottetown*/` are self-consistent with the
extraction schema. Removes the need for the importer-side propagation
shim added in commit `57b21f1` (see `propagate_group_applicability` in
`scripts/import-charlottetown-zoning.py`).

### Current state

- The current importer fix (Option A from the gap-3 investigation) does
  the regulation_group → requirements propagation in memory before
  content-hash, so the database is correct: 804/1145 requirements now
  carry `applies_to_zone_codes` and 768/1145 carry
  `applies_to_use_terms` (rev 1 + rev 2 combined).
- The on-disk JSON artifacts are unchanged. `requirements[*].applicability`
  still has only `conditions` (or is missing entirely), and
  `applies_to_*` lists still live one indirection away on
  `regulation_groups[*]`. Anything that consumes the artifacts directly
  (the extractor's own re-runs, the schema validator, or future
  downstream tooling that bypasses the importer) sees the pre-Option-A
  shape.
- Two extractors are involved:
  - `scripts/extract-charlottetown-zoning-bylaw.py` (5,454 lines).
    The zone-document branch around line 4884 already has
    `metadata.zone_code`, builds the per-zone `requirements` list, and
    constructs the bundling `regulation_group` with
    `applicability.applies_to_zone_codes=[zone_code]` (line 4891).
    The piece that's missing is stamping the same `applies_to_zone_codes`
    onto each requirement before the regulation_group is built — and,
    where the group's `regulated_use_terms` is the canonical
    "applies-to-all-permitted-uses-in-zone" list, copying that into
    each requirement's `applicability.applies_to_use_terms`.
  - `scripts/extract-charlottetown-draft-zoning-bylaw.py` (1,208 lines)
    has zero `applicability` references today; the equivalent stamping
    step needs to be added wherever per-zone requirements are built.

### What to build

1. **Current-bylaw extractor.** Add a small helper (e.g.
   `stamp_zone_and_use_applicability(requirements, zone_code,
   regulated_use_terms)`) and call it from the zone-document branch
   right after `build_numeric_and_requirements()` and before the
   `regulation_groups` entry is constructed (around line 4884). The
   helper:
   - Sets `requirement["applicability"].setdefault("applies_to_zone_codes", []).append(zone_code)` (dedup-preserving order, identical semantics to `propagate_group_applicability`'s union).
   - If `regulated_use_terms` is non-empty, mirrors it into
     `requirement["applicability"].setdefault("applies_to_use_terms", [])`.
   - Leaves `applicability.conditions` untouched so existing
     narrative-condition population (e.g. `apply_dms_bonus_height_context`)
     continues to round-trip cleanly.
2. **Draft-bylaw extractor.** Mirror the same logic in
   `extract-charlottetown-draft-zoning-bylaw.py`. The draft's per-zone
   files already carry the zone code in `document_metadata.zone_code`;
   confirm that `regulated_use_terms` (or its draft analogue) is
   available at the same scope.
3. **Doc-level documents stay untouched.** General-provisions,
   design-standards, appendix-b/c, and definitions don't have a single
   owning zone or use-term list; their requirements should keep empty
   `applies_to_*` lists. The audit's residual ~24% (rev 1) /
   ~39% (rev 2) gap reflects exactly this group and is the expected
   floor.
4. **Re-run the extractors and the importer.** The artifacts get
   rewritten with the `applies_to_*` fields in place; `content_hash`
   is unchanged for any requirement whose payload was already in the
   propagated state (because Option A landed the same values into the
   stored payload), so the importer should report zero `changed` rows
   for `requirements`. If it reports non-zero, that's a discrepancy
   worth investigating before merging.
5. **Retire the importer shim.** Once both extractors stamp the fields
   directly, delete `propagate_group_applicability()` from
   `scripts/import-charlottetown-zoning.py` (and its call site in
   `collect_records`). Re-run the importer one more time to confirm
   the database state is unchanged. Document the retirement in the
   commit message and link back to commit `57b21f1`.
6. **Schema enforcement (optional but recommended).** Tighten
   `schema/json-schema/charlottetown-bylaw-extraction.schema.json` to
   require `applicability.applies_to_zone_codes` and
   `applies_to_use_terms` on `requirements` for `document_type='zone'`
   artifacts. This converts a soft expectation into a hard contract
   and catches future extractor regressions at validation time rather
   than via the audit.

### Acceptance criteria

- After re-running both extractors and the importer:
  - Every `requirement` in a zone-document JSON artifact has
    `applicability.applies_to_zone_codes` containing the document's
    `zone_code`. Spot-check on disk by `jq` over a few zones.
  - Where the matching `regulation_group` has a non-empty
    `regulated_use_terms`, every member requirement carries the same
    list as `applicability.applies_to_use_terms`.
  - `propagate_group_applicability()` is removed from the importer.
  - `python scripts/audit-charlottetown-population.py` reports the
    same `requirement_applicability_missing` gap values as today
    (~24% rev 1 / ~39% rev 2) — i.e. the extractor-side fix is
    semantically equivalent to the importer-side shim.
- `python scripts/import-charlottetown-zoning.py` reports zero
  `changed` rows for the `requirements` family on the first post-fix
  run (the values are identical to what Option A had already
  propagated; only the on-disk JSON moved).
- If schema enforcement is in scope: the JSON schema validator
  rejects a zone-document artifact missing
  `applicability.applies_to_zone_codes` on any requirement.

### Open decisions

1. **Whether to copy `regulated_use_terms` verbatim or attempt
   per-requirement use specificity.** Verbatim copy says "this rule
   applies to every permitted use in the zone" — true for zone-wide
   dimensional rules (lot area, frontage, height) but loose for
   use-specific rules (e.g. "for a Home Daycare, max GFA is..."). A
   verbatim copy preserves Option A's semantics; a per-requirement
   refinement is a deeper extractor change and is out of scope for
   this task. Recommend: verbatim, and log per-requirement
   specificity as a follow-up.
2. **Whether to retire the shim in the same PR as the extractor fix
   or in a follow-up PR.** Bundling makes the change atomic; splitting
   makes the audit-equivalence claim independently reviewable.
   Recommend: split — land the extractor fix first, verify zero
   importer churn, then drop the shim.
3. **Whether to schema-enforce the `applies_to_*` fields.** Hard
   contract catches regressions early; loose contract leaves room for
   future doc-level documents (design-standards, etc.) to coexist.
   Recommend: enforce only on `document_type='zone'`, since that's
   the only case with a single owning zone.

### Effort estimate

~half day. The current-extractor change is one helper plus one call
site; the draft-extractor change is the same shape but the per-zone
requirements pipeline needs to be located first (the draft script
doesn't reference `applicability` today, so the right insertion point
isn't already obvious). Verification is short because Option A's audit
numbers serve as the equivalence target.

---

## Task 8 — `DISTINCT ON` shortest-path projection in `inherited_reqs`

### Goal

Stop `v_zone_effective_requirements` from emitting the same inherited
requirement once per ancestor path. Today a zone with a deep / branchy
inheritance closure (e.g. C-2 at depth 7 across 12 ancestors) sees
6,923 requirement rows where the underlying distinct facts number a
few hundred. Downstream callers (`zoning.parcel_effective_zoning`,
the future viz layer) iterate that bloated set and pay the cost; the
parcel resolver climbs from ~150 ms to 5+ seconds for any C-2-rooted
PID as a result.

### Current state

`schema/sql/008_zone_inheritance_resolver.sql` defined the original
view with a `DISTINCT ON (root_zone, structured_fact_id)`-style
projection in `inherited_uses` but **not** in `inherited_reqs` —
asymmetry that has carried through every subsequent migration that
re-defines the view (010, 011, 013). Concretely, `inherited_uses`
ends with:

```sql
SELECT DISTINCT ON (cl.root_zone, bu.use_name_raw, bu.use_status,
                    cl.document_revision_id) ...
ORDER BY cl.root_zone, bu.use_name_raw, bu.use_status,
         cl.document_revision_id, cl.depth
```

while `inherited_reqs` has no `DISTINCT ON` clause at all.

### What to build

A small migration (call it `014_inherited_reqs_distinct_on.sql`) that
re-defines `v_zone_effective_requirements` with `DISTINCT ON (cl.root_zone,
br.structured_fact_id, cl.document_revision_id)` projecting the
shortest-path (`ORDER BY cl.depth`) inherited row. Mirror the pattern
already used by `inherited_uses`. View column list is unchanged so
`CREATE OR REPLACE VIEW` is sufficient.

### Acceptance criteria

- `SELECT COUNT(*) FROM zoning.v_zone_effective_requirements WHERE
  root_zone='C-2' AND document_revision_id=1` drops from 6923 to a
  few hundred (the count of distinct underlying requirement
  structured_facts in C-2's inheritance closure).
- `zoning.parcel_effective_zoning('386557')` returns in <300 ms
  (currently 5+ s).
- All other zones return the same set of distinct requirements as
  before (no row dropped that wasn't a duplicate). Verify by spot-
  checking C-1, DMUN, WF row counts.
- Task 2's smoke-test 3 still passes for C-1 / DC / WF / I.

### Open decisions

1. **Whether to also de-duplicate by `requirement_label_raw +
   requirement_text_raw`.** Two distinct structured_facts can describe
   semantically identical rules (e.g. via the importer's
   re-extraction supersession). Recommend: no — keep the projection
   keyed on `structured_fact_id`, since the audit and resolver views
   want to surface every structurally-distinct fact even if two
   happen to read identically. A semantic de-dup belongs in the viz
   layer.

### Status (delivered)

Migration `schema/sql/014_inherited_reqs_distinct_on.sql` replaces
`zoning.v_zone_effective_requirements` with a shortest-path
`DISTINCT ON (root_zone, structured_fact_id, document_revision_id)`
projection inside `inherited_reqs`. The view column list is unchanged.

Smoke checks after applying the migration:

- C-2 current requirements dropped to 245 rows, matching 245 distinct
  `structured_fact_id` values.
- `zoning.parcel_effective_zoning('386557')` returned in 268 ms on a
  warm local dev DB run.
- C-1, DMUN, and WF all returned `rows = distinct_facts`.
- Task 2 Appendix-C override visibility remained true for C-1, DC, WF,
  and I.

### Effort estimate

~30 minutes including the migration, smoke queries, and applying.
The fix is a one-line CTE addition.

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
