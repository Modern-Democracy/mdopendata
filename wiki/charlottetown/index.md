---
type: index
tags:
  - charlottetown
  - catalog
updated: 2026-04-29
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
| [entities](entities/.gitkeep) | Future pages for zones, bylaws, maps, schedules, parcels, streets, and neighbourhoods. |
| [topics](topics/.gitkeep) | Future pages for zoning concepts, provisions, definitions, and review themes. |
| [Draft layout repair notes](topics/draft-layout-repair-notes.md) | Durable notes for draft bylaw section-title and two-column clause-assignment repairs. |
| [Draft validation rebaseline](topics/draft-validation-rebaseline.md) | Durable notes for the 2026-04-24 validation-plan rebaseline after parser repairs restored or added clauses and sections. |
| [Unified zoning ingestion plan](topics/unified-zoning-ingestion-plan.md) | Active plan and implementation status for unified relational, spatial, comparison, revision, and vector-ready ingestion of current and draft bylaws. |
| [Workstream context](topics/workstream-context.md) | Active Charlottetown source paths, output paths, purpose, and maintenance duties. |
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

The wiki contains a scaffold, targeted draft extraction repair and validation notes, and the active unified zoning ingestion plan. The unified zoning schema and initial JSON importer are implemented, the relational core is populated, and section-equivalence candidate generation has started.

## Sources

- [Charlottetown wiki guide](./README.md)
- [Charlottetown workstream context](./topics/workstream-context.md)
- [Unified zoning ingestion plan](./topics/unified-zoning-ingestion-plan.md)
