---
type: implementation
tags:
  - budget
  - import
  - schema
  - decision
updated: 2026-07-08
---

This page defines the proposed full-document manifest contract, identity rules, inventories, vocabulary mappings, and approval decisions for Phase 1 of the 2026/2027 normalized import.

# 2026/2027 Normalized Import Phase 1 Decisions

## Status

Phase 1 is complete. Gate 1 and Gate 2 were approved by the project owner on 2026-07-08. No SQL, importer, normalized artifact, or database record was changed during Phase 1.

## Direct Requirements

- Cover all 28 normalization files, 1,163 mapped rows, 2,165 facts, and 24 capital profiles.
- Preserve raw labels and source identities; normalized keys are separate fields.
- Make identities deterministic and independent of insertion order.
- Materialize periods per source-table column.
- Translate every artifact vocabulary value explicitly.
- Keep publication snapshots at zero.

## Manifest Protocol

Use one canonical JSON document with these ordered top-level blocks:

1. `manifest_metadata`
2. `source_documents`
3. `source_tables`
4. `reporting_entities`
5. `organization_units`
6. `funds`
7. `fiscal_periods`
8. `document_periods`
9. `statements`
10. `statement_relationships`
11. `line_items`
12. `facts`
13. `fact_sources`
14. `capital_projects`
15. `capital_project_aliases`
16. `capital_project_profiles`
17. `capital_project_facts`
18. `debt_instruments`
19. `debt_facts`
20. `reconciliations`
21. `review_issues`
22. `expected_counts`

Every block is an array sorted by its natural key. Object properties use a fixed schema order. The canonical manifest hash is SHA-256 over UTF-8 JSON serialized with sorted object keys, compact separators, normalized LF line endings, and no insignificant whitespace. Display order is stored explicitly where required and is not identity.

Unknown optional attributes are `null`; they are not inferred. Missing mandatory attributes fail manifest generation. Source labels remain exact source text.

## Stable Natural Keys

| Record | Natural-key contract |
| --- | --- |
| Source document | PDF SHA-256; `document_key` is the stable manifest alias |
| Source table | `document_key` plus reviewed canonical source-table key |
| Reporting entity | municipality key plus reviewed entity slug plus effective start |
| Organization unit | reporting entity key plus reviewed unit key plus effective start |
| Fund | reporting entity key plus reviewed fund key plus effective start |
| Fiscal period | municipality key, start date, end date, and period kind |
| Document period | document key, source-table key, source-column index, and period role |
| Statement | document key plus reviewed `statement_key` |
| Statement relationship | parent statement key, child statement key, and relationship type |
| Line item | statement key plus source row identity; reconstructed logical rows use an explicit reviewed logical-row key |
| Fact | line key, document-period key, amount type, and measure unit |
| Fact source | fact key, source-cell key, source role, and source order |
| Capital project | municipality key, reporting entity key, and reviewed project key |
| Debt instrument | reporting entity key plus reviewed instrument key plus effective start |
| Reconciliation | statement key, fiscal-period key, and reviewed check key |
| Review issue | reviewed `review_key` |

Source evidence is not part of the database fact uniqueness constraint because the schema permits multiple source cells for one fact. The manifest fact content hash includes ordered source evidence so changed provenance is detected without creating a duplicate fact.

### Key Examples By Family

| Family | Statement example | Line example | Fact example |
| --- | --- | --- | --- |
| Consolidated operating | `2026-2027:consolidated-operating` | `consolidated-operating:row-<source-id>` | line plus `2026-2027-budget:budget:cad` |
| Departmental operating | `2026-2027:police-services-operating` | statement plus source row ID | line plus table-specific period, `budget`, `cad` |
| Supporting breakdown | parent departmental statement or reviewed child statement | statement plus source row ID | line plus table-specific period, `budget`, `cad` |
| Civic Centre | `2026-2027:civic-centre-operating` | statement plus source row ID | line plus `2026-2027-budget:budget:cad` |
| Bell Aliant Centre | `2026-2027:bell-aliant-centre-operating` | statement plus source row ID | line plus current/prior table period, `budget`, `cad` |
| Capital schedule | `2026-2027:<schedule-key>-capital` | statement plus source row ID | line plus current period and `gross`, `funding_deduction`, or `net` |
| Rates | `2026-2027:tax-utility-rates` | statement plus source row ID | line plus table period, approved rate amount type, and rate unit |
| Debt | `2026-2027:water-sewer-debt` | statement plus source row ID | line plus table period and `balance`, `principal`, or `interest` |

Exact statement keys are generated in Phase 2 from the approved section/table inventory. Phase 1 fixes their construction rules, not unreviewed semantic assignments.

## Entity, Unit, Fund, And Family Inventory

### Reporting Entities

| Key | Required treatment |
| --- | --- |
| `city-of-charlottetown` | Municipality reporting entity |
| `charlottetown-water-sewer` | Reviewed reporting entity; parent relationship to be materialized only where already supported by the reviewed section |
| `charlottetown-civic-centre-management` | Facility operating reporting entity |
| `bell-aliant-centre` | Facility operating reporting entity |

`Eastlink Centre` appears only as a candidate label in family discovery artifacts. It is not promoted to a fifth reporting entity without a reviewed mapping.

### Organization Units

Thirteen explicit unit keys occur in reviewed mappings: `aquatics`, `general-administrative`, `fiscal-services`, `arena`, `simmons-arena`, `police`, `city-government`, `information-technology`, `cody-banks-arena`, `planning`, `strategic-priorities`, `other-revenue`, and `communications`. Phase 2 must also derive section-level unit assignments only from reviewed section mappings, not candidate labels.

### Funds

No reviewed artifact declares a stable `fund_key`. Statements therefore use a null fund unless a later reviewed source mapping explicitly supplies one. Entity names must not be converted into funds.

### Statement/Table Families

The reviewed artifact set covers consolidated operating, operating supporting schedules, 13 departmental/facility operating sections, 13 capital schedules, 24 capital profiles, tax and utility rates, and Water and Sewer debt. Summary/detail and consolidated/component relationships must be explicit records; they cannot be inferred from row indentation or file order.

## Vocabulary Inventory And Proposed Mappings

### Aggregation Roles

| Artifact value | Count | Proposed database value | Condition |
| --- | ---: | --- | --- |
| `additive_detail` | 711 | `detail` | Direct |
| `supporting_breakdown` | 301 | `non_additive` | Must link to the authoritative summary context |
| `reported_total` | 121 | `total` or `subtotal` | Use reviewed `line_kind`; generation fails if absent or inconsistent |
| `deduction` | 9 | `detail` or `non_additive` | Use reviewed schedule role and `funding_deduction`; never aggregate twice |

Rate rows have no artifact aggregation role. Proposed treatment is `non_additive` because rates are operands, not additive monetary flows.

### Value States

| Artifact value | Count | Database value |
| --- | ---: | --- |
| `reported_value` | 2,118 | `reported` |
| `dash_unresolved` | 41 | `dash_unresolved` |

### Measure Units

| Artifact value | Count | Database value | Status |
| --- | ---: | --- | --- |
| `CAD` | 2,144 | `cad` | Seeded |
| `CAD_per_100_assessed_value` | 8 | `cad_per_100_assessed` | Seeded |
| `CAD_per_year` | 3 | `cad_per_year` | New seed proposed |
| `CAD_per_day` | 2 | `cad_per_day` | New seed proposed |
| `CAD_per_cubic_metre` | 2 | `cad_per_cubic_metre` | New seed proposed |

Proposed seed definitions use `unit_kind = 'rate'`, `currency_code = 'CAD'`, `scale = 1`, and denominator text `year`, `day`, or `cubic metre`.

### Amount Types

| Artifact condition | Count | Proposed database value |
| --- | ---: | --- |
| Operating current/prior budget period | Determined from 1,163 current-budget and 529 prior-budget facts | `budget` |
| Operating prior forecast period | 452 | `forecast` |
| `reported_amount` on capital detail | Included in 512 explicit values | `gross` |
| `partner_funding` | 11 | `funding_deduction` |
| Reviewed capital net total | Derived from reviewed role, not label alone | `net` |
| Debt `balance` | 11 | `balance` |
| Debt `principal` | 11 | `principal` |
| Debt `interest` | 11 | `interest` |
| Property/utility rate fact | 15 | `actual` |

The 1,603 facts without an artifact `amount_type` receive a value only from the approved document-period role and reviewed family/row role. Any fact that matches more than one rule or no rule fails generation.

## Representative Collision Evidence

The representative manifest contains 19 normalized facts. All 19 belong to the same 2026/2027 source document and overlap full-document semantic families: Bell Aliant operating, capital schedules, property tax/rates, and long-term debt. The other representative cases are raw-only or refer to another document and contribute no normalized facts.

Reusing representative natural keys is unsafe because representative normalized facts point to representative source tables and cells rather than the completed full raw layer. A reused fact could retain stale provenance while appearing idempotent.

### Proposed Coexistence Rule

Classify all representative normalized records as test-only and exclude them from the full-document production identity space. Before the controlled full import, the implementation must produce an explicit retirement plan listing every affected normalized natural key and dependent reconciliation/review record. Retirement requires its own transactional dry-run evidence under Gate 6; it is not performed in Phase 1.

Raw representative evidence remains immutable. No representative record is silently reused, overwritten, or deleted by manifest generation.

## Gate 1 Decision

**Proposed approval:** approve the manifest protocol, natural-key rules, null-fund rule, entity inventory, and test-only retirement coexistence rule.

**Effect of approval:** authorizes Phase 2 to generate the deterministic full-document manifest and a representative retirement plan. It does not authorize database mutation.

**Status:** approved 2026-07-08.

## Gate 2 Decision

**Proposed approval:** approve the vocabulary mappings, rate rows as `non_additive` with amount type `actual`, and the three active measure-unit seeds `cad_per_year`, `cad_per_day`, and `cad_per_cubic_metre` with the definitions above.

**Effect of approval:** authorizes a later schema-seed change and Phase 2 vocabulary generation. It does not authorize SQL changes in Phase 1.

**Status:** approved 2026-07-08.

## Stop Conditions Carried Into Phase 2

- An unknown entity, organization unit, fund, statement scope, or relationship is required.
- A source row maps to multiple statements without an explicit reviewed relationship.
- A `reported_total` lacks a consistent reviewed `line_kind`.
- A fact matches zero or multiple amount-type rules.
- A representative natural key lacks an explicit retirement disposition.
- A new vocabulary value appears outside this inventory.

## Sources

- [Normalized import implementation plan](./2026-normalized-import-gap-report.md)
- [Representative normalized mapping](./representative-spike-normalized-mapping.md)
- [Database schema](./database-schema.md)
- [2026/2027 normalization status](./2026-normalization-status.md)
- `data/budget/charlottetown/schema-spike/normalized-mapping.json`
- `data/budget/charlottetown/2026-2027/normalization/`
- `schema/sql/025_budget_schema.sql`
