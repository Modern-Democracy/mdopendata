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
5. the most appropriate next role

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

Choose the next role by the role descriptions in `AGENTS.md` and each role skill. Route to implementation only when the request is narrow, approved, and specified; then follow the `AGENTS.md` implementation protocol.
