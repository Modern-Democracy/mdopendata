---
type: implementation
tags:
  - web-ui
  - design-kit
  - charlottetown
  - postgis
updated: 2026-05-01
---

This page plans the design-kit replacement of the current web page with a database-backed Charlottetown parcel lookup, map explorer, and zoning comparison demo.

# Web Demo Design Kit Plan

## Objective

Replace the current static review page at `web/public/index.html` with a functional demo site based on the four design-kit folders in `web/public/ui_kits`.

The landing page should be the parcel lookup experience. A selected address should resolve to a parcel and route into a map explorer centered on that parcel. The map explorer should support current and draft zoning overlays, selected-parcel details, and a `Compare to draft` flow into the zoning comparison page. A separate city-view map route should allow map browsing without starting from a parcel.

## Design-Kit Inputs

| Design kit | Demo route | Functional role |
| --- | --- | --- |
| `web/public/ui_kits/parcel-lookup` | `/` or `/parcel-lookup` | Address or PID search with autocomplete, parcel result preview, and selection redirect. |
| `web/public/ui_kits/map-explorer` | `/map-explorer?pid=...` | Parcel-focused map view after lookup, with selected parcel, base layers, overlays, and comparison action. |
| `web/public/ui_kits/zoning-comparison` | `/zoning-comparison?pid=...` | Current-versus-draft zone and rule comparison for the selected parcel. |
| `web/public/ui_kits/map-explorer-leaflet` | `/city-view` or `/map` | Leaflet-based city map for browsing, parcel selection, overlays, and future non-parcel-specific features. |

## Current Technical Baseline

The web app is a small Node.js service in `web/server.js` that serves static files from `web/public` and exposes PostgreSQL-backed JSON APIs. Current APIs are limited to `zoning.section_equivalence` review workflows.

Known database inputs for the demo include:

- `public."CHTWN_Civic_Addresses"` for address autocomplete and PID lookup.
- `public."CHTWN_Parcel_Map"` for current parcel geometry.
- `public."CHTWN_Draft_Parcel_Map"` for draft parcel geometry or draft parcel candidates.
- `public."CHTWN_Zoning_Boundaries"` for current zoning polygons.
- `public."CHTWN_Draft_Zoning_Boundaries"` for draft zoning polygons and draft `zone_code` / `zone_name` attributes.
- `zoning.section`, `zoning.clause`, `zoning.raw_table`, and related tables for bylaw text and citations where parcel zones need rule context.

## Target Information Architecture

Use static HTML, CSS, and browser JavaScript for the demo unless shared routing or state becomes large enough to justify a frontend build system.

Recommended routes:

- `/`: parcel lookup landing page.
- `/parcel-lookup`: alias for the landing page.
- `/map-explorer?pid=PID` or `/map-explorer?addressId=ID`: parcel-centered map.
- `/zoning-comparison?pid=PID`: current and draft zoning comparison.
- `/city-view`: general Leaflet city map.
- `/api/addresses?q=TEXT`: autocomplete results with address label, PID, coordinate, and confidence fields.
- `/api/parcels/:pid`: selected parcel summary, geometry, current zone, draft zone, and source status.
- `/api/parcels.geojson?bbox=...`: viewport parcel GeoJSON for city-view and map explorer.
- `/api/zoning/current.geojson?bbox=...`: current zoning polygons.
- `/api/zoning/draft.geojson?bbox=...`: draft zoning polygons.
- `/api/zoning-comparison/:pid`: current-versus-draft zone summary, changed attributes, and citations.

## Database Connection Steps

1. Normalize address labels in the API layer from `STREET_NO`, `STREET_NM`, `APT_NO`, `COMM_NM`, and `PID` in `public."CHTWN_Civic_Addresses"`.
2. Add indexed search support for autocomplete. Start with `ILIKE` plus limit for the demo; move to generated `tsvector`, trigram, or materialized lookup table if response time is poor.
3. Resolve selected addresses to parcels by PID first, then fall back to spatial point-in-polygon where PID is missing or inconsistent.
4. Resolve parcel zones with spatial joins against current and draft zoning layers. Record overlap area and choose the largest-overlap zone when multiple zones intersect a parcel.
5. Return geometries as web map GeoJSON using `ST_AsGeoJSON(ST_Transform(geom, 4326))`.
6. Add bounding-box endpoints that filter with `ST_MakeEnvelope(..., 4326)` transformed to each source geometry SRID as needed.
7. Connect zone codes to zoning bylaw text through existing `zoning` tables where a stable zone-code relationship exists. Where it does not exist, show zone labels first and mark rule details as pending.
8. Add response metadata for data freshness, source table, and unresolved match status so demo users can distinguish confirmed data from provisional joins.

## UI Cleanup Steps

1. Extract shared header, navigation, logo, buttons, forms, map controls, legends, and parcel cards from the kit HTML into reusable static patterns or a small client-side module.
2. Replace mockup logos with the `Island as needle` mark from `web/public/preview/brand-logo-explorations.html`. Promote the chosen mark into `web/public/assets` as a reusable SVG before wiring it into pages.
3. Replace schematic map placeholders with Leaflet map containers using `web/public/leaflet-theme.css`.
4. Replace hardcoded parcel and zoning values with API data. Keep deterministic fallback examples only for local demo smoke tests.
5. Align route names, query parameters, selected parcel state, and `Compare to draft` behavior across all pages.
6. Remove mockup-only copy, duplicate inline styles, and unused kit-specific assets after each page is wired.
7. Add loading, empty, no-match, multiple-match, and API-error states for address search, parcel lookup, map layers, and zoning comparison.

## Functional Demo Acceptance Criteria

- Opening `/` shows the parcel lookup page, not the current section-equivalence review page.
- Typing part of a Charlottetown address returns autocomplete suggestions from the database.
- Selecting an address routes to `/map-explorer` and centers the map on the selected parcel.
- The map displays a base layer, selected parcel geometry, current zoning, and draft zoning overlay options.
- Clicking `Compare to draft` routes to `/zoning-comparison` for the same selected parcel.
- The comparison page shows current zone, draft zone, change status, and citations or explicit pending markers for missing rule links.
- Opening `/city-view` loads a browsable Leaflet map without requiring a selected parcel.
- Parcel selection from `/city-view` can open the parcel-focused map or comparison page.
- Demo pages use the selected `Island as needle` logo and no mockup placeholder branding remains.

## Timeline

| Phase | Status | Estimate | Deliverable |
| --- | --- | --- | --- |
| 1. Inventory and routing | Complete | 0.5 day | Route map, kit asset inventory, chosen logo asset, and static page entry points. |
| 2. Address and parcel APIs | Complete | 1 day | `/api/addresses`, `/api/parcels/:pid`, selected parcel geometry, and address-to-parcel resolution. |
| 3. Map data APIs | Complete | 1 to 1.5 days | GeoJSON endpoints for parcels, current zoning, draft zoning, and bbox filtering. |
| 4. Parcel lookup page | Complete | 0.5 to 1 day | Landing page wired to autocomplete and redirect behavior. |
| 5. Parcel map explorer | Complete | 1 to 1.5 days | Leaflet parcel-centered map, layer controls, selected parcel panel, and comparison redirect. |
| 6. City-view map | Complete | 0.5 to 1 day | Browse-first Leaflet map with viewport loading and parcel click selection. |
| 7. Zoning comparison page | Not started | 1 day | Current/draft zone comparison backed by parcel and zone APIs, with citation or pending states. |
| 8. Cleanup and demo hardening | Not started | 1 day | Logo replacement, mockup cleanup, loading/error states, responsive QA, and scripted smoke checks. |

Expected effort for a functional local demo is 6 to 8 working days if the current spatial tables are already loaded, indexed, and geometrically valid enough for viewport and parcel joins.

## Phase 1 Progress

Completed on 2026-05-01.

Route entry points are handled in `web/server.js` and currently map to the existing design-kit HTML without modifying the kit originals:

- `/` and `/parcel-lookup` load `web/public/ui_kits/parcel-lookup/index.html`.
- `/map-explorer` loads `web/public/ui_kits/map-explorer/index.html`.
- `/city-view` and `/map` load `web/public/ui_kits/map-explorer-leaflet/index.html`.
- `/zoning-comparison` loads `web/public/ui_kits/zoning-comparison/index.html`.

The server injects a route-specific `<base>` tag for these aliases so existing relative kit assets continue to resolve.

Current asset inventory:

- Shared design tokens: `web/public/colors_and_type.css`.
- Shared Leaflet theme: `web/public/leaflet-theme.css`.
- Existing brand assets: `web/public/assets/logo-mdopendata.svg`, `web/public/assets/logo-monogram.svg`, and `web/public/assets/logo-wordmark.svg`.
- Selected promoted logo asset: `web/public/assets/logo-island-needle.svg`.
- Kit-specific parcel lookup CSS: `web/public/ui_kits/parcel-lookup/styles.css`.
- UI kit source pages and notes: the four `web/public/ui_kits/*` folders listed in this plan.

## Phase 2 Progress

Completed on 2026-05-01.

The web server now exposes the first parcel demo APIs:

- `/api/addresses?q=TEXT&limit=N` searches `zoning.v_charlottetown_civic_addresses`, normalizes address labels from civic address attributes, returns PID, WGS84 point coordinates, confidence, and source metadata.
- `/api/parcels/:pid` resolves PID through the civic address layer, finds the containing current parcel candidate polygon, returns WGS84 selected parcel geometry, centroid, current zone, draft zone, and explicit resolution/source status.

Parcel identity remains provisional because `zoning.v_charlottetown_parcel_map` does not expose native PID fields. The API reports `parcelPidNative: false` and uses `address_pid_to_point_in_parcel` when a civic address point resolves to a containing parcel polygon.

## Phase 3 Progress

Completed on 2026-05-01.

The web server now exposes viewport-oriented GeoJSON APIs:

- `/api/parcels.geojson?bbox=west,south,east,north&limit=N` returns parcel candidate polygons from `zoning.v_charlottetown_parcel_map`.
- `/api/zoning/current.geojson?bbox=west,south,east,north&limit=N` returns current zoning polygons from `zoning.v_charlottetown_current_zoning_boundaries`.
- `/api/zoning/draft.geojson?bbox=west,south,east,north&limit=N` returns draft zoning polygons from `zoning.v_charlottetown_draft_zoning_boundaries`.

All three endpoints accept WGS84 bboxes, transform the envelope to source SRID 2954 for filtering, and return WGS84 GeoJSON FeatureCollections with source metadata. The default feature limit is 1000 and the maximum accepted limit is 5000.

## Phase 4 Progress

Completed on 2026-05-01.

The parcel lookup landing page now uses the live `/api/addresses` endpoint for debounced civic address and PID search. The page shows loading, empty, API-error, and result-list states, supports mouse selection and basic keyboard movement through matches, and redirects selected address rows with a PID to `/map-explorer?pid=PID`.

The page also switches the header logo from the mock wordmark asset to `web/public/assets/logo-island-needle.svg` and links the main navigation entries to the planned demo routes.

## Phase 5 Progress

Completed on 2026-05-01.

The parcel-focused map explorer at `/map-explorer?pid=PID` now loads `/api/parcels/:pid`, centers Leaflet on the selected parcel geometry, and displays the selected parcel with current and draft zone summaries. It loads viewport-filtered parcel outlines, current zoning polygons, and draft zoning polygons through the phase 3 GeoJSON APIs, exposes layer toggles with visible feature counts, and keeps the selected parcel highlighted above overlay layers.

The right panel now shows selected-address, PID, parcel area, current zone, draft zone, overlap areas, resolution status, and a `Compare to draft` link to `/zoning-comparison?pid=PID`.

## Phase 6 Progress

Completed on 2026-05-01.

The city-view map at `/city-view` now loads live Leaflet viewport layers from `/api/parcels.geojson`, `/api/zoning/current.geojson`, and `/api/zoning/draft.geojson`. The page supports current zoning, draft zoning, and parcel-outline toggles with visible feature counts, status messages, and source notes.

Parcel click selection now resolves a clicked WGS84 point through `/api/parcels/point?lon=...&lat=...`, finds the containing parcel, and selects the nearest civic-address PID inside that parcel when available. A resolved PID enables `Open full parcel` routing to `/map-explorer?pid=PID` and `Compare to draft` routing to `/zoning-comparison?pid=PID`.

## Risks and Open Decisions

- Parcel identity may be unstable if `CHTWN_Parcel_Map` and `CHTWN_Draft_Parcel_Map` do not share PID attributes. The demo should prefer civic-address PID and spatial joins until a durable parcel key is confirmed.
- Current zoning polygons expose `ZONING`, while draft zoning polygons expose `zone_code` and `zone_name`. The API should normalize these names before the browser sees them.
- Rule-level comparison depends on a stable link between parcel zone codes and extracted bylaw sections or structured facts. If the link is incomplete, the first demo should compare zones and cite source status rather than invent rule diffs.
- Autocomplete quality depends on address normalization. Apartment numbers, alternate street names, and duplicate PIDs need explicit handling before public use.
- Large GeoJSON responses may become slow. If viewport endpoints are too heavy, move zoning and parcel layers to vector tiles or simplify geometries for demo zoom levels.

## Sources

- [Web UI stack](./web-ui-stack.md)
- [Root wiki index](../index.md)
- [Charlottetown wiki index](../charlottetown/index.md)
- [Web server](../../web/server.js)
- [Parcel lookup UI kit](../../web/public/ui_kits/parcel-lookup/README.md)
- [Map explorer UI kit](../../web/public/ui_kits/map-explorer/README.md)
- [Map explorer Leaflet UI kit](../../web/public/ui_kits/map-explorer-leaflet/README.md)
- [Zoning comparison UI kit](../../web/public/ui_kits/zoning-comparison/README.md)
- [Logo explorations](../../web/public/preview/brand-logo-explorations.html)
