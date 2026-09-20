"""Owned-store durability and privacy, independent of Recorder and live devices."""
import sqlite3

import pytest

from custom_components.ai_automation_suggester.history_store import HistoryStore, observation


@pytest.fixture
def store(tmp_path):
    value = HistoryStore(tmp_path / "observations.sqlite")
    value.initialize()
    return value


def test_overlap_retry_and_immutable_historical_mapping(store):
    event = observation("registry-a", 100, "on", {"brightness": 50, "secret": "never store", "latitude": 42})
    store.append([event], job="live", checkpoint=100, mappings={"registry-a": {"area_id": "bedroom"}})
    store.append([event], job="backfill", checkpoint=101, mappings={"registry-a": {"area_id": "garage"}})
    assert store.diagnostics()["events"] == 1
    assert store.page()[0]["mapping"]["area_id"] == "bedroom"
    assert store.page()[0]["attributes"] == {"brightness": 50}
    assert store.diagnostics()["checkpoints"] == {"live": 100, "backfill": 101}


def test_failed_batch_cannot_advance_checkpoint(store):
    valid = observation("registry-a", 100, "on", {})
    invalid = {**valid, "id": "forged"}
    with pytest.raises(ValueError):
        store.append([valid, invalid], job="backfill", checkpoint=200, mappings={})
    assert store.diagnostics()["events"] == 0
    assert store.diagnostics()["checkpoints"] == {}


def test_privacy_delete_prevents_later_reingestion(store):
    event = observation("registry-a", 100, "on", {})
    store.append([event], job="live", checkpoint=100, mappings={})
    store.mark_coverage("registry-a", 90, 100, "observed", "Live listener active")
    store.exclude("registry-a")
    store.append([event], job="backfill", checkpoint=101, mappings={})
    assert store.page() == []
    assert store.diagnostics()["coverage"] == []


def test_snapshot_restores_and_future_schema_refused(store, tmp_path):
    store.append([observation("registry-a", 100, "unknown", {}, kind="seed")], job="seed", checkpoint=100, mappings={})
    destination = tmp_path / "snapshot.sqlite"
    store.snapshot(destination)
    restored = HistoryStore(destination)
    assert restored.page()[0]["kind"] == "seed"
    with sqlite3.connect(destination) as connection:
        connection.execute("PRAGMA user_version=99")
    with pytest.raises(ValueError, match="downgrade"):
        restored.initialize()


def test_cursor_keeps_same_timestamp_events_and_checkpoint_never_rewinds(store):
    events = [observation(f"registry-{i}", 100, "on", {}) for i in range(4)]
    store.append(events, job="live", checkpoint=100, mappings={})
    first = store.page(limit=2)
    second = store.page(before=(first[-1]["at"], first[-1]["id"]), limit=2)
    assert len({row["id"] for row in first + second}) == 4
    store.append([], job="live", checkpoint=90, mappings={})
    assert store.diagnostics()["checkpoints"]["live"] == 100


def test_database_cap_failure_preserves_committed_checkpoint(tmp_path):
    store = HistoryStore(tmp_path / "capped.sqlite", cap_bytes=1024 * 1024)
    store.initialize()
    last_committed = None
    for batch_number in range(40):
        events = [observation(f"registry-{i}", batch_number * 500 + i, "on", {"brightness": i % 255}) for i in range(500)]
        try:
            store.append(events, job="live", checkpoint=batch_number, mappings={})
        except sqlite3.OperationalError as err:
            assert "full" in str(err).lower()
            break
        last_committed = batch_number
    else:
        pytest.fail("The configured database cap was not reached")
    assert store.path.stat().st_size <= 1024 * 1024
    assert store.diagnostics()["checkpoints"]["live"] == last_committed
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_nonfinite_or_text_attribute_values_are_not_persisted():
    event = observation("registry-a", 100, "on", {"brightness": float("nan"), "humidity": "private text", "unit_of_measurement": "x" * 100})
    assert event["attributes"] == {}
