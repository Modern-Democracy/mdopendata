---
name: role-coding-architect
description: Use when a task involves module boundaries, memory pressure, runtime ownership, packing implications, protocol changes, schema design, extraction workflow design, or new technical patterns.
metadata:
  short-description: Design repository-safe technical changes
---

# Coding Architect

Use this role before implementation when design choices affect more than a narrow local edit.

## Objective

Show that the design is viable for this repository's memory, packing, runtime, schema, and workflow constraints before implementation.

## Workflow

1. Identify affected modules, scripts, generated data, schemas, and import workflows.
2. Confirm compatibility and template-fit requirements are explicit.
3. Prefer existing repository patterns over new abstractions.
4. Avoid unapproved helper modules, protocols, workflow changes, or architectural refactors.
5. Define the smallest implementation that satisfies the clarified requirements.
6. Define discriminating QA checks before coding.

## Bulk Data and Extraction Design

For extraction or normalization workflows:
- Separate raw source preservation from normalized query fields.
- Define review outputs for material mismatch cases before generating data.
- Preserve raw source labels exactly unless a project-wide rule explicitly allows normalization.

## Targeted Code-Table and Structured-Data Edits

When a request names exact code-table entries, terms, uses, categories, clauses, or fields:
- Build an explicit allowlist of the exact identifiers before editing.
- Patch structured formats by keyed object where possible, not by broad search-and-replace.
- If a helper script or regeneration can affect additional identifiers, define a post-run diff check that fails on out-of-allowlist changes before implementation.

Do not transition to implementation until the design is viable and material compatibility requirements are explicit.
