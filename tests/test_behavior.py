"""Seeded truth and negative controls for local recommendation evidence."""
import copy

from custom_components.ai_automation_suggester.behavior import Series, analyze, episodes

DAY = 86400


def fixture(scheduled=False):
    inventory = {"entities": [
        {"id": "motion", "entity_id": "binary_sensor.motion", "name": "Motion", "device_class": "motion", "area_id": "room"},
        {"id": "light", "entity_id": "light.room", "name": "Room light", "area_id": "room"}]}
    events = []

    def event(identity, at, state, kind="state"):
        events.append({"id": str(len(events)), "identity": identity, "at": at, "state": state, "kind": kind,
                       "mapping": {"area_id": "room"}})

    event("motion", -1, "off", "seed")
    event("light", -1, "off", "seed")
    for day in range(30):
        timestamp = day * DAY + 36000 + (0 if scheduled else day * 373 % 12000)
        event("motion", timestamp, "on")
        event("motion", timestamp + 90, "off")
        event("light", timestamp + 20, "on")
        event("light", timestamp + 300, "off")
    snapshot = {"events": events, "coverage": [
        {"identity": identity, "start": -1, "end": 30 * DAY, "status": "observed"} for identity in ("motion", "light")],
        "start": 0, "end": 30 * DAY, "truncated": False}
    return inventory, snapshot


def test_planted_relationship_has_held_out_counts_and_draft_only():
    inventory, snapshot = fixture()
    report = analyze(inventory, {}, snapshot)
    assert len(report["recommendations"]) == 1
    recommendation = report["recommendations"][0]
    assert recommendation["evidence"]["training"]["opportunities"] == 20
    assert recommendation["evidence"]["holdout"]["matches"] == 10
    assert recommendation["evidence"]["conservative_baseline"] == 0
    assert recommendation["automation"]["actions"][0]["action"] == "light.turn_on"
    assert recommendation["replay_status"] == "Not replayed"


def test_same_daily_schedule_is_rejected_by_time_matched_controls():
    inventory, snapshot = fixture(scheduled=True)
    report = analyze(inventory, {}, snapshot)
    assert not report["recommendations"]
    assert report["reviewed"][0]["evidence"]["conservative_baseline"] == 1


def test_unknown_coverage_seeds_retriggers_and_already_on_are_not_support():
    inventory, snapshot = fixture()
    snapshot["coverage"] = []
    report = analyze(inventory, {}, snapshot)
    assert not report["recommendations"]
    assert report["reviewed"][0]["evidence"]["holdout"]["opportunities"] == 0
    assert episodes([0, 5, 10, 120, 125]) == [0, 120]
    series = Series([{"at": 0, "id": "0", "kind": "seed", "state": "on"},
                     {"at": 1, "id": "1", "kind": "state", "state": "on"}],
                    [{"start": 0, "end": 10, "status": "observed"}])
    assert not series.activations
    inventory, snapshot = fixture()
    for row in snapshot["events"]:
        if row["identity"] == "light":
            row["state"] = "on"
    report = analyze(inventory, {}, snapshot)
    assert report["reviewed"][0]["evidence"]["holdout"]["already_on"] == 10
    assert not report["recommendations"]


def test_gap_overrides_observed_and_room_moves_never_relabel_old_events():
    inventory, snapshot = fixture()
    snapshot["coverage"].append({"identity": "light", "start": 20 * DAY, "end": 30 * DAY, "status": "gap"})
    assert not analyze(inventory, {}, snapshot)["recommendations"]
    inventory, snapshot = fixture()
    snapshot["events"][0]["mapping"]["area_id"] = "old-room"
    assert "Location changed" in analyze(inventory, {}, snapshot)["reviewed"][0]["reason"]


def test_exclusions_truncation_and_existing_automation_block_new_recommendation():
    inventory, snapshot = fixture()
    assert not analyze(inventory, {}, snapshot, excluded=["motion"])["recommendations"]
    truncated = copy.deepcopy(snapshot)
    truncated["truncated"] = True
    assert analyze(inventory, {}, truncated)["status"] == "input_limit"
    definitions = {"automation.existing": {"triggers": [{"trigger": "state", "entity_id": "binary_sensor.motion", "to": "on"}],
                                            "actions": [{"action": "light.turn_on", "target": {"entity_id": "light.room"}}]}}
    report = analyze(inventory, definitions, snapshot)
    assert not report["recommendations"]
    assert report["reviewed"][0]["existing_automations"] == ["automation.existing"]


def test_future_holdout_cannot_rescue_failed_training():
    inventory, snapshot = fixture()
    snapshot["events"] = [row for row in snapshot["events"] if row["identity"] != "light" or row["at"] < 0 or row["at"] >= 20 * DAY]
    assert not analyze(inventory, {}, snapshot)["recommendations"]
