# Normalized Generated Outputs

## Direct Answer

This directory stores generated normalized land-use conversion outputs and must not replace or mutate the source extraction trees under `data/zoning` or `data/municipal-planning-strategy`.

## Purpose

Use this tree for repeatable QA runs of the normalization process. Each conversion run gets its own immutable run directory so changes to the converter, schema, review decisions, or source extracts can be compared without losing prior outputs.

## Layout

```text
data/normalized/
  README.md
  land-use-standard-version.json
  runs/
    <run-id>/
      manifest.json
      bundle.json
      bundle.validation.json
      review-items.json
      stats.json
      zoning/
      municipal-planning-strategy/
  latest/
    manifest.json
    bundle.json
    review-items.json
```

## Directory Rules

- `runs/<run-id>/` is the authoritative output for a specific conversion attempt.
- `latest/` is only a convenience copy or pointer for local tooling.
- Source extraction files remain under `data/zoning` and `data/municipal-planning-strategy`.
- Database imports should read from a selected run directory, not directly from source extraction directories.
- QA should compare run outputs across run ids instead of overwriting old runs.

## Run Id Format

Use UTC timestamp run ids that sort lexically:

```text
YYYYMMDDTHHMMSSZ
```

Example:

```text
20260417T000000Z
```

## Required Run Files

- `manifest.json`: source paths, source checksums if available, converter version, standard version, git commit, run command, run timestamp, and output file inventory.
- `bundle.json`: combined normalized bundle conforming to `schema/normalized_land_use_bundle.schema.json`.
- `bundle.validation.json`: schema validation result and any validation errors.
- `review-items.json`: unresolved clause syntax, unit parsing, condition parsing, spatial matching, relationship resolution, and classification review items.
- `stats.json`: counts by source, document, zone, regulation type, policy type, relationship type, and review status.

## Standard Version

`land-use-standard-version.json` records the default standard version used by the current converter. Individual run manifests must also record the standard version used for that run.
