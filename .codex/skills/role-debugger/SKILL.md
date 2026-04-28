---
name: role-debugger
description: Use when a task begins from a reported error, unexpected runtime behavior, failed output, suspected extraction defect, or unverified regression.
metadata:
  short-description: Reduce failures to discriminating causes
---

# Debugger

Use this role when starting from a failure or suspected defect.

## Objective

Reduce the problem to observed facts plus a discriminating cause before fixing it, unless the user approves a hypothesis-driven fix.

## Workflow

1. State the reported failure or unexpected behavior.
2. Read the wiki pages identified by `Project Management`, and use `wiki/index.md` to find additional relevant project, domain, implementation, or source-summary context.
3. Identify the expected invariant.
4. Reproduce or inspect the failure at the earliest reliable source level.
5. Separate source defects, parser defects, transformation defects, and rendering/output defects.
6. Build or run a discriminating check that can fail only if the suspected cause is real.
7. Implement only after the cause is sufficiently narrowed or the user approves a hypothesis-driven fix.

## Data Extraction Debugging

Prefer raw source data, parser inputs, database records, or canonical controls over derived outputs that may add noise.

If the current troubleshooting check can pass while the reported problem remains present, it is not discriminating. Replace it before continuing.

## Unintended Structured-Data Changes

When debugging a reported unintended code-table, term, use, category, or schema change:
- Identify the exact affected identifier and the expected value before editing.
- Compare the current diff against the intended allowlist.
- Patch only named identifiers unless the user expands scope.
- Before closing, run a negative-control check on nearest similar unmentioned identifiers.
