import argparse
import json
import sys
from pathlib import Path


DEFAULT_SOURCE_DIR = Path("data/zoning/bedford/zones")
DEFAULT_BUNDLE_PATH = Path("data/normalized/runs/20260417T010000Z/bundle.json")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_zone_code(path, document):
    return document.get("document_metadata", {}).get("zone_code") or path.stem


def source_review_count(document):
    policy = document.get("normalization_policy", {})
    return len(policy.get("pending_review_clause_patterns", [])) + len(
        document.get("open_issues", [])
    )


def populated_unmapped_sections(document):
    section_names = [
        "requirement_sections",
        "content_blocks",
        "zone_specific_requirements",
        "shared_requirement_references",
        "prohibitions",
    ]
    populated = []
    for name in section_names:
        value = document.get(name)
        if isinstance(value, list) and value:
            populated.append({"section": name, "count": len(value)})
        elif isinstance(value, dict) and value:
            populated.append({"section": name, "count": len(value)})
    return populated


def source_summary(source_dir):
    files = sorted(source_dir.glob("*.json"))
    zones = []
    permitted_uses = 0
    review_signals = 0
    unmapped_sections = []

    for path in files:
        document = read_json(path)
        zone_code = source_zone_code(path, document)
        zones.append(zone_code)
        permitted_uses += len(document.get("permitted_uses", []))
        review_signals += source_review_count(document)
        for item in populated_unmapped_sections(document):
            unmapped_sections.append(
                {
                    "source_file": path.name,
                    "zone_code": zone_code,
                    **item,
                }
            )

    return {
        "source_files": len(files),
        "zones": zones,
        "permitted_uses": permitted_uses,
        "review_signals": review_signals,
        "unmapped_sections": unmapped_sections,
    }


def normalized_summary(bundle):
    zones = [zone["zone_code_raw"] for zone in bundle.get("zones", [])]
    use_permissions = [
        regulation
        for regulation in bundle.get("regulations", [])
        if regulation.get("regulation_type") == "use_permission"
    ]
    dimensional_standards = [
        regulation
        for regulation in bundle.get("regulations", [])
        if regulation.get("regulation_type") == "dimensional_standard"
    ]
    return {
        "zones": zones,
        "use_permissions": len(use_permissions),
        "dimensional_standards": len(dimensional_standards),
        "relationships": len(bundle.get("relationships", [])),
        "review_items": len(bundle.get("review_items", [])),
    }


def compare(source, normalized):
    failures = []
    warnings = []

    missing_zones = sorted(set(source["zones"]) - set(normalized["zones"]))
    extra_zones = sorted(set(normalized["zones"]) - set(source["zones"]))
    if missing_zones:
        failures.append(
            {
                "check": "zones_present",
                "message": "Normalized bundle is missing source zones.",
                "zones": missing_zones,
            }
        )
    if extra_zones:
        failures.append(
            {
                "check": "zones_no_extras",
                "message": "Normalized bundle contains zones not present in source.",
                "zones": extra_zones,
            }
        )
    if len(source["zones"]) != len(normalized["zones"]):
        failures.append(
            {
                "check": "zone_count",
                "source": len(source["zones"]),
                "normalized": len(normalized["zones"]),
            }
        )
    if source["permitted_uses"] != normalized["use_permissions"]:
        failures.append(
            {
                "check": "permitted_use_count",
                "source": source["permitted_uses"],
                "normalized": normalized["use_permissions"],
            }
        )
    if source["review_signals"] != normalized["review_items"]:
        failures.append(
            {
                "check": "review_signal_count",
                "source": source["review_signals"],
                "normalized": normalized["review_items"],
            }
        )

    if source["unmapped_sections"]:
        warnings.append(
            {
                "check": "populated_sections_not_fully_conserved",
                "message": "Source sections exist that are only partially normalized or are preserved through review/source references.",
                "count": len(source["unmapped_sections"]),
                "sections": source["unmapped_sections"],
            }
        )

    return failures, warnings


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check Bedford source-to-normalized conservation."
    )
    parser.add_argument(
        "--source-dir",
        default=str(DEFAULT_SOURCE_DIR),
        help="Directory containing Bedford source zone JSON files.",
    )
    parser.add_argument(
        "--bundle",
        default=str(DEFAULT_BUNDLE_PATH),
        help="Normalized bundle JSON to check.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    source_dir = Path(args.source_dir)
    bundle_path = Path(args.bundle)

    source = source_summary(source_dir)
    normalized = normalized_summary(read_json(bundle_path))
    failures, warnings = compare(source, normalized)

    report = {
        "source_dir": source_dir.as_posix(),
        "bundle": bundle_path.as_posix(),
        "passed": not failures,
        "source": {
            "source_files": source["source_files"],
            "zones": len(source["zones"]),
            "permitted_uses": source["permitted_uses"],
            "review_signals": source["review_signals"],
        },
        "normalized": {
            "zones": len(normalized["zones"]),
            "use_permissions": normalized["use_permissions"],
            "dimensional_standards": normalized["dimensional_standards"],
            "relationships": normalized["relationships"],
            "review_items": normalized["review_items"],
        },
        "failures": failures,
        "warnings": warnings,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
