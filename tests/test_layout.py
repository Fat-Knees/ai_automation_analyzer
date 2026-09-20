"""T02: confirmed aliases do not merge distinct rooms or invent floors."""
import copy

import pytest

from custom_components.ai_automation_suggester.layout import empty_layout, layout_findings, validate_layout


def fixture():
    inventory = {"areas": [{"id": item, "name": item} for item in ("living", "lounge", "bath", "guest")],
                 "entities": [{"id": "stable-phone"}]}
    layout = empty_layout()
    layout["areas"] = [
        {"key": "living", "name": "Living Room", "floor_key": None, "aliases": ["Lounge"], "registry_area_ids": ["living", "lounge"], "outdoor": False},
        {"key": "bath", "name": "Bathroom", "floor_key": None, "aliases": [], "registry_area_ids": ["bath"], "outdoor": False},
        {"key": "guest", "name": "Guest Bath", "floor_key": None, "aliases": [], "registry_area_ids": ["guest"], "outdoor": False},
        {"key": "yard", "name": "Backyard", "floor_key": None, "aliases": [], "registry_area_ids": [], "outdoor": True},
    ]
    return inventory, layout


def test_confirmed_aliases_preserve_distinct_bathrooms_and_no_invented_floor():
    inventory, layout = fixture()
    original = copy.deepcopy(inventory)
    saved = validate_layout(layout, inventory)
    assert saved["floors"] == []
    findings = layout_findings(saved, inventory)
    assert [finding["kind"] for finding in findings] == ["consolidation", "missing_area", "label"]
    assert findings[0]["canonical_area_id"] == "living"
    assert findings[0]["other_area_ids"] == ["lounge"]
    assert findings[0]["blocker"] is True
    assert inventory == original


def test_missing_registry_area_requires_reconfirmation():
    inventory, layout = fixture()
    inventory["areas"] = inventory["areas"][1:]
    assert layout_findings(layout, inventory)[0]["kind"] == "stale"
    with pytest.raises(ValueError):
        validate_layout(layout, inventory)


def test_portable_and_privacy_policies_bound_to_stable_identity():
    inventory, layout = fixture()
    layout["entity_policies"]["stable-phone"] = {"location": "portable", "analysis": "always", "privacy_excluded": True}
    assert validate_layout(layout, inventory)["entity_policies"]["stable-phone"]["privacy_excluded"] is True
    layout["entity_policies"]["missing"] = layout["entity_policies"]["stable-phone"]
    with pytest.raises(ValueError):
        validate_layout(layout, inventory)


@pytest.mark.parametrize("mutate", [
    lambda value: value.update(approved=True),
    lambda value: value.update(description="x" * 4001),
    lambda value: value["areas"][0].update(floor_key="invented"),
    lambda value: value["areas"][1].update(registry_area_ids=["living"]),
    lambda value: value["areas"][0].update(aliases=["x"] * 21),
    lambda value: value["areas"][0].update(outdoor="yes"),
])
def test_invalid_confirmation_rejected(mutate):
    inventory, layout = fixture()
    mutate(layout)
    with pytest.raises(ValueError):
        validate_layout(layout, inventory)
