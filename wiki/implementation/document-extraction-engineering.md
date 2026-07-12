---
type: implementation
tags:
  - extraction
  - architecture
  - maintainability
  - quality-assurance
updated: 2026-07-08
---

This page defines the project-wide engineering contract for maintainable, repeatable document extraction.

# Document Extraction Engineering

## Core Rule

Extraction defects and source variations must be evaluated across the full document before adding a section-specific fix. When the same structural pattern occurs in more than one section, implementation must address the document-wide pattern through reusable code.

Reusable mechanisms should also support other documents when their source structures are materially equivalent. Cross-document reuse must not erase real differences between document families.

## Required Workflow

1. Reproduce the issue at the earliest raw source or parser-input level.
2. Audit the complete document for equivalent and nearby negative-control patterns.
3. Quantify affected pages, sections, rows, tokens, and source variations.
4. Identify whether the cause belongs to raw extraction, structural grouping, semantic normalization, or import.
5. Design the smallest reusable rule that covers confirmed equivalent patterns.
6. Preserve non-equivalent cases as explicit review outputs instead of forcing them through the rule.
7. Regenerate all affected artifacts, reimport when persisted raw data changes, and run deterministic QA.

## Reuse Requirements

- Prefer document-level parsers, table-family strategies, shared mapping functions, and schema-aware transformations over page or section branches.
- Parameterize source-specific inputs such as page ranges, section keys, column roles, entities, and period labels.
- Keep raw extraction separate from semantic normalization. A recovered token does not become a normalized fact without an approved mapping.
- Preserve raw labels, source text, coordinates, token positions, and provenance.
- Use stable identities that survive reruns and do not depend on insertion order.
- Make generation deterministic and idempotent.
- Keep reusable logic independent of one municipality or fiscal period when the source pattern supports that scope.

## One-Off Exception Gate

A one-off rule is permitted only when all of the following are recorded:

- the source location and exact mismatch
- evidence that the pattern does not recur elsewhere in the document
- why a reusable rule would create false positives or distort other source patterns
- an isolated allowlist or configuration entry rather than scattered conditional code
- positive and negative regression controls

If the exception later appears in another section, it must be replaced with a shared mechanism.

## Variation Boundaries

Reuse is appropriate only for materially equivalent structures. Stop and produce a review record when differences affect column meaning, reporting entity, fiscal period, hierarchy, aggregation role, units, dash semantics, totals, or source authority.

Templates and shared mappers may accept parameters for documented variation. They must not infer unsupported semantics from visual similarity alone.

## Duplicate Visualizations

Charts, bubbles, pies, graphs, and other visual presentations are not normalization sources when the same figures appear in an authoritative source table elsewhere in the budget document. Preserve their raw extraction evidence and classify the page or table as `duplicate_summary`; exclude it from fact mapping, reconciliation inputs, and unresolved row-review registers. Only use a visualization as a source when the document contains no authoritative tabular equivalent; retain a source-linked decision identifying that absence before mapping any value.

## QA Contract

Every extraction change must verify:

- complete-document impact counts before and after the change
- expected target recovery and nearest negative controls
- absence of unintended narrative-number or layout-token capture
- exact row, token, and value-state coverage where applicable
- stable keys and deterministic regeneration
- raw artifact and database count agreement after reimport
- no publication of unresolved or review-blocked facts
- no out-of-scope changes to unrelated document families

Tests must validate the reusable invariant, not only the first page or section that exposed the defect.

## Current Reference Implementation

The Charlottetown 2026/2027 budget workflow demonstrates this contract:

- financial-column anchors recover aligned small integers and dash variants across the document
- narrative years and unaligned layout content are negative controls
- a reusable departmental operating mapper handles equivalent summary and supporting-detail sections
- section grouping preserves page identities while moving review to meaningful source units

These implementations are examples, not universal assumptions. New document families must prove template fit before reuse.

## Sources

- [Wiki schema](../AGENTS.md)
- [Budget normalization status](../budgets/2026-normalization-status.md)
- [Budget normalized mapping contract](../budgets/representative-spike-normalized-mapping.md)
- `scripts/extract-charlottetown-budget-raw-rows.py`
- `scripts/build-budget-2026-normalization-artifacts.py`
