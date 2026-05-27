# Municipal Document Processing Pipeline — Component Map & Data Model

**Status:** Phase 1 design draft for diff against existing project. Naming is generic and meant to be remapped to project conventions.

---

## 1. Scope & Assumptions

- **Phase 1 source:** Charlottetown, PEI. Single municipality.
- **Primary target document:** Agenda packages (composite documents containing distinct sub-document templates). Other types — bylaws, reports, budgets, minutes — supported with simpler text-based handling.
- **Primary classifier strategy:** Vision model (Claude vision) for agenda packages in Phase 1. Design accommodates swapping in structural fingerprinting (text blocks, positions, font features) as the labeled corpus matures and per-document cost matters at scale.
- **Discovery model:** Fingerprint matching against a curated TemplateLibrary with novelty detection. Not unsupervised clustering.
- **Storage:** Database-first. Human-authored definitions (templates, field specs, routing rules) live in dedicated tables with a `human_authored` flag and timestamped versioning, so a config-file overlay can be added later without schema change.
- **Cross-document linking:** Forward-reference resolution with stubs — references to not-yet-ingested meetings create stub Meeting / ExtractedRecord rows that get upgraded when the source document arrives.
- **Oversight:** Human + LLM review during bootstrap; confidence-driven routing of items into a review queue surfaced through the existing web UI. Target is increasing automation as confidence calibrates.

---

## 2. Subsystems

### Ingestion
Accepts a PDF + a `source_id`. Persists the raw artifact, computes per-page rasters (PNG, configurable DPI) and extracted text + structure (text blocks with bounding boxes, font metadata, reading order). Emits one `Page` record per PDF page. Both vision inputs (rasters) and structural inputs (text + layout) are produced on every ingest so the classifier strategy can be swapped later without re-ingesting.

Suggested tooling: `pypdfium2` or `pdfplumber` for text + structure; `pdf2image` or `pdfium` for rasters. OCR fallback (Tesseract or a vision model pass) when extracted text is empty or low-confidence — common for scanned council documents.

### Source Profiling
Resolves a `Source` to a `SourceProfile` — the central pluggability point. The profile controls:
- Which `DocumentType`s this source publishes
- Which classifier strategy (vision / structural / hybrid) applies per document type
- Which `TemplateLibrary` is in scope
- Confidence thresholds for routing
- Extraction prompts / rules per template

Profiles are versioned; effective-dating lets old pipeline runs be reproduced.

### Document Type Classifier
First-pass classifier: is this PDF a Bylaw, Report, Budget, AgendaPackage, Minutes, etc.? Cheap heuristics first (filename patterns, first-page text patterns from the SourceProfile), then a vision/text fallback. Outputs `DocumentType` + confidence.

### Page Template Classifier
For composite documents, classifies each `Page` against a `TemplateLibrary` scoped to its `DocumentType`. 
- Phase 1: Claude vision with per-template prompt or matching against a template description and exemplars.
- Phase 2: structural fingerprint matching (vector similarity over layout features + anchor text patterns), with vision retained as a fallback for low-confidence cases and novelty detection.

Outputs `TemplateMatch` (page → template, confidence, evidence). Confidence below the novelty threshold flags the page as a candidate for a new template, surfaced in the review UI.

### Sub-Document Assembler
Groups consecutive `Page`s sharing or sequencing a `Template` into `ExtractedRecord` instances. A "Council Resolution" may span 2–3 pages; a "Letter from a business" may be one. Assembly rules live on the `Template` (continuation conditions, end-of-record markers, expected page count range).

### Field Extractor
For each `ExtractedRecord`, runs extraction defined by its `Template`'s `FieldSpec` list. 
- Phase 1: vision model with structured-output prompt per template.
- Phase 2: deterministic extraction (text + bounding-box rules) where layout is stable enough, vision fallback for anomalies.

Outputs filled `ExtractedRecord.fields` plus per-field confidence and (where possible) source coordinates.

### Cross-Document Linker
Scans `ExtractedRecord.fields` for references (meeting dates, committee names, prior resolution numbers, bylaw citations). Normalizes:
- Date strings → ISO date
- Committee strings → canonical `Committee` IDs via alias table
- Resolution numbers → canonical resolution refs

Resolves each reference to an existing record or creates a stub. Stubs carry a `created_by_reference_id` so the reverse link is preserved when the stub is later filled in. Stub upgrade is idempotent — when a real document arrives matching a stub, the stub is upgraded in place and back-references preserved.

### Oversight & Review Queue
Every classification and extraction emits a confidence. `SourceProfile` holds three thresholds: `auto_accept`, `llm_judge`, `human_review`. Routing:

```
confidence >= auto_accept            → commit silently
llm_judge <= confidence < auto_accept → LLM judge re-evaluates with source page + record; agree commits, disagree → human
confidence < llm_judge               → human review
```

Adjustable frequency = threshold tuning in `SourceProfile`, plus a sampling override (e.g. 5% of auto-accepted items randomly routed to the LLM judge for ongoing calibration). Track judge agreement rate per `Template`; when it stabilizes above target, auto-accept threshold lowers.

### Audit / Observability
Every record (`Page`, `TemplateMatch`, `ExtractedRecord`, `Reference`) carries: `pipeline_version`, `classifier_model_version`, `prompt_hash` (if applicable), `confidence`, `source_coordinates` (page + bounding box where applicable), and `review_state`. Required for regression analysis, retraining, and trust calibration as you automate.

---

## 3. Data Model

Generic names; rename to project conventions.

### Sources & Profiles

- **`Source`** — `(id, name, jurisdiction_level [municipal/provincial/federal], location, created_at)`
- **`SourceProfile`** — `(id, source_id, version, effective_from, classifier_strategy_by_doctype JSON, template_library_id, thresholds JSON, active, human_authored=true)`
- **`Committee`** — `(id, source_id, canonical_name, aliases text[], parent_committee_id nullable)`

### Type & Template Definitions

- **`DocumentType`** — `(id, name, is_composite bool)`
- **`TemplateLibrary`** — `(id, name, document_type_id, version)`
- **`Template`** — `(id, library_id, name, document_type_id, assembly_rules JSON, version, human_authored=true)`
- **`FieldSpec`** — `(id, template_id, name, type [string/date/money/enum/reference/text], required, extraction_hint, validation_rule, human_authored=true)`
- **`TemplateFingerprint`** — `(id, template_id, kind [vision_exemplar/structural_vector/text_pattern], payload JSON or blob, example_page_id, created_at, active)` — multiple per template, accumulated as variations are discovered.

### Documents & Pages

- **`Document`** — `(id, source_id, document_type_id, original_filename, sha256, ingested_at, page_count, parent_meeting_id nullable, pipeline_version, status)`
- **`Page`** — `(id, document_id, page_number, raster_path, text_blocks JSON, ocr_used bool)`
- **`TemplateMatch`** — `(id, page_id, template_id, confidence, fingerprint_id, evidence JSON, review_state)`

### Sub-Documents & Linking

- **`ExtractedRecord`** — `(id, document_id, template_id, page_range int4range, fields JSONB, confidence, is_stub bool, parent_record_id nullable, stub_resolved_by_record_id nullable, review_state, source_coordinates JSON)`
- **`Meeting`** — `(id, source_id, committee_id, scheduled_date date, is_stub bool, created_by_reference_id nullable)`
  - One Meeting has many Documents (agenda package, minutes, supplementary). A Meeting is the anchor for cross-references.
- **`Reference`** — `(id, source_record_id, target_kind [Meeting/Document/Record/Resolution/Bylaw], target_id nullable, raw_text, normalized_value JSON, resolved_at nullable, resolution_method)`

### Operations

- **`ReviewItem`** — `(id, subject_kind, subject_id, reason, confidence, assigned_to [human/llm/null], status, resolution, resolved_at)`
- **`PipelineRun`** — `(id, document_id, pipeline_version, started_at, completed_at, status, summary JSON)`
- **`JudgeEvaluation`** — `(id, review_item_id, model, prompt_hash, verdict [agree/disagree], reasoning, created_at)` — separate from `ReviewItem` so multiple judges or repeat evals are tracked.

### Key Relationships

```
Source 1—* SourceProfile
Source 1—* Committee
Source 1—* Document
Committee 1—* Meeting
Meeting 1—* Document (agenda package, minutes, etc.)
Document 1—* Page
Document 1—* ExtractedRecord
Page 1—1 TemplateMatch
ExtractedRecord 1—* Reference
Template 1—* FieldSpec
Template 1—* TemplateFingerprint
Template 1—* ExtractedRecord
```

---

## 4. Per-Source Profile — Where Definitions Live

Your default (DB) is right for nearly everything. Two narrow areas where config files have a real advantage if you ever want them:

- **Template + FieldSpec definitions** are human-authored, change rarely, and benefit from git review. A YAML overlay at `config/sources/<source_id>/templates/*.yaml` with a loader that materializes rows into the DB on deploy would give you change history without losing queryability. The DB tables become a materialized view of the config.
- **Confidence thresholds and routing rules** in `SourceProfile` are tuned over time and benefit from change history.

Operational and generated data — fingerprints, extracted records, review items, meetings, references — is churning data and belongs in the DB unambiguously; no advantage to config.

**Recommendation for Phase 1:** keep everything in the DB. Mark `Template`, `FieldSpec`, and `SourceProfile` rows with `human_authored=true` and maintain a stable schema for those tables. If config-overlay becomes attractive later, the migration is mechanical (dump → YAML → write loader). Don't pay the loader cost now.

---

## 5. Confidence & Oversight Flow

Routing logic (per stage — DocType, TemplateMatch, FieldExtraction, Reference resolution):

```
confidence >= auto_accept_threshold       → commit
llm_judge_threshold <= c < auto_accept    → LLM judge → agree=commit, disagree=human
confidence < llm_judge_threshold          → human review queue
```

**Adjustable frequency** is achieved via:
1. Threshold tuning per `(SourceProfile, stage, template?)` — finer granularity if you want different thresholds per template.
2. Sampling override: e.g. randomly route N% of auto-accepted items to the LLM judge for ongoing calibration regardless of confidence.
3. Per-template agreement-rate tracking — once stable above target, auto-accept threshold can be lowered automatically or with a human gate.

**Novelty detection** is a separate signal from confidence: a page that fingerprint-matches *nothing* in the library is structurally different from a page that matches one template ambiguously. Both need human attention, but the review UI should distinguish them.

---

## 6. Open Questions / Decisions to Confirm

These are the points I'd expect to find overlap, contradiction, or already-made decisions when you diff against your existing project:

1. **Resolution-with-attachments structure.** Does a "Council Resolution" record own its attached supporting documents (letters, reports referenced in the resolution body), or are those siblings linked by `Reference`? The model above allows `ExtractedRecord.parent_record_id`; whether that's the right shape depends on how downstream queries traverse it.

2. **Template versioning.** When a municipality changes its letterhead or layout, do you create a new `Template` version (preserving old extractions' link to the old version) or update fingerprints in place under the same `Template.id`? Lean toward versioning — preserves auditability and lets old extractions remain correct.

3. **Bounding-box storage.** Capture per-field source coordinates always (audit + retraining value), or only when review flags it (storage cost)? Lean toward always — cheap to store, expensive to recompute.

4. **Pipeline reruns.** If a `Template` or `FieldSpec` definition changes, do you re-extract historical records automatically, mark them stale, or leave them? Recommend a `pipeline_version` on every record and a manual rerun trigger with a diff preview.

5. **Source identity granularity.** A single `Source` per municipality, or per publishing surface (City Council vs. Planning Board vs. Committee of the Whole)? Affects how granular `SourceProfile` gets and whether template libraries are shared across committees.

6. **OCR strategy.** When extracted text is empty/garbled, run OCR locally (Tesseract) or via a vision model? Vision model is more accurate on poor scans but per-page cost matters at scale.

7. **Stub TTL / unresolved reference policy.** How long does a `Reference` stay in unresolved state before it surfaces as a `ReviewItem`? Some references will never resolve (referenced meeting is pre-pipeline-era).

8. **Confidence calibration.** The vision model's self-reported confidence is unreliable; you may need a calibrated confidence (e.g., logistic regression on model output + structural features against human-labeled outcomes). Worth a dedicated subsystem if/when you have enough labels.
