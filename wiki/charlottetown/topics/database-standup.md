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
| Spatial layers | `data/spatial/charlottetown/` |
| Manual spatial corrections (draft zoning map) | `scripts/apply-charlottetown-draft-zoning-manual-corrections.py` |

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

`run-migrations.py` only enumerates `001`–`005` today. Apply later migrations
manually until that list is updated:

```powershell
docker exec -i mdopendata-postgis psql -v ON_ERROR_STOP=1 -U mdopendata -d mdopendata < schema/sql/006_charlottetown_spatial_registration.sql
docker exec -i mdopendata-postgis psql -v ON_ERROR_STOP=1 -U mdopendata -d mdopendata < schema/sql/007_charlottetown_spatial_gis_views.sql
docker exec -i mdopendata-postgis psql -v ON_ERROR_STOP=1 -U mdopendata -d mdopendata < schema/sql/008_zone_inheritance_resolver.sql
```

`008_zone_inheritance_resolver.sql` depends only on the `zoning.section`,
`zoning.clause`, and `zoning.structured_fact` tables, so it can be run before
or after the JSON import — but the views return rows only after the import
populates the underlying data.

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

### 7. Capture new reviewer decisions back to the JSON

After any new accept/reject pass through the review UI:

```powershell
./scripts/python.ps1 scripts/export-charlottetown-section-equivalence-decisions.py
```

Commit the updated
`data/zoning/charlottetown/manual-corrections/section-equivalence-decisions.json`
so future standups replay the full set. The natural-key fields used for
matching are recorded in the file header.

### 8. Verification queries

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

- **`scripts/run-migrations.py` lags the migration list.** It hard-codes `001`
  through `005`. Update the `MIGRATIONS` tuple when new SQL files are added,
  or run later files manually as in step 2.
- **Manual draft spatial corrections are hard-coded.**
  `scripts/apply-charlottetown-draft-zoning-manual-corrections.py` carries its
  parcel-id list in source rather than a versioned data file. Migrating to the
  same JSON-artifact pattern as section-equivalence decisions is a future
  cleanup.
- **`zone_code_crosswalk` for the draft is incomplete.** 20 polygons are loaded
  but only 1 crosswalk row exists. Spatial→zone linkage on the draft side is
  pending.
- **Importer drops natural-key ids no longer applies.** A previous version of
  `import-charlottetown-zoning.py` stripped every payload key ending in `_id`,
  silently flattening cross-references in `structured_fact.value_payload`.
  Fixed 2026-05-04. After any re-import, confirm
  `value_payload->'target_ref'->>'source_ref_id'` is populated on
  `zone_relationships` facts; the recovery layer in
  `008_zone_inheritance_resolver.sql` is no longer required once that holds.
- **Override relationship facts are unpopulated.** No
  `notwithstanding`, `exception_to`, `supersedes`, or `applies_to_parcel` rows
  exist in `structured_fact`. The inheritance resolver therefore does not yet
  apply override semantics; visualizations should treat its output as the
  unconditional inherited set.

## Sources

- `docker-compose.yml`
- `scripts/run-migrations.py`
- `scripts/import-charlottetown-zoning.py`
- `scripts/generate-charlottetown-section-equivalence.py`
- `scripts/export-charlottetown-section-equivalence-decisions.py`
- `scripts/apply-charlottetown-section-equivalence-decisions.py`
- `schema/sql/00*_*.sql`
- [Unified zoning ingestion plan](unified-zoning-ingestion-plan.md)
