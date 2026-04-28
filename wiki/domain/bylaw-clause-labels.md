---
type: domain
tags:
  - bylaw
  - clauses
  - extraction
updated: 2026-04-28
---

This page records reusable by-law clause label handling guidance for extraction, normalization, and validation work.

# By-law Clause Labels

## Label Preservation

Preserve each raw by-law zone, section, and clause label exactly as written in the source unless a project-specific rule explicitly allows normalization.

## Hierarchy Normalization

For clause hierarchy normalization, use hierarchical addressing:

- `20(1)(a.1)` becomes `20 -> 1 -> a.1`
- `21(e)` becomes `21 -> e`
- `21(ea)` becomes `21 -> ea`
- `21(ea)(1)` becomes `21 -> ea -> 1`

## Single-Unit Labels

Treat alphabetic, numeric, roman-numeral, decimal, and compact alphanumeric labels as single label units when they contain no whitespace and follow an incrementing sequence pattern.

Examples include:

- `a`
- `1`
- `i`
- `1.1`
- `ba`
- `c1`
- `2a`
- `5.1`
- `24A1`

Preserve each unit as one hierarchy segment.

Do not split compact amendment labels such as `aa`, `ea`, `ba`, `c1`, `2a`, `24A1`, or `34B38` into character-level segments.

## Whitespace Compaction

For section-level labels only, compact whitespace may be stripped when the source uses spacing inside a single amendment label, such as `24 A3` to `24A3`.

Do not apply this whitespace compaction to clause labels.

## Repealed Labels

Retain repealed section or clause labels with a repealed status when the source provides that tag or related amendment dates.

## Review Flags

Flag an identified section or clause label for review when it does not follow the preceding and following label pattern and does not clearly start a new sub-pattern.

## Sources

- [Root instruction placement](../index.md)
- [Data Engineer skill](../../.codex/skills/role-data-engineer/SKILL.md)
