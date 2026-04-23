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

## Python environment

Use `.venv` as the canonical project Python environment for PDF extraction, JSON conversion, schema validation, GIS processing, and database import scripts. QGIS MCP remains separate because it runs under QGIS's bundled Python and uses `.qgis-mcp-packages` plus `qgis_mcp_vendor`.

Create or refresh the project environment from the root `pyproject.toml`:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install .
```

For a repeatable install using the exact package versions validated for this repository, install from the lockfile after creating `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps .
```

Run project Python scripts through:

```powershell
.\scripts\python.ps1 .\scripts\validate-code-table-candidates.py
```

### Current approved Python libraries

- `pypdf`: Primary text extraction from bylaw and planning PDF documents through `PdfReader` and `page.extract_text()`.
- `pymupdf`: PDF layout, word-position, drawing, and vector-content inspection through the `fitz` import.
- `pdfplumber`: Table-like PDF text extraction where coordinates, text boxes, and visual layout matter.
- `jsonschema`: Validation of extracted JSON and normalized bundles against repository schemas.
- `python-dateutil`: Date parsing and date utilities for metadata, source dates, amendments, and future document ingestion.
- `numpy`: Numeric array foundation for raster, geometry, image, and tabular processing.
- `pandas`: Dataframe processing for extracted attributes, spatial joins, QA summaries, and import preparation.
- `pillow`: Image handling for PDF-derived images, raster sources, and map processing workflows.
- `opencv-python`: Image preprocessing, color segmentation, contour detection, and raster map workflows.
- `shapely`: Geometry operations including polygon creation, union, intersection, and validity repair.
- `pyproj`: Coordinate reference system transforms and reprojection.
- `geopandas`: Spatial dataframe workflows that combine geometry with tabular attributes.
- `pyogrio`: Fast vector GIS file I/O, especially GeoPackage and shapefile-style sources.
- `rasterio`: Raster reading, writing, sampling, georeferencing, and map raster processing.
- `sqlalchemy`: Database connection and SQL execution layer for import and review scripts.
- `psycopg[binary]`: PostgreSQL driver for direct database access.
- `geoalchemy2`: PostGIS geometry support for SQLAlchemy workflows.
- `rapidfuzz`: Fast fuzzy matching for zone names, land-use terms, definitions, and noisy extraction cleanup.

### Future Python libraries to consider

- `camelot-py`: PDF table extraction for lattice and stream tables when source PDFs contain extractable table structures.
- `tabula-py`: Java-backed PDF table extraction fallback for sources that Camelot or pdfplumber do not handle well.
- `pdfminer.six`: Lower-level PDF text layout extraction when `pypdf` or PyMuPDF ordering is insufficient.
- `scikit-image`: Image morphology and segmentation for scanned maps and zoning-map cleanup.
- `lxml`: Robust XML and HTML parsing for future municipal web pages, agendas, and exported structured documents.
- `pytesseract`: Python wrapper for Tesseract OCR when scanned PDFs or images need text recognition.
- `ocrmypdf`: Adds searchable text layers to scanned PDFs before extraction workflows.
- `networkx`: Graph traversal for zone inheritance, cross-references, definitions, amendments, and policy dependencies.
- `pydantic`: Typed validation for internal normalized objects before writing JSON or database rows.
- `duckdb`: Fast local analytics over JSON, CSV, Parquet, and spatial extensions for QA and exploratory joins.
- `pyarrow`: Columnar data interchange and Parquet support for larger extracted datasets.
- `dask`: Larger-than-memory dataframe processing if source volume grows substantially.
- `rtree`: Optional spatial indexing support for workloads that need it beyond the installed geometry stack.
- `fiona`: Legacy vector I/O fallback when a GIS workflow requires it and `pyogrio` is insufficient.

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

- OCR tooling is not part of the approved project Python environment yet
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
