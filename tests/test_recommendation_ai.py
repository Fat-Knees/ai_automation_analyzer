import json

import pytest

from custom_components.ai_automation_suggester.recommendation_ai import prepare, validate_response


def context():
    return prepare({"areas": [{"id": "room", "name": "Office"}], "entities": [
        {"id": "light", "entity_id": "light.office", "name": "Desk light", "area_id": "room", "attributes": {"token": "secret"}},
        {"id": "private", "entity_id": "sensor.private", "name": "private value", "area_id": "room"},
        {"id": "person", "entity_id": "person.someone", "name": "person value", "area_id": "room"}]}, excluded=["private"])


def idea():
    return {"title": "Desk lighting", "description": "Consider lighting the desk during work; confirm the desired schedule.",
            "entity_ids": ["light.office"], "kind": "capability_idea", "evidence_ids": []}


def test_prompt_only_contains_selected_metadata_and_no_claim_of_history():
    preview = context()
    assert "secret" not in preview["instructions"]
    assert "private value" not in preview["instructions"]
    assert "person value" not in preview["instructions"]
    assert preview["payload"]["history_status"] == "No validated behavioral evidence available"
    parsed = validate_response(json.dumps({"ideas": [idea()]}), preview)
    assert not parsed[0]["installed"] and not parsed[0]["enabled"]


@pytest.mark.parametrize("change", [
    {"entity_ids": ["light.invented"]}, {"kind": "behavior_evidence"},
    {"evidence_ids": ["invented"]}, {"approval": True}, {"title": ""},
])
def test_untrusted_ai_cannot_invent_facts_or_approve(change):
    with pytest.raises(ValueError):
        validate_response({"ideas": [{**idea(), **change}]}, context())


def test_rejects_code_fences_and_oversized_results():
    for value in ('```json\n{"ideas": []}\n```', " " * 32001, {"ideas": [idea()] * 6}):
        with pytest.raises(ValueError):
            validate_response(value, context())
