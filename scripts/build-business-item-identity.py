from __future__ import annotations

import argparse
import json
import re
from itertools import combinations
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEETING = REPO_ROOT / "data" / "council-meetings" / "charlottetown" / "2026-05-12-regular-council" / "meeting.json"
DEFAULT_CONFIG = REPO_ROOT / "data" / "council-meetings" / "charlottetown" / "business-item-identity-config.json"


def norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def related_source_items(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for collection in ("resolutions", "bylaw_readings", "planning_items"):
        for item in payload.get(collection, []):
            key = item.get("item_id") or item.get("planning_item_id")
            if key:
                items[key] = item
    return items


def extract_identifiers(text: str, patterns: list[dict[str, str]]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for pattern in patterns:
        for match in re.finditer(pattern["regex"], text, flags=re.IGNORECASE):
            value = match.group(1) if match.groups() else match.group(0)
            found.append((pattern["name"], value))
    return found


def build_identity(payload: dict[str, Any], config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    meeting_date = payload["meeting"]["date"]
    source_items = related_source_items(payload)
    evidence: list[dict[str, Any]] = []
    business_items = {item["business_item_id"]: item for item in payload.get("business_items", [])}

    for business_id, item in business_items.items():
        texts = [item.get("title", ""), item.get("summary", "")]
        for agenda_id in item.get("related_agenda_item_ids", []):
            source_item = source_items.get(agenda_id)
            if source_item:
                texts.extend([source_item.get("title", ""), source_item.get("public_summary", "")])
                for reference in source_item.get("property_references", []):
                    for pid in reference.get("pids", []):
                        evidence.append({
                            "business_item_evidence_id": f"{business_id}:pid:{pid}",
                            "business_item_id": business_id,
                            "source_document_id": "package",
                            "evidence_type": "property_identifier",
                            "evidence_value_raw": pid,
                            "evidence_value_normalized": norm(pid),
                            "signal_weight": config["matching_policy"]["property_identifier_weight"],
                            "confidence": 1.0,
                            "observed_date": meeting_date,
                            "metadata": {"identifier_kind": "pid"},
                        })
        joined = "\n".join(texts)
        for kind, value in extract_identifiers(joined, config.get("official_identifier_patterns", [])):
            evidence.append({
                "business_item_evidence_id": f"{business_id}:{kind}:{norm(value)}",
                "business_item_id": business_id,
                "source_document_id": "package",
                "evidence_type": "official_identifier",
                "evidence_value_raw": value,
                "evidence_value_normalized": norm(value),
                "signal_weight": config["matching_policy"]["official_identifier_weight"],
                "confidence": 1.0,
                "observed_date": meeting_date,
                "metadata": {"identifier_kind": kind},
            })
        evidence.append({
            "business_item_evidence_id": f"{business_id}:title",
            "business_item_id": business_id,
            "source_document_id": "package",
            "evidence_type": "title",
            "evidence_value_raw": item.get("title", ""),
            "evidence_value_normalized": norm(item.get("title", "")),
            "signal_weight": config["matching_policy"]["title_similarity_weight"],
            "confidence": 0.7,
            "observed_date": meeting_date,
            "metadata": {},
        })

    relationships: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    evidence_by_item: dict[str, list[dict[str, Any]]] = {}
    for row in evidence:
        evidence_by_item.setdefault(row["business_item_id"], []).append(row)

    for left_id, right_id in combinations(sorted(business_items), 2):
        left = evidence_by_item.get(left_id, [])
        right = evidence_by_item.get(right_id, [])
        left_official = {row["evidence_value_normalized"] for row in left if row["evidence_type"] == "official_identifier"}
        right_official = {row["evidence_value_normalized"] for row in right if row["evidence_type"] == "official_identifier"}
        left_pids = {row["evidence_value_normalized"] for row in left if row["evidence_type"] == "property_identifier"}
        right_pids = {row["evidence_value_normalized"] for row in right if row["evidence_type"] == "property_identifier"}
        shared_official = left_official & right_official
        shared_pids = left_pids & right_pids
        if shared_official:
            relationships.append({
                "business_item_relationship_id": f"{left_id}:same_as:{right_id}",
                "from_business_item_id": left_id,
                "to_business_item_id": right_id,
                "relationship_type": "same_as",
                "confidence": 1.0,
                "rationale": f"Shared official identifier: {', '.join(sorted(shared_official))}",
                "metadata": {"reason_codes": ["shared_official_identifier"]},
            })
        elif shared_pids:
            candidates.append({
                "business_item_candidate_link_id": f"{left_id}:candidate_same_as:{right_id}",
                "from_business_item_id": left_id,
                "to_business_item_id": right_id,
                "proposed_relationship_type": "same_as",
                "score": config["matching_policy"]["property_identifier_weight"],
                "review_status": "pending",
                "reason_codes": ["shared_property_identifier"],
                "explanation": f"Shared property identifier: {', '.join(sorted(shared_pids))}",
                "metadata": {},
            })
    return {
        "business_item_evidence": evidence,
        "business_item_relationships": relationships,
        "business_item_candidate_links": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build durable business-item identity evidence for one meeting payload.")
    parser.add_argument("--meeting", type=Path, default=DEFAULT_MEETING)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    payload = load(args.meeting)
    config = load(args.config)
    payload.update(build_identity(payload, config))
    if args.write:
        args.meeting.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps({
            "business_item_evidence": len(payload["business_item_evidence"]),
            "business_item_relationships": len(payload["business_item_relationships"]),
            "business_item_candidate_links": len(payload["business_item_candidate_links"]),
        }, indent=2))


if __name__ == "__main__":
    main()
