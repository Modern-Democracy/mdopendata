---
type: index
tags:
  - charlottetown
  - catalog
updated: 2026-05-19
---

This index catalogs the Charlottetown LLM Wiki pages and source families. Update it whenever wiki pages are added, renamed, or materially changed.

# Charlottetown Wiki Index

## Core Pages

| Page | Purpose |
| --- | --- |
| [README](README.md) | Local operating contract for the Charlottetown LLM Wiki. |
| [Log](log.md) | Append-only chronological record of wiki setup, ingests, queries, and lint passes. |

## Page Areas

| Area | Purpose |
| --- | --- |
| [sources](sources/.gitkeep) | Future source-summary pages for approved Charlottetown source artifacts. |
| [Budget 2026/2027 first pass](sources/budget-2026-2027-first-pass.md) | First-pass page inventory and table manifest notes for the current proposed budget PDF. |
| [entities](entities/.gitkeep) | Future pages for zones, bylaws, maps, schedules, parcels, streets, and neighbourhoods. |
| [topics](topics/.gitkeep) | Future pages for zoning concepts, provisions, definitions, and review themes. |
| [Draft layout repair notes](topics/draft-layout-repair-notes.md) | Durable notes for draft bylaw section-title and two-column clause-assignment repairs. |
| [Draft validation rebaseline](topics/draft-validation-rebaseline.md) | Durable notes for the 2026-04-24 validation-plan rebaseline after parser repairs restored or added clauses and sections. |
| [Unified zoning ingestion plan](topics/unified-zoning-ingestion-plan.md) | Active plan and implementation status for unified relational, spatial, comparison, revision, and vector-ready ingestion of current and draft bylaws. |
| [Workstream context](topics/workstream-context.md) | Active Charlottetown source paths, output paths, purpose, and maintenance duties. |
| [Database standup](topics/database-standup.md) | End-to-end instructions for bringing up the Charlottetown zoning database, including manual-decision replay. |
| [Data-layer conventions](topics/data-layer-conventions.md) | Operating conventions for adding new scripts that touch the zoning schema (versioned JSON artifacts, natural-key + content-hash discipline, read-only MCP boundary). |
| [Database rebuild incident 2026-05-05](topics/database-rebuild-incident-2026-05-05.md) | Handoff summary for the accidental whole-cluster Postgres rebuild, current database state, missing spatial source tables, and recovery options. |
| [Zoning data-layer backlog](topics/zoning-data-layer-backlog.md) | Self-contained briefs for the four follow-up tasks (population audit, override-aware resolver, parcel resolver, visualization). Written so a fresh agent can pick one up cold. |
| [LiDAR building height plan](topics/lidar-building-height-plan.md) | Implemented workflow for deriving Charlottetown building heights from PEI 2020 COPC LAZ tiles and attaching LiDAR-derived height fields to derived layer `public."CHTWN_Buildings"`. |
| [Parcel LiDAR metrics plan](topics/parcel-lidar-metrics-plan.md) | Plan for deriving parcel-level building, terrain, canopy, QA, and provenance metrics from Charlottetown parcels, LiDAR tiles, and the derived building-height layer. |
| [comparisons](comparisons/.gitkeep) | Future current-versus-draft, parcel, zone, or neighbourhood comparison pages. |
| [questions](questions/.gitkeep) | Future reusable answers generated from user queries. |
| [templates](templates/source-summary.md) | Templates for future wiki maintenance. |

## Templates

| Template | Use |
| --- | --- |
| [Source summary](templates/source-summary.md) | Summarize a source artifact without copying it into the wiki. |
| [Entity or concept](templates/entity-or-concept.md) | Create an entity or topic page with citations and open questions. |
| [Comparison](templates/comparison.md) | Create a reusable comparison page. |
| [Query analysis](templates/query-analysis.md) | File a durable answer produced from a user query. |
| [Lint report](templates/lint-report.md) | Record a wiki health-check pass. |

## Source Families

These source families remain outside the wiki and must be referenced in place:

| Source family | Repository path |
| --- | --- |
| Charlottetown source PDFs and notes | `docs/charlottetown` |
| Map source files and rendered views | `maps` |
| Current zoning extraction outputs | `data/zoning/charlottetown` |
| Draft zoning extraction outputs | `data/zoning/charlottetown-draft` |
| Charlottetown spatial outputs | `data/spatial/charlottetown` |
| Active Charlottetown plans and ledgers | `plan` |

## Current Status

The wiki contains a scaffold, targeted draft extraction repair and validation notes, and the active unified zoning ingestion plan. The unified zoning schema and importer are implemented, the relational core is populated, current Chapters 1-3 and split current general-provisions artifacts are imported, Phase 4 spatial registration and linkage is active, and the regenerated section-equivalence candidates are fully reviewed.

## Sources

- [Charlottetown wiki guide](./README.md)
- [Charlottetown workstream context](./topics/workstream-context.md)
- [Unified zoning ingestion plan](./topics/unified-zoning-ingestion-plan.md)
