# mdopendata Spatial Knowledge Datastore

This repository now has a concrete path toward a spatially-aware datastore for land use, development controls, and municipal business records.

## Current source inventory

The repository currently contains:

- Official plan PDF and future land use map
- Zoning bylaw PDF and zoning map
- General city maps such as wards, neighborhoods, truck routes, cycling, parks, and streets

The repository does not yet contain council agendas, minutes, committee packets, permit records, or parcel geometry. Those sources are required for full day-to-day operational queries.

## Target outcome

Build a datastore that can answer questions such as:

- What zoning rules apply to a parcel or location
- What official plan designation overlaps that same location
- What uses, setbacks, density, height, parking, and overlay constraints apply
- Which council or committee decisions affect that area, zone, or policy topic
- Which meetings discussed a specific address, development application, street, or neighborhood

## Recommended datastore

Use PostgreSQL with PostGIS as the canonical query layer.

Reasons:

- Strong spatial joins and indexing
- Good fit for parcel, zone, ward, neighborhood, and application geometries
- Full-text search can coexist with structured land-use rules
- Easy to add embeddings later without changing the core schema

The repository includes a starter schema at [schema/sql/postgis.sql](/D:/opendata/mdopendata/schema/sql/postgis.sql).

## Local database and MCP

The repository now includes a local PostGIS runtime and MCP wiring:

- Docker service: [docker-compose.yml](/D:/opendata/charlottown/docker-compose.yml)
- MCP config: [.mcp.json](/D:/opendata/charlottown/.mcp.json)
- Setup guide: [POSTGIS-MCP.md](/D:/opendata/charlottown/POSTGIS-MCP.md)

Use the MCP server for read-only inspection and querying. Load data through PostgreSQL tools or repository ingestion scripts.

## Data model

The model separates five concerns:

1. Source documents
2. Extracted text blocks and citations
3. Structured land-use rules
4. Spatial features and overlays
5. Municipal business records such as meetings, agenda items, motions, and decisions

This allows one query to combine a parcel geometry, a zoning rule, and a meeting decision with traceable citations.

## Ingestion strategy

### Phase 1: inventory and classify

Run:

```powershell
npm run inventory
```

This writes a machine-readable source manifest to `data/manifest/sources.json`.

### Phase 2: extract

For each source:

- Text PDFs: extract text with page-level coordinates where possible
- Map PDFs: extract vector layers if available; otherwise render and georeference for OCR/manual digitization
- Images: OCR and classify legends, labels, and map content

### Phase 3: normalize

Normalize extracted content into:

- `documents`
- `document_pages`
- `text_spans`
- `land_use_rules`
- `spatial_features`
- `meetings`
- `agenda_items`
- `decisions`

### Phase 4: spatial linking

Link:

- parcels to zones
- parcels to future land use designations
- parcels to wards and neighborhoods
- agenda items and decisions to locations, parcels, streets, and policy topics

## Current implementation

Added in this repository:

- Source inventory builder: [src/build-inventory.js](/D:/opendata/charlottown/src/build-inventory.js)
- PostGIS starter schema: [schema/sql/postgis.sql](/D:/opendata/mdopendata/schema/sql/postgis.sql)
- Detailed design notes: [docs/architecture.md](/D:/opendata/charlottown/docs/architecture.md)

## Known gaps

- No OCR or PDF parsing dependency is installed in this environment
- No parcel dataset is present
- No council or committee records are present
- No georeferencing metadata is present for the map documents

## Next implementation step

The next practical step is to install extraction tooling and add parsers for:

- zoning bylaw text
- official plan text
- zoning map features
- future land use map features
- meeting agendas and minutes when added
