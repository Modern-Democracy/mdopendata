---
type: status
tags:
  - budget
  - normalized-mapping
  - charlottetown
  - week-5
updated: 2026-07-09
---

# Week 5 Normalized Mapping Review

Week 5 normalized mapping review classified prior-year source candidates for template fit, raw-readiness, and review blockers without authorizing normalized import.

## Scope

The review covers the 2025/2026 and 2024/2025 Charlottetown budget PDFs. It uses the profile inventories, full-2 raw manifests, and raw row/value summaries generated during Week 5 raw ingestion.

The review does not create normalized facts, compatibility records, publication facts, or publication snapshots.

## Review Artifact

| Artifact | Purpose |
| --- | --- |
| `scripts/build-budget-week5-normalized-mapping-review.py` | Builds deterministic prior-year mapping-review classifications. |
| `data/budget/charlottetown/week-5-normalized-mapping-review.json` | Records document counts, table-level dispositions, raw gaps, and review groups. |

## Document Results

| Document | Profile candidates | full-2 raw tables | Candidate equivalent | Review-blocked | Raw-blocked |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2025/2026 | 114 | 114 | 36 | 78 | 0 |
| 2024/2025 | 58 | 58 | 21 | 37 | 0 |

`candidate_equivalent` means profile family and period labels fit baseline review inputs. It does not approve fact publication.

## Raw Coverage Resolution

| Document | Raw-blocked pages | Reason |
| --- | --- | --- |
| 2025/2026 | None remaining | Supplemental full-2 raw tables were added for pages 14-17. |
| 2024/2025 | None remaining | Supplemental full-2 raw tables were added for pages 14-16, 62-63, and 78-86. |

All profile candidates now have matching full-2 raw table coverage.

## Review Blockers

The remaining review-blocked candidates are blocked by at least one of:

- continuation membership requiring section-level review
- capital project aliases requiring cross-year review
- debt instrument identity and maturity labels requiring review
- tax assessment/rate operands requiring formula review
- period labels requiring explicit source-label mapping

## Gate Status

Normalized prior-year import is not ready. The next gate is to approve document-specific mappings for period labels, section continuation groups, project aliases, debt identities, tax/rate operands, and cross-period compatibility.

## Sources

- [Week 5 raw ingestion status](./week-5-raw-ingestion-status.md)
- [Implementation and test plan](./implementation-plan.md)
- `data/budget/charlottetown/week-5-normalized-mapping-review.json`
