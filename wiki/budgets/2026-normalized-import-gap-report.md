---
type: implementation
tags:
  - budget
  - import
  - reconciliation
  - data-quality
updated: 2026-07-08
---

This plan converts the reviewed Charlottetown 2026/2027 normalization artifacts into a controlled full-document normalized import with explicit approval gates.

# 2026/2027 Normalized Import Implementation Plan

## Objective

Import the 2,165 reviewed facts and their identities, provenance, extensions, and reconciliations into PostgreSQL without unsupported inference, duplicate logical records, silent content conflicts, or publication.

The current database contains only the representative spike: 7 statements, 16 line items, 19 facts, 21 fact-source links, 7 reconciliations, and 3 review issues. Publication snapshots must remain at zero throughout this plan.

## Scope

### Included

- One deterministic full-document normalized manifest for all 28 normalization files, 1,163 mapped rows, 2,165 mapped facts, and 24 capital profiles.
- Stable identities for statements, lines, facts, entities, organization units, periods, capital projects, and debt instruments.
- Exact source-value-to-source-cell provenance.
- Explicit vocabulary and amount-type translations.
- Full-document reconciliations and blocking review issues.
- A dry-run-first, transactional, idempotent full normalized importer mode.
- Source-fidelity, count, reconciliation, and rerun QA.

### Excluded

- Publication snapshot creation.
- Public API or UI changes.
- Inference of unknown lender, debt type, hierarchy, fund, entity, or financial semantics.
- Normalization of rows not present in the reviewed artifacts.
- Dependency, runtime, or deployment changes unless separately proposed and approved through DevOps.

## Approval Authority

Each gate requires a recorded approval in the implementation record before dependent work begins. The user or designated project owner approves product and workflow decisions. The data/schema owner approves controlled vocabularies and schema seed changes. The normalization reviewer approves semantic mappings. The QA reviewer approves evidence and completion gates. One person may hold multiple authorities, but each approval must identify the decision and evidence reviewed.

## Phase 1: Freeze Contracts And Resolve Decisions

### Work

1. Define the manifest schema and deterministic ordering.
2. Define stable natural-key rules:
   - line key: statement identity plus source row identity
   - fact key: line, document period, amount type, measure unit, and source evidence
   - document period: document, source table column, and period role
3. Inventory reporting entities, organization units, funds, statement/table families, and parent/component relationships.
4. Specify explicit translations for aggregation roles, value states, units, and amount types.
5. Decide how full-document records coexist with the representative spike.

### Gate 1: Manifest And Coexistence Approval

**Decision required:** approve the manifest protocol and choose one coexistence rule: reuse identical natural keys where semantics are identical, or isolate and retire representative records as test-only. Mixing both approaches without an explicit record-level rule is prohibited.

**Evidence:** manifest schema, natural-key examples for every statement family, entity/unit inventory, representative-to-full collision report, and expected record counts.

**Pass criteria:** every record class has a stable identity; repeated labels cannot collide; representative records have an explicit disposition; no key depends on insertion order or label text alone.

**Stop condition:** unresolved statement scope, reporting entity, fund, hierarchy, or representative-data collision.

### Gate 2: Vocabulary And Schema Approval

**Decision required:** approve all translation tables and separately approve schema seeds for `cad_per_year`, `cad_per_day`, and `cad_per_cubic_metre`.

Required translations include:

| Artifact value | Database treatment |
| --- | --- |
| `additive_detail` | `detail` |
| `supporting_breakdown` | Usually `non_additive`, linked to its authoritative summary |
| `reported_total` | Reviewed `total` or `subtotal` |
| `deduction` | Reviewed detail/non-additive role plus `funding_deduction` amount type |
| `reported_value` | `reported` |
| `CAD` | `cad` |
| `CAD_per_100_assessed_value` | `cad_per_100_assessed` |

**Evidence:** complete distinct-value inventory, proposed mappings, affected counts, and schema migration/seed diff if required.

**Pass criteria:** every artifact vocabulary value maps to an allowed database value; rate rows have approved aggregation and amount-type treatment; all 1,603 currently missing amount types have deterministic reviewed rules.

**Stop condition:** an unmapped value, unsupported unit, or ambiguous gross/deduction/net treatment remains.

## Phase 2: Build The Deterministic Manifest

### Work

1. Materialize entities, units, funds, source-table-specific periods, statements, and relationships.
2. Generate stable line and fact keys from the approved rules.
3. Assign amount types:
   - operating periods to `budget` or `forecast`
   - capital details to `gross`
   - partner funding to `funding_deduction`
   - net capital totals to `net`
   - rates to the Gate 2 treatment
   - existing `reported_amount` and `partner_funding` to approved database codes
4. Generate stable capital-project and debt-instrument identities and links. Leave unknown lender/type fields null.
5. Add aliases, profile-field provenance, project-to-fact links, and debt-to-fact links.
6. Emit expected counts by document, statement family, record class, period, amount type, unit, and value state.

### Gate 3: Semantic Mapping Approval

**Evidence:** generated manifest, unresolved-decision report, distinct-value report, identity-collision report, extension-link report, and count matrix.

**Pass criteria:** all 2,165 facts have a stable key, statement, line, table-specific document period, amount type, unit, value state, and reporting entity; all 24 capital profiles and 10 debt instruments have stable identities and required links; no unsupported semantic inference exists.

**Stop condition:** any missing identity, collision, ambiguous hierarchy, missing amount type, or inferred unknown attribute.

## Phase 3: Resolve And Validate Provenance

### Work

1. Build the deterministic bridge from `source_value_id` through raw row, source table, and value-column index to `source_table_cell`.
2. Validate exact raw token and parsed numeric equivalence for every fact.
3. Represent page 87 split-line reconstruction with evidence from all contributing physical rows.
4. Link every capital profile field to its source evidence.

### Gate 4: Provenance Approval

**Evidence:** 2,165-link validation report, 24-profile field-link report, mismatch report, duplicate-link report, and explicit page 87 reconstruction evidence.

**Pass criteria:** every reported fact resolves to at least one exact source cell; all source tokens and parsed values agree; multi-row reconstruction is explicit; mismatch count is zero.

**Stop condition:** missing, ambiguous, duplicated, or value-inconsistent source-cell evidence.

## Phase 4: Define Full Reconciliations

### Work

Create stable-keyed checks for:

- operating revenue, expense, and net totals by statement and period
- departmental summary/detail comparisons without double counting
- Civic Centre revenue minus expenses equals net income
- Bell Aliant departmental totals and earnings/loss for both periods
- capital gross less partner funding equals reported net
- consolidated capital component totals
- debt principal plus interest equals reported debt service where asserted
- rate and assessment calculations where the source supplies all operands

Every reconciliation input must resolve to an exact manifest fact key. Every failure must create or link a blocking review issue.

### Gate 5: Reconciliation Design Approval

**Evidence:** reconciliation catalogue, input fact-key resolution report, tolerance definitions with rationale, and expected pass/review outcomes.

**Pass criteria:** all applicable statement families are covered; every input resolves; double-counting exclusions are explicit; tolerances are approved; failures cannot be omitted from review.

**Stop condition:** unresolved inputs, implicit tolerances, incomplete family coverage, or an untracked failed check.

## Phase 5: Implement Full Normalized Import Mode

### Work

1. Add a normalized full-document mode with a version distinct from `full-1`.
2. Validate source hashes, manifest hash, schemas, natural keys, expected counts, provenance, and reconciliation inputs before mutation.
3. Produce a machine-readable dry-run plan.
4. Import in one transaction with deferred constraints.
5. Detect changed content for existing natural keys and fail visibly; do not silently rely on `ON CONFLICT DO NOTHING`.
6. Record batch identity, extractor/importer version, source hashes, manifest hash, and per-class counts.
7. Prohibit publication snapshot creation in this mode.

### Gate 6: Dry-Run Implementation Approval

**Evidence:** automated tests, first dry-run plan, second dry-run plan, exact plan diff, expected-count comparison, collision behavior test, rollback test, and proof that publication snapshots remain zero.

**Pass criteria:** both dry runs are byte-for-byte or canonically identical; all expected counts match; changed-content conflicts fail; validation failures cause no database mutation; the transaction rollback test passes.

**Stop condition:** nondeterministic plan, count variance, silent conflict, partial write, missing hash/version, or publication-side effect.

## Phase 6: Execute Controlled Import

### Work

1. Back up or otherwise capture the approved pre-import database state using the existing project procedure.
2. Execute the approved manifest in one transaction.
3. Compare database counts and hashes with the manifest.
4. Rerun the same import and verify idempotence.
5. Run all reconciliations and generate review issues.

### Gate 7: Import Acceptance

**Evidence:** import batch record, transaction result, file/database count matrix, hash comparison, second-run change report, reconciliation results, review-issue inventory, and publication snapshot count.

**Pass criteria:** exact file/database count agreement by statement family; the second run creates no duplicate logical records and reports no content conflicts; all expected source links and extensions exist; publication snapshots remain zero.

**Stop and rollback criteria:** transaction failure, count/hash mismatch, duplicate logical record, unexpected mutation, unresolved provenance loss, or publication snapshot creation.

## Phase 7: Source-Fidelity And Completion QA

### Work

1. Validate normalized facts against reviewed artifacts and sampled source cells across every statement family and source pattern.
2. Verify dash-versus-zero preservation, signs, units, periods, amount types, aggregation roles, entity scope, and extension links.
3. Review every reconciliation failure and severity assignment.
4. Confirm representative-data disposition matches Gate 1.
5. Record residual issues and completion status in the budget wiki.

### Gate 8: QA Completion And Publication Eligibility

**Evidence:** QA report, family-stratified source-fidelity results, reconciliation report, open-issue register, count reconciliation, and publication snapshot query.

**Pass criteria:** exact count agreement; zero provenance mismatches; all totals reconcile within approved tolerance or have an open blocking issue; zero unresolved high-severity issues; zero publication snapshots.

Passing this gate makes the dataset eligible for a separate publication decision. It does not authorize publication.

**Stop condition:** any unresolved high-severity issue, unexplained reconciliation failure, source-fidelity mismatch, or nonzero publication snapshot count.

## Deliverables

| Deliverable | Produced by | Required gate |
| --- | --- | --- |
| Manifest protocol and coexistence decision record | Phase 1 | Gate 1 |
| Vocabulary and schema decision record | Phase 1 | Gate 2 |
| Deterministic full-document manifest and count matrix | Phase 2 | Gate 3 |
| Provenance validation report | Phase 3 | Gate 4 |
| Full reconciliation catalogue | Phase 4 | Gate 5 |
| Dry-run-capable importer mode and tests | Phase 5 | Gate 6 |
| Import batch and idempotence evidence | Phase 6 | Gate 7 |
| Source-fidelity and completion QA report | Phase 7 | Gate 8 |

## Execution Order And Dependencies

Gates 1 and 2 must pass before manifest generation. Gate 3 must pass before provenance and reconciliation finalization. Gates 4 and 5 must pass before importer implementation is accepted. Gate 6 must pass before any normalized database write. Gate 7 must pass before final QA. Gate 8 is the terminal gate for this plan.

No downstream phase may waive a failed upstream gate. A material schema, identity, vocabulary, coexistence, or reconciliation change returns the plan to the applicable earlier gate.

## Sources

- [Database schema](./database-schema.md)
- [Representative normalized mapping](./representative-spike-normalized-mapping.md)
- [2026/2027 normalization status](./2026-normalization-status.md)
- [Document extraction engineering](../implementation/document-extraction-engineering.md)
- `schema/sql/025_budget_schema.sql`
- `scripts/import-budget-schema-spike.py`
- `data/budget/charlottetown/2026-2027/normalization/`
- `data/budget/charlottetown/2026-2027/raw-tables/source_values.json`
