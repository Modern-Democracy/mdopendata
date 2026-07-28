---
type: implementation
tags:
  - extraction
  - pdf
  - charlottetown
  - budget
  - quality-assurance
updated: 2026-07-16
---

This page defines the frozen baseline, representative source controls, implementation sequence, and acceptance criteria for the first staged PDF inventory and extraction shadow pilot.

# Charlottetown 2026/2027 Staged Extraction Shadow Pilot

## Scope

The pilot tests the [staged PDF inventory and extraction architecture](./staged-pdf-inventory-extraction-architecture.md) against the known published source `docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf`.

It must write versioned shadow artifacts beside the current budget artifacts. It must not mutate current raw or normalized files, write PostgreSQL, change snapshot membership, or publish any result.

## Frozen Baseline

The source control is SHA-256 `d926634427e80aa2b06b6425bdbb117424fe53567ae344980cd10791f8e39bac`, 154 PDF pages, and database source document ID 9.

Existing reviewed controls include 116 canonical candidates in 31 sections, 114 raw source tables, 3,233 raw rows, 3,092 detected source values, 112 `normalize` dispositions, three `duplicate_summary` dispositions, and one `non_financial` disposition.

Published snapshot 1 contains 2,165 distinct observations for this document. Published snapshot 3 contains 2,290 distinct observations after 125 reviewed property-tax and City-debt observations were recovered. The pilot must preserve snapshot 3 source coverage and explain the historical 125-observation difference rather than treating snapshot 1 as the final oracle.

## Representative Regression Controls

| PDF pages | Observed pattern | Required result |
| --- | --- | --- |
| 10 | Budget explanation formatted text with financial terms | Formatted-text block; no financial row extraction. |
| 18-19 | Revenue and expense charts with backing data tables | Preserve blocks; reviewed duplicate-summary treatment prevents double counting. |
| 20 | Consolidated City and Water and Sewer operating statement | One authoritative statement group with three physical financial columns and distinct entity scopes. |
| 21-22 | Detailed revenue schedule continued across pages with repeated headers | One logical group with preserved physical pages, repeated-header evidence, and uninterrupted row hierarchy. |
| 23 | Property-tax and utility rates | Separate rate group; per-100, per-day, and per-volume units must not inherit currency semantics. |
| 28-33 | City Government overview followed by detail pages | Reviewed summary-detail relationship; overview totals and detail lines remain distinct without double counting. |
| 87-92 | Public Works and Municipal Buildings overview and multi-page detail | Preserve two entities on page 87, continued detail, the page 91 within-page transition, and page 92 completion. |
| 105 | Bell Aliant Centre statement | Facility reporting entity remains separate from City grant line content. |
| 110 | Consolidated capital rollup | City and utility scopes, current and prior columns, gross amounts, partner funding, and net totals remain distinct. |
| 111 | Capital schedule | Parenthesized external partner funding retains sign and funding-deduction evidence. |
| 112 | Capital project profile | Narrative years and quantities remain non-financial; profile fields remain structured context. |
| 149 | Property-tax calculation | Assessment, rate, calculated revenue, subtotals, and grant retain separate units and row roles. |
| 151 | City debt schedule | Balance, principal, interest, maturity-in-label, and reported total controls remain aligned. |
| 152 | Appendix divider | Divider block terminates City debt context and produces no financial values. |
| 153 | Water and Sewer debt schedule | New entity group after the divider; it must not continue or merge with page 151. |

## Acceptance Criteria

- The source hash and all 154 pages match the registered source.
- Every page has evidence and inventory dispositions.
- Every detected financial block belongs to exactly one primary logical group or an approved exclusion.
- No logical group crosses a material entity, period, unit, hierarchy, source-authority, or purpose boundary.
- All representative controls pass through direct source-image and artifact comparison.
- Two clean shadow runs are canonically identical.
- All 2,290 snapshot 3 observations are matched or have exact source-linked discrepancy records.
- No current source-linked observation silently changes value, sign, unit, period, entity, statement scope, or provenance.
- The 125 later-recovered tax and debt observations do not regress.
- Duplicate summaries remain excluded from additive publication paths.
- Narrative and profile negative controls do not become financial observations.
- The shadow run performs zero PostgreSQL writes and creates no publication snapshot.
- Review actions round-trip to deterministic artifacts and invalidate dependent approvals when an upstream hash changes.

## Stage 0 Result

Stage 0 source evidence is complete under `data/budget/charlottetown/2026-2027/staged-pdf/v1/stage-0/`.

| Control | Result |
| --- | --- |
| Source identity | SHA-256 `d926634427e80aa2b06b6425bdbb117424fe53567ae344980cd10791f8e39bac`; 154 pages. |
| Canonical artifact | `source-evidence.json`; SHA-256 `d24885a23ebf33a63d9e09273a5335cdbef45fd727dcf93d6c23b5bbe9c3eb2e`. |
| Evidence package | 154 renders at 144 DPI, 154 thumbnails at 72 DPI, 154 embedded-word files, and one OCR-word file. |
| OCR fallback | PDF page 24 had four embedded words; Tesseract produced fallback evidence with mean confidence `0.864112`. |
| Dispositions | 154 complete, zero text-deficient, zero blocked, and zero `needs_review`. |
| Package size | 464 files and 43,550,929 bytes. |
| Determinism | A clean second run returned `unchanged` with the same artifact and file hashes. |
| Visual QA | Pages 24, 87, 149, and 153 confirmed divider, dense statement, tax, and debt render fidelity. |

The generator validates the proposed artifact before atomically creating the output directory. It refuses to overwrite any existing package whose file hashes differ.

## Stage 1 Result

Stage 1 block inventory is complete under `data/budget/charlottetown/2026-2027/staged-pdf/v1/stage-1/`.

| Control | Result |
| --- | --- |
| Canonical artifact | Mutable reviewed `block-inventory.json`; table-grid migration checkpoint SHA-256 `f880de6838c16cf9fa5ef5f82a4633ad26c9613a9ca55b9a1074260e2eabe8c2` at decision 39. Later hashes are recorded by review events. |
| Coverage | 154 page dispositions, 440 generated candidates, and one reviewer-added chart block, accounted for exactly once. |
| Candidate types | 143 titles, 135 page numbers, 77 tables, 67 formatted-text blocks, 2 tables of contents, 8 dividers, and 8 footers. No automated block is classified as a repeating header. |
| Internal structure | 709 proposed formatted-text regions; 77 table grids containing 10,063 typed cells inferred from Stage 0 word geometry. |
| Financial candidates | 101 conservative candidates; all remain proposed and require later structural review. |
| Review queue | PDF page 24 is `needs_review` because its block geometry comes from OCR; the other 153 pages are inventoried. |
| Regression controls | Page 10 remains formatted text and non-financial; pages 18 and 19 retain financial table candidates; page 112 retains formatted-text profile content with financial-candidate context. |
| Determinism | An identical rerun returns `unchanged`; conflicting existing output is refused. |

The generator consumes the validated Stage 0 artifact and its recorded word sidecars. It does not consume the legacy page or table inventories, create logical multi-page groups, approve candidates, normalize values, query PostgreSQL, or change publication state.

## Implementation Sequence

1. Completed: define and validate JSON Schemas for source evidence, blocks, groups, templates, applications, decisions, and parity reports.
2. Completed: build and validate the deterministic Stage 0 source-evidence generator using embedded text and targeted OCR fallback.
3. Completed: generate Stage 1 candidate blocks and expose selectable, resizable, reclassifiable, deletable, and drawable overlays in the [local inventory-review UI](./staged-pdf-inventory-review-ui-plan.md). Each change is validated and recorded in the append-only review artifact.
4. Review Stage 1 bounds, including complete table column headers and row-label regions, without assuming every continuation page has a header.
5. Completed: add 77 Stage 2 logical groups and group-driven adapters around the reviewed raw and normalized extraction logic.
6. Completed: export 2,290 shadow observations, compare a canonical natural-key, value, state, review, and source-provenance set digest, and verify the same semantic and source-link sets against live published Snapshot 3 under a read-only transaction.
7. Run and resolve the representative controls, then the complete 154-page corpus.
8. Propose any importer or database changes only after shadow parity passes.
9. Test a non-Charlottetown document before promoting any template to cross-municipality scope.

## Phase 7 Structural Parity Result

The version 2 Phase 7 core compares 154 source-page records, 154 page dispositions, 442 blocks, one relationship, 105 shadow review events, one complete repository observation-set digest, and one live publication-state comparison. The 858-record report has 753 exact matches, zero missing records, zero changed records, 104 approved provenance-only review shifts, and one explicit schema-migration event.

Stage 2 now contains 77 logical groups with exact primary ownership for every financial candidate block. Its write-free shadow export contains 2,165 approved manifest observations plus 76 property-tax and 49 City-debt observations regenerated from reviewed page 149 and page 151 raw rows. All 2,290 records have unique natural keys and logical-group mappings.

Repository-baseline observation parity passes by a canonical full-set digest. Live published Snapshot 3 contains 6,381 observations across documents 7, 8, and 9; its document-9 subset contains exactly 2,290 unique semantic records, 2,290 unique source links, and zero missing links. Its canonical semantic and source digests exactly match Stage 2. Live verification is complete with zero database writes. The active-workspace transition is approved, version 2 is the local reviewer default and downstream structural-extraction input, the final parity report passes with zero blockers, and version 1 remains an explicit rollback.

## Required Evidence Package

- frozen source, artifact, database, and publication baseline hashes
- complete page, block, group, template-application, and review-decision artifacts
- representative-control report with exact PDF page and block locators
- two-run canonical hash comparison
- raw coverage and exclusion comparison
- 2,290-observation natural-key parity report
- source-linked disposition for every missing, extra, changed, or provenance-shifted observation
- proof of zero database writes and unchanged publication snapshots

## Sources

- [Staged PDF inventory and extraction architecture](./staged-pdf-inventory-extraction-architecture.md)
- [Staged PDF artifact JSON Schemas](./staged-pdf-artifact-json-schemas.md)
- [Staged PDF inventory review UI plan](./staged-pdf-inventory-review-ui-plan.md)
- [Municipal budget requirements](../budgets/requirements.md)
- [Charlottetown three-year budget source profile](../charlottetown/sources/budget-three-year-source-profile.md)
- [2026/2027 normalization status](../budgets/2026-normalization-status.md)
- [Budget content and observation redesign status](../budgets/content-and-observation-redesign-status.md)
- `docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf`, PDF pages 10, 18-23, 28-33, 87-92, 105, 110-112, 149, and 151-153
- `data/budget/charlottetown/2026-2027/`
