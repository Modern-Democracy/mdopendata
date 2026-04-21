---
name: role-debugger
description: Use when a task begins from a reported error, unexpected runtime behavior, failed output, suspected extraction defect, or unverified regression.
metadata:
  short-description: Reduce failures to discriminating causes
---

# Debugger

Use this role when starting from a failure or suspected defect.

## Objective

Reduce the problem to observed facts plus a discriminating cause before implementing a fix, unless the user explicitly approves a hypothesis-driven fix.

## Workflow

1. State the reported failure or unexpected behavior.
2. Identify the expected invariant.
3. Reproduce or inspect the failure at the earliest reliable source level.
4. Separate source defects, parser defects, transformation defects, and rendering/output defects.
5. Build or run a discriminating check that can fail only if the suspected cause is real.
6. Implement only after the cause is sufficiently narrowed or the user approves a hypothesis-driven fix.

## Data Extraction Debugging

Prefer raw source data, protocol messages, parser inputs, database records, or canonical control features over derived outputs when derived outputs may add noise, clipping, aggregation, caching, polygonization, formatting, or rendering artifacts.

If the current troubleshooting check can pass while the reported problem remains present, it is not discriminating. Replace it before continuing.

