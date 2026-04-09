# Local GIS Repository Requirements

## Role Progression

### Project Management

- Objective: build a local, low-cost GIS-capable repository and development stack for Charlottetown zoning, official plan, transportation, and related spatial layers.
- Scope boundaries: cover public-source intake, conversion, storage, indexing, and a web-facing API/UI foundation; exclude production hosting, proprietary data purchases, and advanced analytics not needed for an initial portal.
- Affected artifacts: source PDFs and images under `zoning/`, `ocp/`, and `maps/`; inventory logic in `src/`; schema in `schema/`; design and operating docs in `docs/`; generated manifests and derived data under `data/`.
- Next role: Business Analyst.

### Business Analyst

This document defines the minimum repository and system requirements before implementation expands.

## Direct Outcome

The first deliverable should be a local system that can ingest public Charlottetown planning documents and map sources, convert them into GIS-queryable datasets, and expose them to a web client through open-source components only.

## Phase 1 Scope

Phase 1 includes:

- zoning bylaw text extraction and citation indexing
- zoning map extraction or digitization into GIS polygons
- official plan text extraction and citation indexing
- future land use map extraction or digitization into GIS polygons
- transportation layers already present in repository maps
- repository-local metadata, provenance, and update tracking
- a local API and browser map interface for search and layer display

Phase 1 excludes:

- paid basemaps or proprietary GIS servers
- custom mobile applications
- automated legal interpretation beyond direct rule extraction
- full council, permit, or development application history unless separate public data is added
- parcel ownership data if licensing is unclear or non-public

## User and Query Requirements

The local system must support these primary user tasks:

1. Search by address, parcel identifier, or map click.
2. Return zoning district, future land use designation, and overlapping map layers.
3. Show cited bylaw and official plan sections that apply to the selected area.
4. Toggle transportation and city context layers such as wards, neighborhoods, cycling, truck routes, parks, and streets.
5. Trace every displayed result back to a source document, revision date, and extraction status.

## Data Requirements

The repository must store these classes of data:

- source files: original PDFs, images, and future downloadable datasets
- source manifest: file inventory, revision date, checksum, extraction status, licensing notes
- extracted text: page text, section hierarchy, tables, clauses, citations
- spatial layers: zoning, future land use, wards, neighborhoods, transportation, parks, streets
- derived lookup data: normalized addresses, legends, aliases, controlled vocabularies
- provenance data: extraction method, operator notes, confidence, validation state

The repository should add these external public datasets when available:

- parcel fabric or property polygons from PEI or municipal open data
- civic address points or road centerlines with names
- orthophoto or public base reference layers for georeferencing validation
- coordinate reference metadata for all published maps

## Functional Requirements

### Ingestion

- The system must inventory all source files and classify them by domain and extraction strategy.
- The system must compute stable file hashes so source changes can be detected.
- The system must support repeatable ingestion runs without duplicating records.
- The system must separate original sources from derived artifacts.

### Text conversion

- PDF text sources must be converted into structured sections and citation spans.
- Tables in zoning and policy documents must be preserved in a machine-usable form.
- Extracted clauses must map to atomic rules where practical.
- Failed or low-confidence extraction segments must be flagged for manual review.

### Spatial conversion

- Vector content must be extracted directly from PDFs when present.
- Raster-only maps must support georeferencing and manual or semi-manual digitization.
- Every spatial layer must be stored with a defined CRS and normalized to a canonical query CRS.
- Polygon, line, and point geometry validity must be checked before publication.

### Query and serving

- The datastore must support spatial intersection, containment, and proximity queries.
- The API must return both geometry and citation-backed regulatory metadata.
- The web interface must support layer toggles, popups, search, and source links.
- The system must distinguish official published data from repository-derived interpretations.

## Non-Functional Requirements

- Open-source only for the core stack.
- Local development on commodity hardware.
- Reproducible setup with scripted install and build steps.
- Incremental updates without full repository rebuilds where possible.
- Human-auditable outputs and clear provenance.
- Storage layout that can later move to hosted infrastructure without redesign.

## Recommended Open-Source Stack

- Database: PostgreSQL with PostGIS
- Desktop GIS and georeferencing: QGIS
- Data translation: GDAL and OGR
- PDF inspection and extraction: `pdftotext`, `pdfimages`, `mutool`, and `gdal` where applicable
- OCR for scanned content: Tesseract
- ETL orchestration: Node.js scripts already aligned with repository structure
- Local API: Node.js with Express or Fastify
- Web map UI: Leaflet or OpenLayers
- Basemap option: OpenStreetMap tiles for development, or self-hosted vector tiles later if needed

## Local Build Requirements

The local machine should provide:

- Node.js LTS and npm
- PostgreSQL 16 or compatible with PostGIS extension
- GDAL/OGR command-line tools
- QGIS for manual QA and georeferencing work
- Tesseract OCR
- Git and enough disk space for derived rasters and vector exports

The repository should add scripts for:

- source inventory
- checksum generation
- text extraction
- map extraction
- raster georeferencing metadata registration
- geometry import into PostGIS
- validation reports
- local API start
- local web UI start

## Repository Requirements

The repository should add these top-level data areas:

- `data/raw/` for immutable source snapshots if downloads are automated later
- `data/derived/text/` for extracted text and tables
- `data/derived/spatial/` for GeoJSON, GeoPackage, and import-ready outputs
- `data/qa/` for validation reports and manual review logs
- `config/` for layer definitions, CRS settings, legend mappings, and source rules

The repository should add these documentation artifacts:

- setup guide for local dependencies
- data source register with URLs and license notes
- ingestion runbook
- digitization and QA workflow guide
- API contract for the future web client

## Conversion Workflow Requirements

1. Register source metadata and compute checksums.
2. Attempt direct vector and text extraction from each PDF.
3. Route sources that fail direct extraction into OCR or georeferencing workflows.
4. Normalize outputs into structured text tables and GIS layers.
5. Validate geometry, CRS, attributes, and citations.
6. Load canonical records into PostGIS.
7. Publish API-ready views for the web client.

## Minimum Canonical Layer Set

The initial canonical GIS repository should expose:

- zoning districts
- future land use designations
- wards
- neighborhoods
- truck routes
- cycling routes
- parks
- street network or labeled street reference layer

Each layer must include:

- stable feature identifier
- source document reference
- source revision date if known
- geometry type
- CRS metadata
- human-readable name or label where applicable
- extraction status and validation status

## Risks and Gaps

- The current repository contains public source documents but not parcel geometry.
- Some maps may be raster-only or visually styled in ways that prevent reliable automated extraction.
- Licensing for external cadastral or address data must be checked before inclusion.
- OCR quality may be poor for map legends or scanned appendices.
- A low-budget workflow will likely require some manual georeferencing and digitization in QGIS.

## Acceptance Criteria For First Useful Release

- A local developer can install dependencies from documented instructions.
- The repository can build or refresh a manifest of source files.
- Zoning bylaw and official plan text are searchable with citation references.
- Zoning and future land use layers are available as GIS geometry in PostGIS.
- At least one transportation layer is queryable and visible in the web map.
- A local web interface can display layers, inspect a selected location, and show linked citations.
- Validation artifacts identify which sources were automated and which require manual QA.

## Recommended Next Role

The next role after this document is Coding Architect.

Reason:

- module boundaries for ingestion, normalization, storage, and web serving need to be fixed before implementation
- map extraction paths depend on runtime tooling and manual QA boundaries
- the repository needs a concrete open-source stack and workflow contract before code expands
