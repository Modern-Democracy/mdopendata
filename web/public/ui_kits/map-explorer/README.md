# Map Explorer — UI kit

Three-column layout: layer panel · map canvas · selected-parcel panel. The map is a schematic SVG placeholder — in production this would be a tile-based map (Mapbox / Leaflet / MapLibre) with GeoJSON overlays served from PostGIS.

## Components
- Layer panel with base layers, overlays, and bylaw-version toggle
- Search overlay (top-left, floating)
- Map controls (zoom, recenter, layers)
- Legend (bottom-right)
- Scale bar (bottom-left)
- Selected parcel card + nearby-changes list
