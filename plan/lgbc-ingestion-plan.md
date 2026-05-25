---
status: phase_4_chapters_1_6_7_10_and_12_complete
updated: 2026-05-25
source: docs/LGBC-All.pdf
---

# Local Government in British Columbia Ingestion Plan

This plan defines a staged ingestion path for `docs/LGBC-All.pdf`, using the book as a prototype source for municipal-performance benchmarks, analysis workflows, and portal evaluation processes.

## Objective

Create a source-faithful data index of the book before interpreting chapter content. Use that index to support chapter-by-chapter review, benchmark discovery, and later process design for target municipalities, starting with Charlottetown.

## Source Profile

| Field | Value |
| --- | --- |
| Source file | `docs/LGBC-All.pdf` |
| Title | `Local Government in British Columbia - 4th Edition` |
| Authors | Robert L. Bish; Eric G. Clemens |
| Publisher | Union of British Columbia Municipalities |
| PDF pages | 250 |
| Visible content pages | front matter plus pages 1-231 |
| PDF properties | OCR-derived, untagged, unencrypted, letter size |
| SHA-256 | `57D8C1762E354BA871B4408C85FD6B76A8F895A8926BDA0951C21600D16F9D8E` |

## Required First Outputs

| Output | Path | Purpose |
| --- | --- | --- |
| Source summary | `wiki/sources/lgbc-local-government-bc.md` | Durable wiki entry for source scope, structure, and project relevance. |
| Structure index | `data/sources/lgbc/structure_index.json` | Machine-readable chapters, sections, exhibits, appendix, notes, bibliography, and page locators. |
| Review workbook | `data/sources/lgbc/chapter_review_queue.json` | Chapter-by-chapter decision queue for source interpretation and downstream process design. |
| Extraction notes | `data/sources/lgbc/extraction_notes.md` | Known OCR, pagination, table, exhibit, and provenance issues. |

Do not create normalized benchmark schemas until the structure index is complete and at least Chapter 6 has been reviewed.

## Book Structure Index

| Unit | Title | Visible start page | Priority | Initial municipal-portal relevance |
| --- | --- | ---: | --- | --- |
| Preface | Preface | xi | Low | Source intent and limits. |
| Chapter 1 | Introduction | 1 | High | Fiscal equivalence, local government definition, evaluation criteria. |
| Chapter 2 | The Provincial Setting | 11 | Medium | Province-local relations and oversight context. |
| Chapter 3 | Municipal Governments | 21 | High | Municipal structure, functions, governance, elections, reporting. |
| Chapter 4 | Regional District Governments | 45 | Medium | Intermunicipal service scale and regional governance. |
| Chapter 5 | Other Local Governments | 65 | Medium | Special-purpose local bodies and service fragmentation. |
| Chapter 6 | Service Delivery | 81 | Critical | Performance measures, benchmarking, program evaluation, cost-benefit analysis. |
| Chapter 7 | Protective Services | 97 | High | Police, fire, emergency service benchmark candidates. |
| Chapter 8 | Engineering Services | 115 | High | Water, wastewater, solid waste, transportation, transit benchmark candidates. |
| Chapter 9 | Human Services | 137 | Medium | Education, parks, libraries, museums, public health, housing context. |
| Chapter 10 | Regulatory and Development Functions | 151 | Critical | Planning, zoning, subdivision, enforcement, fiscal equivalence. |
| Chapter 11 | Labour Relations | 173 | Medium | Workforce, unionization, bargaining-unit context. |
| Chapter 12 | Finance | 179 | Critical | Revenue, property tax, fees, transfers, debt, reserves. |
| Chapter 13 | Concluding Observations | 207 | Medium | System-level synthesis. |
| Appendix | First Nations Governments | 209 | Medium | Relationship context and jurisdiction caveats. |
| Back matter | Chapter Notes, legislation index, bibliography, acknowledgements | 223 | Medium | Citation graph and source discovery. |

## Exhibit Index Seed

The exhibit list should be extracted as structured records with exhibit id, title, visible page, chapter, inferred topic, and extraction status.

Initial high-value exhibit families:

| Exhibit family | Examples | Relevance |
| --- | --- | --- |
| Government inventory | `1-1`, `4-1`, `4-2`, `5-1`, `5-3`, `5-5` | Entity counts, structural comparison, government-type vocabulary. |
| Municipal and regional functions | `3-2`, `4-4`, `5-4` | Service-domain mapping for municipal datasets. |
| Expenditures and revenue | `3-3`, `4-5`, `12-1`, `12-2`, `12-3` | Budget and finance benchmark prototypes. |
| Governance and organization | `3-4` through `3-7`, `4-6`, `4-7` | Council, committee, election, and board-process context. |
| Performance measures | `7-2`, `8-1`, `8-2`, `8-3` | Direct seed material for municipal-performance indicators. |
| Planning and land use | `10-1`, `10-2`, `10-3` | Planning and zoning process comparison. |
| Labour relations | `11-1` through `11-4` | Workforce and bargaining context. |
| Property tax and fees | `12-4`, `12-5` | Tax-class and service-charge vocabulary. |

## Ingestion Phases

### Phase 1: Source Registration

Status: complete as of 2026-05-25.

Create `data/sources/lgbc/` and store raw extraction artifacts separately from normalized outputs:

- `pdfinfo.txt`
- `pages_text/NNN.txt`
- `full_text_layout.txt`
- `structure_index.json`
- `exhibit_index.json`
- `chapter_review_queue.json`
- `extraction_notes.md`

Acceptance criteria:

- File hash and PDF metadata are recorded.
- PDF page count and visible page locator scheme are documented.
- OCR limitations are listed before any semantic extraction.

### Phase 2: Structure Extraction

Status: complete as of 2026-05-25.

Extract the table of contents, chapter headings, section headings, exhibit list, appendix headings, notes, bibliography, and legislation index.

Acceptance criteria:

- Every chapter and section has a stable id.
- Each record stores source title text exactly as extracted and a normalized display title.
- Each record includes PDF page and visible page when available.
- Ambiguous or OCR-damaged headings are flagged for review instead of silently corrected.

### Phase 3: Chapter Review Queue

Status: complete as of 2026-05-25.

Create a review queue with one record per chapter or back-matter unit.

Each queue record should include:

- `unit_id`
- `title`
- `page_range`
- `review_priority`
- `portal_domains`
- `candidate_benchmark_topics`
- `required_municipal_inputs`
- `output_decision`
- `review_status`
- `notes`

Acceptance criteria:

- Chapters 1, 6, 10, and 12 are marked as first-pass priority.
- Chapters 7 and 8 are marked as service-benchmark priority.
- Records avoid deciding schema or scoring methods before chapter review.

### Phase 4: Prototype Chapter Analysis

Status: Chapters 6, 1, 10, 12, and 7 complete as of 2026-05-25.

Review chapters in this order:

1. Chapter 6, because it defines service performance, benchmarking, program evaluation, and cost-benefit framing.
2. Chapter 1, because it defines fiscal equivalence and general evaluation criteria.
3. Chapter 10, because it maps directly to planning, zoning, subdivision, and enforcement workflows.
4. Chapter 12, because it maps to budgets, taxes, fees, debt, and reserves.
5. Chapters 7 and 8, because they contain concrete service-performance exhibit candidates.

For each chapter, produce a chapter note under `wiki/sources/lgbc/` only after review. Use one page per chapter if summaries become long.

Acceptance criteria:

- Keep source claims separate from proposed portal metrics.
- Identify required municipal datasets for each candidate metric.
- Mark every benchmark as `direct_source`, `derived_from_source`, or `requires_external_standard`.

### Phase 5: Benchmark And Process Candidate Catalogue

Build a catalogue after the priority chapters are reviewed.

Candidate record fields:

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

Initial comparison modes:

- longitudinal comparison within one municipality
- cross-sectional comparison across municipalities
- benchmark against stated local objective
- benchmark against external standard
- fiscal-equivalence review
- source-completeness review

### Phase 6: Charlottetown Prototype Mapping

Map benchmark candidates to currently available or planned Charlottetown data sources.

Initial target domains:

- planning and land use
- council and committee meetings
- budgets and finance
- maps and parcels
- protective services
- engineering services
- public reporting and annual reports

Acceptance criteria:

- Do not mark a candidate as implementable without identifying available source data.
- Record missing datasets as portal gaps, not metric failures.
- Separate municipal-performance evaluation from source-ingestion completeness evaluation.

## Stop Conditions

Stop and route back to Business Analyst when:

- a chapter contains concepts that do not fit the current portal domain inventory;
- a proposed metric would imply a scoring model or public ranking;
- a benchmark requires external standards not present in the book;
- a BC-specific governance concept is being generalized to Charlottetown or PEI without explicit review;
- OCR or pagination defects prevent stable source locators.

Stop and route to Coding Architect before:

- creating a new database schema for benchmark candidates;
- adding new ingestion workflow protocols;
- integrating benchmark outputs into public portal routes.

## Open Decisions

| Decision | Default for now |
| --- | --- |
| Should the first structure index be JSON only or JSON plus CSV? | JSON only, with CSV export deferred. |
| Should benchmark candidates become a database schema? | No, keep as source-derived JSON until reviewed. |
| Should BC-specific institutional material be adapted to PEI immediately? | No, first preserve source concepts, then map differences. |
| Should the portal expose municipal performance scores? | No, expose evidence, context, and candidate measures before scoring. |

## Verification

After Phase 2, verify:

- count of chapters equals 13;
- count of listed numbered chapter sections equals 78;
- count of listed exhibits equals 41;
- all extracted exhibit ids match the visible exhibit list;
- no generated locator points outside the 250 PDF pages.

After each chapter review, finish with QA Reviewer and update the relevant wiki source page, root wiki index if pages are added, and root wiki log.
