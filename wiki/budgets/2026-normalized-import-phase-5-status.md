---
type: implementation
tags:
  - budget
  - import
  - dry-run
  - data-quality
updated: 2026-07-09
---

This page records Phase 5 dry-run importer implementation status for the 2026/2027 normalized budget import.

# 2026/2027 Normalized Import Phase 5 Status

## Result

Phase 5 implemented the dry-run-capable full normalized importer. Gate 6 is ready for review, not automatically approved.

The importer version is `normalized-full-1`. It validates the approved manifest hash, source PDF hash, expected counts, raw `full-2` provenance, reconciliation fact-key inputs, publication snapshot count, and deterministic event plan before commit. Dry-run mode runs the full transaction and rolls it back.

## Dry-Run Evidence

Two consecutive dry runs produced the same plan hash:

`5FFB51AA0977CA1A218ED9236D64EFB134D3DB5143A325DEEA1094643FD19176`

The dry-run plan records 2,165 facts, 2,165 fact-source links, 161 reconciliation results, one review issue, 169 capital projects, 192 capital-project fact links, 30 debt fact links, 120 capital-project profile field records, and one Vehicle Equipment profile exception event.

Post-dry-run database checks confirmed zero persisted `normalized-full-1` import batches and zero publication snapshots.

## Controls

- Source hashes and manifest hash must match before database writes.
- Existing normalized records with the same natural keys fail on content conflict instead of relying on silent `ON CONFLICT DO NOTHING`.
- Reconciliation inputs must resolve to imported fact keys.
- Publication snapshot count must be zero before and after import.
- The importer records per-record import events in the same transaction.

## Gate 6 Status

**Status:** ready for review 2026-07-09.

Gate 6 can be approved after review accepts the dry-run plan, deterministic plan hash, rollback evidence, changed-content conflict checks, and publication-snapshot prohibition.

## Sources

- [Normalized import implementation plan](./2026-normalized-import-gap-report.md)
- [Phase 4 status](./2026-normalized-import-phase-4-status.md)
- `scripts/import-budget-2026-normalized-full.py`
- `data/budget/charlottetown/2026-2027/normalized-import-dry-run-plan.json`
- `data/budget/charlottetown/2026-2027/normalized-import-manifest.json`
- `data/budget/charlottetown/2026-2027/normalized-import-reconciliation-catalogue.json`
