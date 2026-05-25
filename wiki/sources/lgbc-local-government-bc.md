---
type: source
tags:
  - source
  - municipal-governance
  - performance
  - ingestion
updated: 2026-05-25
---

This page summarizes `docs/LGBC-All.pdf` as a source for municipal-governance structure, service-performance concepts, and benchmark discovery.

# Local Government in British Columbia

## Source

| Field | Value |
| --- | --- |
| Source file | `docs/LGBC-All.pdf` |
| Title | `Local Government in British Columbia - 4th Edition` |
| Authors | Robert L. Bish; Eric G. Clemens |
| Publisher | Union of British Columbia Municipalities |
| Copyright edition | 2008 UBCM |
| PDF pages | 250 |
| Source condition | OCR-derived, untagged PDF with extractable layout text |
| SHA-256 | `57D8C1762E354BA871B4408C85FD6B76A8F895A8926BDA0951C21600D16F9D8E` |

## Project Relevance

The book is a prototype source for turning municipal-governance concepts into portal workflows, municipal dataset checklists, and performance-analysis candidates.

The strongest initial relevance is:

- Chapter 1 for fiscal equivalence and evaluation criteria.
- Chapter 6 for service performance, benchmarking, program evaluation, and cost-benefit framing.
- Chapter 10 for planning, zoning, subdivision, enforcement, and land-use regulation.
- Chapter 12 for municipal finance, revenue, property taxation, service charges, transfers, debt, and reserves.
- Chapters 7 and 8 for protective-service and engineering-service performance-measure examples.
- Chapters 9 and 11 for human-service responsibility mapping and workforce/labour-relations context.

## Structure

The source contains front matter, 13 chapters, an appendix on First Nations governments, chapter notes, legislation/regulation index, selected bibliography, and acknowledgements.

Priority chapters for first-pass analysis:

| Chapter | Title | Visible start page | Reason |
| --- | --- | ---: | --- |
| 1 | Introduction | 1 | Defines local government, fiscal equivalence, and general evaluation criteria. |
| 6 | Service Delivery | 81 | Defines service performance, benchmarking, program evaluation, and cost-benefit analysis. |
| 10 | Regulatory and Development Functions | 151 | Connects directly to planning, zoning, permits, subdivision, and enforcement workflows. |
| 12 | Finance | 179 | Connects directly to budget, revenue, tax, fee, debt, and reserve ingestion. |
| 7 | Protective Services | 97 | Contains police, fire, and emergency service performance candidates. |
| 8 | Engineering Services | 115 | Contains water, wastewater, solid waste, transportation, and transit performance candidates. |

## Exhibit Families

The source has an exhibit list with 41 listed exhibits. High-value exhibit families include local-government inventories, municipal and regional functions, expenditure and revenue tables, service-performance measures, planning and land-use exhibits, labour relations tables, and property-tax/service-charge vocabulary.

Direct benchmark seed exhibits include:

- `7-2` Fire Service Performance Measures.
- `8-1` Waterworks Utility Performance Measures.
- `8-2` Transportation Service Performance Measures.
- `8-3` Public Transit Service Performance Measures.

## Ingestion Plan

The active plan is [Local Government in British Columbia ingestion plan](../../plan/lgbc-ingestion-plan.md).

Phase 3 chapter review queue setup is complete under `data/sources/lgbc/`. The registered artifacts are `pdfinfo.txt`, `full_text_layout.txt`, `pages_text/`, `structure_index.json`, `exhibit_index.json`, `chapter_review_queue.json`, and `extraction_notes.md`.

The extracted structure index contains 13 chapters, 78 numbered chapter sections, 12 appendix sections, and 4 back-matter units. The extracted exhibit index contains 41 listed exhibits.

The chapter review queue contains 18 records: 13 chapters, 1 appendix, and 4 back-matter units. The first-pass priority order was Chapter 6, Chapter 1, Chapter 10, Chapter 12, Chapter 7, and Chapter 8. Completed Phase 4 reviews are [Chapter 6: Service Delivery](./lgbc/chapter-6-service-delivery.md), [Chapter 1: Introduction](./lgbc/chapter-1-introduction.md), [Chapter 10: Regulatory And Development Functions](./lgbc/chapter-10-regulatory-development-functions.md), [Chapter 12: Finance](./lgbc/chapter-12-finance.md), [Chapter 7: Protective Services](./lgbc/chapter-7-protective-services.md), [Chapter 8: Engineering Services](./lgbc/chapter-8-engineering-services.md), [Chapter 9: Human Services](./lgbc/chapter-9-human-services.md), and [Chapter 11: Labour Relations](./lgbc/chapter-11-labour-relations.md).

Phase 5 has started with [LGBC Benchmark And Process Candidate Catalogue](./lgbc/benchmark-process-candidate-catalogue.md), which summarizes `data/sources/lgbc/benchmark_process_candidate_catalogue.json`. The initial catalogue contains 86 source-derived candidates from Chapters 1, 6, 7, 8, 9, 10, 11, and 12.

Benchmark schemas, scoring models, and portal routes should remain deferred until Phase 6 Charlottetown source mapping is complete.

## Caveats

The source is British Columbia-specific and should not be generalized to Charlottetown or PEI without an explicit jurisdiction-mapping review.

The PDF is OCR-derived and untagged. Stable locators should include both PDF page and visible page when available.

The source is from 2008. It can support governance and evaluation prototypes, but current legal requirements, municipal counts, and contemporary standards require separate source verification before public-facing claims.

## Sources

- `docs/LGBC-All.pdf`
- [Local Government in British Columbia ingestion plan](../../plan/lgbc-ingestion-plan.md)
- [Municipal portal product purpose](../product/municipal-portal-purpose.md)
- [Municipal portal domain inventory](../product/municipal-portal-domain-inventory.md)
