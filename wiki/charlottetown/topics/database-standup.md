---
type: topic
tags:
  - charlottetown
  - database
  - standup
  - operations
updated: 2026-05-04
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
```

## Known issues and follow-ups

- **Override semantics in the resolver are not yet wired up.** 46 override
  relationships are now captured in `zoning.structured_fact` with
  `fact_family='cross_references'` and `relationship_type` in
  {`notwithstanding`, `does_not_apply`, `exception_to`, `supersedes`,
  `applies_to_parcel`, `references_zone`}, but `v_zone_effective_uses` and
  `v_zone_effective_requirements` do not yet honor override semantics.
  Implementing exception/supersession requires projecting category-level
  overrides (e.g. "Notwithstanding the lot area and frontage requirements")
  down to the specific `requirements` rows they invalidate per zone — and
  doing the same for section-level `exception_to` edges (the EXEMPTION
  sections). Non-trivial and deferred to a follow-up migration. Until then the
  resolver returns the unconditional inherited set and the override facts are
  surfaceable as an audit/UX side panel.
- **Appendix C site-specific exemptions are coarse-grained.** 14
  `applies_to_parcel` facts capture *which zones* have parcel-specific
  overrides in Appendix C (one fact per affected zone), but per-PID rows are
  not yet structured: Appendix C is loaded as `pages_raw` text only, with no
  `structured_data.cross_references` populated. Detailed PID/civic-address
  extraction (~47 distinct PIDs) is a focused follow-up and a precondition
  for parcel-resolution in any visualization layer.
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
- **Override relationship facts are unpopulated.** No
  `notwithstanding`, `exception_to`, `supersedes`, or `applies_to_parcel` rows
  exist in `structured_fact`. The inheritance resolver therefore does not yet
  apply override semantics; visualizations should treat its output as the
  unconditional inherited set.

## Backlog

Open follow-up work — population audit, override-aware resolver, parcel
resolver, and visualization — is captured as agent-pickable briefs in
[Zoning data-layer backlog](zoning-data-layer-backlog.md).

## Sources

- `docker-compose.yml`
- `scripts/run-migrations.py`
- `scripts/import-charlottetown-zoning.py`
- `scripts/generate-charlottetown-section-equivalence.py`
- `scripts/export-charlottetown-section-equivalence-decisions.py`
- `scripts/apply-charlottetown-section-equivalence-decisions.py`
- `schema/sql/00*_*.sql`
- [Unified zoning ingestion plan](unified-zoning-ingestion-plan.md)
