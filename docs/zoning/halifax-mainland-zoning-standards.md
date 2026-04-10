# Halifax Mainland Zoning JSON Standards

## Purpose

This document defines the first repository standard for translating Halifax Mainland Land Use By-law zone content into machine-usable JSON that can later be loaded into PostgreSQL and PostGIS.

The immediate scope is the `R-1` zone, but the structure is intended to scale across all zone sections that begin after Section `16(1)`.

## Source scope

- Source document: `docs/halifaxmainlandlanduseby-law-edition231-eff-26feb02-minorrev2025-02922-toclinked_1.pdf`
- Shared setup sections: `15` through `19`
- Zone list section: `16(1)` and `16(2)`
- First zone implementation: `R-1 ZONE: SINGLE FAMILY DWELLING ZONE`, Sections `20` through `23E`

## Core design rules

1. Preserve every clause label exactly as written in the source under a `*_raw` field.
2. Normalize hierarchy only for clause patterns already approved in this repository context.
3. Store atomic rules whenever a clause expresses a single measurable requirement, permission, prohibition, or exception.
4. Keep paraphrased summaries separate from citation metadata so the source can be re-checked.
5. Represent area-limited permissions and exceptions with explicit applicability scopes plus a linked spatial feature backlog entry when geometry is needed.
6. Carry repealed or deleted clauses forward as explicit records when they appear inside the active zone section, because later amending by-laws may still cross-reference them.

## Clause label policy

### Approved normalization

The currently approved hierarchy interpretation is:

- `20(1)(a.1)` -> `["20","1","a.1"]`
- `21(e)` -> `["21","e"]`
- `21(ea)` -> `["21","e","a"]`
- `21(ea)(1)` -> `["21","e","a","1"]`
- `23A` -> `["23","A"]`
- `23E(1)` -> `["23","E","1"]`
- `23E(1)(a)` -> `["23","E","1","a"]`

This same pattern is safe for similar letter-pair subsection labels such as `20(1)(ba)`, `20(1)(ja)`, and `21(ca)`.

### Preserve raw and mark pending review

The following patterns must remain raw until explicitly reviewed:

- Any future pattern equivalent to `34B38`

For those cases:

- keep `clause_label_raw` or `section_label_raw`
- set normalized path to `null`
- set a status flag such as `pending_review_dotted_subclause` or `pending_review_alphanumeric_section`
- add the example to the zone file `open_issues`

## Zone JSON top-level structure

Each zone file should contain these top-level objects:

- `document_metadata`
- `normalization_policy`
- `general_context`
- `permitted_uses`
- `prohibitions`
- `requirements`
- `sign_controls`
- `use_specific_standards`
- `spatial_features_needed`
- `open_issues`
- `citations`

This keeps shared zone identity separate from rule records and leaves room for later ingestion into atomic database tables.

## Rule type taxonomy

Use these standard categories unless the source requires a new reviewed type:

- `principal_use`
- `residential_use`
- `accessory_use`
- `ancillary_nonresidential_use`
- `institutional_or_open_space_use`
- `recreation_use`
- `site_specific_residential_use`
- `use_with_specific_standard`
- `development_prohibition`
- `use_prohibition`
- `lot_frontage_minimum`
- `lot_area_minimum`
- `lot_coverage_maximum`
- `building_height_maximum`
- `front_yard_setback_minimum`
- `rear_yard_setback_minimum`
- `side_yard_setback_minimum`
- `building_separation_minimum`
- `yard_and_building_separation_bundle`
- `accessory_building_setbacks`
- `accessory_building_rear_yard_exemption`
- `backyard_suite_exemption`
- `corner_lot_flanking_street_setback`
- `site_specific_lot_area_override`
- `notwithstanding_override`
- `repealed`

If a later zone introduces a materially different by-law pattern, add a new type only after confirming it is not representable with the existing list.

## Applicability scope codes

Use explicit scope codes instead of free-form text wherever possible.

Current codes required by `R-1`:

- `all_r1_lands`
- `urban_service_area_only`
- `mainland_south_area_inland_watercourse_lots_only`
- `zm_33_townhouse_building_lands_only`

When adding a new code:

1. define it in the zone JSON
2. describe its geographic trigger in `spatial_features_needed`
3. add it to the future shared code table once reused

## Measurement and unit standards

Use numeric fields whenever the by-law provides a measurable threshold.

Current unit codes:

- `ft`
- `sq_ft`
- `percent`
- `acre`
- `space`
- `unit`
- `facility`
- `full_storey`
- `ft_per_unit`
- `sq_ft_per_unit`

Use `condition_text` for qualifiers that cannot yet be modeled as structured comparators, such as:

- frontage reduction on cul-de-sac bulbs
- zero side yard where townhouse units share a common wall
- parking space exclusive of front yard

## Citation standard

Every rule block should carry source traceability with:

- `pdf_page`
- `bylaw_page`
- `section_label_raw` or `clause_label_raw`

Use `pdf_page_start` and `pdf_page_end` when a rule spans multiple pages.

Do not rely only on page text order. The stored citation must allow later reconstruction against the PDF.

## Shared versus zone-specific rules

Separate rules into these buckets:

1. `general_context`
   Use for shared provisions such as zone establishment, boundary interpretation, and other sections that apply broadly across zones.
2. `permitted_uses`
   Use for the zone entry list that enumerates what may occur in the zone.
3. `prohibitions`
   Use for clauses that explicitly deny other uses or development.
4. `requirements`
   Use for dimensional controls, area-specific overrides, accessory building rules, and corner-lot rules.
5. `sign_controls`
   Use when the zone has a dedicated sign section.
6. `use_specific_standards`
   Use for detailed standards attached to a particular permitted use or site-specific use.

This split maps cleanly onto the existing repository target tables `land_use_rules`, `rule_applicability`, and `spatial_features`.

## Spatial feature capture standard

Every geographic trigger must be represented as one of these:

- `planning_area_boundary`
- `subdivision_boundary`
- `site_specific_area`
- `hydrography_line_or_polygon`
- `road_centerline`
- `address_or_parcel_exception`

Every spatial backlog entry should state:

- `feature_key`
- `feature_class`
- `source_type`
- `reason`

Recommended `source_type` values:

- `existing_or_derived_polygon`
- `external_geospatial_layer`
- `polygon_from_zm_33`
- `schedule_digitization`
- `base_map_reference`
- `parcel_or_address_lookup`

## R-1 spatial dependencies identified

The `R-1` zone already requires these spatial features:

- Urban Service Area boundary
- Mainland South Area boundary
- Inland watercourses
- Parkmoor Ridge Subdivision boundary
- ZM-33 compact lot area
- ZM-33 moderate lot area
- ZM-33 townhouse building area
- Schedule A wetland area between Boscobel Road and Purcell's Cove Road
- Boscobel Road reference geometry
- Purcell's Cove Road reference geometry
- Civic number `290 Purcell's Cove Road` as an exception target

## One-off variation handling

The current source already shows several variation patterns that the standard must preserve:

- inserted dotted clauses such as `a.1`
- inserted letter-pair clauses such as `ba`, `ca`, `ga`, `ja`
- notwithstanding overrides replacing an earlier requirement bundle
- map-based subareas identified by schedule or zoning map label
- address-specific carve-outs
- deleted or repealed provisions still present in section flow
- cross-references to rules outside the current zone section

These are not edge noise. They are part of the actual zoning logic and must survive normalization.

## Mapping to database tables

Planned relational mapping:

- `document_metadata` -> `documents`
- page citations -> `document_pages` and `text_spans`
- atomic controls and permissions -> `land_use_rules`
- applicability scopes and geometry links -> `rule_applicability`
- geometry backlogs and derived polygons -> `spatial_features`

The zone JSON is therefore the intermediate canonical representation, not the final database shape.

## Current review-required examples

These raw clause formats still require explicit repository review before broader rollout:

- any future dotted subtype outside the approved `a.1` style handling
- any future alphanumeric section-style identifier outside the approved `23A` and `23E(1)` style handling
- any future pattern equivalent to `34B38`

## Next conversion workflow

For each additional zone:

1. capture zone title and section range
2. extract permitted uses
3. extract prohibitions
4. extract dimensional and operational requirements
5. extract area-specific overrides and schedule references
6. register all spatial triggers
7. record unresolved clause patterns before normalization

This allows zone-by-zone expansion without losing source fidelity.
