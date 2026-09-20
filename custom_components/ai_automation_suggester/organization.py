"""Deterministic, non-actuating organization preview.

This module has no HA imports or device/service adapters. A preview cannot apply
registry changes. Static target expansion is intentionally conservative.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re

MAX_OPERATIONS = 200
MAX_ACTION_NODES = 5000


def digest(value):
    """Canonical content identity; timestamps are kept outside revisions."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def classify(entity):
    """Metadata-based roles, without interpreting inactivity as irrelevance."""
    domain = entity["entity_id"].split(".", 1)[0]
    device_class = entity.get("device_class")
    roles, reasons = [], []
    if device_class in {"smoke", "gas", "carbon_monoxide", "moisture", "safety", "tamper"}:
        roles.append("safety/security")
        reasons.append("Safety metadata remains relevant even with no observed activations.")
    if device_class == "battery" or entity.get("entity_category") == "diagnostic":
        roles.append("maintenance/diagnostic")
        reasons.append("Diagnostic metadata is useful for maintenance, not necessarily household routines.")
    if domain in {"person", "device_tracker"} or device_class in {"occupancy", "presence"}:
        roles.append("presence")
        reasons.append("Presence metadata does not establish a fixed physical room.")
    if domain in {"light", "switch", "fan", "climate", "cover", "lock", "alarm_control_panel", "valve"}:
        roles.append("actuator")
        reasons.append("Control capability is present; the actual load and its safety still need review.")
    if domain == "binary_sensor":
        roles.append("trigger")
    if domain == "sensor":
        roles.append("measurement")
    if not roles:
        roles.append("unknown")
    risk = "needs load review" if "actuator" in roles else "not assessed for actuation"
    return {"roles": roles, "reasons": reasons or ["Role inferred from domain metadata only."], "risk": risk}


def effective_area(entity, devices):
    device = devices.get(entity.get("device_id"), {})
    # Native ChildDeviceEntry inheritance is distinct from via_device gateways.
    parent = devices.get(device.get("parent_device_id"), {})
    return entity.get("explicit_area_id") or device.get("area_id") or parent.get("area_id")


def with_effective_areas(inventory):
    devices = {device["id"]: device for device in inventory["devices"]}
    for entity in inventory["entities"]:
        entity["area_id"] = effective_area(entity, devices)
    return inventory


def overlay(inventory, operations):
    """Validate an allowlisted virtual plan; never write to HA."""
    if not isinstance(operations, list) or len(operations) > MAX_OPERATIONS:
        raise ValueError("Preview must contain at most 200 operations")
    proposed = copy.deepcopy(inventory)
    maps = {key: {row["id"]: row for row in proposed[key]} for key in ("entities", "devices", "areas", "floors")}
    rules = {"entity_area": ("entities", "explicit_area_id"), "area_name": ("areas", "name"),
             "area_floor": ("areas", "floor_id"), "device_area": ("devices", "area_id")}
    seen = set()
    for operation in operations:
        if not isinstance(operation, dict) or set(operation) != {"kind", "subject_id", "after"}:
            raise ValueError("Invalid preview operation fields")
        kind, subject, after = operation["kind"], operation["subject_id"], operation["after"]
        if not isinstance(kind, str) or kind not in rules or not isinstance(subject, str):
            raise ValueError("Unsupported preview operation")
        collection, field = rules[kind]
        if subject not in maps[collection] or (kind, subject) in seen:
            raise ValueError("Unknown or duplicate preview subject")
        seen.add((kind, subject))
        if field == "name":
            if not isinstance(after, str) or not after.strip() or len(after) > 100:
                raise ValueError("Area name must contain 1–100 characters")
            after = after.strip()
        else:
            target = "floors" if field == "floor_id" else "areas"
            if after is not None and (not isinstance(after, str) or after not in maps[target]):
                raise ValueError("Unknown destination; no physical locations are inferred")
        maps[collection][subject][field] = after
    return with_effective_areas(proposed)


def recommendations(inventory):
    proposals, questions = [], []
    areas = inventory["areas"]
    by_name = {}
    for area in areas:
        clean = " ".join(area["name"].split())
        if clean != area["name"]:
            proposal = {"kind": "area_name", "subject_id": area["id"], "field": "name",
                        "before": area["name"], "after": clean,
                        "reason": "Normalize whitespace while preserving area identity.",
                        "evidence": [f"area:{area['id']}"], "status": "pending"}
            proposal["id"] = digest(proposal)[:24]
            proposals.append(proposal)
        normalized = re.sub(r"[\W_]", "", clean.casefold())
        if normalized in by_name:
            questions.append({"id": f"duplicate:{area['id']}",
                              "question": f"Do {by_name[normalized]['name']} and {area['name']} describe the same physical room? No merge is assumed."})
        by_name[normalized] = area
    for entity in inventory["entities"]:
        if entity["area_id"] is None and not set(entity["roles"]) & {"presence"}:
            questions.append({"id": entity["id"], "question": f"Where is {entity['name']}? Leave unassigned if portable or whole-house."})
    return proposals, questions


def _ids(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError("Nonliteral target")


def expand_target(target, inventory, service):
    """Static membership estimate. Unknown constructs never become empty success.

    Labels, groups, disabled entries and runtime service capability filtering
    require native runtime verification, so these remain explicit unknowns.
    """
    unknown, result = [], set()
    if not isinstance(service, str) or "{{" in service or "." not in service:
        return result, ["Dynamic or unsupported action service"]
    if not isinstance(target, dict) or not target:
        return result, ["No explicit supported target"]
    if set(target) - {"entity_id", "device_id", "area_id", "floor_id", "label_id"}:
        unknown.append("Unsupported target fields")
    resolved = {}
    for key, value in target.items():
        try:
            resolved[key] = _ids(value)
            if any("{{" in item or "{%" in item or item in {"all", "none"} for item in resolved[key]):
                unknown.append(f"Dynamic or special target: {key}")
        except ValueError:
            unknown.append(f"Nonliteral target: {key}")
    if "label_id" in resolved:
        unknown.append("Label expansion requires native runtime verification")
    areas = {row["id"]: row for row in inventory["areas"]}
    devices = {row["id"]: row for row in inventory["devices"]}
    floors = {row["id"] for row in inventory["floors"]}
    entities = {row["entity_id"]: row for row in inventory["entities"]}
    for key, known in (("entity_id", entities), ("device_id", devices), ("area_id", areas), ("floor_id", floors)):
        if set(resolved.get(key, [])) - set(known):
            unknown.append(f"Missing or unresolved reference: {key}")
    domain = service.split(".")[0]
    for entity in inventory["entities"]:
        area = areas.get(entity["area_id"], {})
        matched = (entity["entity_id"] in resolved.get("entity_id", [])
                   or entity.get("device_id") in resolved.get("device_id", [])
                   or entity["area_id"] in resolved.get("area_id", [])
                   or area.get("floor_id") in resolved.get("floor_id", []))
        if not matched:
            continue
        if entity["entity_id"].startswith("group."):
            unknown.append("Group members not expanded")
        elif domain == "homeassistant" or entity["entity_id"].split(".")[0] == domain:
            result.add(entity["entity_id"])
            if entity.get("disabled"):
                unknown.append("Disabled target requires runtime review")
    return result, sorted(set(unknown))


def target_impacts(definitions, current, proposed):
    impacts, count = [], 0
    stack = [(source, definition) for source, definition in definitions.items()]
    while stack:
        source, node = stack.pop()
        count += 1
        if count > MAX_ACTION_NODES:
            impacts.append({"source": "scan", "added": [], "removed": [], "unknown": ["Action scan node limit reached"]})
            break
        if isinstance(node, list):
            stack.extend((f"{source}/{i}", value) for i, value in enumerate(node))
        elif isinstance(node, dict):
            service = node.get("action", node.get("service"))
            if isinstance(service, str):
                before, errors = expand_target(node.get("target", node.get("data", {})), current, service)
                after, after_errors = expand_target(node.get("target", node.get("data", {})), proposed, service)
                if before != after or errors or after_errors:
                    impacts.append({"source": source, "added": sorted(after-before), "removed": sorted(before-after),
                                    "unknown": sorted(set(errors + after_errors))})
            elif "device_id" in node and "domain" in node:
                impacts.append({"source": source, "added": [], "removed": [], "unknown": ["Device action requires native resolution"]})
            stack.extend((f"{source}/{key}", value) for key, value in node.items() if isinstance(value, (dict, list)))
    return impacts


def build_audit(inventory, definitions, preferences, limitations=()):
    """Build an immutable report tied to inventory, definitions AND saved review."""
    inventory = with_effective_areas(copy.deepcopy(inventory))
    revision = digest({"inventory": inventory, "definitions": definitions, "preferences": preferences})
    operations = preferences.get("operations", [])
    warnings = list(limitations)
    try:
        proposed = overlay(inventory, operations)
    except ValueError as err:
        proposed = copy.deepcopy(inventory)
        warnings.append(f"Saved preview is stale and was not applied: {err}")
    proposals, questions = recommendations(inventory)
    for proposal in proposals:
        proposal["status"] = preferences.get("reviews", {}).get(proposal["id"], "pending")
    return {"revision": revision, "inventory": inventory, "proposed": proposed,
            "operations": operations, "proposals": proposals, "questions": questions,
            "impacts": target_impacts(definitions, inventory, proposed),
            "limitations": warnings + ["Target sets are static estimates; service capabilities and dynamic references require runtime review.",
                                       "Scenes, dashboards, YAML includes and external automation systems are not scanned.",
                                       "Preview only. Registry changes and automation execution are disabled."],
            "mutation_enabled": False}
