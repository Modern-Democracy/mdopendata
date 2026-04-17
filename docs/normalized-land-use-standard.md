# Normalized Land Use Standard

## Direct Answer

Use a local canonical standard, not a single external standard, because the available public zoning standards are useful references but do not preserve enough source text, clause hierarchy, conditional regulation, recursive zone inclusion, and metric conversion detail for this repository.

## Task Classification

- Role: Project Management.
- Objective: normalize zoning bylaws, land-use bylaws, municipal planning strategies, maps, and related extracted JSON into one database-loadable structure.
- Scope boundaries: use the current `data`, `docs`, `zoning`, `ocp`, `schema`, and `scripts` artifacts; do not overwrite extracted source trees; preserve raw clauses and source citations.
- Affected artifacts: extracted JSON under `data/zoning` and `data/municipal-planning-strategy`, source PDFs, database schema under `schema`, import scripts, and future QA fixtures.
- Next role: Business Analyst for requirements and edge cases, then Coding Architect for the canonical JSON and database mapping.

## Public Standard Review

- National Zoning Atlas: good methodology for district classification, housing permissions, overlays, maps, and review workflows. It is not a complete public JSON schema for reconstructing bylaw text, but its concepts should inform normalized categories and overlay flattening. Source: https://www.zoningatlas.org/how and https://www.zoningatlas.org/snapshots-methods.
- Washington State Zoning Atlas: useful example of translating local zoning designations into consistent statewide categories and attributes. It explicitly notes that local zoning lacks a standard publication format. Source: https://www.commerce.wa.gov/growth-management/data-research/waza/.
- Vermont Zoning GIS Data Standard: useful for zoning geometry naming, metadata, status, district type categories, and spatial reference practice. It is mainly a GIS standard, not a bylaw-rule standard. Source: https://files.vcgi.vermont.gov/other/standards-guidelines/zoning/zoning-standard.html.
- Regrid Standardized Zoning Schema: useful field inventory for parcel/zoning enrichment, especially setbacks, height, coverage, density, land uses, and zone type. It is flattened, uses imperial units, and cannot encode complex conditional rules without loss. Source: https://support.regrid.com/parcel-data/zoning-schema.
- OKFN U.S. City Open Data Census zoning definition: useful minimum open-data expectation that mapped zones and allowed-use descriptions should both be public. Source: https://us-cities.survey.okfn.org/dataset/zoning.html.

Conclusion: define an HRM-oriented canonical structure that can export simplified fields compatible with atlas-style schemas, while keeping richer source-preserving records for legal and planning analysis.

## Design Principles

- Non-destructive: every normalized record must point to source JSON and source document citations.
- Source-preserving: `raw_label`, `raw_text`, `raw_symbols`, source page ranges, and extraction method remain available.
- Metric-first: normalized numeric values use SI units where possible, with original value and unit retained.
- Conditional-first: regulations are atomic facts with contextual predicates, not flattened columns.
- Recursive: zone-to-zone and rule-to-rule inclusions are explicit graph edges with cycle detection.
- Review-gated: unknown clause syntax is preserved raw and placed in `review_items`; it is not normalized.
- Spatial-aware: features and rule applicability can target zones, overlays, corridors, road classes, schedules, parcels, or named map features.

## Canonical Bundle

The database-loadable JSON root is a bundle:

```json
{
  "standard_version": "0.1.0",
  "bundle_id": "hrm-land-use-2026-04-17",
  "generated_at": "2026-04-17T00:00:00Z",
  "sources": [],
  "documents": [],
  "jurisdictions": [],
  "planning_areas": [],
  "zones": [],
  "spatial_features": [],
  "definitions": [],
  "regulations": [],
  "policies": [],
  "relationships": [],
  "review_items": []
}
```

## Core Records

### Source

`sources` records source files and generated extraction files.

Required fields:

- `source_id`: stable path-derived id.
- `source_type`: `pdf`, `image`, `extracted_json`, `gis_layer`, `database_table`.
- `path`: repository-relative path.
- `official_status`: `official`, `derived`, `unknown`.
- `checksum`: optional.
- `metadata`: source-specific object.

### Document

`documents` records bylaws, planning strategies, schedules, maps, appendices, and extracted section files.

Required fields:

- `document_id`
- `jurisdiction_id`
- `document_type`: `land_use_bylaw`, `zoning_bylaw`, `municipal_planning_strategy`, `secondary_planning_strategy`, `map`, `schedule`, `appendix`, `definitions`, `general_provisions`
- `title_raw`
- `source_ids`
- `effective_date`: nullable.
- `revision_date`: nullable.
- `raw_tree_ref`: pointer to original extracted JSON or source PDF.

### Zone

`zones` records base zones, overlays, comprehensive development districts, planned growth zones, and unmapped text-only zones.

Required fields:

- `zone_id`
- `jurisdiction_id`
- `document_id`
- `zone_code_raw`
- `zone_code_normalized`
- `zone_name_raw`
- `zone_kind`: `base`, `overlay`, `schedule_zone`, `planned_development`, `text_only`, `unknown`
- `classification`: atlas-style class such as `primarily_residential`, `mixed_with_residential`, `nonresidential`, `special`, `planned`, `overlay`, `unknown`
- `mapped_status`: `mapped`, `unmapped`, `partially_mapped`, `unknown`
- `citations`
- `raw_tree_ref`

### Regulation

`regulations` records atomic permissions, dimensional standards, procedural requirements, definitions, prohibitions, bonuses, exceptions, and policy constraints.

Required fields:

- `regulation_id`
- `document_id`
- `applies_to`: array of applicability targets.
- `regulation_type`: `use_permission`, `dimensional_standard`, `parking`, `signage`, `procedure`, `definition`, `policy`, `prohibition`, `exception`, `bonus`, `reference`
- `subject`: normalized subject such as `front_yard_setback`, `lot_area`, `building_height`, `retail_use`, or `policy_im-43`.
- `permission_status`: nullable enum `permitted`, `permitted_with_conditions`, `conditional`, `development_agreement`, `site_plan_approval`, `prohibited`, `not_specified`, `unknown`.
- `value`: nullable value object.
- `conditions`: array of condition objects.
- `source_clause`: raw clause object.
- `citations`
- `normalization_status`: `normalized`, `partial`, `raw_only`, `needs_review`.

### Value

`value` stores both original and normalized values.

```json
{
  "kind": "quantity",
  "comparator": "minimum",
  "original": {
    "amount": 20,
    "unit": "ft",
    "text": "20 ft"
  },
  "normalized": {
    "amount": 6.096,
    "unit": "m",
    "precision": "converted"
  }
}
```

Allowed `kind` values:

- `quantity`
- `percentage`
- `ratio`
- `range`
- `text`
- `formula`
- `boolean`
- `list`
- `reference`

### Condition

`conditions` records context outside the feature.

Examples:

```json
{
  "condition_id": "cond-road-local",
  "condition_type": "road_class",
  "operator": "equals",
  "value": "local",
  "source_text": "Local Street",
  "source_authority": "bylaw_text"
}
```

```json
{
  "condition_id": "cond-primary-residence",
  "condition_type": "operator_residence",
  "operator": "equals",
  "value": "primary_residence",
  "source_text": "provided that the dwelling unit is the primary residence of the operator"
}
```

Condition types should remain open-ended but normalized where repeated:

- `road_class`
- `lot_type`
- `lot_area`
- `frontage`
- `building_type`
- `use_type`
- `adjacent_feature`
- `overlay_presence`
- `planning_area`
- `development_agreement`
- `site_plan_approval`
- `temporal`
- `operator_residence`
- `source_reference`

### Relationship

`relationships` records graph edges between zones, rules, policies, definitions, and features.

Required fields:

- `relationship_id`
- `from_type`
- `from_id`
- `relationship_type`
- `to_type`
- `to_id`
- `resolution_status`: `resolved`, `unresolved`, `cycle_detected`, `blocked_by_review`
- `source_text`
- `citations`

Relationship types:

- `includes_uses_from`
- `subject_to_requirements_of`
- `overrides`
- `modifies`
- `references`
- `implements_policy`
- `requires_development_agreement_under_policy`
- `applies_within_spatial_feature`
- `has_definition`

Recursive zone inclusion should be resolved by traversing `includes_uses_from` and `subject_to_requirements_of` relationships. The traversal must preserve inherited provenance and stop on cycles.

## Clause Handling

Preserve every raw clause label exactly as written in the source.

Approved hierarchy normalization is limited to existing reviewed patterns:

- `21(e)` maps to `21 -> e`
- `21(ea)` maps to `21 -> ea`
- `21(ea)(1)` maps to `21 -> ea -> 1`
- `20(1)(a.1)` maps to `20 -> 1 -> a.1`

If a new pattern appears, create a `review_items` record and do not normalize it. Known review examples include alphanumeric section-style identifiers such as `34B38`.

## Unit Normalization

Preferred normalized units:

- length: `m`
- area: `m2`
- land area: `ha` plus `m2` where query precision requires it
- floor area: `m2`
- percentage: `percent`
- density: `dwelling_units_per_ha`
- parking: `spaces_per_unit`, `spaces_per_m2`, or a formula object

Conversions:

- `ft` to `m`: multiply by `0.3048`.
- `sq ft` to `m2`: multiply by `0.09290304`.
- `acre` to `ha`: multiply by `0.40468564224`.
- `du/acre` to `du/ha`: multiply by `2.4710538147`.

Every conversion must retain:

- original amount
- original unit
- normalized amount
- normalized unit
- conversion factor
- rounding policy
- source text

## Database Mapping

The current `hrm` schema already has useful targets:

- `documents` and `sources` map to `hrm.bylaw` plus `hrm.section_file`.
- `zones` maps to `hrm.zone`.
- `definitions` maps to `hrm.definition`.
- `regulations` maps to `hrm.provision` plus `hrm.rule_atom`.
- `spatial_features` maps to `hrm.spatial_reference`, `hrm.zone_spatial_match`, and `hrm.geometry_registry`.
- `relationships` needs a new table or can temporarily live in `metadata` until a graph table is approved.
- `review_items` needs a new table or can temporarily be emitted as JSON QA output.

Recommended new relational tables before full import:

- `hrm.normalized_bundle`
- `hrm.rule_condition`
- `hrm.rule_value`
- `hrm.rule_relationship`
- `hrm.normalization_review_item`

These are new schema changes and require approval before implementation.

## Converter Run Manifest

Every converter run must write `manifest.json` under `data/normalized/runs/<run-id>/`.

The manifest is required for QA reproducibility and must be treated as part of the generated output. It must not modify source extraction files.

Required fields:

- `run_id`: UTC timestamp id using `YYYYMMDDTHHMMSSZ`.
- `generated_at`: ISO 8601 UTC timestamp.
- `standard_version`: normalized land-use standard version used by the run.
- `schema_path`: repository-relative path to the JSON Schema used for validation.
- `converter`: object containing converter name, version, command, arguments, and working directory.
- `git`: object containing repository root, current commit if available, branch if available, and dirty status.
- `source_inventory`: array of source files read by the converter.
- `output_inventory`: array of generated files written by the converter.
- `validation`: schema validation result summary.
- `qa_summary`: counts of warnings, review items, unresolved relationships, and blocked normalizations.
- `review_policy`: object recording the clause syntax and normalization gates active during the run.

Each `source_inventory` item must include:

- `source_id`
- `path`
- `source_type`
- `bytes`
- `checksum_sha256`, if computed
- `modified_at`, if available
- `role`: `primary_source`, `source_extract`, `schema`, `converter_code`, or `reference`

Each `output_inventory` item must include:

- `path`
- `output_type`: `bundle`, `validation`, `review_items`, `stats`, `community_bundle`, or `manifest`
- `bytes`
- `checksum_sha256`, if computed
- `record_counts`, where applicable

The manifest should also include optional `inputs_filter` fields when a run intentionally covers only part of the repository, such as:

```json
{
  "communities": ["bedford", "regional-centre"],
  "document_types": ["land_use_bylaw"],
  "paths": [
    "data/zoning/bedford",
    "data/zoning/regional-centre"
  ]
}
```

Validation summaries must distinguish:

- `schema_valid`: whether `bundle.json` conforms to `schema/normalized_land_use_bundle.schema.json`.
- `review_blocked_count`: records intentionally not normalized because review is required.
- `relationship_unresolved_count`: references that could not be resolved to a known record.
- `conversion_warning_count`: non-fatal parser or source-quality warnings.

The manifest must be sufficient to answer:

- Which source files were read.
- Which converter version and command produced the output.
- Which schema and standard version governed the output.
- Whether the repository was dirty.
- Which outputs were produced.
- Which issues require human review before database import.

## Current Data Fit

Observed current inputs:

- `data/zoning`: 440 extracted JSON files.
- `data/municipal-planning-strategy`: 172 extracted JSON files.
- Current extracts already contain zones, permitted uses, requirement sections, content blocks, raw clause labels, citations, open issues, and pending review patterns.
- Current examples include imperial and metric dimensional standards.
- Current examples include context-dependent setbacks by road class: local street versus collector or arterial.
- Current examples include recursive references such as one zone allowing uses subject to another zone's requirements.

## Initial Review Gates

- Confirm whether decimal section labels such as `30.1` and `31.2` may be normalized as section identifiers.
- Confirm how alphanumeric labels such as `34B38` should be represented.
- Confirm whether inherited uses should be materialized into each zone at import time or resolved by recursive query views.
- Confirm whether atlas-style simplified fields should be stored as derived columns or generated views.
- Confirm whether source PDFs or current extracted JSON are the legal reconstruction source of record.

## First Implementation Slice

After approval, implement only a narrow slice:

1. Generate one normalized bundle from `data/zoning/bedford` and `data/zoning/regional-centre`.
2. Normalize permitted uses, simple dimensional standards, unit conversions, road-class conditions, citations, and recursive zone-use references.
3. Emit unresolved review items without blocking the bundle.
4. Add fixtures for known cases: `Local Street 20 ft; Collector or Arterial 30 ft`, metric `9.1m`, and inherited `P and POS uses`.
5. Review output before expanding to all communities and MPS policy records.
