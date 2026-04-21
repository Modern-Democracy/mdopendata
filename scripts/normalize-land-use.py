import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


STANDARD_VERSION = "0.1.0"
SCHEMA_PATH = "schema/json-schema/normalized_land_use_bundle.schema.json"
STANDARD_DOC_PATH = "docs/normalized-land-use-standard.md"
DEFAULT_INPUT_PATHS = [
    "data/zoning/bedford",
]
OUTPUT_ROOT = Path("data/normalized")
BEDFORD_ZONES_PATH = Path("data/zoning/bedford/zones")
BEDFORD_DOCUMENT_ID = "document:bedford-land-use-bylaw"
HRM_JURISDICTION_ID = "jurisdiction:halifax-regional-municipality"
DIMENSIONAL_KEYWORDS = [
    "lot area",
    "lot frontage",
    "frontage",
    "front yard",
    "minimum yard",
    "flankage yard",
    "rear yard",
    "side yard",
    "height",
    "lot coverage",
    "floor area",
    "gross floor area",
    "separation distance",
    "landscaped open space",
    "parking",
    "number of units",
    "dwelling units",
    "distance between",
]
DIMENSIONAL_PATTERN = re.compile(
    r"(?<![\d.])(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
    r"(?P<unit>square metres|square meters|sq\.?\s*ft\.?|sq\.?\s*m\.?|square feet|metres|meters|percent|units|unit|m2|m|ft\.?|feet|ha|%)",
    re.IGNORECASE,
)
APPROVED_SINGLE_SECTION_CODES_BY_ZONE = {
    "CD-1": {"26.1", "26.2", "26.3", "26.4", "26.5"},
    "CD-2": {"27.1", "27.2", "27.3", "27.4", "27.5", "27.6"},
    "CD-3": {"28.1", "28.2", "28.3", "28.4", "28.5", "28.6"},
    "ICH": {"29.1", "29.2"},
    "RPK": {"23A.1", "23A.2"},
    "UR": {"30.1", "30.2"},
    "US": {"31.1", "31.2"},
}


def utc_now():
    return datetime.now(timezone.utc)


def run_id_from(dt):
    return dt.strftime("%Y%m%dT%H%M%SZ")


def relpath(path, root):
    return path.resolve().relative_to(root.resolve()).as_posix()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(args, cwd):
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    value = result.stdout.strip()
    return value or None


def git_status(cwd):
    status = git_value(["status", "--short"], cwd)
    return {
        "root": str(cwd),
        "commit": git_value(["rev-parse", "HEAD"], cwd),
        "branch": git_value(["branch", "--show-current"], cwd),
        "dirty": bool(status),
        "status_short": status.splitlines() if status else [],
    }


def source_type_for(path):
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "extracted_json"
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff"}:
        return "image"
    if suffix in {".gpkg", ".shp", ".geojson"}:
        return "gis_layer"
    return "unknown"


def source_role_for(path):
    parts = set(path.parts)
    if "schema" in parts:
        return "schema"
    if "scripts" in parts:
        return "converter_code"
    if "docs" in parts or "zoning" in parts or "ocp" in parts:
        if path.suffix.lower() == ".pdf":
            return "primary_source"
    return "source_extract"


def iter_files(paths, root):
    for input_path in paths:
        path = (root / input_path).resolve()
        if not path.exists():
            continue
        if path.is_file():
            yield path
            continue
        for child in sorted(path.rglob("*")):
            if child.is_file():
                yield child


def build_source_inventory(input_paths, root, include_checksums):
    inventory = []
    for path in iter_files(input_paths, root):
        stat = path.stat()
        item = {
            "source_id": relpath(path, root),
            "path": relpath(path, root),
            "source_type": source_type_for(path),
            "bytes": stat.st_size,
            "checksum_sha256": sha256_file(path) if include_checksums else None,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "role": source_role_for(path),
        }
        inventory.append(item)
    return inventory


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_inventory_item(path, root, output_type, include_checksums, record_counts=None):
    stat = path.stat()
    return {
        "path": relpath(path, root),
        "output_type": output_type,
        "bytes": stat.st_size,
        "checksum_sha256": sha256_file(path) if include_checksums else None,
        "record_counts": record_counts or {},
    }


def manifest_inventory_item(path, root):
    stat = path.stat()
    return {
        "path": relpath(path, root),
        "output_type": "manifest",
        "bytes": stat.st_size,
        "checksum_sha256": None,
        "record_counts": {},
    }


def output_inventory(paths, root, include_checksums):
    return [
        manifest_inventory_item(paths["manifest"], root),
        file_inventory_item(paths["bundle"], root, "bundle", include_checksums),
        file_inventory_item(paths["validation"], root, "validation", include_checksums),
        file_inventory_item(paths["review_items"], root, "review_items", include_checksums),
        file_inventory_item(paths["stats"], root, "stats", include_checksums),
    ]


def empty_bundle(generated_at):
    return {
        "standard_version": STANDARD_VERSION,
        "bundle_id": f"hrm-land-use-{generated_at.strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
        "sources": [],
        "documents": [],
        "jurisdictions": [],
        "planning_areas": [],
        "zones": [],
        "spatial_features": [],
        "definitions": [],
        "regulations": [],
        "policies": [],
        "relationships": [],
        "review_items": [],
    }


def slugify(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def stable_id(*parts):
    return ":".join(slugify(str(part)) for part in parts if part is not None and str(part) != "")


def normalized_clause_path(zone_code, label):
    approved = APPROVED_SINGLE_SECTION_CODES_BY_ZONE.get(zone_code, set())
    if label in approved:
        return [label]
    return None


def source_clause_path(zone_code, section_label_raw, clause_label_raw):
    direct = normalized_clause_path(zone_code, clause_label_raw) or normalized_clause_path(
        zone_code, section_label_raw
    )
    if direct:
        return direct
    if (
        section_label_raw
        and clause_label_raw
        and clause_label_raw != "section"
        and clause_label_raw != section_label_raw
        and re.fullmatch(r"[A-Za-z]+|[ivxlcdm]+|\d+", str(clause_label_raw), re.IGNORECASE)
    ):
        return [str(section_label_raw), str(clause_label_raw)]
    if section_label_raw and clause_label_raw == "section":
        return [str(section_label_raw)]
    return None


def unresolved_pending_patterns(zone_code, document):
    policy = document.get("normalization_policy", {})
    return [
        pattern
        for pattern in policy.get("pending_review_clause_patterns", [])
        if not normalized_clause_path(zone_code, pattern)
    ]


def source_record(source_id, source_type, path, official_status, metadata=None):
    return {
        "source_id": source_id,
        "source_type": source_type,
        "path": path,
        "official_status": official_status,
        "checksum": None,
        "metadata": metadata or {},
    }


def bundle_sources(source_inventory):
    records = {}
    for item in source_inventory:
        records[item["source_id"]] = source_record(
            item["source_id"],
            item["source_type"],
            item["path"],
            "derived" if item["source_type"] == "extracted_json" else "unknown",
            {
                "bytes": item["bytes"],
                "modified_at": item["modified_at"],
                "role": item["role"],
            },
        )
    official_source = source_record(
        "docs/bedford-land-use-bylaw.pdf",
        "pdf",
        "docs/bedford-land-use-bylaw.pdf",
        "official",
        {"role": "primary_source"},
    )
    records.setdefault(official_source["source_id"], official_source)
    return list(records.values())


def citations_for(source_path, citations):
    value = dict(citations or {})
    value.setdefault("source_path", source_path)
    value.setdefault("source_id", source_path)
    value.setdefault("source_json_pointer", None)
    return value


def zone_citations(source_path, document):
    citations = document.get("citations", {})
    if isinstance(citations, dict) and "zone_section" in citations:
        return citations_for(source_path, citations["zone_section"])
    return citations_for(source_path, citations)


def zone_kind(metadata):
    if metadata.get("source_schedule"):
        return "schedule_zone"
    zone_code = metadata.get("zone_code", "")
    zone_name = metadata.get("zone_name", "")
    text = f"{zone_code} {zone_name}".lower()
    if "comprehensive" in text or "development district" in text:
        return "planned_development"
    return "base"


def classify_zone(permitted_uses, kind):
    if kind == "planned_development":
        return "planned"
    categories = {
        str(item.get("source_category_raw", "")).lower()
        for item in permitted_uses
        if item.get("source_category_raw")
    }
    names = {
        str(item.get("use_type", "")).lower()
        for item in permitted_uses
        if item.get("use_type")
    }
    text = " ".join(sorted(categories | names))
    has_residential = "residential" in text or "dwelling" in text
    has_commercial = "commercial" in text or "business" in text or "office" in text
    if has_residential and has_commercial:
        return "mixed_with_residential"
    if has_residential:
        return "primarily_residential"
    if permitted_uses:
        return "nonresidential"
    return "unknown"


def mapped_status(document):
    metadata = document.get("document_metadata", {})
    if metadata.get("source_schedule"):
        return "partially_mapped"
    return "unknown"


def permission_status(use):
    conditions = use.get("conditions") or []
    symbols = [str(item).lower() for item in use.get("permission_symbols", [])]
    if conditions:
        return "permitted_with_conditions"
    if symbols and symbols != ["permitted"]:
        return "permitted_with_conditions"
    return "permitted"


def clean_number(value):
    return float(value.replace(",", ""))


def normalize_unit(unit):
    if unit == "M":
        return "unknown"
    normalized = unit.lower().replace(".", "").strip()
    normalized = re.sub(r"\s+", " ", normalized)
    if normalized in {"ft", "feet"}:
        return "ft"
    if normalized in {"m", "metres", "meters"}:
        return "m"
    if normalized in {"sq ft", "square feet"}:
        return "sq ft"
    if normalized in {"square metres", "square meters", "sq m", "m2"}:
        return "m2"
    if normalized in {"%", "percent"}:
        return "percent"
    if normalized in {"unit", "units"}:
        return "unit"
    if normalized == "ha":
        return "ha"
    return normalized


def converted_value(amount, unit):
    if unit == "ft":
        return amount * 0.3048, "m", 0.3048, "converted"
    if unit == "sq ft":
        return amount * 0.09290304, "m2", 0.09290304, "converted"
    if unit == "unit":
        return amount, "unit", None, "exact"
    if unit in {"m", "m2", "ha", "percent", "unit"}:
        return amount, unit, None, "exact"
    return amount, unit, None, "unknown"


def comparator_for_text(text):
    lowered = text.lower()
    if "minimum" in lowered or "at least" in lowered:
        return "minimum"
    if "maximum" in lowered or "not exceed" in lowered or "no more than" in lowered:
        return "maximum"
    return "unknown"


def dimensional_subject(context):
    lowered = context.lower()
    for keyword in DIMENSIONAL_KEYWORDS:
        if keyword in lowered:
            return slugify(keyword)
    return "dimensional-standard"


def metric_context(text, start, preserve_clause_context=False):
    context = text[max(0, start - (320 if preserve_clause_context else 120)) : start]
    if not preserve_clause_context:
        sentence_start = max(context.rfind("."), context.rfind(";"), context.rfind(":"))
        if sentence_start >= 0:
            context = context[sentence_start + 1 :]
    return " ".join(context.split())


def is_parenthetical_imperial_equivalent(text, start, unit):
    if unit not in {"ft", "sq ft"}:
        return False
    open_position = text.rfind("(", 0, start)
    close_position = text.rfind(")", 0, start)
    if open_position <= close_position:
        return False
    prior = text[max(0, open_position - 100) : open_position].lower()
    return bool(
        re.search(
            r"\d+(?:,\d{3})*(?:\.\d+)?\s*"
            r"(?:square metres|square meters|sq\.?\s*m\.?|metres|meters|m2|m)\b",
            prior,
        )
    )


def dimensional_value(amount, unit, source_text):
    normalized_amount, normalized_unit, factor, precision = converted_value(amount, unit)
    return {
        "kind": "percentage" if normalized_unit == "percent" else "quantity",
        "comparator": comparator_for_text(source_text),
        "original": {
            "amount": amount,
            "unit": unit,
            "text": source_text,
            "precision": "exact",
            "conversion_factor": None,
        },
        "normalized": {
            "amount": round(normalized_amount, 6),
            "unit": normalized_unit,
            "text": f"{round(normalized_amount, 6)} {normalized_unit}",
            "precision": precision,
            "conversion_factor": factor,
        },
        "text": source_text,
        "items": [],
        "metadata": {},
    }


def dimensional_conditions(context, zone_id, regulation_index):
    conditions = []
    lowered = context.lower()
    road_classes = [
        ("local", "local"),
        ("collector", "collector"),
        ("arterial", "arterial"),
    ]
    for raw, value in road_classes:
        if raw in lowered:
            conditions.append(
                {
                    "condition_id": stable_id(zone_id, "dimensional-condition", regulation_index, value),
                    "condition_type": "road_class",
                    "operator": "equals",
                    "value": value,
                    "source_text": context,
                    "source_authority": "bylaw_text",
                    "metadata": {},
                }
            )
    return conditions


CHR_SCOPED_DIMENSIONAL_CLAUSES = {
    ("1", "a"): {
        "subject": "lot-frontage",
        "comparator": "minimum",
        "alternatives": [
            {
                "source_text": "9.75 metres (32 feet) for Apartment, single unit dwellings and duplexes",
                "amount": 9.75,
                "unit": "m",
                "imperial_amount": 32.0,
                "imperial_unit": "ft",
                "applicability": [
                    ("construction_type", "apartment", "Apartment"),
                    ("construction_type", "single_unit_dwelling", "single unit dwellings"),
                    ("construction_type", "duplex", "duplexes"),
                ],
                "qualifiers": [],
            },
            {
                "source_text": "7.62 metres (25 feet) per unit for semi-detached",
                "amount": 7.62,
                "unit": "m",
                "imperial_amount": 25.0,
                "imperial_unit": "ft",
                "applicability": [
                    ("construction_type", "semi_detached", "semi-detached"),
                ],
                "qualifiers": [
                    ("rate_basis", "per_unit", "per unit"),
                ],
            },
        ],
    },
    ("1", "b"): {
        "subject": "lot-area",
        "comparator": "minimum",
        "alternatives": [
            {
                "source_text": "315.9 square metres (3,400 square feet) for single unit dwellings and duplexes",
                "amount": 315.9,
                "unit": "m2",
                "imperial_amount": 3400.0,
                "imperial_unit": "sq ft",
                "applicability": [
                    ("construction_type", "single_unit_dwelling", "single unit dwellings"),
                    ("construction_type", "duplex", "duplexes"),
                ],
                "qualifiers": [],
            },
            {
                "source_text": "232.3 square metres (2,500 square feet) per unit for a semi-detached dwelling",
                "amount": 232.3,
                "unit": "m2",
                "imperial_amount": 2500.0,
                "imperial_unit": "sq ft",
                "applicability": [
                    ("construction_type", "semi_detached", "semi-detached dwelling"),
                ],
                "qualifiers": [
                    ("rate_basis", "per_unit", "per unit"),
                ],
            },
        ],
    },
    ("1", "f"): {
        "subject": "rear-yard",
        "comparator": "minimum",
        "alternatives": [
            {
                "source_text": "Minimum rear yard 6.1 metres (20 feet)",
                "amount": 6.1,
                "unit": "m",
                "imperial_amount": 20.0,
                "imperial_unit": "ft",
                "applicability": [
                    ("yard_context", "rear_yard", "rear yard"),
                ],
                "qualifiers": [],
                "conditions": [],
            },
            {
                "source_text": "Where parking is located in the rear yard, the minimum rear yard setback shall be 9.14 metres (30 feet)",
                "amount": 9.14,
                "unit": "m",
                "imperial_amount": 30.0,
                "imperial_unit": "ft",
                "applicability": [
                    ("yard_context", "rear_yard", "rear yard"),
                ],
                "qualifiers": [],
                "conditions": [
                    ("parking_location", "rear_yard", "Where parking is located in the rear yard"),
                ],
            },
        ],
    },
    ("1", "g"): {
        "subject": "side-yard",
        "comparator": "minimum",
        "alternatives": [
            {
                "source_text": "Minimum side yard 1.22 metres (4 feet)",
                "amount": 1.22,
                "unit": "m",
                "imperial_amount": 4.0,
                "imperial_unit": "ft",
                "applicability": [
                    ("yard_context", "side_yard", "side yard"),
                ],
                "qualifiers": [],
                "conditions": [],
            },
            {
                "source_text": "0 metres for the common lot line between semi-detached dwellings units",
                "amount": 0.0,
                "unit": "m",
                "imperial_amount": None,
                "imperial_unit": None,
                "applicability": [
                    ("yard_context", "common_lot_line", "common lot line"),
                    ("construction_type", "semi_detached", "semi-detached dwellings units"),
                ],
                "qualifiers": [],
                "conditions": [],
            },
        ],
    },
    ("3", "c"): {
        "subject": "lot-area",
        "comparator": "minimum",
        "alternatives": [
            {
                "source_text": "Minimum Lot Area Per Dwelling Unit Single Detached 315.9 square metres (3400 square feet)",
                "amount": 315.9,
                "unit": "m2",
                "imperial_amount": 3400.0,
                "imperial_unit": "sq ft",
                "applicability": [
                    ("construction_type", "single_detached", "Single Detached"),
                ],
                "qualifiers": [
                    ("rate_basis", "per_dwelling_unit", "Per Dwelling Unit"),
                ],
            },
            {
                "source_text": "Semi Detached/Duplex 232.3 square metres (2,500 square feet)",
                "amount": 232.3,
                "unit": "m2",
                "imperial_amount": 2500.0,
                "imperial_unit": "sq ft",
                "applicability": [
                    ("construction_type", "semi_detached", "Semi Detached"),
                    ("construction_type", "duplex", "Duplex"),
                ],
                "qualifiers": [
                    ("rate_basis", "per_dwelling_unit", "Per Dwelling Unit"),
                ],
            },
            {
                "source_text": "Rowhouse/Townhouse 167.2 square metres (1800 square feet)",
                "amount": 167.2,
                "unit": "m2",
                "imperial_amount": 1800.0,
                "imperial_unit": "sq ft",
                "applicability": [
                    ("construction_type", "rowhouse", "Rowhouse"),
                    ("construction_type", "townhouse", "Townhouse"),
                ],
                "qualifiers": [
                    ("rate_basis", "per_dwelling_unit", "Per Dwelling Unit"),
                ],
            },
        ],
    },
}


def scoped_condition(condition_id, condition_type, value, source_text):
    return {
        "condition_id": condition_id,
        "condition_type": condition_type,
        "operator": "equals",
        "value": value,
        "source_text": source_text,
        "source_authority": "bylaw_text",
        "metadata": {},
    }


def scoped_dimensional_regulation(
    zone_id,
    zone_code,
    text,
    citations,
    section_label_raw,
    clause_label_raw,
    source_kind,
):
    if zone_code != "CHR" or source_kind != "requirement_sections":
        return None
    scoped = CHR_SCOPED_DIMENSIONAL_CLAUSES.get((section_label_raw, clause_label_raw))
    if not scoped:
        return None

    regulation_id = stable_id(
        "regulation",
        "bedford",
        zone_code,
        source_kind,
        section_label_raw,
        clause_label_raw,
    )
    alternatives = []
    for index, item in enumerate(scoped["alternatives"], start=1):
        alternative_id = stable_id(regulation_id, "alternative", index)
        value = dimensional_value(item["amount"], item["unit"], item["source_text"])
        value["comparator"] = scoped["comparator"]
        if item.get("imperial_amount") is not None and item.get("imperial_unit"):
            value["metadata"]["original_equivalents"] = [
                {
                    "amount": item["imperial_amount"],
                    "unit": item["imperial_unit"],
                    "text": f"{item['imperial_amount']:g} {item['imperial_unit']}",
                }
            ]
        else:
            value["metadata"]["original_equivalents"] = []
        alternatives.append(
            {
                "alternative_id": alternative_id,
                "label_raw": None,
                "value": value,
                "applicability": [
                    scoped_condition(
                        stable_id(alternative_id, applicability_value),
                        condition_type,
                        applicability_value,
                        source_text,
                    )
                    for condition_type, applicability_value, source_text in item["applicability"]
                ],
                "qualifiers": [
                    {
                        "qualifier_type": qualifier_type,
                        "value": qualifier_value,
                        "source_text": source_text,
                        "metadata": {},
                    }
                    for qualifier_type, qualifier_value, source_text in item["qualifiers"]
                ],
                "conditions": [
                    scoped_condition(
                        stable_id(alternative_id, condition_type, condition_value),
                        condition_type,
                        condition_value,
                        source_text,
                    )
                    for condition_type, condition_value, source_text in item.get("conditions", [])
                ],
                "source_text": item["source_text"],
                "metadata": {},
            }
        )

    return {
        "regulation_id": regulation_id,
        "document_id": BEDFORD_DOCUMENT_ID,
        "applies_to": [
            {
                "target_type": "zone",
                "target_id": zone_id,
            }
        ],
        "regulation_type": "dimensional_standard",
        "subject": scoped["subject"],
        "permission_status": None,
        "value": None,
        "value_alternatives": alternatives,
        "conditions": [],
        "source_clause": {
            "section_label_raw": section_label_raw,
            "clause_label_raw": clause_label_raw,
            "clause_path": source_clause_path(zone_code, section_label_raw, clause_label_raw),
            "text_raw": text,
            "raw_symbols": [],
            "normalization_review_required": False,
        },
        "citations": citations,
        "normalization_status": "partial",
        "metadata": {
            "source_kind": source_kind,
            "scoped_alternatives": True,
        },
    }


def has_dimensional_signal(text):
    lowered = text.lower()
    return any(keyword in lowered for keyword in DIMENSIONAL_KEYWORDS) and DIMENSIONAL_PATTERN.search(text)


def dimensional_regulations_from_text(
    zone_id,
    zone_code,
    source_path,
    text,
    citations,
    section_label_raw,
    clause_label_raw,
    source_kind,
    start_index,
):
    regulations = []
    if not text or not has_dimensional_signal(text):
        return regulations

    scoped_regulation = scoped_dimensional_regulation(
        zone_id,
        zone_code,
        text,
        citations,
        section_label_raw,
        clause_label_raw,
        source_kind,
    )
    if scoped_regulation:
        return [scoped_regulation]

    for local_index, match in enumerate(DIMENSIONAL_PATTERN.finditer(text), start=1):
        context = metric_context(
            text,
            match.start(),
            preserve_clause_context=source_kind == "requirement_sections",
        )
        amount = clean_number(match.group("amount"))
        unit = normalize_unit(match.group("unit"))
        if unit == "unknown":
            continue
        if is_parenthetical_imperial_equivalent(text, match.start(), unit):
            continue
        sample = f"{context} {match.group(0)}".strip()
        if not has_dimensional_signal(sample):
            continue
        regulation_index = start_index + len(regulations) + 1
        subject = dimensional_subject(sample)
        regulations.append(
            {
                "regulation_id": stable_id(
                    "regulation",
                    "bedford",
                    zone_code,
                    source_kind,
                    section_label_raw,
                    clause_label_raw,
                    local_index,
                ),
                "document_id": BEDFORD_DOCUMENT_ID,
                "applies_to": [
                    {
                        "target_type": "zone",
                        "target_id": zone_id,
                    }
                ],
                "regulation_type": "dimensional_standard",
                "subject": subject,
                "permission_status": None,
                "value": dimensional_value(amount, unit, sample),
                "conditions": dimensional_conditions(sample, zone_id, regulation_index),
                "source_clause": {
                    "section_label_raw": section_label_raw,
                    "clause_label_raw": clause_label_raw,
                    "clause_path": source_clause_path(zone_code, section_label_raw, clause_label_raw),
                    "text_raw": text,
                    "raw_symbols": [],
                    "normalization_review_required": False,
                },
                "citations": citations,
                "normalization_status": "partial",
                "metadata": {
                    "source_kind": source_kind,
                    "source_text_sample": sample,
                },
            }
        )
    return regulations


def dimensional_regulations_for_zone(zone_id, zone_code, source_path, document, start_index):
    regulations = []

    for section in document.get("requirement_sections", []):
        section_label = section.get("section_label_raw")
        for provision in section.get("provisions", []):
            text = provision.get("text", "")
            citations = citations_for(source_path, provision.get("citations") or section.get("citations"))
            regulations.extend(
                dimensional_regulations_from_text(
                    zone_id,
                    zone_code,
                    source_path,
                    text,
                    citations,
                    section_label,
                    provision.get("provision_label_raw"),
                    "requirement_sections",
                    start_index + len(regulations),
                )
            )

    for chapter in document.get("zone_specific_requirements", []):
        chapter_title = chapter.get("chapter_title_raw")
        for section in chapter.get("sections", []):
            section_label = section.get("section_label_raw")
            for provision in section.get("provisions", []):
                text = provision.get("text", "")
                citations = citations_for(source_path, provision.get("citations") or section.get("citations"))
                regulations.extend(
                    dimensional_regulations_from_text(
                        zone_id,
                        zone_code,
                        source_path,
                        text,
                        citations,
                        section_label,
                        provision.get("provision_label_raw"),
                        f"zone_specific_requirements:{chapter_title}",
                        start_index + len(regulations),
                    )
                )

    if not document.get("requirement_sections") and not document.get("zone_specific_requirements"):
        for block_index, block in enumerate(document.get("content_blocks", []), start=1):
            text = " ".join(
                item
                for item in [block.get("heading_context_raw"), block.get("text")]
                if item
            )
            citations = zone_citations(source_path, document)
            regulations.extend(
                dimensional_regulations_from_text(
                    zone_id,
                    zone_code,
                    source_path,
                    text,
                    citations,
                    block.get("heading_context_raw"),
                    f"content_block_{block_index}",
                    "content_blocks",
                    start_index + len(regulations),
                )
            )
    return regulations


def use_conditions(zone_id, regulation_index, conditions):
    normalized = []
    for index, condition in enumerate(conditions or [], start=1):
        normalized.append(
            {
                "condition_id": stable_id(zone_id, "condition", regulation_index, index),
                "condition_type": "source_text",
                "operator": "exists",
                "value": condition,
                "source_text": condition,
                "source_authority": "bylaw_text",
                "metadata": {},
            }
        )
    return normalized


def source_clause_for(use, zone_code):
    symbols = use.get("permission_symbols") or []
    clause_path = use.get("clause_path")
    return {
        "section_label_raw": use.get("table_label_raw"),
        "clause_label_raw": use.get("clause_label_raw"),
        "clause_path": clause_path,
        "text_raw": use.get("use_name"),
        "raw_symbols": symbols,
        "normalization_review_required": False,
    }


def review_items_for_zone(zone_id, zone_code, source_path, document):
    review_items = []
    unresolved_patterns = unresolved_pending_patterns(zone_code, document)
    for index, pattern in enumerate(unresolved_patterns, start=1):
        review_items.append(
            {
                "review_item_id": stable_id(zone_id, "clause-syntax", index),
                "review_type": "clause_syntax",
                "status": "open",
                "source_text": pattern,
                "citations": zone_citations(source_path, document),
                "metadata": {
                    "zone_id": zone_id,
                    "source_path": source_path,
                    "reason": "Clause pattern is pending review and was not normalized.",
                },
            }
        )
    for index, issue in enumerate(document.get("open_issues", []), start=1):
        if (
            isinstance(issue, dict)
            and issue.get("issue_type") == "normalization_review"
            and not unresolved_patterns
        ):
            continue
        review_items.append(
            {
                "review_item_id": stable_id(zone_id, "open-issue", index),
                "review_type": "other",
                "status": "open",
                "source_text": issue.get("description") if isinstance(issue, dict) else str(issue),
                "citations": zone_citations(source_path, document),
                "metadata": {
                    "zone_id": zone_id,
                    "source_path": source_path,
                    "issue": issue,
                },
            }
        )
    return review_items


def relationship_target_for_shared_requirement(reference):
    title = (
        reference.get("chapter_title_raw")
        or reference.get("title_label_raw")
        or reference.get("part_label_raw")
    )
    slug = reference.get("chapter_slug") or slugify(title or reference.get("part_label_raw") or "unknown")
    return {
        "to_type": "regulation",
        "to_id": stable_id("regulation", "bedford", "requirement-reference", slug),
        "source_text": title or reference.get("part_label_raw") or slug,
        "metadata": {
            "chapter_slug": reference.get("chapter_slug"),
            "chapter_title_raw": reference.get("chapter_title_raw"),
            "part_label_raw": reference.get("part_label_raw"),
            "title_label_raw": reference.get("title_label_raw"),
        },
    }


def shared_requirement_relationships_for_zone(zone_id, zone_code, source_path, document):
    relationships = []
    for index, reference in enumerate(document.get("shared_requirement_references", []), start=1):
        target = relationship_target_for_shared_requirement(reference)
        relationships.append(
            {
                "relationship_id": stable_id(
                    "relationship",
                    "bedford",
                    zone_code,
                    "shared-requirement",
                    index,
                ),
                "from_type": "zone",
                "from_id": zone_id,
                "relationship_type": "subject_to_requirements_of",
                "to_type": target["to_type"],
                "to_id": target["to_id"],
                "resolution_status": "resolved",
                "source_text": target["source_text"],
                "citations": citations_for(source_path, reference.get("citations")),
                "metadata": {
                    "source_path": source_path,
                    **target["metadata"],
                },
            }
        )
    return relationships


def requirement_reference_regulations_for_bedford(root):
    targets = {}
    zones_dir = root / BEDFORD_ZONES_PATH
    for path in sorted(zones_dir.glob("*.json")):
        source_path = relpath(path, root)
        document = read_json(path)
        for reference in document.get("shared_requirement_references", []):
            target = relationship_target_for_shared_requirement(reference)
            existing = targets.setdefault(
                target["to_id"],
                {
                    "target": target,
                    "source_paths": [],
                    "citations": citations_for(source_path, reference.get("citations")),
                },
            )
            existing["source_paths"].append(source_path)

    regulations = []
    for target_id, item in sorted(targets.items()):
        target = item["target"]
        regulations.append(
            {
                "regulation_id": target_id,
                "document_id": BEDFORD_DOCUMENT_ID,
                "applies_to": [
                    {
                        "target_type": "document",
                        "target_id": BEDFORD_DOCUMENT_ID,
                    }
                ],
                "regulation_type": "reference",
                "subject": slugify(target["source_text"]),
                "permission_status": None,
                "value": {
                    "kind": "reference",
                    "comparator": None,
                    "original": None,
                    "normalized": None,
                    "text": target["source_text"],
                    "items": [],
                    "metadata": {
                        "target_id": target_id,
                    },
                },
                "conditions": [],
                "source_clause": {
                    "section_label_raw": item["target"]["metadata"].get("part_label_raw"),
                    "clause_label_raw": item["target"]["metadata"].get("chapter_slug"),
                    "clause_path": None,
                    "text_raw": target["source_text"],
                    "raw_symbols": [],
                    "normalization_review_required": False,
                },
                "citations": item["citations"],
                "normalization_status": "partial",
                "metadata": {
                    **target["metadata"],
                    "source_paths": sorted(set(item["source_paths"])),
                    "source_reference_count": len(item["source_paths"]),
                },
            }
        )
    return regulations


def normalize_bedford_bundle(root, generated_at, source_inventory):
    zones_dir = root / BEDFORD_ZONES_PATH
    bundle = empty_bundle(generated_at)
    bundle["sources"] = bundle_sources(source_inventory)
    bundle["jurisdictions"] = [
        {
            "jurisdiction_id": HRM_JURISDICTION_ID,
            "name_raw": "Halifax Regional Municipality",
            "name_normalized": "Halifax Regional Municipality",
            "metadata": {},
        }
    ]
    bundle["documents"] = [
        {
            "document_id": BEDFORD_DOCUMENT_ID,
            "jurisdiction_id": HRM_JURISDICTION_ID,
            "document_type": "land_use_bylaw",
            "title_raw": "Bedford Land Use By-law",
            "source_ids": ["docs/bedford-land-use-bylaw.pdf"],
            "effective_date": None,
            "revision_date": None,
            "raw_tree_ref": {
                "source_id": "data/zoning/bedford",
                "path": "data/zoning/bedford",
                "json_pointer": None,
                "table": None,
                "identifier": None,
            },
            "metadata": {},
        }
    ]
    bundle["regulations"].extend(requirement_reference_regulations_for_bedford(root))

    regulation_index = 0
    for path in sorted(zones_dir.glob("*.json")):
        source_path = relpath(path, root)
        document = read_json(path)
        metadata = document.get("document_metadata", {})
        zone_code = metadata.get("zone_code") or path.stem
        zone_id = stable_id("zone", "bedford", zone_code)
        permitted_uses = document.get("permitted_uses", [])
        kind = zone_kind(metadata)
        bundle["zones"].append(
            {
                "zone_id": zone_id,
                "jurisdiction_id": HRM_JURISDICTION_ID,
                "document_id": BEDFORD_DOCUMENT_ID,
                "zone_code_raw": zone_code,
                "zone_code_normalized": str(zone_code).upper(),
                "zone_name_raw": metadata.get("zone_name"),
                "zone_kind": kind,
                "classification": classify_zone(permitted_uses, kind),
                "mapped_status": mapped_status(document),
                "citations": zone_citations(source_path, document),
                "raw_tree_ref": {
                    "source_id": source_path,
                    "path": source_path,
                    "json_pointer": "",
                    "table": None,
                    "identifier": zone_code,
                },
                "metadata": {
                    "bylaw_name": metadata.get("bylaw_name"),
                    "part_label_raw": metadata.get("part_label_raw"),
                    "source_schedule": metadata.get("source_schedule"),
                },
            }
        )
        bundle["review_items"].extend(review_items_for_zone(zone_id, zone_code, source_path, document))
        bundle["relationships"].extend(
            shared_requirement_relationships_for_zone(zone_id, zone_code, source_path, document)
        )

        for use_index, use in enumerate(permitted_uses, start=1):
            regulation_index += 1
            use_name = use.get("use_name") or "unknown use"
            citations = citations_for(source_path, use.get("citations") or document.get("citations"))
            bundle["regulations"].append(
                {
                    "regulation_id": stable_id("regulation", "bedford", zone_code, use_index),
                    "document_id": BEDFORD_DOCUMENT_ID,
                    "applies_to": [
                        {
                            "target_type": "zone",
                            "target_id": zone_id,
                        }
                    ],
                    "regulation_type": "use_permission",
                    "subject": slugify(use_name),
                    "permission_status": permission_status(use),
                    "value": None,
                    "conditions": use_conditions(zone_id, use_index, use.get("conditions")),
                    "source_clause": source_clause_for(use, zone_code),
                    "citations": citations,
                    "normalization_status": "partial",
                    "metadata": {
                        "use_name_raw": use_name,
                        "use_type_raw": use.get("use_type"),
                        "source_category_raw": use.get("source_category_raw"),
                        "status_raw": use.get("status"),
                    },
                }
            )
        dimensional_regulations = dimensional_regulations_for_zone(
            zone_id,
            zone_code,
            source_path,
            document,
            regulation_index,
        )
        regulation_index += len(dimensional_regulations)
        bundle["regulations"].extend(dimensional_regulations)
    return bundle


def bundle_stats(bundle, source_inventory):
    regulation_types = {}
    relationship_types = {}
    review_statuses = {}
    for regulation in bundle["regulations"]:
        key = regulation["regulation_type"]
        regulation_types[key] = regulation_types.get(key, 0) + 1
    for relationship in bundle["relationships"]:
        key = relationship["relationship_type"]
        relationship_types[key] = relationship_types.get(key, 0) + 1
    for review_item in bundle["review_items"]:
        key = review_item["status"]
        review_statuses[key] = review_statuses.get(key, 0) + 1
    return {
        "source_files": len(source_inventory),
        "documents": len(bundle["documents"]),
        "zones": len(bundle["zones"]),
        "regulations": len(bundle["regulations"]),
        "policies": len(bundle["policies"]),
        "relationships": len(bundle["relationships"]),
        "review_items": len(bundle["review_items"]),
        "regulation_types": regulation_types,
        "relationship_types": relationship_types,
        "review_statuses": review_statuses,
    }


def json_type_matches(value, expected_type):
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return True


def json_type_name(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return type(value).__name__


def schema_pointer_part(part):
    return str(part).replace("~", "~0").replace("/", "~1")


def resolve_schema_ref(ref, root_schema):
    if not ref.startswith("#/"):
        raise ValueError(f"Only local schema refs are supported: {ref}")
    current = root_schema
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        current = current[part]
    return current


def validate_with_builtin(instance, schema, root_schema=None, path="$"):
    root_schema = root_schema or schema
    errors = []

    if "$ref" in schema:
        ref_schema = resolve_schema_ref(schema["$ref"], root_schema)
        return validate_with_builtin(instance, ref_schema, root_schema, path)

    if "anyOf" in schema:
        branch_errors = []
        for branch in schema["anyOf"]:
            branch_result = validate_with_builtin(instance, branch, root_schema, path)
            if not branch_result:
                return []
            branch_errors.extend(branch_result)
        return [
            {
                "path": path,
                "message": "Value does not match any allowed schema.",
                "validator": "anyOf",
                "details": branch_errors[:5],
            }
        ]

    if "type" in schema:
        expected = schema["type"]
        expected_types = expected if isinstance(expected, list) else [expected]
        if not any(json_type_matches(instance, item) for item in expected_types):
            return [
                {
                    "path": path,
                    "message": f"Expected {expected_types}, got {json_type_name(instance)}.",
                    "validator": "type",
                }
            ]

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(
            {
                "path": path,
                "message": f"Value {instance!r} is not in enum.",
                "validator": "enum",
            }
        )

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                errors.append(
                    {
                        "path": path,
                        "message": f"Missing required property {key!r}.",
                        "validator": "required",
                    }
                )

        properties = schema.get("properties", {})
        for key, value in instance.items():
            child_path = f"{path}/{schema_pointer_part(key)}"
            if key in properties:
                errors.extend(
                    validate_with_builtin(value, properties[key], root_schema, child_path)
                )
            elif schema.get("additionalProperties") is False:
                errors.append(
                    {
                        "path": child_path,
                        "message": f"Additional property {key!r} is not allowed.",
                        "validator": "additionalProperties",
                    }
                )

    if isinstance(instance, list) and "items" in schema:
        item_schema = schema["items"]
        for index, item in enumerate(instance):
            errors.extend(
                validate_with_builtin(item, item_schema, root_schema, f"{path}/{index}")
            )

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(
                {
                    "path": path,
                    "message": f"String is shorter than {schema['minLength']}.",
                    "validator": "minLength",
                }
            )
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(
                {
                    "path": path,
                    "message": f"String does not match pattern {schema['pattern']!r}.",
                    "validator": "pattern",
                }
            )

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(
                {
                    "path": path,
                    "message": f"Number is less than minimum {schema['minimum']}.",
                    "validator": "minimum",
                }
            )

    return errors


def validate_bundle(bundle_path, schema_path):
    bundle = read_json(bundle_path)
    schema = read_json(schema_path)
    try:
        import jsonschema
    except ModuleNotFoundError:
        errors = validate_with_builtin(bundle, schema)
        return {
            "schema_valid": not errors,
            "schema_path": SCHEMA_PATH,
            "validator": "builtin-json-schema-subset",
            "message": "Validation completed with built-in JSON Schema subset validator.",
            "errors": errors,
        }

    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = [
        {
            "path": "$" + "".join(f"/{schema_pointer_part(part)}" for part in error.path),
            "message": error.message,
            "validator": error.validator,
        }
        for error in sorted(validator.iter_errors(bundle), key=lambda item: list(item.path))
    ]
    return {
        "schema_valid": not errors,
        "schema_path": SCHEMA_PATH,
        "validator": f"jsonschema:{validator_cls.__name__}",
        "message": "Validation completed with jsonschema.",
        "errors": errors,
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a normalized land-use converter run scaffold."
    )
    parser.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help="Repository-relative source path to inventory. May be repeated.",
    )
    parser.add_argument(
        "--run-id",
        help="Run id to use instead of the current UTC timestamp.",
    )
    parser.add_argument(
        "--checksum",
        action="store_true",
        help="Compute SHA-256 checksums for source and output files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing run directory.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    generated_at = utc_now()
    run_id = args.run_id or run_id_from(generated_at)
    input_paths = args.inputs or DEFAULT_INPUT_PATHS
    run_dir = root / OUTPUT_ROOT / "runs" / run_id

    bundle_path = run_dir / "bundle.json"
    validation_path = run_dir / "bundle.validation.json"
    review_items_path = run_dir / "review-items.json"
    stats_path = run_dir / "stats.json"
    manifest_path = run_dir / "manifest.json"
    output_paths = {
        "manifest": manifest_path,
        "bundle": bundle_path,
        "validation": validation_path,
        "review_items": review_items_path,
        "stats": stats_path,
    }

    if run_dir.exists() and any(run_dir.iterdir()) and not args.force:
        raise SystemExit(
            f"Run directory already exists: {relpath(run_dir, root)}. "
            "Use --force to overwrite generated outputs."
        )

    source_inventory = build_source_inventory(input_paths, root, args.checksum)

    bundle = normalize_bedford_bundle(root, generated_at, source_inventory)
    stats = bundle_stats(bundle, source_inventory)
    unresolved_relationship_count = sum(
        1
        for relationship in bundle["relationships"]
        if relationship.get("resolution_status") == "unresolved"
    )
    write_json(bundle_path, bundle)
    validation_result = validate_bundle(bundle_path, root / SCHEMA_PATH)
    write_json(validation_path, validation_result)
    write_json(review_items_path, bundle["review_items"])
    write_json(stats_path, stats)

    manifest = {
        "run_id": run_id,
        "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
        "standard_version": STANDARD_VERSION,
        "schema_path": SCHEMA_PATH,
        "standard_doc_path": STANDARD_DOC_PATH,
        "converter": {
            "name": "normalize-land-use",
            "version": "0.1.0",
            "command": subprocess.list2cmdline([sys.executable, *sys.argv]),
            "arguments": {
                "inputs": input_paths,
                "run_id": run_id,
                "checksum": args.checksum,
                "force": args.force,
            },
            "working_directory": str(root),
        },
        "git": git_status(root),
        "inputs_filter": {
            "paths": input_paths,
            "communities": ["bedford"],
            "document_types": ["land_use_bylaw"],
        },
        "source_inventory": source_inventory,
        "output_inventory": [],
        "validation": {
            "schema_valid": validation_result["schema_valid"],
            "review_blocked_count": len(bundle["review_items"]),
            "relationship_unresolved_count": unresolved_relationship_count,
            "conversion_warning_count": 0,
        },
        "qa_summary": {
            "warnings": 0,
            "review_items": len(bundle["review_items"]),
            "unresolved_relationships": unresolved_relationship_count,
            "blocked_normalizations": len(bundle["review_items"]),
        },
        "review_policy": {
            "clause_labels_preserved_raw": True,
            "approved_hierarchy_examples": [
                "21(e)",
                "21(ea)",
                "21(ea)(1)",
                "20(1)(a.1)",
            ],
            "unknown_clause_syntax_action": "emit_review_item_without_normalizing",
        },
    }

    write_json(manifest_path, manifest)

    previous_size = None
    for _ in range(5):
        manifest["output_inventory"] = output_inventory(output_paths, root, args.checksum)
        write_json(manifest_path, manifest)
        current_size = manifest_path.stat().st_size
        if current_size == previous_size:
            break
        previous_size = current_size

    print(relpath(manifest_path, root))


if __name__ == "__main__":
    main()
