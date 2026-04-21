# Charlottetown Code-Table Candidate Discovery Workflow

This workflow discovers provisional zoning terms and code-table candidates before final extraction. It does not approve codes, modify reviewed seed files, or write generated zoning extraction data.

## Scope

- Source document: `docs/charlottetown/charlottetown-zoning-bylaw.pdf`
- Candidate output folder: `data/normalized/code-tables/candidates/charlottetown/`
- Candidate schema: `schema/json-schema/candidate-code-table-seed.schema.json`
- Discovery script: `scripts/discover-charlottetown-code-table-candidates.py`
- Candidate validator: `scripts/validate-code-table-candidates.py`

The workflow must not write to `data/zoning/charlottetown`.

## Phases

1. Extract text from the source PDF.
2. Segment evidence by page, detectable section, detectable clause, and line context.
3. Detect provisional candidates for terms, requirement types, relationship phrases, and use names.
4. Emit candidate JSON files with `status: candidate`.
5. Validate candidate JSON shape.
6. Stop for human review before changing any reviewed `*.seed.json` file.

## Candidate Files

- `term_candidate.seed.json`
- `requirement_type_candidate.seed.json`
- `relationship_type_candidate.seed.json`
- `use_candidate.seed.json`
- `review_report.json`

## Candidate Record Fields

Each candidate entry includes:

- `candidate_id`: deterministic Charlottetown-specific candidate id.
- `canonical_candidate`: provisional display phrase from source evidence.
- `suggested_code`: machine-safe suggested code.
- `candidate_table`: target candidate table.
- `category`: provisional category.
- `status`: always `candidate`.
- `aliases`: exact or conservative spelling and punctuation variants.
- `occurrence_count`: number of detected occurrences.
- `confidence`: heuristic confidence from observable evidence only.
- `match_basis`: detector evidence such as `known_phrase`, `numeric_unit_pattern`, or `relationship_phrase`.
- `existing_code_match`: exact reviewed seed match when available.
- `source_refs`: source document, page, section, clause, and context.
- `examples`: short source examples.
- `review_flags`: reasons human review is required.
- `review_decision`: human review placeholder.

## First Discovery Targets

Discovery should prioritize:

- dwelling types
- accessory uses and structures
- approval processes
- lot contexts
- yard and setback types
- requirement categories
- relationship and inheritance phrases
- use names in permitted, conditional, prohibited, and special-use contexts

## Automation Boundary

Safe automated steps:

- PDF text scanning
- exact and conservative phrase grouping
- singular canonical candidates with plural source forms retained as aliases and examples
- frequency counts
- source reference capture
- short examples
- tentative matching to existing reviewed seed files
- omission of candidate tables, such as units and measure types, when all candidates already exist in reviewed code tables
- candidate JSON and review report generation

Review-required steps:

- approving final canonical codes
- merging near-synonyms
- assigning ambiguous categories
- interpreting relationship phrases as inheritance, exception, overlay, applicability, or reference
- handling municipality-specific map references and zone codes outside municipality-agnostic code tables
- changing existing reviewed seed files
- using candidates in final extraction

## Commands

Dry run:

```powershell
& 'C:\Users\19029\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\scripts\discover-charlottetown-code-table-candidates.py --dry-run
```

Write candidate files:

```powershell
& 'C:\Users\19029\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\scripts\discover-charlottetown-code-table-candidates.py
```

Validate candidate files:

```powershell
& 'C:\Users\19029\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\scripts\validate-code-table-candidates.py
```
