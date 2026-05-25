---
type: index
tags:
  - wiki
  - catalog
updated: 2026-05-20
---

This page catalogs the root wiki structure and links to active project wiki areas.

## Core Pages

| Page | Purpose |
| --- | --- |
| [Wiki schema](./AGENTS.md) | Root schema, layout, conventions, workflows, and high-value ingest targets. |
| [Root log](./log.md) | Append-only record of root wiki structural changes, ingests, queries, and lint passes. |

## Page Areas

| Area | Purpose |
| --- | --- |
| [sources](./sources/.gitkeep) | Project-wide source summaries. |
| [domain](./domain/.gitkeep) | Shared domain concepts and cross-project terminology. |
| [platform](./platform/.gitkeep) | Durable platform, toolchain, GIS, database, and runtime notes. |
| [implementation](./implementation/.gitkeep) | Durable workflow, extraction, schema, and implementation notes. |
| [charlottetown](./charlottetown/README.md) | Active Charlottetown current and draft zoning wiki. |
| [council-committee-meetings](./council-committee-meetings/README.md) | Meeting-preparation workflows and extraction notes for public, council/committee, and staff audiences. |

## Source Pages

| Page | Purpose |
| --- | --- |
| [PEI LIDAR and bathymetry metadata](./sources/pei-lidar-bathymetry-metadata.md) | Observed PDAL and GDAL metadata for PEI LIDAR and Charlottetown harbour bathymetry source files. |
| [Local Government in British Columbia](./sources/lgbc-local-government-bc.md) | Source profile and ingestion plan link for the BC local-government handbook used as a municipal-performance prototype source. |

## Domain Pages

| Page | Purpose |
| --- | --- |
| [By-law clause labels](./domain/bylaw-clause-labels.md) | Reusable clause-label preservation, hierarchy normalization, compact-label, repealed-label, and review-flag guidance. |

## Project Pages

| Page | Purpose |
| --- | --- |
| [Municipal portal product purpose](./product/municipal-portal-purpose.md) | 1.0 product definition for the Charlottetown municipal public-data portal. |
| [Municipal portal 1.0 roadmap](./product/municipal-portal-v1-roadmap.md) | Route map, ordered work, backlog, and acceptance criteria for portal 1.0. |
| [Municipal portal role model](./product/municipal-portal-role-model.md) | Public role-preset model for the portal without creating a permission model. |
| [Municipal portal domain inventory](./product/municipal-portal-domain-inventory.md) | Current implementation depth and 1.0 treatment for each municipal portal domain. |
| [Council and committee meetings](./council-committee-meetings/README.md) | JSON-first council/committee meeting extraction and audience workflow notes, starting with Charlottetown council on May 12, 2026. |
| [Agenda and package document taxonomy](./council-committee-meetings/agenda-document-taxonomy.md) | Agenda item and agenda package attachment type catalogue for document-import review and parser refinement. |

## Implementation Pages

| Page | Purpose |
| --- | --- |
| [Municipal portal UI architecture](./product/municipal-portal-ui-architecture.md) | React/Babel portal-shell architecture, page context contract, theming, and basic-HTML feasibility gate. |
| [Municipal portal UI component architecture](./product/municipal-portal-ui-component-architecture.md) | Reusable view-component contract, dependency posture, and implementation-independence guidance for portal UI. |
| [Web UI stack](./implementation/web-ui-stack.md) | Initial Docker-hosted Node web UI decision and first Charlottetown section-equivalence review page shape. |
| [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) | Plan and timeline for replacing the current web page with the design-kit-based Charlottetown parcel lookup, map explorer, city-view map, and zoning comparison demo. |
| [Parcel 3D LIDAR terrain plan](./implementation/parcel-3d-lidar-terrain-plan.md) | Preprocessing and integration plan for using PEI LIDAR as terrain and building-height inputs in the parcel 3D viewer. |
| [Charlottetown terrain DEM pipeline](./implementation/charlottetown-terrain-dem-pipeline.md) | First repeatable PDAL/GDAL pipeline design for producing a bare-earth DEM from PEI COPC LIDAR tiles. |
| [Storm surge demo plan](./implementation/storm-surge-demo-plan.md) | Demo-only Charlottetown tidal and storm-surge visualization scope, controls, source assumptions, limits, and upgrade path. |
| [Municipal budget data model](./implementation/municipal-budget-data-model.md) | Initial scalable schema design for raw and normalized municipal operating, capital, rate, tax, debt, reserve, and funding data. |

## Plans

| Page | Purpose |
| --- | --- |
| [Local Government in British Columbia ingestion plan](../plan/lgbc-ingestion-plan.md) | Staged source-indexing, chapter-review, benchmark-candidate, and Charlottetown-prototype mapping plan for `docs/LGBC-All.pdf`. |

## Active Project Wikis

| Wiki | Status | Scope |
| --- | --- | --- |
| [Charlottetown](./charlottetown/index.md) | Active | Current zoning, draft zoning, validation, comparison, maps, parcels, and future QGIS/PostGIS use. |

## Instruction Placement

| Location | Scope |
| --- | --- |
| [Root AGENTS](../AGENTS.md) | Minimal universal startup routing instructions. |
| [Role skills](../.codex/skills/role-project-management/SKILL.md) | Role-specific universal operating rules and implementation gates. |
| [Wiki schema](./AGENTS.md) | Wiki structure, page conventions, ingest, query, and lint workflows. |
| [Charlottetown workstream context](./charlottetown/topics/workstream-context.md) | Active project-specific Charlottetown context. |

## High-Value Ingest Targets

See [Wiki schema](./AGENTS.md) for the maintained list of high-value root wiki integration targets.

## Sources

- [Wiki schema](./AGENTS.md)
- [Charlottetown wiki guide](./charlottetown/README.md)
