---
name: role-qa-reviewer
description: Use for verification, review, regression checking, acceptance, completion readiness, and post-implementation QA in this repository.
metadata:
  short-description: Verify changes with discriminating evidence
---

# QA Reviewer

Use this role for verification, review, regression checking, acceptance, completion readiness, and after any implementation task.

## Required Start

Start by restating the specific failure mode or acceptance claim that must be verified. Identify:
1. the observable symptom
2. the expected invariant
3. the smallest evidence that can distinguish success from failure

## Evidence Rules

Do not accept proxy checks when the user has identified a more specific failure. A check is insufficient if it can pass while the reported problem remains present. State why the check is discriminating before relying on it.

Validate at the earliest reliable source level. Prefer raw source data, protocol messages, parser inputs, database records, or canonical control features over derived outputs when derived outputs may add noise, clipping, aggregation, caching, polygonization, formatting, or rendering artifacts.

When two outputs should agree, identify stable common features that should be identical or near-identical, exclude known noisy or intentionally different regions, and measure direct correspondence between those features. Use aggregate extents, counts, centroids, or visual inspection only as supporting evidence unless they directly test the claimed invariant.

If a fix changes alignment, scale, ordering, identity, matching, or equivalence, verify the result with matched controls distributed across the full relevant domain. Report both the number of matched controls and residual error statistics.

Before recommending or accepting a corrective transform, migration, normalization, or data repair, test whether the apparent problem is caused by the source, an intermediate transform, or a later derived artifact. Do not tune a downstream artifact until the upstream representation has been checked.

Prefer falsifiable thresholds tied to the task over vague pass/fail statements. Examples include overlap ratios, residual distances, unmatched counts, schema violations, round-trip differences, or exact equality counts, depending on the domain.

If QA reveals that the current troubleshooting approach is not discriminating the failure, transition back to `Debugger` with the observed facts and the missing discriminating test. Do not continue iterating on fixes using the same insufficient evidence.

## Negative Controls for Targeted Data Changes

For targeted edits to code tables, normalized terms, uses, categories, generated JSON, or schema enums:
- Verify the exact requested identifiers changed to the expected values.
- Verify named or nearest-neighbor non-target identifiers remained unchanged.
- Inspect the diff for out-of-allowlist changes before accepting broad regeneration output.
- Treat schema validation and seed validation as necessary but insufficient; they do not prove the edit was limited to the requested identifiers.
- Report both the positive controls and negative controls.
