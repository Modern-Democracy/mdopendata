---
type: project
tags:
  - budget
  - normalization
  - taxonomy
  - comparison
  - review
updated: 2026-07-13
---

This page records the original category proposal and its 2026-07-13 transition into an authorized browser-review implementation.

# Normalized Budget Category Taxonomy And Fact-Mapping Proposal

## Decision Status

The project owner authorized the Charlottetown-only candidate `charlottetown-budget-category-v1`, the versioned assignment architecture, database migration, assignment writes, and changing snapshot `1` for browser review on 2026-07-13.

Migration 027 implements a taxonomy revision overlay instead of mutating the snapshot row or legacy line-item foreign key. Snapshot `1` retains exactly 6,256 fact memberships, but its effective taxonomy version is now `charlottetown-budget-category-v1`; 667 controlled-label assignments are exposed as `proposed`, not approved.

## Verified Starting State

| Check | Result |
| --- | ---: |
| Published snapshot | `1`, `charlottetown-budget-v1` |
| Published facts | 6,256 |
| Published line items | 3,376 |
| Existing normalized categories | 0 |
| Published facts with categories | 0 |
| Detail line items eligible for first mapping | 2,420 |
| Detail facts supported by eligible lines | 4,941 |
| Non-detail line items excluded from first aggregate mapping | 956 |
| Non-detail facts excluded from first aggregate mapping | 1,315 |
| Repeated-label cohorts requiring context-aware treatment | 325 cohorts covering 1,107 line items |

The existing exact-identity comparison remains valid and independent of this proposal.

## Blocking Schema Finding

`budget.line_item.normalized_category_id` permits one category assignment per line item, while `budget.normalized_category` is versioned. Updating that field would change category semantics returned for facts already frozen in published snapshot `1`. The current published-snapshot immutability triggers do not prevent this indirect semantic change.

Do not populate `line_item.normalized_category_id` or `capital_project_fact.funding_source_category_id` for published records. Add two versioned assignment relations before category mapping: `line_item_category_assignment` for economic-purpose or account-nature categories, and `capital_funding_category_assignment` for funding-source categories on capital project facts.

| Field | Requirement |
| --- | --- |
| Subject foreign key | `line_item_id` in the line-item relation; `fact_id` in the capital-funding relation, constrained to `capital_project_fact`. |
| `normalized_category_id` | Required foreign key whose taxonomy version matches the assignment version. |
| `taxonomy_version` | Required immutable version label. |
| `assignment_status` | `proposed`, `approved`, `rejected`, or `superseded`. |
| `mapping_basis` | `structural`, `controlled_label`, or `manual`. |
| `normalization_decision_id` | Required for approved assignments. |
| `created_at` | Required timestamp. |

The line-item relation enforces one active approved category per line item and taxonomy version. The capital-funding relation enforces one active approved funding category per fact and taxonomy version and accepts only facts whose amount type represents a funding source or deduction. The publication view joins through effective snapshot taxonomy metadata rather than either legacy mutable foreign key. Snapshot `1` now exposes proposed candidates under the separately recorded taxonomy revision, as explicitly authorized.

## Taxonomy Design Rules

- The first taxonomy is municipality-specific and does not authorize cross-municipality comparison.
- Categories describe economic purpose or account nature. Reporting entity and organization unit remain separate service-delivery axes.
- Capital investment purpose and capital funding source are separate axes. A project line may have one investment category while a funding fact linked to that line has one funding category.
- Amount types remain separate from categories. `budget`, `forecast`, `gross`, `funding_deduction`, `net`, `balance`, `principal`, and `interest` must not become category keys.
- Operating, capital, revenue, funding, rate, and debt contexts remain distinct.
- Raw labels are preserved. Display-name cleanup does not alter raw evidence.
- Categories may have a parent only within the same taxonomy version and domain.
- `other` categories require manual approval and rationale; they are not fallback defaults.

## Proposed Vocabulary

### Operating Revenue

| Category key | Display name | Includes only when source context confirms |
| --- | --- | --- |
| `revenue.taxation` | Taxation | Property and related municipal tax revenue. |
| `revenue.utility` | Utility revenue | Water, sewer, and utility operating revenue. |
| `revenue.grants_transfers` | Grants and transfers | Federal, provincial, municipal, and partner operating transfers. |
| `revenue.fees_charges` | Fees and charges | User fees, permits, rentals, admissions, and service charges. |
| `revenue.facility_program` | Facility and program revenue | Facility, event, recreation, and program receipts. |
| `revenue.investment_financing` | Investment and financing revenue | Interest income and explicitly reported financing revenue. |
| `revenue.other` | Other operating revenue | Reviewed revenue that fits no approved specific category. |

### Operating Expense

| Category key | Display name | Includes only when source context confirms |
| --- | --- | --- |
| `expense.workforce` | Workforce | Salaries, wages, benefits, training, and staff development. |
| `expense.contracts_professional` | Contracted and professional services | Service contracts, consulting, legal, audit, and professional services. |
| `expense.materials_supplies` | Materials and supplies | Office, operating, cleaning, clothing, and program supplies. |
| `expense.facilities_occupancy` | Facilities and occupancy | Utilities, rent, building operations, repairs, and maintenance. |
| `expense.fleet_transport` | Fleet and transportation | Fuel, vehicle operation, travel, and transportation. |
| `expense.technology_communications` | Technology and communications | Software, hardware operations, telecommunications, advertising, and communications. |
| `expense.grants_contributions` | Grants and contributions | Grants, partner contributions, and transfers to external recipients. |
| `expense.debt_financing` | Debt and financing costs | Interest and other operating financing costs, excluding principal. |
| `expense.insurance_risk` | Insurance and risk | Insurance premiums, claims, and risk costs. |
| `expense.programs_projects` | Programs and projects | Source-identified operating programs and projects not classified by a more specific account nature. |
| `expense.other` | Other operating expense | Reviewed expense that fits no approved specific category. |

### Capital Investment

| Category key | Display name | Includes only when source context confirms |
| --- | --- | --- |
| `capital.transportation` | Transportation infrastructure | Streets, sidewalks, traffic systems, transit, active transportation, and related works. |
| `capital.water_wastewater` | Water and wastewater | Water supply, distribution, sewer, treatment, and utility infrastructure. |
| `capital.facilities` | Buildings and facilities | Civic, emergency, recreation, and operational buildings or facility systems. |
| `capital.parks_recreation` | Parks and recreation | Parks, trails, fields, playgrounds, arenas, and recreation assets. |
| `capital.fleet_equipment` | Fleet and equipment | Vehicles, machinery, specialized equipment, and movable capital assets. |
| `capital.technology` | Technology infrastructure | Networks, servers, software capital, communications equipment, and control systems. |
| `capital.land_development` | Land and development | Land acquisition, site development, and municipally identified development projects. |
| `capital.environment_resilience` | Environment and resilience | Energy, climate, stormwater, urban forest, and resilience investments. |
| `capital.other` | Other capital investment | Reviewed capital investment that fits no approved specific category. |

### Capital Funding

| Category key | Display name | Includes only when source context confirms |
| --- | --- | --- |
| `funding.external_partner` | External partner funding | Explicit partner deductions or contributions. |
| `funding.government_grant` | Government grants | Federal or provincial capital grants. |
| `funding.debt` | Debt financing | Borrowing or planned debt used for capital funding. |
| `funding.reserve` | Reserve funding | Named reserve contributions or withdrawals used for capital. |
| `funding.utility` | Utility funding | Water and sewer or other utility-funded capital. |
| `funding.general_revenue` | General revenue funding | General municipal revenue or tax-supported capital funding. |
| `funding.other` | Other capital funding | Reviewed funding that fits no approved specific category. |

### Rates And Debt

Do not create initial debt categories. Debt instrument identity plus amount type already distinguishes balance, principal, and interest. Do not create initial tax-class categories because `budget.tax_class` and `budget.rate_fact` carry the more precise classification. Category expansion for these domains requires a separate reviewed use case.

## Mapping Cohorts

### Cohort A: Structural Candidates

Generate proposed assignments only where statement kind, section hierarchy, line role, and source context all agree. Examples include source-identified capital schedule sections and explicit revenue or expense sections. Structural mapping must never rely on statement kind alone.

### Cohort B: Controlled-Label Candidates

Map repeated labels only through an approved label rule scoped by statement kind and section context. The 325 repeated-label cohorts must not be assigned globally. For example, `Grants`, `Projects`, `Revenue`, `Miscellaneous`, and `Property Taxes` can represent different semantics depending on hierarchy and statement scope.

Controlled-label rules require:

- exact normalized label variants
- allowed statement kinds
- required ancestor or section context
- allowed reporting entities when material
- target category key
- positive examples
- nearest negative controls
- reviewer rationale

### Cohort C: Manual Review

Use manual review when labels are generic, context is incomplete, source sections conflict, a line could fit multiple categories, or an `other` category is proposed. No automatic fallback assignment is permitted.

## Exact Review Register Contract

Every proposed assignment must identify:

- source document ID and title
- PDF page number or every candidate page for a multi-page table
- source table ID and table key
- source row ID, row key, row index, raw label, and raw row text
- line item ID, statement key, statement kind, reporting entity, aggregation role, and hierarchy path
- affected fact IDs, fiscal-period labels, amount types, units, and values
- proposed category key, mapping basis, confidence, rationale, and review status
- assignment scope: `line_item` or `capital_funding_fact`; funding assignments must identify the exact fact and amount type
- ambiguity statement and nearest non-target control

Rows must be presented individually for user review. Do not group unresolved assignments behind counts or vague labels.

## First-Pass Scope

- Include only the 2,420 published detail line items supporting 4,941 facts.
- Exclude all 956 subtotal, total, memo, and non-additive line items from category-backed aggregation. They remain source-visible and available for reconciliation.
- Exclude rows whose raw label is `0`, blank, a layout artifact, or unresolved context.
- Exclude debt and tax/rate category assignment in the first pass.
- Preserve project identity and organization-unit identity independently of category assignment.

## Workflow And Gates

1. **Gate 1: Vocabulary approval.** Approve, rename, add, or remove the exact category keys above.
2. **Gate 2: Schema approval.** Approve the versioned assignment relation and category-aware publication-view design.
3. **Gate 3: Candidate generation.** Produce a non-mutating JSON/CSV review register with counts by category, basis, statement kind, document, and reporting entity.
4. **Gate 4: Source-fidelity review.** Review every proposed assignment and every ambiguity using the exact review-register fields.
5. **Gate 5: Negative controls.** Confirm that nearby same-label rows outside each rule remain unmapped.
6. **Gate 6: Dry run.** Generate deterministic category, assignment, and decision plans with hashes and zero database writes.
7. **Gate 7: Controlled migration.** Completed after explicit DevOps and data-migration authorization; migration 027 and the assignment script were applied transactionally.
8. **Gate 8: Browser-review QA.** Completed for schema integrity, row uniqueness, fact-membership stability, idempotence, API filtering, and proposed-status visibility. Category source-fidelity approval remains open.
9. **Gate 9: Publication decision.** Replaced by the explicitly authorized snapshot `1` taxonomy revision overlay. No new fact membership or source document was added.

## Browser-Review Acceptance Criteria

- Snapshot `1` continues returning exactly 6,256 facts without duplicate fact rows.
- Every approved assignment has one normalization decision and exact source evidence.
- No line item has more than one approved economic category in a taxonomy version, and no capital funding fact has more than one approved funding category in a taxonomy version.
- Category domain, hierarchy, amount type, statement scope, and measure unit are compatible.
- Category aggregates include detail facts only and reconcile to their mapped inputs exactly.
- Coverage reports eligible, proposed, approved, rejected, unresolved, and excluded line and fact counts.
- Repeated-label negative controls show zero unintended mappings.
- Proposed assignments are visibly distinguished from approved assignments and raw labels remain available.

## Data Quality Review

The versioned assignment relations and explicit snapshot revision remove the original schema blocker. The 667 controlled-label assignments remain proposed because repeated labels and context-sensitive matches can produce false positives; browser review is required before any approval conversion.

No source-fidelity approval claim is made for the proposed category assignments. Approved project-department, capital-program, and subsequent-forecast writes use separate explicit evidence rules documented in the implementation status.

## Sources

- [Municipal budget requirements](./requirements.md)
- [Municipal budget database schema](./database-schema.md)
- [Budget API and UI contract](./api-and-ui-contract.md)
- [Representative normalized mapping](./representative-spike-normalized-mapping.md)
- [Prior-year normalized import completion](./prior-year-normalized-import-completion-status.md)
- [Budget web and taxonomy implementation status](./budget-web-taxonomy-implementation-status.md)
- `budget.v_published_facts`, `budget.normalized_category`, `budget.line_item`, and `budget.normalization_decision`, queried on 2026-07-12
