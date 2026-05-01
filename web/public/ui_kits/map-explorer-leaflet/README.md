# Map Explorer (Leaflet) — UI kit

Working Leaflet skeleton, themed to match the cartographic-heritage palette. Intended as the starting point for the real front end that will talk to the PostGIS backend.

## Stack

- **Leaflet 1.9.4** from CDN
- **OpenStreetMap** tiles at 45% opacity (so the zoning polygons read as the figure, not the ground) — swap to your own tile provider or self-hosted tiles in production
- **GeoJSON** for parcels — currently a hardcoded FeatureCollection near Charlottetown City Hall; swap for a `fetch('/api/parcels?bbox=…')` hitting your PostGIS-backed endpoint
- **`leaflet-theme.css`** (at project root) — restyles Leaflet's default chrome (zoom, popups, attribution, scale, tooltip, layer control) to match the brand

## Data shape the layer expects

Each GeoJSON feature's `properties`:
```json
{
  "pid": "421009",
  "addr": "81 University Avenue",
  "zone": "C-2",
  "zoneName": "General commercial",
  "zoneClass": "commercial",
  "area_ha": 0.14,
  "lot_area": "1,400 m²",
  "height_max": "14.0 m",
  "front_yard": "3.0 m",
  "parking": "1 / 30 m²"
}
```

`zoneClass` ∈ `residential | commercial | mixed | institutional | openspace | waterfront | heritage | agricultural` — this drives the fill color via the `--zone-*` CSS variables.

## Wiring to your PostGIS backend

Replace the `PARCELS` constant with something like:

```js
const bounds = map.getBounds();
const res = await fetch(`/api/parcels.geojson?bbox=${bounds.toBBoxString()}`);
const PARCELS = await res.json();
```

Hook `moveend` / `zoomend` to refetch on viewport change. For large layers, switch to vector tiles (`Leaflet.VectorGrid`) or the `mapbox-gl-leaflet` plugin.
