"""User-confirmed physical layout; names alone never establish room identity."""
from __future__ import annotations

import copy
import re

KEY = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
ANALYSIS_POLICIES = {"always", "high", "automatic", "low", "ignore"}
LOCATIONS = {"fixed", "portable", "multi-room", "whole-house", "unknown"}


def empty_layout():
    return {"description": "", "floors": [], "areas": [], "entity_policies": {}}


def _text(value, maximum=100):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"Expected nonempty text of at most {maximum} characters")
    return value.strip()


def validate_layout(value, inventory):
    """Validate facts entered by an admin, without editing any HA registry."""
    if not isinstance(value, dict) or set(value) != set(empty_layout()):
        raise ValueError("Expected description, floors, areas and entity_policies")
    result = copy.deepcopy(value)
    if not isinstance(result["description"], str) or len(result["description"]) > 4000:
        raise ValueError("Layout description must contain at most 4,000 characters")
    keys = {"floors": set(), "areas": set()}
    registry_areas = {area["id"] for area in inventory["areas"]}
    assigned = set()
    for collection in ("floors", "areas"):
        rows = result[collection]
        if not isinstance(rows, list) or len(rows) > 100:
            raise ValueError("Layout supports at most 100 floors and 100 areas")
        for row in rows:
            fields = {"key", "name"} if collection == "floors" else {"key", "name", "floor_key", "aliases", "registry_area_ids", "outdoor"}
            if not isinstance(row, dict) or set(row) != fields:
                raise ValueError("Invalid layout row fields")
            if not isinstance(row["key"], str) or not KEY.fullmatch(row["key"]) or row["key"] in keys[collection]:
                raise ValueError("Invalid or duplicate layout key")
            keys[collection].add(row["key"])
            row["name"] = _text(row["name"])
            if collection == "floors":
                continue
            if row["floor_key"] is not None and row["floor_key"] not in keys["floors"]:
                raise ValueError("Area refers to an unknown physical floor")
            if type(row["outdoor"]) is not bool:
                raise ValueError("Outdoor must be a boolean")
            if not isinstance(row["aliases"], list) or len(row["aliases"]) > 20:
                raise ValueError("An area supports at most 20 aliases")
            row["aliases"] = list(dict.fromkeys(_text(alias) for alias in row["aliases"]))
            ids = row["registry_area_ids"]
            if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
                raise ValueError("Invalid existing area references")
            if len(ids) != len(set(ids)) or set(ids) - registry_areas or assigned.intersection(ids):
                raise ValueError("Existing areas must refer to exactly one confirmed physical space")
            assigned.update(ids)
    policies = result["entity_policies"]
    if not isinstance(policies, dict) or len(policies) > 5000:
        raise ValueError("Invalid entity policies")
    entities = {entity["id"] for entity in inventory["entities"]}
    for identity, policy in policies.items():
        if identity not in entities or not isinstance(policy, dict) or set(policy) != {"location", "analysis", "privacy_excluded"}:
            raise ValueError("Invalid entity policy fields or identity")
        if policy["location"] not in LOCATIONS or policy["analysis"] not in ANALYSIS_POLICIES or type(policy["privacy_excluded"]) is not bool:
            raise ValueError("Invalid entity policy values")
    return result


def layout_findings(layout, inventory):
    """Explain confirmed missing spaces and consolidation, never silently merge."""
    findings = []
    current = {area["id"]: area for area in inventory["areas"]}
    for area in layout.get("areas", []):
        evidence = f"confirmed-layout:{area['key']}"
        ids = area["registry_area_ids"]
        missing = set(ids) - set(current)
        if missing:
            findings.append({"kind": "stale", "name": area["name"], "evidence": evidence,
                             "reason": "A referenced HA area was removed; reconfirm its mapping.", "blocker": True})
        elif not ids:
            findings.append({"kind": "missing_area", "name": area["name"], "evidence": evidence,
                             "reason": "Confirmed physical space has no mapped HA area.", "blocker": False})
        elif len(ids) > 1:
            findings.append({"kind": "consolidation", "name": area["name"], "evidence": evidence,
                             "canonical_area_id": ids[0], "other_area_ids": ids[1:],
                             "reason": "You mapped these HA areas to one space. Review assignments and references before merging; deletion needs separate approval.", "blocker": True})
        if area["outdoor"]:
            findings.append({"kind": "label", "name": area["name"], "evidence": evidence,
                             "reason": "Consider an Exterior label. Outdoor does not establish a physical floor.", "blocker": False})
    return findings
