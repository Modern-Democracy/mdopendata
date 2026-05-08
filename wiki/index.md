---
type: index
tags:
  - wiki
  - catalog
updated: 2026-05-08
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

## Source Pages

| Page | Purpose |
| --- | --- |
| [PEI LIDAR and bathymetry metadata](./sources/pei-lidar-bathymetry-metadata.md) | Observed PDAL and GDAL metadata for PEI LIDAR and Charlottetown harbour bathymetry source files. |

## Domain Pages

| Page | Purpose |
| --- | --- |
| [By-law clause labels](./domain/bylaw-clause-labels.md) | Reusable clause-label preservation, hierarchy normalization, compact-label, repealed-label, and review-flag guidance. |

## Implementation Pages

| Page | Purpose |
| --- | --- |
| [Web UI stack](./implementation/web-ui-stack.md) | Initial Docker-hosted Node web UI decision and first Charlottetown section-equivalence review page shape. |
| [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) | Plan and timeline for replacing the current web page with the design-kit-based Charlottetown parcel lookup, map explorer, city-view map, and zoning comparison demo. |
| [Parcel 3D LIDAR terrain plan](./implementation/parcel-3d-lidar-terrain-plan.md) | Preprocessing and integration plan for using PEI LIDAR as terrain and building-height inputs in the parcel 3D viewer. |
| [Charlottetown terrain DEM pipeline](./implementation/charlottetown-terrain-dem-pipeline.md) | First repeatable PDAL/GDAL pipeline design for producing a bare-earth DEM from PEI COPC LIDAR tiles. |

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
