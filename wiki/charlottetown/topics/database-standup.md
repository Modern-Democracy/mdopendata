---
type: topic
tags:
  - charlottetown
  - database
  - standup
  - operations
updated: 2026-05-05
---

# Database Standup

End-to-end instructions for bringing up the Charlottetown zoning database from
scratch: container boot, schema migrations, JSON ingestion, manual-decision
replay, and verification queries. Follow the steps in order; skipping the
manual-decision replay leaves 139 reviewer decisions on `section_equivalence`
unrecoverable from the JSON sources alone.

## Source-of-truth artifacts

| Artifact | Repository path |
| --- | --- |
| Postgres / PostGIS service definition | `docker-compose.yml` |
| Schema migrations (ordered) | `schema/sql/00*_*.sql` |
| Migration runner | `scripts/run-migrations.py` |
| Bylaw JSON (current) | `data/zoning/charlottetown/` |
| Bylaw JSON (draft) | `data/zoning/charlottetown-draft/` |
| Bylaw importer | `scripts/import-charlottetown-zoning.py` |
| Section-equivalence generator | `scripts/generate-charlottetown-section-equivalence.py` |
| Section-equivalence decisions | `data/zoning/charlottetown/manual-corrections/section-equivalence-decisions.json` |
| Decisions export script | `scripts/export-charlottetown-section-equivalence-decisions.py` |
| Decisions apply script | `scripts/apply-charlottetown-section-equivalence-decisions.py` |
| Override relationships (curated) | `data/zoning/charlottetown/manual-corrections/override-relationships.json` |
| Override-candidate discovery script | `scripts/extract-charlottetown-override-candidates.py` |
| Override-relationships apply script | `scripts/apply-charlottetown-override-relationships.py` |
| Spatial layers | `data/spatial/charlottetown/` |
| Manual draft zoning-map corrections (data) | `data/spatial/charlottetown/manual-corrections/draft-zoning-map-corrections.json` |
| Manual draft zoning-map corrections (script) | `scripts/apply-charlottetown-draft-zoning-manual-corrections.py` |

## Connection settings

`.env` (or shell environment) drives all scripts. Defaults from
`docker-compose.yml`:

```
PGHOST=localhost
PGPORT=54329
PGDATABASE=mdopendata
PGUSER=mdopendata
PGPASSWORD=mdopendata_dev
```

Connection inside the `mdopendata-postgis` container uses port `5432`. The
runner `scripts/run-migrations.py` calls `docker exec` against the container,
so it reads `PGCONTAINER`, `PGDATABASE`, and `PGUSER` rather than the host
port.

## Standup procedure

### 1. Start the Postgres / PostGIS service

```powershell
docker compose up -d postgis
```

Optional: also start `pgadmin` (port 5050 by default) for ad-hoc inspection.

The first start runs `schema/sql/postgis.sql` from the entrypoint mount, which
enables the PostGIS extension on the fresh database. Subsequent restarts skip
this step.

If the data volume already exists (`./data/postgres/`) and you want a truly
clean rebuild, stop the container and remove that directory before bringing it
back up. This destroys all data — including reviewer decisions — so confirm
the decisions JSON is committed first.

### 2. Apply migrations

```powershell
./scripts/python.ps1 scripts/run-migrations.py
```

The runner autodiscovers every `schema/sql/NNN_*.sql` file in ascending
numeric order, tracks applied filenames in `public.schema_migrations`, and
skips any that have already been applied. Add a new migration by dropping a
correctly numbered file into `schema/sql/`; no code change is required.
`schema/sql/postgis.sql` is excluded by the numeric-prefix filter — it is
mounted as the container entrypoint init and runs once on first boot.

Pass `--list` to preview pending migrations without applying them:

```powershell
./scripts/python.ps1 scripts/run-migrations.py --list
```

`008_zone_inheritance_resolver.sql` depends only on the `zoning.section`,
`zoning.clause`, and `zoning.structured_fact` tables, so its views return
rows only after the JSON import populates the underlying data.

The resolver stack on top of 008 (apply in numeric order):

- `009_coverage_gap_views.sql` — relaxes the `coverage_gap.gap_type`
  CHECK and adds `v_coverage_gap_summary` / `v_coverage_gap_by_zone`
  for the population audit (Task 1).
- `010_override_aware_resolver.sql` — adds `v_zone_override_edge` and
  replaces the effective-rule views with override-aware variants
  (Task 2).
- `011_table_anchored_inheritance.sql` — extends the `owner_zone`
  regex from `(clause|section)` to `(clause|section|table)` so
  table-anchored requirements (e.g. zone I) flow through the resolver
  (Task 5 sub-piece).
- `012_parcel_resolver.sql` — adds `zoning.zone_effective_payload`
  and `zoning.parcel_effective_zoning` (Task 3 v1, Appendix-C-only).
- `013_parcel_resolver_civic_address.sql` — replaces
  `parcel_effective_zoning` to resolve a parcel's base zone via the
  `charlottetown_civic_addresses` point layer (PID attribute) ↔
  zoning-boundary intersect, plus map-overlay rollups (Task 3 v1.1).
- `014_inherited_reqs_distinct_on.sql` — replaces
  `v_zone_effective_requirements` so inherited requirements are
  de-duplicated by `(root_zone, structured_fact_id,
  document_revision_id)`, keeping the shortest inheritance path
  (Task 8).

The canonical parcel-lookup API is
`zoning.parcel_effective_zoning(pid text, document_family text)`. It
returns a jsonb document with `civic_addresses[]`, `zones[]`,
`site_specific_exemptions[]`, `zone_payloads[]` (effective uses +
requirements with override-aware columns), `map_overlays[]`, and a
`resolution_method` field. Returns NULL when the PID is unknown to
both the civic-address layer and the Appendix C exemption set.

### 3. Import the bylaw JSON

```powershell
./scripts/python.ps1 scripts/import-charlottetown-zoning.py
```

This walks `data/zoning/charlottetown/` and `data/zoning/charlottetown-draft/`
and seeds `bylaw_document`, `document_revision`, `section`, `clause`,
`definition`, `structured_fact`, and the raw-data sidecars. The importer is
idempotent across re-runs by `natural_key` + `content_hash`.

Expected post-import counts (current loaded dataset):

| Table | Count |
| --- | --- |
| `bylaw_document` | 2 |
| `section` | 486 |
| `clause` | 3779 |
| `structured_fact` | 5515 |

### 4. Load the spatial layers

The spatial datasets are loaded directly into the `public` schema and then
registered into `zoning.spatial_layer` / `zoning.spatial_feature` /
`zoning.zone_spatial_feature` by migration `006`. Reload the source GeoPackages
through your normal `ogr2ogr` or `pyogrio`-driven pipeline (see
`data/spatial/charlottetown/`) before running migration `006`. Expected
counts:

| `spatial_layer.layer_key` | Features |
| --- | --- |
| `charlottetown_parcel_map` | 13833 |
| `charlottetown_civic_addresses` | 14676 |
| `charlottetown_street_network` | 4598 |
| `charlottetown_current_zoning_boundaries` | 1558 |
| `charlottetown_draft_zoning_boundaries` | 20 |
| `charlottetown_schedule_a_wetlands` | 64 |

### 5. Generate section-equivalence candidates

```powershell
./scripts/python.ps1 scripts/generate-charlottetown-section-equivalence.py
```

Seeds `zoning.section_equivalence` with `review_status='candidate'` rows. On
subsequent re-runs, rows whose `review_status` is anything other than
`candidate` are preserved untouched (see
`generate-charlottetown-section-equivalence.py:302`). Stale candidate rows are
pruned (line 334).

### 6. Apply reviewer decisions

```powershell
./scripts/python.ps1 scripts/apply-charlottetown-section-equivalence-decisions.py
```

Reads `data/zoning/charlottetown/manual-corrections/section-equivalence-decisions.json`
and stamps the recorded `review_status`, `equivalence_type`, and
`reviewer_notes` onto matching rows, joined on the natural-key triple
`(current_section_key, draft_section_key, candidate_method)`. Only rows with
`review_status='candidate'` are touched, making the script idempotent and safe
to re-run.

Useful flags:

- `--dry-run` reports planned changes without writing.
- `--force` overwrites already-reviewed rows; use only when reconciling
  diverged datasets.
- `--in <path>` overrides the input file location.

After a successful run, expect:

```
Updated: 139
Unchanged: 0
Skipped (already reviewed, use --force to override): 0
Missing (no matching row in DB): 0
```

A non-zero `Missing` count means the section-equivalence generator did not
produce a candidate for one or more recorded decisions; investigate the
generator before forcing.

### 7. Apply curated override relationships

```powershell
./scripts/python.ps1 scripts/apply-charlottetown-override-relationships.py
```

Reads `data/zoning/charlottetown/manual-corrections/override-relationships.json`
and inserts each entry as a `cross_references` row in
`zoning.structured_fact` with the appropriate `relationship_type`
(`notwithstanding`, `does_not_apply`, `references_zone`). Idempotent by
natural key + content hash; re-running with no JSON changes reports all
entries unchanged.

`scripts/extract-charlottetown-override-candidates.py` is the
companion discovery tool: it scans `zoning.clause` for candidate phrasing
(notwithstanding / does/shall not apply / except as provided / supersedes),
classifies each by pattern, and writes
`override-candidates-review.json`. The classification covers patterns that
should and should not be promoted to facts; only entries with a real graph
target appear in the curated `override-relationships.json`.

`--dry-run` reports planned changes without writing.

### 7b. Apply Appendix C site-specific exemptions

Two scripts, run in order. The extractor parses the raw appendix text;
the applier promotes the high-confidence rows to `structured_fact`:

```powershell
./scripts/python.ps1 scripts/extract-charlottetown-appendix-c-exemptions.py
./scripts/python.ps1 scripts/apply-charlottetown-appendix-c-exemptions.py
```

The extractor writes
`data/zoning/charlottetown/manual-corrections/appendix-c-exemptions.json`
with one entry per (PID, source_page). 36 of the 48 records currently
parse cleanly (`confidence='high'`); the other 12 are tagged
`needs_review` with the raw block text preserved in `notes`. The
applier promotes only `confidence='high'` rows by default; pass
`--include-needs-review` to promote everything (with the
`needs_review` confidence carried into the resulting fact's
`value_payload`).

Each promoted entry becomes a `cross_references` `applies_to_parcel`
fact keyed on `(zone, pid, source_page)`, so multi-amendment parcels
(e.g. PID 342790 / 199 Grafton Street has three Appendix C entries on
pages 3/4/6) stay distinct rather than overwriting each other.
`zoning.parcel_effective_zoning(pid)` reads these rows directly.

### 8. Capture new reviewer decisions back to the JSON

After any new accept/reject pass through the review UI:

```powershell
./scripts/python.ps1 scripts/export-charlottetown-section-equivalence-decisions.py
```

Commit the updated
`data/zoning/charlottetown/manual-corrections/section-equivalence-decisions.json`
so future standups replay the full set. The natural-key fields used for
matching are recorded in the file header.

### 9. Verification queries

Smoke-test the result. All queries use the read-only Postgres MCP server or
`psql` against the running container.

```sql
-- Document baseline
SELECT bylaw_document_id, document_family, bylaw_name FROM zoning.bylaw_document;

-- Population baseline
SELECT 'section' AS t, COUNT(*) FROM zoning.section
UNION ALL SELECT 'clause', COUNT(*) FROM zoning.clause
UNION ALL SELECT 'structured_fact', COUNT(*) FROM zoning.structured_fact
UNION ALL SELECT 'section_equivalence', COUNT(*) FROM zoning.section_equivalence;

-- Reviewer decisions present
SELECT review_status, COUNT(*) FROM zoning.section_equivalence GROUP BY 1 ORDER BY 1;
-- Expect: accepted=83, rejected=56, candidate=remainder.

-- Spatial layers loaded
SELECT layer_key, feature_count_baseline, status FROM zoning.spatial_layer ORDER BY layer_key;

-- Inheritance resolver smoke test (requires migration 008)
SELECT root_zone, depth, ancestor_zone, relationship_type
  FROM zoning.v_zone_inheritance_closure
 WHERE root_zone='MUC' AND document_revision_id=1
 ORDER BY depth, ancestor_zone;
-- Expect rows reaching depth 6 through MUC -> R-4 -> R-3 -> R-2 -> R-1S
-- and through MUC -> ER-MUVC -> R-4B -> R-3T -> R-3 -> ...

-- Parcel resolver smoke test (requires migrations 010-013)
SELECT (zoning.parcel_effective_zoning('339994'))->'zones',
       (zoning.parcel_effective_zoning('339994'))->'resolution_method',
       jsonb_array_length((zoning.parcel_effective_zoning('339994'))->'site_specific_exemptions') AS n_ex;
-- Expect: zones=["DMUN"], resolution_method="civic_address_intersect", n_ex=1.

SELECT (zoning.parcel_effective_zoning('338129'))->'zones',
       jsonb_array_length((zoning.parcel_effective_zoning('338129'))->'zone_payloads') AS n_payloads;
-- Expect: zones=["DMUN"], n_payloads=1 (non-Appendix-C parcel resolves
-- via civic-address intersect alone).

SELECT (zoning.parcel_effective_zoning('335307'))->'map_overlays';
-- Expect a wetland feature_key in map_overlays[].
```

#### Population audit (requires migration 009)

Run the per-revision structural-gap audit. It writes
`is_audit_generated=true` rows into `zoning.coverage_gap` (a per-revision
summary row plus per-zone breakdown rows for zone-scopable metrics) and
a JSON snapshot under `data/zoning/charlottetown/audits/`. Re-runs are
idempotent — every run deletes prior audit rows for the touched revisions
before re-inserting fresh ones; manual gap rows are left alone.

```sh
python scripts/audit-charlottetown-population.py
# add --dry-run to see results without writing
# add --no-snapshot to skip the JSON snapshot
```

The audit emits two scopes per metric where applicable:

- **Per-revision summary** (`logical_bylaw_part='<family>'`, e.g.
  `requirements`) — one row per `(document_revision_id, gap_type)`,
  carrying the global `population_total` and `population_gap` in `notes`.
- **Per-zone breakdown** (`logical_bylaw_part='zone:<CODE>'`) — one row
  per zone with a non-zero gap, for the zone-scopable metrics:
  `requirement_without_numeric_value`,
  `requirement_applicability_missing`, `use_without_term_id`,
  `relationship_in_text_not_extracted`, and
  `raw_table_no_structured_facts`. These feed
  `zoning.v_coverage_gap_by_zone` and answer "which zones need
  re-extraction first?".

Two metrics intentionally emit only the summary row:
`map_reference_not_linked` (map references are document-level) and
`numeric_value_orphan` (orphans by definition have no requirement to
attribute a zone to).

Roll up the result:

```sql
-- Global summary, one row per (revision, gap_type).
SELECT * FROM zoning.v_coverage_gap_summary;
-- Expect 9 rows on the current local DB (4 for revision 1, 5 for revision 2).
-- requirement_applicability_missing now sits at ~24% rev 1 / ~39% rev 2
-- (the importer-side propagation in commit 57b21f1 dropped it from 100%);
-- the residue is doc-level rules genuinely outside any zone-keyed
-- regulation_group. raw_table_no_structured_facts sits at ~5% on both
-- revisions after the metric was tightened in commit e58c127 to match
-- by synthetic-clause-id prefix; the deeper fix (importer writes
-- source_record_table='raw_table' directly) is pending under backlog
-- Task 5.

-- Worst zones for any zone-scoped gap_type, ranked by absolute gap.
SELECT zone_code, gap_type,
       (substring(notes FROM 'population_gap=(\d+)'))::int AS gap,
       (substring(notes FROM 'population_total=(\d+)'))::int AS total
  FROM zoning.v_coverage_gap_by_zone
 WHERE document_revision_id=1
   AND gap_type='requirement_applicability_missing'
 ORDER BY gap DESC LIMIT 10;
-- Expect rev 1's worst zones to lead with I (41), R-2 / R-2S (34 each),
-- R-3 / R-3T (30 each). On rev 2 the worst zones are GC (26), GN (24),
-- RN (20), RH (19), RM (18). A healthy baseline keeps these orders of
-- magnitude stable; large jumps indicate the latest import dropped
-- coverage in those zones.
```

The seven gap_type families the audit emits are documented in
[zoning-data-layer-backlog.md](zoning-data-layer-backlog.md) (Task 1).

## Known issues and follow-ups

- **Override semantics: wired up via migration 010.** The 46 override
  relationships in `zoning.structured_fact`
  (`fact_family='cross_references'`, `relationship_type` in
  {`notwithstanding`, `does_not_apply`, `exception_to`, `supersedes`,
  `applies_to_parcel`, `references_zone`}) are now read by
  `v_zone_override_edge` and surfaced on every row of
  `v_zone_effective_uses` / `v_zone_effective_requirements` as
  `applicable_overrides jsonb` plus a `superseded_by_override boolean`
  flag. The views never physically filter rows; the visualization
  layer chooses how to render superseded entries. See backlog Task 2
  for design rationale and Open Decisions.
- **Appendix C site-specific exemptions: per-PID rows live.** Replaces
  the earlier coarse 14 zone-level pointer facts. The extractor +
  applier (step 7b above) promote 36 high-confidence per-(PID,
  source_page) rows out of 48; the remaining 12 are tagged
  `needs_review` for curator follow-up. Use `--include-needs-review`
  to promote everything once the rows are corrected.
- **`notwithstanding` patterns intentionally not promoted to facts.** Out of
  46 clauses containing 'notwithstanding', only 14 carry a graph-actionable
  target reference. The other 32 are global standalone rules
  ("Notwithstanding any other provision of this by-law, ..."), within-clause
  back-references ("notwithstanding the foregoing"), or per-zone accessory-use
  templates ("Notwithstanding the requirements, the following are permitted as
  accessory or secondary uses:"). They are captured as `requirements` /
  `uses` facts elsewhere; promoting them to relationship facts would
  duplicate. See the `ignored_patterns` section of
  `override-relationships.json` for the convention details.
- **TODO: retire the draft zoning-map manual corrections.** The 5 missing-block
  fills in `data/spatial/charlottetown/manual-corrections/draft-zoning-map-corrections.json`
  patch around gaps in the polygonized draft zoning map
  (`charlottetown-draft-zoning-map-...-vector-municipal-fit-draft.gpkg`).
  Long-term, those blocks should be added to the upstream GeoPackage so the
  source layer is correct from the start, at which point
  `scripts/apply-charlottetown-draft-zoning-manual-corrections.py` and the
  corresponding JSON can be deleted. Not a priority; revisit when the
  polygonization pipeline is next touched.
- **`NA` and `U` polygons in the current zoning layer are intentionally
  unlinked.** Of 1,558 polygons in `charlottetown_current_zoning_boundaries`,
  12 are tagged `ZONING='NA'` (zoning not assigned, e.g. waterways and road
  allowances) and 1 is tagged `ZONING='U'` (infill area). Neither code appears
  in the current bylaw, so neither has a `zone_code_crosswalk` row and they
  remain absent from `zone_spatial_feature`. Treat as unzoned overlays in any
  visualization; do not add crosswalk rows for them.
- **Importer drops natural-key ids: fixed.** A previous version of
  `import-charlottetown-zoning.py` stripped every payload key ending in `_id`,
  silently flattening cross-references in `structured_fact.value_payload`.
  Fixed 2026-05-04 and the bylaw JSON has been re-imported, so
  `value_payload->'target_ref'->>'source_ref_id'` is now populated on every
  active `zone_relationships` fact. The text-recovery branch in
  `v_zone_inheritance_edge` is retained only as a defensive fallback.
- **C-2-rooted parcel resolver perf: fixed in migration 014.**
  `v_zone_effective_requirements` now de-duplicates inherited
  requirements by `(root_zone, structured_fact_id, document_revision_id)`
  and keeps the shortest inheritance path. After applying 014, C-2
  current requirements return 245 rows / 245 distinct facts, and
  `zoning.parcel_effective_zoning('386557')` returned in 268 ms on a
  warm local dev DB run.

## Backlog

Open follow-up work — population audit, override-aware resolver, parcel
resolver, and visualization — is captured as agent-pickable briefs in
[Zoning data-layer backlog](zoning-data-layer-backlog.md).

## Conventions

Operating conventions for new scripts that read or write the zoning schema
are documented in [Data-layer conventions](data-layer-conventions.md).
Read this before adding a new manual-decisions artifact or a new mutating
script.

## Sources

- `docker-compose.yml`
- `scripts/run-migrations.py`
- `scripts/import-charlottetown-zoning.py`
- `scripts/generate-charlottetown-section-equivalence.py`
- `scripts/export-charlottetown-section-equivalence-decisions.py`
- `scripts/apply-charlottetown-section-equivalence-decisions.py`
- `schema/sql/00*_*.sql`
- [Unified zoning ingestion plan](unified-zoning-ingestion-plan.md)
