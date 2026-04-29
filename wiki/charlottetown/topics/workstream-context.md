---
type: project
tags:
  - charlottetown
  - zoning
  - workstream
updated: 2026-04-29
---

This page records the active Charlottetown zoning workstream context formerly kept in root startup instructions.

# Charlottetown Workstream Context

## Current Focus

The active workstream is the City of Charlottetown current and draft zoning bylaw extraction, including associated zoning maps, parcel layer, and street map.

The active plan is unified relational and PostGIS ingestion for current and draft bylaw comparison, revision-aware draft updates, approved spatial layers, and later text-vector support. The schema migration and initial JSON importer are implemented. Section-equivalence candidate review has been reopened after QA found accepted mismatches and blank-side comparisons; the next active unified-ingestion work is review of the regenerated section-equivalence ledger.

## Purpose

The current purpose is to enable parcel and neighbourhood comparison between current and draft Charlottetown zoning, with outputs suitable for later PostGIS/QGIS use and a future public web front end.

## Source and Output Paths

Use source material under `docs/charlottetown` unless the task explicitly names another source.

Write current zoning bylaw extraction outputs under `data/zoning/charlottetown`.

Write draft zoning bylaw extraction outputs under `data/zoning/charlottetown-draft`.

## Wiki Maintenance

For substantive Charlottetown extraction, validation, comparison, GIS, QA, or planning work, maintain `wiki/charlottetown` when the work creates or changes durable knowledge.

Follow `wiki/charlottetown/README.md`, update `wiki/charlottetown/index.md` for added or materially changed wiki pages, and append `wiki/charlottetown/log.md` in the same change.

Do not add wiki entries for purely mechanical edits, failed experiments, or transient command output unless they affect durable project knowledge.

## Draft Validation Timeline

For the post-fix Charlottetown draft zoning validation rebaseline, keep `plan/charlottetown-draft-zoning-validation-rebaseline-timeline.md` up to date until the plan is complete.

Retain `plan/chalottetown-draft-zoning-timeline.md` as the historical completed validation record from the prior pass.

Update its active phase, overall status, current progress, and phase statuses whenever work advances, pauses, is blocked, or completes.

## Unified Ingestion Timeline

For the Charlottetown unified zoning ingestion workstream, keep `plan/charlottetown-unified-zoning-ingestion-timeline.md` up to date until the unified ingestion plan is complete or superseded.

Update its active phase, overall status, current progress, and phase statuses whenever schema, importer, section-equivalence, spatial, vector, or deferred-coverage work advances, pauses, is blocked, or completes.

## Sources

- [Charlottetown wiki guide](../README.md)
- [Unified zoning ingestion plan](./unified-zoning-ingestion-plan.md)
- [Unified zoning ingestion timeline](../../../plan/charlottetown-unified-zoning-ingestion-timeline.md)
- [Draft zoning validation rebaseline timeline](../../../plan/charlottetown-draft-zoning-validation-rebaseline-timeline.md)
- [Historical draft zoning validation timeline](../../../plan/chalottetown-draft-zoning-timeline.md)
- [Draft zoning validation plan](../../../plan/chalottetown-draft-zoning-plan.md)
