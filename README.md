# mdopendata Spatial Knowledge Datastore

This repository converts open data from public sources into PostGIS database sources and QGIS projects for visualization, spatial analysis, and future public-facing tools.

## Project Status

The project began with two initial workstreams:

- PEI corporate land use: bring in the 2010 and 2020 Prince Edward Island corporate land use layers for spatial comparison of changing land use.
- Halifax Regional Municipality planning data: extract land use bylaws, municipal planning strategy documents, and related spatial layers into normalized content for cross-boundary analysis.

Both workstreams are currently on hold.

The active workstream is Charlottetown zoning extraction. The goal is to extract the current and draft zoning bylaw for the City of Charlottetown, their associated zoning maps, parcel layer, and street map. The resulting data should support parcel and neighbourhood comparison and provide a base for a future web-based public front end.

## Current Charlottetown Inputs and Outputs

Target source material for the active Charlottetown task is stored under:

```text
docs/charlottetown
```

Zone data extraction outputs are split by bylaw status:

```text
data/zoning/charlottetown        current zoning bylaw
data/zoning/charlottetown-draft  draft zoning bylaw
```

The current workflow focuses on:

- extracting zone and clause text from the current Charlottetown zoning bylaw
- extracting equivalent content from the draft Charlottetown zoning bylaw
- preserving source clause labels and citation context
- normalizing zoning content for comparison across current and draft bylaws
- connecting normalized zoning outputs to maps, parcels, streets, and neighbourhood-scale analysis

## Target Outcome

The repository should support queries such as:

- What zoning rules apply to a parcel or location
- How current and draft Charlottetown zoning differ for a parcel, zone, or neighbourhood
- What uses, setbacks, density, height, parking, and overlay constraints apply
- Which zoning map feature overlaps a parcel or street segment
- Which source bylaw clause supports a normalized zoning rule

## Recommended Datastore

Use PostgreSQL with PostGIS as the canonical query layer.

Reasons:

- strong spatial joins and indexing
- good fit for parcel, zone, street, neighbourhood, and overlay geometries
- full-text search can coexist with structured zoning rules
- embeddings can be added later without changing the core spatial model

The repository includes a starter schema at [schema/sql/postgis.sql](/D:/opendata/mdopendata/schema/sql/postgis.sql).

## Local Database

The repository includes a local PostGIS Docker service:

- Docker service: [docker-compose.yml](/D:/opendata/mdopendata/docker-compose.yml)

Use read-only database inspection where possible. Load data through PostgreSQL tools or repository ingestion scripts.

## Python Environment

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

### Current Approved Python Libraries

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

### Future Python Libraries to Consider

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

## Data Model

The model separates five concerns:

1. source documents
2. extracted text blocks and citations
3. structured zoning and land-use rules
4. spatial features and overlays
5. municipal business records such as meetings, agenda items, motions, and decisions

This allows one query to combine parcel geometry, zoning rules, mapped overlays, and traceable source citations.

## Ingestion Strategy

### Phase 1: Inventory and Classify

Run:

```powershell
npm run inventory
```

This writes a machine-readable source manifest to `data/manifest/sources.json`.

### Phase 2: Extract

For each source:

- Text PDFs: extract text with page-level coordinates where possible
- Map PDFs: extract vector layers if available; otherwise render and georeference for OCR or manual digitization
- Images: OCR and classify legends, labels, and map content where needed

### Phase 3: Normalize

Normalize extracted content into:

- `documents`
- `document_pages`
- `text_spans`
- `zoning_rules`
- `spatial_features`
- `meetings`
- `agenda_items`
- `decisions`

### Phase 4: Spatial Linking

Link:

- parcels to current and draft zones
- parcels to overlays and map features
- parcels to streets and neighbourhoods
- rules to source clauses and mapped geometries
- future municipal records to locations, parcels, streets, and policy topics

## Current Implementation

Added in this repository:

- Source inventory builder: [src/build-inventory.js](/D:/opendata/mdopendata/src/build-inventory.js)
- PostGIS starter schema: [schema/sql/postgis.sql](/D:/opendata/mdopendata/schema/sql/postgis.sql)
- Detailed design notes: [docs/architecture.md](/D:/opendata/mdopendata/docs/architecture.md)
- Charlottetown source directory: [docs/charlottetown](/D:/opendata/mdopendata/docs/charlottetown)
- Charlottetown current zoning outputs: [data/zoning/charlottetown](/D:/opendata/mdopendata/data/zoning/charlottetown)
- Charlottetown draft zoning outputs: [data/zoning/charlottetown-draft](/D:/opendata/mdopendata/data/zoning/charlottetown-draft)

## Known Gaps

- The PEI corporate land use and HRM planning workstreams are paused.
- OCR tooling is not part of the approved project Python environment yet.
- Full Charlottetown parcel and street integration is still in progress.
- Georeferencing and vectorization status varies by source map.
- No public web front end exists yet.

## Next Implementation Step

Continue the Charlottetown workflow by extracting and normalizing current and draft zoning bylaw content, then connect those outputs to zoning maps, parcel geometry, and street/neighbourhood comparison layers.
