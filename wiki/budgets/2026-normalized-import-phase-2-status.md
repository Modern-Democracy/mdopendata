---
type: implementation
tags:
  - budget
  - import
  - normalization
  - review
updated: 2026-07-08
---

This page records the deterministic manifest build and the blocking semantic mappings discovered before Gate 3.

# 2026/2027 Normalized Import Phase 2 Status

## Result

The deterministic generator produced a review manifest containing 1,163 line items, 2,165 facts, and 2,165 source-value references with zero identity collisions. Gate 3 is approved: 23 capital profiles link to 24 schedule projects, and Vehicle Equipment is retained as one reviewed narrative-only exception pending City clarification.

No SQL, database, raw artifact, or existing normalization mapping was changed.

## Generated Artifacts

| Artifact | Purpose |
| --- | --- |
| `scripts/build-budget-2026-normalized-manifest.py` | Deterministic family-adapter generator with fail-fast vocabulary and identity checks |
| `data/budget/charlottetown/2026-2027/normalized-import-manifest.json` | Canonical Gate 3 review manifest |
| `data/budget/charlottetown/2026-2027/normalized-import-manifest-report.json` | Count matrix, vocabulary counts, collision results, extension-link coverage, and unresolved decisions |

The canonical manifest hash is regenerated with each reviewed artifact change; the current hash is recorded in `normalized-import-manifest-report.json`.

## Count Matrix

| Record | Count |
| --- | ---: |
| Source tables used | 85 |
| Reporting entities | 4 |
| Organization units | 13 |
| Funds | 0 |
| Fiscal periods | 3 |
| Table-specific document periods | 128 |
| Statements | 30 |
| Line items | 1,163 |
| Facts | 2,165 |
| Fact source-value references | 2,165 |
| Capital projects from reviewed detail rows | 169 |
| Capital project facts | 192 |
| Capital profiles | 24 |
| Debt instruments | 10 |
| Debt facts | 30 |

## Vocabulary Results

- Amount types: 1,419 `budget`, 452 `forecast`, 222 `gross`, 11 `funding_deduction`, 13 `net`, 15 `actual`, and 11 each of `balance`, `principal`, and `interest`.
- Units: 2,150 `cad`, 8 `cad_per_100_assessed`, 3 `cad_per_year`, 2 `cad_per_day`, and 2 `cad_per_cubic_metre`.
- Value states: 2,124 `reported` and 41 `dash_unresolved`.
- Identity collisions: zero.

## Wrapped Field Repair

Capital profile fields are now reconstructed from explicit row boundaries rather than one physical line:

- title: all rows before `Department:`
- department: `Department:` value and continuation rows before `Project:`
- project: `Project:` value and continuation rows before `Project Description`

Confirmed repairs include `Active Transportation (AT) Infrastructure`, `East Royalty Landfill Old Road and Active Transportation Pathway`, and `North River Road & Capital Drive Intersection Upgrades`. Regeneration changed only `capital-project-profile-mapping.json` within the normalization directory.

## Capital Profile Alias Review

Eleven profiles match schedule project keys exactly, including `Specialized Equipment`. Twelve approved aliases and composite mappings resolve the remaining linked profiles. Vehicle Equipment is the only profile without a schedule project link.

- `downtown-tree-planters`
- `east-royalty-landfill-old-road-and-active-transportation-pathway`
- `euston-st-redevelopment`
- `investigative-tools-and-technology`
- `multi-use-outdoor-facility`
- `new-city-website`
- `new-fire-station`
- `new-sidewalk-construction`
- `north-river-road-capital-drive-intersection-upgrades`
- `public-transit-buses`
- `sherwood-recreation-hall-upgrades`
- `vehicle-equipment`
- `victoria-park-ev-charger`

The manifest retains these profiles with `capital_project_key = null`. The regenerated report includes up to five similarity-ranked candidates restricted to the reviewed schedule section. Similarity is review evidence only and does not assign an alias.

## Gate 3 Status

**Status:** approved 2026-07-08.

Verified outcome:

- 23 profiles linked to 24 stable capital project keys
- one reviewed Vehicle Equipment exception with no inferred amount or project link
- zero unresolved decisions
- zero identity collisions
- 1,163 lines and 2,165 facts
- deterministic equality across two consecutive builds

## Proposed Alias Decisions

### Direct Aliases

| Profile project | Proposed schedule project | Evidence |
| --- | --- | --- |
| `Downtown Tree Planters` | `Downtown Tree Pits and Planters` | Same downtown tree-planter scope; profile describes raised concrete tree planters. |
| `Victoria Park EV Charger` | `EV Charger` | Same EV-charger project; profile supplies the Victoria Park location. |
| `Public Transit Buses` | `Buses` | Profile explicitly describes purchasing replacement transit buses. |
| `New City Website` | `New Charlottetown.ca Website` | Same municipal website replacement. |
| `Multi-Use Outdoor Facility` | `Multi-Sport Outdoor Facility` | Same outdoor facility scope despite `Use`/`Sport` label variation. |
| `East Royalty Landfill Old Road and Active Transportation Pathway` | `East Royalty Park Old Road & AT Pathway` | Same old-road and active-transportation pathway at East Royalty. |
| `Investigative Tools and Technology` | `Investigative Tools & Tech` | Abbreviated schedule label for the same police project. |
| `Euston St. Redevelopment` | `Euston Street Redevelopment` | `St.`/`Street` abbreviation only. |
| `Sherwood Recreation Hall Upgrades` | `Sherwood Rec Hall Upgrades` | `Recreation`/`Rec` abbreviation only. |
| `New Sidewalk Construction` | `Sidewalks New Construction` | Word-order and singular/plural variation only. |
| `New Fire Station` | `New Fire Station Build` | Same fire-station project; the schedule adds `Build` and reports $6,000,000. |

### Composite Profile

`North River Road & Capital Drive Intersection Upgrades` describes one intersection but the schedule contains two distinct rows: `North River Road MP- Phase 1` and `Capital Drive - Phase 1`. Do not select one row as authoritative. Proposed treatment: allow the profile to link to both capital projects, preserving both schedule facts. This requires a one-to-many profile-link contract before Gate 3 can pass.

### Unresolved One-To-One Alias

| Profile project | Finding | Proposed treatment |
| --- | --- | --- |
| `Vehicle Equipment` | The approved Police schedule contains `Specialized Equipment` ($128,000), `Communication Equipment` ($93,000), `Investigative Tools & Tech` ($259,000), and `Community Safety` ($14,000). These sum exactly to the $494,000 total, leaving no residual for Vehicle Equipment. | Retain without a schedule fact link pending City clarification; do not infer zero or map it to another Police line. |

### Approved Decision

The project owner approved the eleven direct aliases, the two-project composite treatment, and temporary narrative-only retention for Vehicle Equipment pending City clarification. `Specialized Equipment` links exactly. The resulting manifest has 22 one-to-one profile links, one two-project link, and one reviewed narrative-only exception.

## Sources

- [Phase 1 decisions](./2026-normalized-import-phase-1-decisions.md)
- [Normalized import implementation plan](./2026-normalized-import-gap-report.md)
- [2026/2027 normalization status](./2026-normalization-status.md)
- `data/budget/charlottetown/2026-2027/normalization/capital-budget-schedule-mapping.json`
- `data/budget/charlottetown/2026-2027/normalization/capital-project-profile-mapping.json`
- `data/budget/charlottetown/2026-2027/normalized-import-manifest-report.json`
