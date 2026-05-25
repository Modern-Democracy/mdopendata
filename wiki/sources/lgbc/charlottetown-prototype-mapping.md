---
type: source
tags:
  - source
  - municipal-governance
  - charlottetown
  - prototype-mapping
  - lgbc
updated: 2026-05-25
---

This page summarizes the first Phase 6 source-family mapping from LGBC benchmark and process candidates to known Charlottetown repository artifacts.

# Charlottetown Prototype Mapping

## Source Locator

| Field | Value |
| --- | --- |
| Source catalogue | `data/sources/lgbc/benchmark_process_candidate_catalogue.json` |
| Mapping file | `data/sources/lgbc/charlottetown_prototype_mapping.json` |
| Target municipality | Charlottetown |
| Mapping status | First-pass source-family mapping created; pending dataset review |

## Mapping Results

| Mapping status | Count | Meaning |
| --- | ---: | --- |
| `strong_source_family_identified` | 10 | Existing Charlottetown source families appear directly relevant to candidate review. |
| `partial_source_family_identified` | 56 | Some source families exist, but required operating, financial, service, or governance inputs remain missing. |
| `source_gap` | 20 | No direct Charlottetown source family was identified from the current repository scan. |
| Total mapped candidates | 86 | All Phase 5 candidates are included. |

No candidate is marked ready for public metric, score, or cross-municipality comparison.

## Domain Mapping

| Domain | Count | Mapping status | Source-family finding |
| --- | ---: | --- | --- |
| Governance | 8 | `partial_source_family_identified` | Council meeting and business-item extraction can support decision-channel review, but broader governance and affected-party records remain missing. |
| Service delivery | 12 | `partial_source_family_identified` | Portal domain inventory and budget extraction support source-completeness planning, but service catalogues, contracts, standards, and outputs remain missing. |
| Protective services | 12 | `source_gap` | No direct police, fire, or emergency operating dataset is currently identified; only possible budget context exists. |
| Engineering services | 12 | `partial_source_family_identified` | Street, parcel, terrain, and budget source families exist, but water, wastewater, solid waste, road condition, and transit operating records remain missing. |
| Human services | 12 | `partial_source_family_identified` | Parks, budget, and Official Plan source families exist, but program, library, museum, public-health, and housing operating data remain missing. |
| Planning and land use | 10 | `strong_source_family_identified` | Zoning, draft zoning, OCP, future land use, parcel, map, and meeting-package source families make this the strongest immediate mapping domain. |
| Labour relations | 8 | `source_gap` | No direct HR, collective agreement, bargaining-unit, or labour-relations source family is currently identified. |
| Finance | 12 | `partial_source_family_identified` | Budget PDFs and raw budget extraction exist, but audited statements, assessment detail, fee bylaws, debt, reserve, and reviewed normalization remain missing. |

## Immediate Prototype Priority

Planning and land use is the only strong Phase 6 source-family match because the repository already contains current and draft zoning bylaws, zoning spatial layers, parcel data, OCP material, future land use mapping, and meeting-package extraction for rezoning examples.

Finance is the next practical mapping area because budget source extraction exists, but candidate use should remain limited to source-completeness and normalization review until audited statements, tax/assessment records, fee bylaws, debt records, and reserve records are identified.

Engineering, human services, governance, and service delivery are useful for gap analysis and source inventory planning. Protective services and labour relations require source discovery before candidate analysis.

## Use Rules

The mapping is not an implementation approval. It identifies whether the repository appears to contain source families relevant to each LGBC candidate.

Candidate readiness remains constrained by:

- Charlottetown and PEI jurisdiction mapping.
- Local source availability.
- Stable definitions and denominators.
- Disclosure and sensitivity review.
- Public-route source contracts.
- Explicit approval before metrics, scoring, or public comparison.

## Sources

- `data/sources/lgbc/charlottetown_prototype_mapping.json`
- [LGBC Benchmark And Process Candidate Catalogue](./benchmark-process-candidate-catalogue.md)
- [Municipal portal domain inventory](../../product/municipal-portal-domain-inventory.md)
- [Municipal portal product purpose](../../product/municipal-portal-purpose.md)
- [Charlottetown wiki index](../../charlottetown/index.md)
- [Municipal budget data model](../../implementation/municipal-budget-data-model.md)
