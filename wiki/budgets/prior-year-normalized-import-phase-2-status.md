---
type: status
tags:
  - budget
  - normalization
  - prior-year
  - phase-2
updated: 2026-07-09
---

This page records the initial source-linked row-mapping inputs for prior-year Phase 2 normalization.

# Prior-Year Normalized Import Phase 2 Status

Phase 2 has generated deterministic mapping inputs for every Phase 1 `normalize` candidate. The artifacts preserve raw row text, labels, value IDs, parsed values, value kinds, candidate family, section key, and source table identity. They create no normalized facts, manifests, imports, compatibility records, or publication snapshots.

| Document | Candidates | Raw rows | Status |
| --- | ---: | ---: | --- |
| 2024/2025 | 58 | 1,701 | Row-semantic review required |
| 2025/2026 | 112 | 3,808 | Row-semantic review required |

The first family-specific approvals are complete: 14 standard 2024/2025 City department operating tables now map detail and total rows to the City reporting entity, CAD, and the reviewed 2023/2024 budget, 2023/2024 forecast, and 2024/2025 budget period roles. Their 514 applicable rows are approved.

All 43 capital project profiles are approved as narrative-only fields, covering 288 rows in 2025/2026 and 2024/2025. Their dates, quantities, and narrative numbers remain source text and cannot create financial facts.

The remaining 4,707 rows retain `unreviewed` semantics and `needs_review` status. Phase 2 must still approve each applicable row's hierarchy, aggregation role, amount type, unit, reporting entity, and period role before it can become a normalized fact candidate.

## Artifacts

- `scripts/build-budget-prior-year-phase2-artifacts.py`
- `data/budget/charlottetown/prior-year-phase-2-row-mapping-package.json`
- `data/budget/charlottetown/2024-2025/phase-2-row-mapping-input.json`
- `data/budget/charlottetown/2025-2026/phase-2-row-mapping-input.json`

## Sources

- [Prior-year Phase 1 status](./prior-year-normalized-import-phase-1-status.md)
- [Prior-year normalized import gap report](./prior-year-normalized-import-gap-report.md)
