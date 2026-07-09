---
type: implementation
tags:
  - budget
  - import
  - normalization
  - data-quality
updated: 2026-07-09
---

This report defines the step-through plan and current blockers for normalizing and importing the 2025/2026 and 2024/2025 Charlottetown budget documents to the same reviewed database level as 2026/2027.

# Prior-Year Normalized Import Gap Report

## Objective

Normalize and import the 2025/2026 and 2024/2025 budget documents with reviewed facts, source-cell provenance, reconciliations, review issues, compatibility records where approved, idempotent import evidence, and source-fidelity QA.

The target completion level is the current 2026/2027 standard: reviewed normalization, deterministic manifest, controlled normalized import, idempotence rerun, source-fidelity QA, zero publication snapshots, and no public compatibility claim without explicit review.

## Current State

| Document | Raw status | Normalized status | Immediate gate |
| --- | --- | --- | --- |
| 2025/2026 | 150 source pages, 114 full-2 raw tables, 3,871 raw rows, 5,182 detected values in artifacts. | 0 normalized facts approved or imported for this document. | Approve document-specific mappings for 78 review-blocked candidates. |
| 2024/2025 | 88 source pages, 58 full-2 raw tables, 1,701 raw rows, 2,019 detected values in artifacts. | 0 normalized facts approved or imported for this document. | Approve document-specific mappings for 37 review-blocked candidates. |

Publication snapshots must remain at zero throughout this work.

## Blocker Summary

| Document | Candidate-equivalent | Review-blocked | Raw-blocked |
| --- | ---: | ---: | ---: |
| 2025/2026 | 36 | 78 | 0 |
| 2024/2025 | 21 | 37 | 0 |

`candidate_equivalent` means the profile family and period labels fit baseline review inputs. It is not approval to import normalized facts.

## Blockers By Family

| Document | Family | Candidate-equivalent | Review-blocked | Main review need |
| --- | --- | ---: | ---: | --- |
| 2025/2026 | operating_statement | 15 | 7 | Section grouping, duplicate summaries, period labels. |
| 2025/2026 | operating_detail | 14 | 35 | Section grouping and summary/detail role review. |
| 2025/2026 | facility_operating_statement | 1 | 3 | Facility layout and period mapping review. |
| 2025/2026 | capital_budget_schedule | 6 | 6 | Schedule grouping and gross/funding/net treatment. |
| 2025/2026 | capital_project_profile | 0 | 23 | Cross-year project alias review. |
| 2025/2026 | tax_assessment_rate | 0 | 2 | Formula operand and period-label review. |
| 2025/2026 | debt_schedule | 0 | 2 | Debt instrument identity and maturity review. |
| 2024/2025 | operating_statement | 15 | 7 | Section grouping and period labels. |
| 2024/2025 | facility_operating_statement | 1 | 3 | Facility layout and period mapping review. |
| 2024/2025 | capital_budget_schedule | 5 | 7 | Schedule grouping and period labels. |
| 2024/2025 | capital_project_profile | 0 | 20 | Cross-year project alias review. |

## Blockers By Reason

| Document | Blocker | Count | Pages to review |
| --- | --- | ---: | --- |
| 2025/2026 | Continuation membership requires section-level review. | 68 | 15-16, 18, 26-29, 32, 34-36, 40-41, 45-46, 50-51, 55, 59, 62, 64-70, 74-75, 79-81, 85-87, 92-95, 100-101, 104-106, 109, 111, 113, 115, 117, 119-123, 125-135, 138-140, 143 |
| 2025/2026 | Project alias requires cross-year review. | 23 | 110-111, 114-115, 118-120, 124-135, 137-140 |
| 2025/2026 | Assessment/rate operands require formula review. | 2 | 19, 145 |
| 2025/2026 | Debt instrument identity and maturity labels require review. | 2 | 147, 149 |
| 2025/2026 | Period labels require review. | 2 | 19, 97 |
| 2024/2025 | Continuation membership requires section-level review. | 29 | 15-16, 22, 35, 46, 49, 51, 53, 55-59, 63, 65-69, 71-72, 74-76, 79-81, 85-86 |
| 2024/2025 | Project alias requires cross-year review. | 20 | 47, 50-51, 54-59, 61, 64-69, 73-76 |
| 2024/2025 | Period labels require review. | 2 | 62, 82 |

## User Review Queue

Review should proceed in this order because later import artifacts depend on these decisions.

### 1. Period Labels

Decision required: map every raw period label to a fiscal period date range and amount type role, or mark it non-importable.

Known prior-year label blockers:

| Document | Page | Raw label issue |
| --- | ---: | --- |
| 2025/2026 | 19 | Period label `2025` requires review. |
| 2025/2026 | 97 | Period label `2023` requires review. |
| 2024/2025 | 62 | Period label `2024` requires review. |
| 2024/2025 | 82 | Period labels `2023`, `2024`, and `2025` require review. |

Output needed: approved document-period mapping table for each document.

### 2. Section Continuation Groups

Decision required: identify which pages belong to the same reviewed source section, which pages are duplicate summaries, and which pages are non-financial context.

Review focus:

- 2025/2026 operating pages 15-106
- 2025/2026 capital and appendix pages 109-149
- 2024/2025 operating pages 15-35 and 79-86
- 2024/2025 capital pages 46-76

Output needed: section inventory and continuation decision artifacts matching the 2026/2027 pattern.

### 3. Capital Project Aliases

Decision required: map each raw prior-year capital project label/profile to a stable cross-year capital project identity, or mark it unmatched, split, merged, or document-only.

Review focus:

- 2025/2026 capital profile pages 110-140
- 2024/2025 capital profile pages 47-76

Output needed: reviewed `capital_project_alias` decisions and compatibility notes.

### 4. Tax And Rate Formula Operands

Decision required: identify assessment bases, rates, denominators, reported outputs, and formula applicability.

Review focus:

- 2025/2026 pages 19 and 145
- 2024/2025 page 62 if the capital schedule period label affects amount role rather than formula treatment

Output needed: approved operand roles and reconciliation formulas, or explicit exclusion.

### 5. Debt Identity

Decision required: map each debt row to a stable debt instrument identity and maturity treatment, or mark it document-only.

Review focus:

- 2025/2026 pages 147 and 149

Output needed: debt instrument mapping with balance, principal, interest, and maturity evidence.

## Implementation Phases

### Phase 1: Freeze Prior-Year Mapping Contracts

Work:

- create document-period mapping tables for 2025/2026 and 2024/2025
- create section inventories and continuation decisions
- create candidate dispositions for normalize, duplicate summary, non-financial, review-blocked, or excluded
- record project alias, tax/rate, and debt review decisions

Gate: no review-blocked candidate may enter manifest generation unless it has a mapped review issue that intentionally blocks import.

### Phase 2: Build Normalization Artifacts

Work:

- generate row-mapping artifacts for approved operating, facility, capital, tax/rate, and debt sections
- preserve raw labels, row IDs, source value IDs, value states, units, and review statuses
- produce unresolved-review reports for any section that cannot be approved

Gate: every approved fact candidate must have source evidence, period role, amount type, unit, entity, and aggregation role.

### Phase 3: Build Deterministic Manifests

Work:

- generate one normalized manifest per document
- generate expected counts by record type, statement family, period, amount type, unit, and value state
- detect identity collisions and missing source links
- represent project aliases, project profile links, debt facts, and compatibility candidates

Gate: manifest hashes are stable across reruns; all unresolved decisions are explicit.

### Phase 4: Build Reconciliation Catalogues

Work:

- operating revenue, expense, and net checks
- departmental summary/detail checks where source structure supports them
- facility operating checks
- capital gross, funding deduction, and net checks
- tax/rate formula checks where operands are approved
- debt principal plus interest checks where asserted by the source

Gate: every reconciliation input resolves to a manifest fact key; every failed check creates or links a review issue.

### Phase 5: Dry-Run Import

Work:

- adapt the normalized importer to accept prior-year manifests or create controlled prior-year import scripts
- validate source hashes, manifest hashes, expected counts, source-cell links, and reconciliation inputs before mutation
- produce deterministic dry-run plans

Gate: dry-run plans are deterministic, no publication snapshot is created, and changed-content conflicts fail visibly.

### Phase 6: Controlled Import And Idempotence

Work:

- capture pre-import database state
- import each approved prior-year manifest transactionally
- rerun import to prove idempotence
- compare database counts with manifest counts

Gate: second run creates no duplicate logical records, reports no content conflict, and publication snapshots remain zero.

### Phase 7: Source-Fidelity QA

Work:

- validate every fact source link against raw row/value artifacts and database cells
- verify dash-versus-zero, signs, units, fiscal periods, amount types, aggregation roles, entity scope, capital aliases, and debt links
- run family-stratified checks comparable to 2026/2027 Phase 7

Gate: zero source-fidelity mismatches; all reconciliation failures have approved review issue status; zero publication snapshots.

### Phase 8: Compatibility Review

Work:

- create compatibility records for approved cross-period facts only
- preserve restated values as separate reported observations
- document coverage differences and non-comparable facts

Gate: no cross-period comparison is exposed without approved identity, period, entity, line semantics, amount type, unit, and aggregation role.

## Stop Conditions

Stop and request review when:

- a reused 2026/2027 mapper would classify a materially different section
- a raw period label cannot be mapped to fiscal dates and an amount role
- a capital project label may refer to a split, merged, renamed, or unmatched project
- a debt row cannot be tied to a stable instrument identity
- tax/rate operands are missing or visually similar but semantically different
- a reconciliation failure has no source-supported explanation
- source-cell provenance does not match the approved raw value
- any import path would create a publication snapshot

## Completion Criteria

Both prior-year documents are complete when:

- all candidates have reviewed dispositions
- all approved normalized facts have source-cell provenance
- deterministic manifests and reconciliation catalogues exist for both documents
- normalized database imports are controlled, transactional, and idempotent
- source-fidelity QA passes with zero mismatches
- review issues record every approved exception
- publication snapshots remain zero
- compatibility records exist only for explicitly approved cross-period identities
- the refactor tracker has been updated with lessons learned

## Sources

- [2026/2027 normalized import gap report](./2026-normalized-import-gap-report.md)
- [2026/2027 normalized import Phase 7 status](./2026-normalized-import-phase-7-status.md)
- [Week 5 raw ingestion status](./week-5-raw-ingestion-status.md)
- [Week 5 normalized mapping review](./week-5-normalized-mapping-review.md)
- [Budget ingestion refactor tracker](./budget-ingestion-refactor-tracker.md)
- `data/budget/charlottetown/week-5-normalized-mapping-review.json`
- `data/budget/charlottetown/2025-2026/raw-tables/raw_row_value_summary.json`
- `data/budget/charlottetown/2024-2025/raw-tables/raw_row_value_summary.json`
