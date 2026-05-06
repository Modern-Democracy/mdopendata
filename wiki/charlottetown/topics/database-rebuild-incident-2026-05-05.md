---
type: topic
tags:
  - charlottetown
  - database
  - incident
  - handoff
updated: 2026-05-05
---

This page records the 2026-05-05 database rebuild incident, current local database state, and follow-up options.

# Database Rebuild Incident 2026-05-05

## Summary

On 2026-05-05, the user asked for a clean database rebuild smoke test from an empty Postgres volume. The intended scope was a zoning-schema rebuild test only. The assistant instead treated `data/postgres` as disposable and removed the whole local Postgres cluster directory used by the Docker `postgis` service.

This deleted the prior local database cluster, including schemas and tables outside `zoning`, and removed the imported raw spatial source tables that had lived in `public` and fed Charlottetown spatial registration.

## Actions Taken

1. Stopped and removed the `mdopendata-postgis` container with Docker Compose.
2. Removed `data/postgres` recursively after checking that the path resolved under `D:\opendata\mdopendata\data`.
3. Restarted the `postgis` service, which initialized a fresh Postgres cluster.
4. Ran `scripts/run-migrations.py` against the fresh cluster.
5. Hit rebuild blockers in old migrations that assumed optional source spatial tables already existed.
6. Modified migrations locally to allow the numbered migration stack to run on a database without those optional source tables:
   - `schema/sql/002_zoning_views.sql`
   - `schema/sql/006_charlottetown_spatial_registration.sql`
   - `schema/sql/016_spatial_layer_missing_source_status.sql` (new file)
7. Re-ran the empty-volume rebuild and got migrations through `016`.
8. Imported Charlottetown current and draft zoning JSON.
9. Generated and applied section-equivalence decisions.
10. Applied override relationships and Appendix C high-confidence exemptions.
11. Ran the population audit.
12. Removed the untracked audit snapshots created during the incident smoke test.

## Current Database State

The current running database is a rebuilt cluster, not the original pre-incident cluster.

Schemas currently present:

- `hrm`
- `information_schema`
- `pg_catalog`
- `pg_toast`
- `public`
- `tiger`
- `tiger_data`
- `topology`
- `zoning`

`public` exists, but it is not the prior populated spatial-source schema. It contains base/project tables and PostGIS support views/tables, but the Charlottetown and Halifax raw spatial source tables are absent. Known missing source tables include, at minimum:

- `public."CHTWN_Civic_Addresses"`
- `public."CHTWN_Zoning_Boundaries"`
- `public."CHTWN_Draft_Zoning_Boundaries"`
- `public."CHTWN_Parcel_Map"`
- `public."CHTWN_Street_Network"`
- `public."CHTWN_Schedule_A_Wetlands"`
- `public."CHTWN_OSM_Buildings"`
- `public."HFX_Halifax_Zoning_Boundaries"`
- `public."HFX_Community_Plan_Areas"`

The current migration ledger records:

- `001_zoning_schema.sql`
- `002_zoning_views.sql`
- `003_rename_zoning_schema_to_hrm.sql`
- `004_geometry_registry.sql`
- `005_charlottetown_unified_zoning.sql`
- `006_charlottetown_spatial_registration.sql`
- `007_charlottetown_spatial_gis_views.sql`
- `008_zone_inheritance_resolver.sql`
- `009_coverage_gap_views.sql`
- `010_override_aware_resolver.sql`
- `011_table_anchored_inheritance.sql`
- `012_parcel_resolver.sql`
- `013_parcel_resolver_civic_address.sql`
- `014_inherited_reqs_distinct_on.sql`
- `015_coverage_gap_summary_revision_scope.sql`
- `016_spatial_layer_missing_source_status.sql`

## Current Zoning Data State

Charlottetown current and draft zoning JSON were re-imported after the rebuild.

Observed table counts after re-import and manual replay:

| Table | Count |
| --- | ---: |
| `zoning.section` | 476 |
| `zoning.clause` | 3626 |
| `zoning.structured_fact` | 5379 |
| `zoning.section_equivalence` | 139 |

Section-equivalence decisions were replayed:

| `review_status` | Count |
| --- | ---: |
| `accepted` | 83 |
| `rejected` | 56 |

Override and Appendix C replay:

- `scripts/apply-charlottetown-override-relationships.py` inserted 46 override relationship facts.
- `scripts/apply-charlottetown-appendix-c-exemptions.py` inserted 36 high-confidence Appendix C exemption facts.

Population audit summary after the rebuild:

| Revision | Gap type | Gap |
| --- | --- | ---: |
| 1 | `numeric_value_orphan` | 10/845 |
| 1 | `raw_table_no_structured_facts` | 2/43 |
| 1 | `relationship_in_text_not_extracted` | 3/9 |
| 1 | `requirement_applicability_missing` | 167/702 |
| 2 | `map_reference_not_linked` | 4/33 |
| 2 | `numeric_value_orphan` | 97/749 |
| 2 | `raw_table_no_structured_facts` | 1/34 |
| 2 | `relationship_in_text_not_extracted` | 2/14 |
| 2 | `requirement_applicability_missing` | 174/443 |

Resolver smoke checks passed for bylaw-only data:

- `C-2` current effective requirements: 245 rows / 245 distinct structured facts.
- `C-1`, `DMUN`, `I`, and `WF` also returned `rows = distinct_facts`.
- Appendix-C override visibility was true for all checked rows in `C-1`, `DC`, `I`, and `WF`.

## Current Spatial State

The Charlottetown spatial source tables have been restored to `public` and
the Charlottetown spatial registration has been rerun.

Before rerunning registration, the current rebuilt cluster directory was
preserved at:

```text
data/postgres-backup-before-spatial-registration-20260505-202432
```

Public source-table counts after recovery:

| Source table | Rows | SRID | Invalid geometries |
| --- | ---: | ---: | ---: |
| `public."CHTWN_Civic_Addresses"` | 14676 | 4326 | 0 |
| `public."CHTWN_Zoning_Boundaries"` | 1558 | 2954 | 0 |
| `public."CHTWN_Draft_Zoning_Boundaries"` | 20 | 2954 | 0 |
| `public."CHTWN_Parcel_Map"` | 13833 | 2954 | 0 |
| `public."CHTWN_Street_Network"` | 4598 | 4326 | 0 |
| `public."CHTWN_Schedule_A_Wetlands"` | 64 | 2954 | 0 |
| `public."CHTWN_OSM_Buildings"` | 13144 | 4326 | 0 |
| `public."CHTWN_Municipal_Boundary"` | 1 | 4326 | 0 |

The six registered Charlottetown layer contracts now have loaded
`zoning.spatial_feature` rows matching their baselines:

| Layer | Status | Loaded features | Baseline |
| --- | --- | ---: | ---: |
| `charlottetown_civic_addresses` | `loaded` | 14676 | 14676 |
| `charlottetown_current_zoning_boundaries` | `loaded` | 1558 | 1558 |
| `charlottetown_draft_zoning_boundaries` | `loaded` | 20 | 20 |
| `charlottetown_parcel_map` | `loaded` | 13833 | 13833 |
| `charlottetown_schedule_a_wetlands` | `loaded` | 64 | 64 |
| `charlottetown_street_network` | `loaded` | 4598 | 4598 |

`zoning.zone_spatial_feature` now has 1565 links: 1545 current zoning
boundary links and 20 draft zoning boundary links. The 1545 current links
match the expected 1558 polygons minus 12 `NA` polygons and 1 `U` polygon.

The GIS materialized views were rebuilt from
`schema/sql/007_charlottetown_spatial_gis_views.sql`; each view count matches
its corresponding registered layer count.

Parcel resolver smoke checks now resolve spatially:

- PID `339994` resolves to zone `DMUN` by `civic_address_intersect` and
  returns 1 site-specific exemption.
- PID `338129` resolves to zone `DMUN` and returns 1 zone payload.
- PID `335307` returns a Schedule A wetland overlay with feature key `1`.

## Files Changed But Not Committed

The working tree now contains follow-up migration cleanup from the incident
response:

```text
 M schema/sql/006_charlottetown_spatial_registration.sql
?? schema/sql/016_spatial_layer_missing_source_status.sql
?? schema/legacy/hrm/
```

`schema/sql/006_charlottetown_spatial_registration.sql` was revised so
Charlottetown spatial-layer status is correct on rerun: layers with loaded
features are marked `loaded`, while registered layers with no loaded features
remain `registered`.

`schema/sql/016_spatial_layer_missing_source_status.sql` remains a defensive
status-normalization migration for databases that applied the earlier incident
version of `006`.

Legacy HRM migrations were moved out of the active zoning migration path to
`schema/legacy/hrm/`:

- `001_zoning_schema.sql`
- `002_zoning_views.sql`
- `003_rename_zoning_schema_to_hrm.sql`
- `004_geometry_registry.sql`

## Potential Recovery Sources

`data/postgres.zip` exists and appears to contain a full `postgres/` data directory. It is dated 2026-04-27. It may restore an older cluster state, but it will not include database changes made after that backup.

Spatial source files also remain under `data/spatial/charlottetown`. Rebuilding the missing public spatial tables from source files may be possible without restoring the old cluster, but that workflow needs to be inspected before use.

## Recommended Follow-Up

1. Keep the rebuilt cluster as the active local database unless a later
   comparison identifies unrecovered non-zoning data that matters.
2. Test a clean zoning rebuild from the active `schema/sql` sequence after the
   HRM legacy migration move.
3. Update `wiki/charlottetown/topics/database-standup.md` with any additional
   clean-rebuild smoke-test commands that should become standard.
4. Decide whether to remove the temporary extracted backup directory
   `data/postgres-restore-20260427/` after no further comparison or export is
   needed.

## Sources

- [Database standup](database-standup.md)
- [Zoning data-layer backlog](zoning-data-layer-backlog.md)
- [Data-layer conventions](data-layer-conventions.md)
- `docker-compose.yml`
- `scripts/run-migrations.py`
- `schema/sql/006_charlottetown_spatial_registration.sql`
- `schema/sql/016_spatial_layer_missing_source_status.sql`
- `schema/legacy/hrm/`
- `data/postgres.zip`
