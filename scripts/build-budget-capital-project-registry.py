import json
import re
from collections import Counter
from pathlib import Path

BASE = Path("data/budget/charlottetown")
DOCUMENTS = ("2024-2025", "2025-2026", "2026-2027")


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def prior_references(document):
    identities = {record["table_key"]: record for record in json.loads((BASE / document / "capital-project-profile-identity-review.json").read_text())["records"]}
    aliases = {record["table_key"]: record for record in json.loads((BASE / document / "capital-project-alias-review.json").read_text())["records"]}
    references = []
    for table_key, identity in sorted(identities.items()):
        alias = aliases[table_key]
        decision = alias["alias_decision"]
        project_keys = alias["capital_project_keys"]
        source_label = identity["source_project"] or identity["source_title"] or identity["title_guess"]
        references.append({
            "document_key": document, "table_key": table_key, "page_start": identity["page_start"],
            "raw_label": source_label, "document_adoption_state": "adopted",
            "project_key": project_keys[0] if len(project_keys) == 1 else None,
            "identity_evidence": "conflicting" if decision == "review_blocked" else "strong",
            "reference_status": "review_blocked" if decision == "review_blocked" else "approved",
            "source_decision": decision,
        })
    return references


def current_references():
    manifest = json.loads((BASE / "2026-2027" / "table_manifest.json").read_text())
    references = []
    for table in manifest["records"]:
        if table.get("table_type") != "capital_project_profile":
            continue
        label = table["title"]
        references.append({
            "document_key": "2026-2027", "table_key": f"2026-2027-p{table['page_start']:03d}", "page_start": table["page_start"],
            "raw_label": label, "document_adoption_state": "adopted", "project_key": slug(label),
            "identity_evidence": "exact", "reference_status": "approved", "source_decision": "document_reference_creates_project_identity",
        })
    return sorted(references, key=lambda record: record["table_key"])


def main():
    references = [*prior_references("2024-2025"), *prior_references("2025-2026"), *current_references()]
    projects = {}
    for reference in references:
        if not reference["project_key"]:
            continue
        project = projects.setdefault(reference["project_key"], {
            "project_key": reference["project_key"], "display_name": reference["raw_label"],
            "lifecycle_status": "unknown", "lifecycle_evidence": None, "reference_keys": [], "document_keys": [],
        })
        project["reference_keys"].append(f"{reference['document_key']}:{reference['table_key']}")
        project["document_keys"].append(reference["document_key"])
    for project in projects.values():
        observed = set(project["document_keys"])
        latest = max(DOCUMENTS.index(document) for document in observed)
        if latest == len(DOCUMENTS) - 1:
            project["lifecycle_status"] = "active"
            project["lifecycle_evidence"] = "adopted_budget_allocation"
        else:
            project["lifecycle_status"] = "complete"
            project["lifecycle_evidence"] = "not_observed_in_immediately_following_adopted_budget"
        project["document_keys"] = sorted(observed)
    output = {
        "schema_version": 1,
        "contract": "municipality_scoped_project_with_document_owned_references",
        "documents": list(DOCUMENTS),
        "projects": sorted(projects.values(), key=lambda record: record["project_key"]),
        "references": sorted(references, key=lambda record: (record["document_key"], record["table_key"])),
        "summary": {
            "projects": len(projects), "references": len(references),
            "references_by_document": dict(Counter(record["document_key"] for record in references)),
            "approved_references": sum(record["reference_status"] == "approved" for record in references),
            "review_blocked_references": sum(record["reference_status"] == "review_blocked" for record in references),
        },
    }
    (BASE / "capital-project-registry.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output["summary"], indent=2))


if __name__ == "__main__":
    main()
