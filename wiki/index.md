---
type: index
tags:
  - wiki
  - catalog
updated: 2026-05-27
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
| [generated](./generated/schema/index.md) | Generated wiki reference outputs, starting with MCP-generated database schema pages. |
| [charlottetown](./charlottetown/README.md) | Active Charlottetown current and draft zoning wiki. |
| [council-committee-meetings](./council-committee-meetings/README.md) | Meeting-preparation workflows and extraction notes for public, council/committee, and staff audiences. |

## Source Pages

| Page | Purpose |
| --- | --- |
| [PEI LIDAR and bathymetry metadata](./sources/pei-lidar-bathymetry-metadata.md) | Observed PDAL and GDAL metadata for PEI LIDAR and Charlottetown harbour bathymetry source files. |
| [Local Government in British Columbia](./sources/lgbc-local-government-bc.md) | Source profile and ingestion plan link for the BC local-government handbook used as a municipal-performance prototype source. |
| [LGBC Chapter 6: Service Delivery](./sources/lgbc/chapter-6-service-delivery.md) | Chapter 6 review notes for service-delivery concepts, performance-analysis candidates, and municipal data needs. |
| [LGBC Chapter 1: Introduction](./sources/lgbc/chapter-1-introduction.md) | Chapter 1 review notes for local-government purpose, fiscal equivalence, collective problems, and municipal data needs. |
| [LGBC Chapter 10: Regulatory And Development Functions](./sources/lgbc/chapter-10-regulatory-development-functions.md) | Chapter 10 review notes for planning, zoning, subdivision, enforcement, fiscal-equivalence limits, and municipal data needs. |
| [LGBC Chapter 12: Finance](./sources/lgbc/chapter-12-finance.md) | Chapter 12 review notes for municipal finance, fiscal equivalence, revenue sources, taxation, fees, transfers, debt, reserves, and municipal data needs. |
| [LGBC Chapter 7: Protective Services](./sources/lgbc/chapter-7-protective-services.md) | Chapter 7 review notes for police, fire, emergency protection, performance-measure caveats, and municipal data needs. |
| [LGBC Chapter 8: Engineering Services](./sources/lgbc/chapter-8-engineering-services.md) | Chapter 8 review notes for water, wastewater, solid waste, transportation, transit, infrastructure performance, and municipal data needs. |
| [LGBC Chapter 9: Human Services](./sources/lgbc/chapter-9-human-services.md) | Chapter 9 review notes for parks, recreation, libraries, museums, public health, social housing, responsibility mapping, and municipal data needs. |
| [LGBC Chapter 11: Labour Relations](./sources/lgbc/chapter-11-labour-relations.md) | Chapter 11 review notes for workforce, unionization, bargaining units, labour relations, service-continuity context, and municipal data needs. |
| [LGBC Benchmark And Process Candidate Catalogue](./sources/lgbc/benchmark-process-candidate-catalogue.md) | Phase 5 catalogue summary for 86 source-derived benchmark and process candidates from reviewed LGBC chapters. |
| [LGBC Charlottetown Prototype Mapping](./sources/lgbc/charlottetown-prototype-mapping.md) | Phase 6 first-pass mapping from 86 LGBC candidates to known Charlottetown source families and source gaps. |
| [LGBC Charlottetown Planning And Land-Use Dataset Review](./sources/lgbc/charlottetown-planning-land-use-dataset-review.md) | Phase 6 dataset-readiness review for 10 planning and land-use candidates against Charlottetown zoning, OCP, map, parcel, and meeting sources. |

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
| [AWS deployment](./implementation/aws-deployment.md) | Repeatable single-host AWS EC2 deployment and local-to-AWS database synchronization workflow for the web application and PostGIS database. |
| [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) | Plan and timeline for replacing the current web page with the design-kit-based Charlottetown parcel lookup, map explorer, city-view map, and zoning comparison demo. |
| [Parcel 3D LIDAR terrain plan](./implementation/parcel-3d-lidar-terrain-plan.md) | Preprocessing and integration plan for using PEI LIDAR as terrain and building-height inputs in the parcel 3D viewer. |
| [Charlottetown terrain DEM pipeline](./implementation/charlottetown-terrain-dem-pipeline.md) | First repeatable PDAL/GDAL pipeline design for producing a bare-earth DEM from PEI COPC LIDAR tiles. |
| [Storm surge demo plan](./implementation/storm-surge-demo-plan.md) | Demo-only Charlottetown tidal and storm-surge visualization scope, controls, source assumptions, limits, and upgrade path. |
| [Municipal budget data model](./implementation/municipal-budget-data-model.md) | Initial scalable schema design for raw and normalized municipal operating, capital, rate, tax, debt, reserve, and funding data. |
| [Release help and MCP plan](./implementation/release-help-and-mcp-plan.md) | Implementation pattern for release-facing contextual help, the `help` schema, web help APIs, and the repo-local `mdopendata-mcp` package. |
| [Agenda package ingestion contract](./implementation/agenda-package-ingestion-contract.md) | Package JSON, logical-document ordering, agenda-item binding, template discovery, and approval gates. |

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
