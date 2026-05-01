---
name: modern-democracy-design
description: Use this skill to generate well-branded interfaces and assets for Modern Democracy — a personal brand focused on transforming public data (especially spatial open data) into knowledge that can be compared across boundaries. Current workstream is mdopendata: Canadian municipal zoning and land-use bylaws, starting with Charlottetown, PEI. Contains design guidelines, colors, type, fonts, logos, a Leaflet theme, and UI kit components for parcel lookup, bylaw comparison, and map exploration.
user-invocable: true
---

# Modern Democracy Design System

Read `README.md` within this skill first — it contains context, content fundamentals, visual foundations, and iconography rules. Then explore the other files.

## What's here

- `README.md` — brand context, content & visual foundations, iconography
- `colors_and_type.css` — CSS custom properties for colors, type, spacing, radii, shadows, and semantic element styles (h1–h4, code, p, etc.)
- `leaflet-theme.css` — restyles Leaflet's default controls/popups/attribution/scale/tooltip to match the brand; load AFTER `leaflet.css`
- `assets/` — logos (`logo-wordmark.svg`, `logo-monogram.svg`, `logo-mdopendata.svg`)
- `preview/` — design-system specimen cards
- `ui_kits/parcel-lookup/` — public parcel-lookup web app
- `ui_kits/zoning-comparison/` — current-vs-draft bylaw diff viewer
- `ui_kits/map-explorer/` — schematic SVG map (for mocks and slides)
- `ui_kits/map-explorer-leaflet/` — **working Leaflet starter** with themed chrome, OSM tiles, and a GeoJSON parcel layer

## How to use it

If you're building **visual artifacts** (slides, mocks, throwaway prototypes, one-off demos):

- Link `colors_and_type.css` from your HTML.
- Copy logos out of `assets/` and reference them directly — do not redraw them.
- Use Lucide via CDN for icons (`<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>` then `lucide.createIcons()`).
- Load Fraunces, IBM Plex Sans, and IBM Plex Mono from Google Fonts.
- Lift components (search box, parcel hero, regulations table, clause block, diff row, map controls) out of the UI kits rather than rebuilding.
- Write copy in the plain-language civic voice documented in README's **Content Fundamentals** — sentence case, metric-first with imperial in parens, clause labels in mono, no emoji, no marketing tone.

If you're working on **production code** (JavaScript/TypeScript + Leaflet + PostGIS is the canonical stack):

- Copy `colors_and_type.css` into the project and wire the CSS custom properties into your app's theme.
- Copy `leaflet-theme.css` in too, and load it AFTER `leaflet.css`.
- Copy logo SVGs into the project's asset pipeline.
- Use the UI kit files as reference implementations — they are cosmetic recreations, not production-ready; translate the patterns into your framework/styling setup. `ui_kits/map-explorer-leaflet/index.html` is the closest to a real starter — swap its hardcoded GeoJSON for a fetch against your PostGIS endpoint.
- Keep the content rules (README's **Content Fundamentals**) in front of whoever writes copy.

## If invoked with no guidance

Ask what the user wants to build or design. A few good starting questions:

- Which product — parcel lookup, bylaw comparison, map explorer, council-facing slide deck, something new?
- Is this a throwaway mock or production code?
- Which municipality? (Charlottetown is the canonical reference; anywhere else needs a palette/legend sanity check.)
- Do they want the full brand voice, or just the visual tokens?

Then act as an expert designer for Modern Democracy — outputting HTML artifacts or production-targeted components depending on the need.

## Non-negotiables

- **No emoji** in UI or copy.
- **No purple–blue gradients**, no glass/frosted effects, no bouncy springs. This is a print-informed civic system.
- **Citations are first-class** — every extracted bylaw claim should link back to a source document + page + raw clause label.
- **Zone codes and clause labels go in IBM Plex Mono**, always.
- **Metric first**, imperial in parens: `540 m² (5,812.5 sq ft)`.
- **Sentence case** for all UI — buttons, headings, menu items, tabs.
