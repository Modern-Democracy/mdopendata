---
type: status
tags:
  - budget
  - normalization
  - prior-year
  - phase-1
updated: 2026-07-09
---

This page records the Phase 1 period-label, section-continuation, operating-detail relationship, capital-project-profile-identity, capital-project-alias, and candidate-disposition review start for the 2025/2026 and 2024/2025 Charlottetown budget normalization work.

# Prior-Year Normalized Import Phase 1 Status

## Scope

Phase 1 has started for period-label, section-continuation, operating-detail relationship, capital-project-profile-identity, capital-project-alias, and candidate-disposition review. No normalized facts, database imports, compatibility records, or publication snapshots were created.

Generated artifacts:

| Artifact | Purpose |
| --- | --- |
| `scripts/build-budget-prior-year-phase1-review.py` | Builds the prior-year Phase 1 period-label and section-continuation review package. |
| `data/budget/charlottetown/prior-year-phase-1-review-package.json` | Combined review package for both prior-year documents. |
| `data/budget/charlottetown/2025-2026/period-label-review.json` | 2025/2026 period-label decisions and exclusions. |
| `data/budget/charlottetown/2025-2026/section-continuation-review.json` | 2025/2026 section-continuation review decisions. |
| `data/budget/charlottetown/2025-2026/operating-detail-relationship-review.json` | 2025/2026 overview-to-detail operating relationship decisions. |
| `data/budget/charlottetown/2025-2026/capital-project-profile-identity-review.json` | 2025/2026 wrapped title and `Project:` identity review for capital profiles. |
| `data/budget/charlottetown/2025-2026/capital-project-alias-review.json` | 2025/2026 capital project alias decisions for prior-year profiles. |
| `data/budget/charlottetown/2025-2026/candidate-disposition-review.json` | 2025/2026 candidate dispositions after Phase 1 period and continuation decisions. |
| `data/budget/charlottetown/2024-2025/period-label-review.json` | 2024/2025 period-label decisions and exclusions. |
| `data/budget/charlottetown/2024-2025/section-continuation-review.json` | 2024/2025 section-continuation review decisions. |
| `data/budget/charlottetown/2024-2025/operating-detail-relationship-review.json` | 2024/2025 total-in-detail operating relationship decisions. |
| `data/budget/charlottetown/2024-2025/capital-project-profile-identity-review.json` | 2024/2025 wrapped title and `Project:` identity review for capital profiles. |
| `data/budget/charlottetown/2024-2025/capital-project-alias-review.json` | 2024/2025 capital project alias decisions for prior-year profiles. |
| `data/budget/charlottetown/2024-2025/candidate-disposition-review.json` | 2024/2025 candidate dispositions after Phase 1 period and continuation decisions. |

## Period-Label Review

| Document | Mapped labels | Excluded false-positive labels | Review-blocked labels |
| --- | ---: | ---: | ---: |
| 2025/2026 | 7 | 20 | 0 |
| 2024/2025 | 6 | 8 | 0 |

The review maps fiscal-year labels and aliases to fiscal-period date ranges and default amount-type roles. Single calendar-year tokens from tax effective dates, Civic Centre line labels, capital profile text, and debt maturity years are excluded from document-period mapping and remain available to their own later review streams.

## Section-Continuation Review

| Document | Duplicate summaries | Proposed section groups | Do-not-merge profile groups | Review-blocked groups |
| --- | ---: | ---: | ---: | ---: |
| 2025/2026 | 2 | 23 | 5 | 0 |
| 2024/2025 | 0 | 10 | 4 | 0 |

Operating, facility, and capital schedule continuation groups are retained as proposed source-section groups for row-level normalization. Adjacent capital project profile groups are explicitly marked `do_not_merge_profiles`; those pages remain separate project records and are deferred to capital project alias review.

The 2025/2026 operating detail groups are not independent departmental summaries. They are multi-page `Detailed Breakdown of Budget Item` tables organized by the expense categories from the immediately preceding departmental overview table. The overview table carries the section totals, while the detail pages carry line items. The 2024/2025 operating budget shows a different pattern: department detail tables generally contain their own totals and do not have a separate preceding overview table. Phase 2 normalization must detect and encode the applicable pattern before generating reconciliation inputs.

## Operating-Detail Relationship Review

| Document | Presentation pattern | Relationships | Total source | Line-item source | Normalized target |
| --- | --- | ---: | --- | --- | --- |
| 2025/2026 | `overview_to_detail` | 14 | Overview table | Detail tables | `department_operating_statement_with_line_items` |
| 2024/2025 | `total_in_detail` | 16 | Detail table | Detail table | `department_operating_statement_with_line_items` |

Both source patterns must normalize to the same target structure. The 2025/2026 review records detail pages plus the associated overview table or overview table group; the 2024/2025 review records the detail table as both the line-item and total source.

The 2025/2026 overview pages 14 and 15 contain a pie chart followed by the backing data table. Matching the reviewed 2026/2027 page 18 and 19 precedent, these pages are classified as `duplicate_summary` for normalization. The chart visual is duplicate presentation for human readers and is ignored; later user-interface charts should be reproduced from reviewed normalized facts rather than extracted from the source PDF chart graphic.

## Universal Duplicate-Visualization Rule

Budget documents commonly repeat the same numbers across visualizations, overview pages, and backing tables to help human readers understand the source. For normalization, duplicate visualization or overview fact sets must be classified as `duplicate_summary` and excluded from normalized facts unless they are approved summary/detail relationships, such as department summaries versus line-item department or project tables. The public UI should reproduce charts from reviewed normalized facts, not from extracted source chart graphics.

## Candidate Dispositions

| Document | Normalize | Duplicate summary | Review-blocked |
| --- | ---: | ---: | ---: |
| 2025/2026 | 107 | 2 | 5 |
| 2024/2025 | 53 | 0 | 5 |
| Total | 160 | 2 | 10 |

The remaining `review_blocked` records are limited to five 2024/2025 capital project alias split/merge questions, one 2025/2026 capital profile title/project mismatch, two tax/rate formula operand records, and two debt instrument identity or maturity records. Period-label-only and continuation-only blockers have been resolved or intentionally excluded from document-period mapping.

## Capital Project Profile Identity Review

| Document | Profile identities reviewed | Identity review-blocked | Wrapped/incomplete title guesses | Wrapped or differing `Project:` values |
| --- | ---: | ---: | ---: | ---: |
| 2025/2026 | 22 | 1 | 3 | 4 |
| 2024/2025 | 20 | 0 | 11 | 14 |
| Total | 42 | 1 | 14 | 18 |

Capital profile alias decisions use reconstructed source titles and `Project:` values from raw page text instead of `title_guess` alone. The remaining identity-blocked record is 2025/2026 page 130: the heading is `Public Works Small Fleet Replacement`, but the source `Project:` line says `Parks and Recreation Small Fleet Replacement`. That contradiction is left blocked because choosing either value silently would corrupt project identity.

The line-wrapping check is a durable extraction requirement, not a one-off prior-year correction. Large-font titles, department names, and project names, especially when placed in narrow columns, are prone to wrapping and must be reconstructed from adjacent wrapped lines before normalization, because truncated headings can produce wrong statement labels, wrong project aliases, and false cross-year matches.

## Capital Project Alias Review

| Document | Mapped to existing 2026/2027 key | Document-only identity | Review-blocked |
| --- | ---: | ---: | ---: |
| 2025/2026 | 20 | 2 | 1 |
| 2024/2025 | 9 | 6 | 5 |
| Total | 29 | 8 | 6 |

`mapped_existing` records use an approved 2026/2027 capital project key where the source label and profile text support the cross-year identity. `document_only` records create stable prior-year identities without claiming cross-period compatibility. The remaining blocked records are 2025/2026 page 130 and 2024/2025 pages 47, 66, 67, 68, and 74, where the profile identity is contradictory or appears to combine, split, or overlap later Public Works, Water and Sewer, fleet, facility, or infrastructure project keys.

## Remaining Phase 1 Work

- Tax/rate formula operand decisions remain unresolved.
- Debt instrument identity and maturity decisions remain unresolved.
- Capital project identity and split/merge decisions remain unresolved for one 2025/2026 profile and five 2024/2025 profiles.

## Gate Status

Gate status: Phase 1 is partially complete. Period-label, section-continuation, capital-project-profile-identity, capital-project-alias, and candidate-disposition artifacts exist, but no review-blocked candidate may enter manifest generation until the remaining identity, split/merge, tax/rate, and debt decisions are recorded.

## Sources

- [Prior-year normalized import gap report](./prior-year-normalized-import-gap-report.md)
- [Week 5 normalized mapping review](./week-5-normalized-mapping-review.md)
- [Budget ingestion refactor tracker](./budget-ingestion-refactor-tracker.md)
- `data/budget/charlottetown/prior-year-phase-1-review-package.json`
