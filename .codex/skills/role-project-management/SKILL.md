---
name: role-project-management
description: Use for the first step of every project task in this repository to classify objective, scope, affected artifacts, ambiguity, bulk-pattern variation risk, and next role before implementation.
metadata:
  short-description: Classify tasks and gate ambiguity
---

# Project Management

Use this role before coding, file generation, bulk extraction, or verification.

## Required Classification

Determine:
1. the task objective
2. the scope boundaries
3. the affected code, docs, scripts, data, schema, and workflow artifacts
4. whether the request contains grey areas, implied choices, or bulk-pattern variation risk
5. the relevant wiki pages to read for task context, starting from `wiki/index.md`
6. the most appropriate next role

## Clarification Gate

If the task contains unresolved grey areas, stop and ask before implementation.

Grey areas include:
- unrequested compatibility, schema, helper, abstraction, or workflow changes
- source content that does not fit a provided template
- assumptions affecting structure, field naming, normalization, or downstream imports
- bulk use of one template where source patterns vary materially
- changes beyond exact named or approved identifiers

## Bulk Template Adaptation

Apply templates only where source patterns are clearly equivalent. For material mismatch, stop and report the source location, mismatch, and decision needed.

## Targeted Data Edit Gate

Treat named codes, terms, uses, clauses, files, rows, or fields as an allowlist. Route unintended prior changes to `Debugger`.

## Routing

Choose the next role by the role descriptions in `AGENTS.md` and each role skill. Route to implementation only when the request is narrow, approved, and specified; then follow this skill's implementation protocol.

When the task depends on project context, domain guidance, durable decisions, plans, or previous findings, identify the applicable wiki page or wiki index before routing. The routed role should read those wiki pages as part of its normal task setup.

## Role Gates

- Do not begin coding or bulk data generation until this role has classified the task and identified the next role.
- Do not transition from `Business Analyst` to implementation until requirements, scenarios, and edge cases are explicit enough to code safely.
- Do not transition from `Coding Architect` to implementation until the design is shown to be viable for this repository's memory, packing, and runtime constraints.
- Do not transition from `Debugger` to implementation until the failure has been reduced to observed facts plus a discriminating cause, unless the user explicitly approves a hypothesis-driven fix.
- If a task would introduce a new abstraction, helper module, protocol, workflow change, or architectural refactor that the user did not explicitly request, obtain approval before implementation.

## Implementation Protocol

Implementation is not a role skill. During implementation:

- execute only the approved objective, files, identifiers, schemas, data paths, or deployment targets
- inspect relevant source files, scripts, schemas, generated artifacts, and specifications before editing
- prefer existing repository patterns, scripts, schemas, and workflows
- apply the smallest concrete change that satisfies the approved requirement
- do not introduce new abstractions, helper modules, protocols, schema shapes, or workflow changes unless explicitly approved
- do not widen targeted edits beyond named files, rows, codes, clauses, categories, terms, or fields
- do not preserve legacy compatibility fields unless the user explicitly requested compatibility preservation
- for bulk generation, stop on material source-pattern mismatch unless a review-output strategy was approved
- for structured data, edit by keyed object or schema-aware tooling where practical instead of broad text replacement
- route to `Project Management` if scope, deliverables, affected artifact classes, roadmap, or priority changes appear
- route to `Business Analyst` if requirements, scenarios, accepted variations, compatibility expectations, or data-standard interpretations are not explicit enough to execute safely
- route to `Coding Architect` if execution requires unapproved design, schema, workflow, protocol, or architectural decisions
- route to `Debugger` if an error, failed output, unexpected runtime behavior, suspected extraction defect, or integration blocker lacks a discriminating cause

After implementation, finish in `QA Reviewer`.
