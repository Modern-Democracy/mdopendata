---
type: source
tags:
  - source
  - municipal-governance
  - charlottetown
  - planning
  - zoning
  - lgbc
updated: 2026-05-25
---

This page records the Phase 6 planning and land-use dataset review for LGBC Chapter 10 candidates against known Charlottetown source artifacts.

# Charlottetown Planning And Land-Use Dataset Review

## Source Locator

| Field | Value |
| --- | --- |
| Source candidate catalogue | `data/sources/lgbc/benchmark_process_candidate_catalogue.json` |
| Prototype mapping | `data/sources/lgbc/charlottetown_prototype_mapping.json` |
| Dataset review | `data/sources/lgbc/charlottetown_planning_land_use_dataset_review.json` |
| Reviewed domain | `planning_land_use` |
| Reviewed candidates | 10 |

## Readiness Findings

| Dataset readiness | Count | Meaning |
| --- | ---: | --- |
| `dataset_ready_for_source_completeness_review` | 2 | Current repository sources can support a source-completeness review, not a public performance metric. |
| `partial_dataset_ready` | 2 | Relevant source families exist, but required process or cost datasets are missing. |
| `sample_dataset_ready_only` | 1 | A sample council-package trace exists, but no complete process-history dataset is identified. |
| `source_gap_for_required_dataset` | 5 | Bylaw or map context exists, but the candidate's required operating/process dataset is not identified. |

No planning and land-use candidate is ready for public scoring, cross-municipality comparison, or outcome claims.

## Candidate-Level Review

| Candidate | Dataset readiness | Current use |
| --- | --- | --- |
| Planning document completeness review | `dataset_ready_for_source_completeness_review` | Source-completeness review across OCP, future land use, current zoning, draft zoning, maps, extracted JSON, and spatial layers. |
| Zoning complexity inventory | `dataset_ready_for_source_completeness_review` | Source-completeness review using current/draft zone files, code crosswalks, parcel relationships, and section-equivalence outputs. |
| Rezoning and variance process trace | `sample_dataset_ready_only` | Sample trace for the May 12, 2026 council package rezoning items only. |
| Regulatory-cost visibility review | `partial_dataset_ready` | Gap analysis for costs and affected-party records; not ready for calculation. |
| Regional/strategic planning relationship map | `partial_dataset_ready` | OCP and future land use context exists; referral and consultation datasets are missing. |
| Building permit process benchmark | `source_gap_for_required_dataset` | Required permit and inspection datasets are not identified. |
| Subdivision approval process trace | `source_gap_for_required_dataset` | Required subdivision application and approving-officer datasets are not identified. |
| Development cost charge linkage review | `source_gap_for_required_dataset` | Required DCC, reserve, capital-cost, and development-approval linkage datasets are not identified. |
| Bylaw enforcement workflow inventory | `source_gap_for_required_dataset` | Required complaint, inspection, notice, ticket, penalty, court, and compliance datasets are not identified. |
| Land-use regulation outcome caution | `source_gap_for_required_dataset` | Required housing, land supply, approval timeline, and infrastructure availability datasets are not identified. |

## Available Source Families

| Source family | Repository evidence | Supports |
| --- | --- | --- |
| Current zoning bylaw extraction | `docs/charlottetown/charlottetown-zoning-bylaw.pdf`, `data/zoning/charlottetown/source-manifest.json`, `data/zoning/charlottetown/` | Planning document completeness, zoning complexity, process-text context. |
| Draft zoning bylaw extraction | `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf`, `data/zoning/charlottetown-draft/source-manifest.json`, `data/zoning/charlottetown-draft/` | Planning document completeness, zoning complexity, draft process context. |
| OCP and future land use | `docs/charlottetown/ocp/Charlottetown Official Plan 2026.pdf`, `docs/charlottetown/ocp/Future Land Use Map - October 24 2025.pdf` | Planning document completeness and strategic planning context. |
| Spatial zoning and parcels | `maps/Charlottetown Zoning Map - March 9, 2026.pdf`, `maps/pei/CHTWN_Zoning_Boundaries.geojson`, `maps/pei/CHTWN_Draft_Zoning_Boundaries.geojson`, `maps/pei/CHTWN_Parcel_Map.geojson` | Zoning complexity, parcel-zone relationships, map source completeness. |
| Council meeting rezoning sample | `data/council-meetings/charlottetown/2026-05-12-regular-council/` | Sample rezoning trace and public-meeting context. |

## Primary Gaps

The next source discovery pass should target:

- Complete permit applications.
- Building inspection records.
- Subdivision applications and approving-officer decisions.
- Development cost charge bylaws, reserves, capital project links, and approval links.
- Bylaw enforcement complaints, inspections, notices, tickets, penalties, court actions, and compliance outcomes.
- Approval timeline datasets.
- Housing, land supply, infrastructure availability, and market indicators for outcome-context analysis.

## Review Limits

This review validates source-family readiness only. It does not approve a metric, route, schema, scoring model, or public comparison.

The current strongest use is source-completeness review for planning documents and zoning complexity. Process performance and outcome analysis remain blocked by missing datasets.

## Sources

- `data/sources/lgbc/charlottetown_planning_land_use_dataset_review.json`
- [LGBC Chapter 10: Regulatory And Development Functions](./chapter-10-regulatory-development-functions.md)
- [LGBC Charlottetown Prototype Mapping](./charlottetown-prototype-mapping.md)
- [Charlottetown workstream context](../../charlottetown/topics/workstream-context.md)
- [Unified zoning ingestion plan](../../charlottetown/topics/unified-zoning-ingestion-plan.md)
- [Council and committee meetings](../../council-committee-meetings/README.md)
