---
type: status
tags:
  - budget
  - normalization
  - prior-year
  - phase-1
updated: 2026-07-11
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
| `data/budget/charlottetown/capital-project-registry.json` | Three-document municipality-scoped project registry and budget-reference evidence. |
| `data/budget/charlottetown/2025-2026/period-label-review.json` | 2025/2026 period-label decisions and exclusions. |
| `data/budget/charlottetown/2025-2026/section-continuation-review.json` | 2025/2026 section-continuation review decisions. |
| `data/budget/charlottetown/2025-2026/operating-detail-relationship-review.json` | 2025/2026 overview-to-detail operating relationship decisions. |
| `data/budget/charlottetown/2025-2026/capital-project-profile-identity-review.json` | 2025/2026 wrapped title and `Project:` identity review for capital profiles. |
| `data/budget/charlottetown/2025-2026/capital-project-alias-review.json` | 2025/2026 capital project alias decisions for prior-year profiles. |
| `data/budget/charlottetown/2025-2026/tax-rate-formula-review.json` | 2025/2026 rate declaration and property-tax formula decisions. |
| `data/budget/charlottetown/2025-2026/debt-identity-review.json` | 2025/2026 entity-scoped debt instrument and planned-debt decisions. |
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
| 2024/2025 | 2 | 9 | 4 | 0 |

Operating, facility, and capital schedule continuation groups are retained as proposed source-section groups for row-level normalization. Adjacent capital project profile groups are explicitly marked `do_not_merge_profiles`; those pages remain separate project records and are deferred to capital project alias review.

The 2025/2026 operating detail groups are not independent departmental summaries. They are multi-page `Detailed Breakdown of Budget Item` tables organized by the expense categories from the immediately preceding departmental overview table. The overview table carries the section totals, while the detail pages carry line items. The 2024/2025 operating budget shows a different pattern: department detail tables generally contain their own totals and do not have a separate preceding overview table. Phase 2 normalization must detect and encode the applicable pattern before generating reconciliation inputs.

## Operating-Detail Relationship Review

| Document | Presentation pattern | Relationships | Total source | Line-item source | Normalized target |
| --- | --- | ---: | --- | --- | --- |
| 2025/2026 | `overview_to_detail` | 14 | Overview table | Detail tables | `department_operating_statement_with_line_items` |
| 2024/2025 | `total_in_detail` | 16 | Detail table | Detail table | `department_operating_statement_with_line_items` |

Both source patterns must normalize to the same target structure. The 2025/2026 review records detail pages plus the associated overview table or overview table group; the 2024/2025 review records the detail table as both the line-item and total source.

The 2025/2026 overview pages 14 and 15 contain a pie chart followed by the backing data table. Matching the reviewed 2026/2027 page 18 and 19 precedent, these pages are classified as `duplicate_summary` for normalization. The chart visual is duplicate presentation for human readers and is ignored; later user-interface charts should be reproduced from reviewed normalized facts rather than extracted from the source PDF chart graphic.

The 2024/2025 bubble-chart pages 15 and 16 are also `duplicate_summary`: page 15 presents revenue and page 16 presents expenses already reported in the operating-budget summary on page 14. Their raw evidence is retained, but neither page can create normalized facts or unresolved row-review work.

## Universal Duplicate-Visualization Rule

Budget documents commonly repeat the same numbers across visualizations, overview pages, and backing tables to help human readers understand the source. For normalization, duplicate visualization or overview fact sets must be classified as `duplicate_summary` and excluded from normalized facts unless they are approved summary/detail relationships, such as department summaries versus line-item department or project tables. The public UI should reproduce charts from reviewed normalized facts, not from extracted source chart graphics.

## Candidate Dispositions

| Document | Normalize | Duplicate summary | Review-blocked |
| --- | ---: | ---: | ---: |
| 2025/2026 | 112 | 2 | 0 |
| 2024/2025 | 56 | 2 | 0 |
| Total | 168 | 4 | 0 |

Period-label-only and continuation-only blockers have been resolved or intentionally excluded from document-period mapping. No Phase 1 candidate remains review-blocked.

## Tax/Rate Formula Review

The 2025/2026 page 19 rate declarations are approved as rate facts with their source denominators and effective-date context. They do not contain assessment-to-revenue formulas and must not be used to derive revenue.

The 22 property-tax expressions on page 145 are approved as `assessment × rate ÷ 100`, with reported revenue rounded to the nearest dollar. Each rounded calculated result matches its reported revenue. Assessment, rate, and reported revenue remain separate reported facts with source-cell evidence; the formula is retained for reconciliation only.

## Debt Identity Review

The 2025/2026 City and Water and Sewer schedules are approved as separate reporting-entity debt statements. The review identifies 20 document-scoped debt instruments by entity, source label, lender/type where reported, and maturity year where reported. `Matuing` is preserved in raw text and corrected only in the normalized label. The City `Capital Leases` row remains an entity-scoped instrument with unknown lender and maturity.

The two `New Debt` rows are approved as document-period planned-debt buckets, not stable debt instruments, because the source supplies no lender, issue year, or maturity. They may carry reported balance and interest facts but cannot create a cross-period instrument identity.

## Capital Project Profile Identity Review

| Document | Profile identities reviewed | Identity review-blocked | Wrapped/incomplete title guesses | Wrapped or differing `Project:` values |
| --- | ---: | ---: | ---: | ---: |
| 2025/2026 | 22 | 0 | 3 | 4 |
| 2024/2025 | 20 | 0 | 11 | 14 |
| Total | 42 | 1 | 14 | 18 |

Capital profile alias decisions use reconstructed source titles and `Project:` values from raw page text instead of `title_guess` alone. For 2025/2026 page 130, the heading and description identify Public Works Small Fleet Replacement while the `Project:` line says Parks and Recreation. The review retains the conflicting source field but approves the heading-and-description identity.

The line-wrapping check is a durable extraction requirement, not a one-off prior-year correction. Large-font titles, department names, and project names, especially when placed in narrow columns, are prone to wrapping and must be reconstructed from adjacent wrapped lines before normalization, because truncated headings can produce wrong statement labels, wrong project aliases, and false cross-year matches.

## Capital Project Alias Review

| Document | Approved project reference | Document-only identity | Review-blocked |
| --- | ---: | ---: | ---: |
| 2025/2026 | 21 | 2 | 0 |
| 2024/2025 | 9 | 11 | 0 |
| Total | 30 | 13 | 0 |

Approved records reference a municipality-scoped project identity using reviewed source evidence. `document_only` records create a valid project identity with a single budget reference and do not claim cross-period compatibility. The three-document registry contains 58 projects and 67 references: 20 from 2024/2025, 23 from 2025/2026, and 24 from 2026/2027. The five 2024/2025 combined or joint profiles remain separate document-scoped identities because the source does not allocate their budgets between components. This preserves the reported project without inventing split, merge, or later-year links.

## Gate Status

Gate status: Phase 1 is complete. Period-label, section-continuation, tax/rate, debt, capital-project-profile-identity, capital-project-alias, candidate-disposition, and three-document project-reference artifacts are approved for manifest generation.

## Sources

- [Prior-year normalized import gap report](./prior-year-normalized-import-gap-report.md)
- [Week 5 normalized mapping review](./week-5-normalized-mapping-review.md)
- [Budget ingestion refactor tracker](./budget-ingestion-refactor-tracker.md)
- `data/budget/charlottetown/prior-year-phase-1-review-package.json`
