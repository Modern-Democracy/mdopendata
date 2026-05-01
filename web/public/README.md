# Modern Democracy Design System

A cartographic, plain-language civic design system for **Modern Democracy** — a personal brand focused on using machine learning and software to transform public data (especially government open data, and especially spatial data) into knowledge that can be centralized, compared, and mined across jurisdictional boundaries.

The active project is **mdopendata**, a spatial knowledge datastore for Canadian municipal zoning, land-use bylaws, and planning strategies. The first workstream is **Charlottetown, PEI** — normalizing current and draft zoning bylaws and marrying them with a PostGIS spatial database of parcels, streets, wards, and neighbourhoods. The design system is built to accept more municipalities and more data types as workstreams expand.

The front end will be JavaScript/TypeScript with **Leaflet** for mapping, talking to the PostGIS database. This system gives that front end a coherent visual voice from day one.

---

## Context & Sources

- **GitHub repo:** [`Modern-Democracy/mdopendata`](https://github.com/Modern-Democracy/mdopendata) (main branch)
- **Sister repos surveyed:** `md-elections`, `organization-founding-documents`, `llm-tools`, `prompt-management`
- **Key upstream files consulted (cite these when iterating):**
  - `README.md` — workstreams, Charlottetown focus, Python libs
  - `AGENTS.md` — role protocol (Project Management → BA → Architect → Data Engineer → QA)
  - `docs/architecture.md` — five-concern data model (sources, text spans, rules, spatial, meetings)
  - `docs/normalized-land-use-standard.md` — canonical bundle schema, zone/regulation/condition records
  - `templates/charlottetown-*.json` — sample extraction shapes
  - `maps/` — Charlottetown zoning map, cycling map, street map, wards, neighbourhoods

### What mdopendata actually is

A **backend / data-engineering project** — PostGIS schema, Python PDF extractors (`pypdf`, `pdfplumber`, `pymupdf`), QGIS projects, and normalized JSON bundles. The README names "a future web-based public front end" as a goal; the front end will be **JavaScript/TypeScript with Leaflet**, connecting to the PostGIS database.

Current focus: **Charlottetown, PEI** — current + draft zoning bylaws, maps, and the parcel/street/neighbourhood layers, so residents and council can compare rules parcel-by-parcel. The architecture and this design system are both built to accept more municipalities next.

### Products this system covers

1. **Parcel Lookup** — public app; type an address, see its zoning, rules, and citations.
2. **Zoning Comparison** — side-by-side current vs. draft bylaw for a parcel, zone, or neighbourhood.
3. **Map Explorer** — pan/zoom zoning, overlays, wards, neighbourhoods.

Each has a UI kit under `ui_kits/<product>/`.

---

## Index

| Path | Purpose |
|---|---|
| `README.md` | This file — brand context, content & visual foundations, iconography |
| `colors_and_type.css` | CSS custom properties: colors, type, spacing, radii, shadows, semantic tokens |
| `leaflet-theme.css` | Restyles Leaflet's default chrome to match the brand (controls, popups, attribution, scale, tooltip, layer control) |
| `SKILL.md` | Agent-skill entry point — read this first when building for Modern Democracy |
| `assets/` | Logos, monogram, map-marker glyphs, favicons |
| `preview/` | Design-system tab cards (colors, type, components, spacing, brand) |
| `ui_kits/parcel-lookup/` | Public parcel-lookup web app — `index.html` + components |
| `ui_kits/zoning-comparison/` | Side-by-side current vs. draft bylaw viewer |
| `ui_kits/map-explorer/` | Schematic SVG map explorer (no JS deps — useful for mocks and slides) |
| `ui_kits/map-explorer-leaflet/` | **Working Leaflet starter** — OSM tiles + GeoJSON parcels + themed chrome |

---

## Content Fundamentals

The voice follows the **GOV.UK plain-language civic** school: clear, neutral, calm, never bureaucratic, never marketingspeak. Assume the reader is a resident with a stake in their parcel, not a planner.

Modern Democracy is a **personal brand**, so the first-person **"I"** is available and welcome for narrator-voice surfaces (about page, blog, changelogs, commit messages, speaker notes). In the product chrome itself, prefer the neutral register — the interface just does the thing.

- **Person:** Address the reader as **you**. In product chrome, avoid a narrator entirely ("Your parcel is zoned R-1L."). In about/blog/changelog surfaces, **"I"** is the right register ("I normalized Charlottetown's zoning bylaws so you can compare them parcel-by-parcel."). Avoid the royal "we."
- **Casing:** Sentence case everywhere — buttons, headings, menu items, tabs. Acronyms stay uppercased (PID, PEI, HRM, R-1L). Zone codes are uppercase and monospace.
- **Numbers & units:** Metric-first with imperial in parentheses, matching the normalized land-use standard. Example: `540 m² (5,812.5 sq ft)`.
- **Clause references:** Keep raw clause labels exactly as written: `9.1.1`, `20(1)(a.1)`, `34B38`. Use monospace. Prefix with "§" only in prose, never in UI chrome.
- **Status words:** Prefer `Current bylaw` / `Draft bylaw` over "old" / "new." Prefer `Permitted`, `Conditional`, `Prohibited`, `Not specified` (mirror the normalized schema's `permission_status` enum).
- **No emoji.** Civic UI.
- **No exclamation marks** except in destructive-action confirmations ("This cannot be undone.").
- **No marketing tone.** Don't say "beautifully simple" or "powerful insights." Do say "Setbacks, height, and parking for this parcel."
- **Citations are first-class.** Every extracted claim links to a source: PDF path + page + raw clause label. Surface them, don't hide them.
- **Empty states** are honest: "No draft zoning has been published for this parcel yet." not "Nothing here yet! 🎉"

### Example rewrites

| Don't | Do |
|---|---|
| "Oops! We couldn't find that address 😕" | "No match for that address. Check the spelling or try a parcel ID (PID)." |
| "Unlock powerful zoning insights" | "Look up zoning for any address in Charlottetown." |
| "Our amazing zoning comparison tool" | "Compare current and draft zoning, parcel by parcel." |
| "SUBMIT" / "CLICK HERE" | "Look up parcel" / "View on map" |

---

## Visual Foundations

### Palette — **cartographic heritage**

A cream-paper ground with four ink anchors borrowed from printed survey maps and PEI municipal documents:

| Role | Token | Notes |
|---|---|---|
| Paper / ground | `--paper` `#f5efe1` | Warm cream; the default background everywhere |
| Ink / figure | `--ink` `#1a1612` | Warm near-black; body + headings |
| Forest — primary | `--forest` `#1e4d3a` | Institutional anchor; primary buttons, wordmark accents |
| Brick — current | `--brick` `#a8391c` | "Current bylaw" marker, destructive, strong alert |
| Ochre — draft / highlight | `--ochre` `#c89434` | "Draft bylaw" marker, highlight, warning |
| Harbour — links / water | `--harbour` `#2b5d75` | Links, informational, water on maps |

Plus a **zoning-category palette** that mirrors standard cartographic tints — residential tan, commercial rose, institutional slate blue, sage open space, amber mixed-use, seafoam waterfront, wheat agricultural, and so on. Use these _only_ for map fills and zone chips, never for UI chrome.

### Type

Three families, each doing one job:

- **Fraunces** (condensed variable serif, `opsz` range) — display, headings, big numerals. Gives the cartographic / heritage voice. Drop `opsz` into the setting so 84px headings feel poster-like and 14px lede still reads as body serif.
- **IBM Plex Sans** — all UI, body copy, nav, forms. Grotesque, civic, IBM's contribution to the commons; feels at home in a government/data context.
- **IBM Plex Mono** — zone codes (`R-1L`), clause labels (`9.1.1`), numeric tokens, PIDs, coordinates. Monospace is meaningful here — it marks "this is a citable identifier."

### Spacing & layout

- **4pt grid.** Tokens from `--space-1` (4px) through `--space-24` (96px).
- **Reading measure capped at 72ch.** Long bylaw prose gets pulled narrow; data views go edge-to-edge.
- **Hairlines over fills.** Cards, tables, and panels are separated by 1px `--border-hair` rules in cream-edge, not by drop shadows or colored fills, unless the thing is interactive.

### Backgrounds & surfaces

- Almost always **solid paper**. No gradients as the default.
- Sidebars and cards step down through `--paper-2` / `--paper-3`.
- One exception: **hero and print headers may use a subtle paper texture** (noise + horizontal hatch) to evoke the survey-map ground — kept under 4% opacity, never more.
- **No glass / frosted effects.** No blurred blobs. No purple–blue gradients. None of that.

### Borders & radii

- Radii are **small** — `--radius` 4px is the default, `--radius-md` 6px for big cards, `--radius-pill` only for status chips. Print UIs shouldn't look like toy apps.
- Borders are hairlines in `--paper-edge` / `--border`. For emphasis, double the weight to 2px in `--border-bold`, don't switch to a brand color.

### Shadows

- Soft, warm, paper-like: see `--shadow-sm` / `--shadow` / `--shadow-md` / `--shadow-lg`.
- Built from `rgba(26, 22, 18, …)` (warm ink), not cool gray/black. That keeps them feeling printed, not glassy.
- `--shadow-inset` for pressed states.

### Motion

- **Muted and print-like.** No bounces, no springs, no parallax.
- Durations `--dur-fast` (120ms), `--dur` (200ms), `--dur-slow` (320ms).
- Eases `--ease-out` and `--ease-inout`; avoid `ease-in-out` defaults — they feel UI-sloppy.
- Map animations (pan/zoom) use linear or near-linear tweens. Buttons fade their backgrounds, they don't scale.

### States

- **Hover:** darken the fill by ~6% or shift to the `*-ink` token. Never lighten.
- **Press:** drop the fill to the `*-ink` variant + add `--shadow-inset`. No scale transform.
- **Focus:** 2px ring in `--harbour` at 2px offset. Always visible for keyboard users.
- **Selected (tabs, rows):** underline in `--brick` or `--ochre` depending on context (current vs draft), 2px.
- **Disabled:** `opacity: 0.5` on ink, `background: var(--paper-2)`.

### Transparency & blur

- **Rarely used.** A map overlay legend may sit on `rgba(245, 239, 225, 0.92)` with a 1px border. That's about it.
- Never use `backdrop-filter: blur()` as a first choice — it fights the paper metaphor.

### Cards

A card is a **hairline rectangle on slightly darker paper**:
```
background: var(--paper-2);
border: 1px solid var(--border-hair);
border-radius: var(--radius);
padding: var(--space-5);
```
Hover states on interactive cards add `--shadow-sm` and shift the border to `--border`. No colored left-border accents.

### Imagery

- **Maps as imagery.** Zoning polygons, street grids, parcel fabric — these _are_ the imagery. Prefer actual cartographic outputs over stock photography.
- **Photography**, when used, is warm, grainy, documentary — PEI landscapes, Charlottetown streetscapes, public meetings. Never corporate stock.
- **Illustration**, when used, is diagrammatic — isometric parcel blocks, axonometric building massing, survey ticks. Think USGS or the old Halifax planning bulletins.

### Fixed chrome

- Navigation is a slim top bar with the monogram, wordmark, and two or three primary links. Flat background, hairline bottom rule.
- Footers list citations, data sources, last-extracted date, and the GitHub repo.

---

## Iconography

**Line icons, 1.5px stroke, 20×20 canvas, rounded joins.** The visual register is mapping / surveying, not consumer-app.

- **Primary icon system: [Lucide](https://lucide.dev/) via CDN.** Clean, line-based, civic-compatible. Load with:
  ```html
  <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>
  <script>lucide.createIcons();</script>
  ```
  Used for all UI chrome (search, menu, close, arrow, download, share, external-link, etc.).

- **Custom map glyphs** live in `assets/map-glyphs/` — parcel pin, zoning marker, heritage star, overlay hatch, compass rose. These are hand-built to feel consistent with cartographic convention (not Lucide defaults).

- **Zone-code chips** are typographic icons, not glyphs. `R-1L` in IBM Plex Mono on a colored cartographic wash is the icon. Don't invent SVG marks for zone types.

- **No emoji.** Not in content, not in UI.

- **No Unicode-as-icon** except conventional punctuation marks: `§` for sections, `·` for separators, `→` for directional flow, `—` for ranges.

- **No hand-rolled full illustrations.** Where this system ships placeholders (e.g. parcel hero imagery), they are labeled as such and flagged for real cartographic output to be swapped in.

### ⚠︎ Substitutions & placeholders — please review

This design system had **no source UI code, no brand assets, and no logo** to work from. The following are my own calls and I flagged them here so you can confirm or replace:

1. **Fonts.** Fraunces + IBM Plex Sans + IBM Plex Mono — all from Google Fonts, all open-license. Swap freely.
2. **Logo / monogram.** A wordmark in Fraunces, a boxed `MD` monogram, and an `mdopendata` mark with a map-datum square. These are my interpretations; happy to iterate on direction (coat-of-arms? PEI island silhouette? compass rose?).
3. **Palette specifics.** I picked concrete hexes for the cartographic-heritage vibe. Easy to retune — each role has one place in `colors_and_type.css`.
4. **Zone category colors.** Inspired by standard zoning-map convention but not tied to Charlottetown's actual legend — compare to `maps/Charlottetown Zoning Map - March 9, 2026.pdf` and override where they disagree.
5. **Icons.** Lucide CDN. No custom icon set to copy from.
