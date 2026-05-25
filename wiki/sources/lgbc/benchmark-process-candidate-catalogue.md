---
type: source
tags:
  - source
  - municipal-governance
  - benchmarks
  - process-candidates
  - lgbc
updated: 2026-05-25
---

This page summarizes the Phase 5 benchmark and process candidate catalogue generated from reviewed `docs/LGBC-All.pdf` chapter notes.

# Benchmark And Process Candidate Catalogue

## Source Locator

| Field | Value |
| --- | --- |
| Source file | `docs/LGBC-All.pdf` |
| Catalogue file | `data/sources/lgbc/benchmark_process_candidate_catalogue.json` |
| Source chapter notes | Chapters 1, 6, 7, 8, 9, 10, 11, and 12 |
| Catalogue status | Candidate catalogue created; pending remaining chapter/back-matter review and Phase 6 Charlottetown mapping |

## Catalogue Shape

The catalogue uses the Phase 5 fields defined in [Local Government in British Columbia ingestion plan](../../../plan/lgbc-ingestion-plan.md):

- `candidate_id`
- `source_unit_id`
- `source_locator`
- `domain`
- `benchmark_or_process_name`
- `source_basis`
- `municipal_inputs_required`
- `calculation_or_review_method`
- `comparison_mode`
- `known_limitations`
- `charlottetown_readiness`
- `status`

The generated file also includes `source_basis_type` so direct-source candidates can be separated from derived candidates during QA and Phase 6 mapping.

## Candidate Counts

| Group | Count |
| --- | ---: |
| Total candidates | 86 |
| Direct-source candidates | 84 |
| Derived-from-source candidates | 2 |
| Chapter 1 governance candidates | 8 |
| Chapter 6 service-delivery candidates | 12 |
| Chapter 7 protective-services candidates | 12 |
| Chapter 8 engineering-services candidates | 12 |
| Chapter 9 human-services candidates | 12 |
| Chapter 10 planning and land-use candidates | 10 |
| Chapter 11 labour-relations candidates | 8 |
| Chapter 12 finance candidates | 12 |

## Domain Coverage

| Domain | Source unit | Count | Initial use |
| --- | --- | ---: | --- |
| Governance | Chapter 1 | 8 | Fiscal equivalence, collective-problem classification, decision-channel mapping. |
| Service delivery | Chapter 6 | 12 | Production fit, performance-measure inventory, evaluation readiness. |
| Protective services | Chapter 7 | 12 | Police, fire, emergency preparedness, response, and context cautions. |
| Engineering services | Chapter 8 | 12 | Water, wastewater, solid waste, transportation, transit, and infrastructure review. |
| Human services | Chapter 9 | 12 | Parks, libraries, museums, public health, housing, and responsibility mapping. |
| Planning and land use | Chapter 10 | 10 | Planning, zoning, permits, subdivision, enforcement, and regulatory-cost review. |
| Labour relations | Chapter 11 | 8 | Workforce, unionization, bargaining units, labour-risk, and service-continuity context. |
| Finance | Chapter 12 | 12 | Revenue, tax, fee, transfer, debt, reserve, and fiscal-equivalence review. |

## Use Rules

The catalogue is an analysis queue, not a normalized database schema, public metric set, or scoring model.

Every candidate remains `requires_phase_6_mapping` for Charlottetown readiness until local source datasets, jurisdiction differences, data availability, and disclosure limits are reviewed.

Cross-municipality, external-standard, statutory-limit, and public-facing interpretations require additional source review before use.

## Review Limits

The catalogue is generated only from chapters already reviewed in Phase 4. Chapters 2, 3, 4, 5, 13, the First Nations appendix, chapter notes, legislation index, bibliography, and acknowledgements remain outside the catalogue until reviewed.

The source is BC-specific and from 2008. PEI or Charlottetown adaptation requires separate jurisdiction mapping.

## Sources

- `data/sources/lgbc/benchmark_process_candidate_catalogue.json`
- [Local Government in British Columbia source summary](../lgbc-local-government-bc.md)
- [Chapter 1: Introduction](./chapter-1-introduction.md)
- [Chapter 6: Service Delivery](./chapter-6-service-delivery.md)
- [Chapter 7: Protective Services](./chapter-7-protective-services.md)
- [Chapter 8: Engineering Services](./chapter-8-engineering-services.md)
- [Chapter 9: Human Services](./chapter-9-human-services.md)
- [Chapter 10: Regulatory And Development Functions](./chapter-10-regulatory-development-functions.md)
- [Chapter 11: Labour Relations](./chapter-11-labour-relations.md)
- [Chapter 12: Finance](./chapter-12-finance.md)
- [Local Government in British Columbia ingestion plan](../../../plan/lgbc-ingestion-plan.md)
