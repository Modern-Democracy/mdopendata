# Parcel Lookup — UI kit

A public web app. Type an address or PID, see the parcel's zoning, rules, and citations to the source bylaw.

## Screens (click-through in `index.html`)

1. **Search** — big hero, search input, recent lookups, example addresses.
2. **Results** — parcel card, zone info, regulations table, bylaw clauses, small map.
3. **Clause detail** — full quoted clause + source link.

## Components

- `SearchHero.jsx` — centered hero with input + examples
- `Header.jsx` — thin top bar with wordmark + nav
- `ParcelHero.jsx` — address + PID + zone lockup
- `RegulationsTable.jsx` — table of requirements with clause citations
- `ClauseBlock.jsx` — quoted clause with citation footer
- `MiniMap.jsx` — placeholder parcel map (SVG)
- `Footer.jsx` — citations, last extracted, repo link
