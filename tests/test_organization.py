"""Grounded preview tests: identities, inherited areas, unknowns, and no writes."""
import asyncio
import copy

import pytest

from custom_components.ai_automation_suggester.config_flow import AIAutomationConfigFlow
from custom_components.ai_automation_suggester.organization import (
    build_audit,
    classify,
    expand_target,
    overlay,
    target_impacts,
    with_effective_areas,
)


@pytest.fixture
def inventory():
    entities = [
        {"id": "registry-plug", "entity_id": "switch.desk", "name": "Desk", "device_id": "relay", "explicit_area_id": None},
        {"id": "registry-light", "entity_id": "light.channel2", "name": "Light", "device_id": "relay", "explicit_area_id": "garage"},
        {"id": "registry-motion", "entity_id": "binary_sensor.motion", "name": "Unnamed sensor", "device_id": None, "explicit_area_id": None},
    ]
    for entity in entities:
        entity.update(classify(entity))
    return with_effective_areas({"entities": entities, "devices": [{"id": "relay", "area_id": "office"}],
                                "areas": [{"id": "office", "name": "Office", "floor_id": "ground"},
                                          {"id": "bedroom", "name": "Bedroom", "floor_id": "ground"},
                                          {"id": "garage", "name": "Garage", "floor_id": None}],
                                "floors": [{"id": "ground", "name": "Ground"}], "labels": []})


def test_move_changes_bedroom_targets_without_id_change(inventory):
    original = copy.deepcopy(inventory)
    proposed = overlay(inventory, [{"kind": "entity_area", "subject_id": "registry-plug", "after": "bedroom"}])
    definitions = {"automation.bedtime": {"actions": [{"action": "homeassistant.turn_off", "target": {"area_id": "bedroom"}}]}}
    impacts = target_impacts(definitions, inventory, proposed)
    assert impacts[0]["added"] == ["switch.desk"]
    assert impacts[0]["removed"] == []
    assert inventory == original
    assert proposed["entities"][0]["entity_id"] == "switch.desk"


def test_device_move_keeps_explicit_channel_override(inventory):
    proposed = overlay(inventory, [{"kind": "device_area", "subject_id": "relay", "after": "bedroom"}])
    assert proposed["entities"][0]["area_id"] == "bedroom"
    assert proposed["entities"][1]["area_id"] == "garage"


def test_labels_do_not_inherit_from_parent_but_explicit_device_target_does(inventory):
    inventory["labels"] = [{"id": "routine", "name": "Routine"}]
    inventory["devices"][0]["labels"] = ["routine"]
    inventory["devices"].append({"id": "child", "parent_device_id": "relay", "area_id": None})
    inventory["entities"][0]["device_id"] = "child"
    selected, unknown = expand_target({"label_id": "routine"}, inventory, "homeassistant.turn_off")
    assert not unknown
    assert "switch.desk" not in selected
    selected, unknown = expand_target({"device_id": "relay"}, inventory, "homeassistant.turn_off")
    assert "switch.desk" in selected


def test_diagnostics_and_hidden_filtering_distinguish_direct_labels(inventory):
    inventory["labels"] = [{"id": "routine", "name": "Routine"}]
    entity = inventory["entities"][0]
    entity.update(entity_category="diagnostic", labels=["routine"])
    assert "switch.desk" not in expand_target({"area_id": "office"}, inventory, "homeassistant.turn_off")[0]
    assert "switch.desk" in expand_target({"label_id": "routine"}, inventory, "homeassistant.turn_off")[0]
    entity["hidden"] = True
    assert "switch.desk" not in expand_target({"label_id": "routine"}, inventory, "homeassistant.turn_off")[0]
    assert "switch.desk" in expand_target({"entity_id": "switch.desk"}, inventory, "homeassistant.turn_off")[0]


def test_clearing_entity_override_restores_inheritance(inventory):
    proposed = overlay(inventory, [{"kind": "entity_area", "subject_id": "registry-light", "after": None}])
    assert proposed["entities"][1]["area_id"] == "office"


def test_native_child_inheritance_is_not_gateway_inference(inventory):
    inventory["devices"].append({"id": "child", "area_id": None, "parent_device_id": "relay"})
    inventory["entities"][0]["device_id"] = "child"
    assert with_effective_areas(inventory)["entities"][0]["area_id"] == "office"
    proposed = overlay(inventory, [{"kind": "device_area", "subject_id": "relay", "after": "bedroom"}])
    assert proposed["entities"][0]["area_id"] == "bedroom"
    inventory["devices"][-1].pop("parent_device_id")
    inventory["devices"][-1]["via_device_id"] = "relay"
    assert with_effective_areas(inventory)["entities"][0]["area_id"] is None


@pytest.mark.parametrize("operation", [
    {"kind": "execute", "subject_id": "registry-plug", "after": "on"},
    {"kind": "entity_area", "subject_id": "registry-plug", "after": "imaginary upstairs"},
    {"kind": "entity_area", "subject_id": "missing", "after": "office"},
    {"kind": "entity_area", "subject_id": "registry-plug", "after": "office", "approved": True},
    {"kind": "area_name", "subject_id": "office", "after": ""},
    {"kind": ["area_name"], "subject_id": "office", "after": "Office"},
])
def test_invalid_operations_rejected(inventory, operation):
    with pytest.raises(ValueError):
        overlay(inventory, [operation])


def test_bounded_and_duplicate_operations(inventory):
    op = {"kind": "area_name", "subject_id": "office", "after": "Office"}
    for operations in ([op, op], [op] * 201):
        with pytest.raises(ValueError):
            overlay(inventory, operations)


@pytest.mark.parametrize("target", [{"area_id": "{{ room }}"}, {"area_id": "missing"}, {"label_id": "lights"}, {"entity_id": "all"}])
def test_unresolved_targets_are_unknown_not_clear(inventory, target):
    _, errors = expand_target(target, inventory, "homeassistant.turn_off")
    assert errors


def test_floor_changes_and_service_domain_filter(inventory):
    proposed = overlay(inventory, [{"kind": "area_floor", "subject_id": "garage", "after": "ground"}])
    definitions = {"script.shutdown": {"sequence": [{"action": "light.turn_off", "target": {"floor_id": "ground"}}]}}
    assert target_impacts(definitions, inventory, proposed)[0]["added"] == ["light.channel2"]


def test_proposals_do_not_invent_locations_or_merge_bathrooms(inventory):
    inventory["areas"].extend([{"id": "bath", "name": "Bathroom", "floor_id": None},
                              {"id": "guest", "name": "Guest Bath", "floor_id": None}])
    report = build_audit(inventory, {}, {})
    assert report["proposed"] == report["inventory"]
    assert report["mutation_enabled"] is False
    assert any(q["id"] == "registry-motion" for q in report["questions"])
    assert not any("duplicate" in q["id"] for q in report["questions"])


def test_whitespace_proposal_and_review_are_stable(inventory):
    inventory["areas"][0]["name"] = " Office  "
    report = build_audit(inventory, {}, {})
    proposal = report["proposals"][0]
    reviewed = build_audit(inventory, {}, {"reviews": {proposal["id"]: "rejected"}})
    assert reviewed["proposals"][0]["status"] == "rejected"
    assert report["revision"] != reviewed["revision"]
    assert reviewed["proposed"]["areas"][0]["name"] == " Office  "


def test_stale_preview_retained_but_not_silently_applied(inventory):
    report = build_audit(inventory, {}, {"operations": [{"kind": "entity_area", "subject_id": "registry-plug", "after": "deleted"}]})
    assert report["proposed"] == report["inventory"]
    assert any("stale" in limitation for limitation in report["limitations"])


def test_revision_changes_when_automation_changes(inventory):
    assert build_audit(inventory, {}, {})["revision"] != build_audit(inventory, {"script.test": {}}, {})["revision"]


def test_safety_and_diagnostics_have_task_specific_roles():
    leak = classify({"entity_id": "binary_sensor.leak", "device_class": "moisture"})
    battery = classify({"entity_id": "sensor.battery", "device_class": "battery"})
    assert "safety/security" in leak["roles"]
    assert "maintenance/diagnostic" in battery["roles"]
    assert "needs load review" == classify({"entity_id": "switch.unknown"})["risk"]


def test_local_flow_never_constructs_provider_validator():
    flow = AIAutomationConfigFlow()
    result = asyncio.run(flow.async_step_user({"provider": "Local audit (no AI)"}))
    assert result["data"] == {"provider": "Local audit (no AI)"}
    assert flow.validator is None
