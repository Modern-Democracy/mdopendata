# Charlottetown Draft Zoning Phase 6 Final QA Summary

Date: 2026-04-28

## Scope

This final QA pass covers regenerated Charlottetown draft zoning bylaw outputs under `data/zoning/charlottetown-draft` for the April 9, 2026 draft source PDF.

## Acceptance Claim

Phase 6 is accepted if regeneration completes, schema validation passes, issue counts remain closed, code-table drift remains resolved, and residual schedule-map limits are documented.

## Checks Run

| Check | Evidence | Result |
| --- | --- | --- |
| Regeneration and schema validation | `.venv/Scripts/python.exe scripts/regenerate-charlottetown-draft-zoning-bylaw.py` exited 0 | Pass |
| Review-flag scan | 34 generated JSON outputs scanned | 0 files, 0 rows |
| `needs_review` scan | 34 generated JSON outputs scanned | 0 files, 0 entries |
| Issue ledger | `plan/chalottetown-draft-zoning-issue-ledger.csv` | Header only, 0 open rows |
| Code-table report | `data/zoning/charlottetown-draft/code-table-match-report.json` | 0 term new codes, 0 use new codes |
| Output coverage | `data/zoning/charlottetown-draft/source-manifest.json` | 20 zone files, 10 supporting files, 4 schedule files |

## Before and After Counts

| Inventory | Baseline | Final |
| --- | ---: | ---: |
| JSON files with `review_flags` | 33 | 0 |
| Total `review_flags` | 139 | 0 |
| JSON files with `confidence: "needs_review"` | 26 | 0 |
| Total `needs_review` entries | 130 | 0 |
| Unmatched code-table phrases | 16 | 0 |
| Refreshed 2026-04-24 `review_flags` | 158 | 0 |
| Refreshed 2026-04-24 `needs_review` entries | 86 | 0 |

## Code-Table Outcome

Final code-table counts:

- Term exact matches: 13
- Term semantic matches: 0
- Term new codes surfaced: 0
- Use exact matches: 97
- Use semantic matches: 11
- Use new codes surfaced: 0

The final reviewed draft-origin use codes are `cluster_housing` and `seniors_housing`. Other repeated draft phrases were either matched semantically, split into existing base uses, or removed as extraction artifacts during earlier phases.

## Residual Limits

Schedules A through D are preserved as page-text map artifacts with map-reference metadata only. They are not digitized spatial zoning layers and require later spatial QA before parcel overlays, zoning-boundary comparison, or downstream GIS use.

## Conclusion

Phase 6 final QA passes. The draft validation and normalization pass satisfies the acceptance criteria in `plan/chalottetown-draft-zoning-plan.md`.
