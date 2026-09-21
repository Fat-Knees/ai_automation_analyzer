"""Local, bounded motion-to-light evidence. No model, service or state writes.

Fixed thresholds are intentionally conservative and are not calibrated confidence.
Calendar-day controls preserve local time, including across daylight-saving changes.
This first detector does not model numeric conditions or multi-step routines.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from statistics import median
from zoneinfo import ZoneInfo

WINDOW = 60
COOLDOWN = 120
MAX_CANDIDATES = 64
MAX_EVENTS = 20000
VERSION = "motion-light-v1"


class Series:
    def __init__(self, events, coverage):
        self.events = sorted(events, key=lambda row: (row["at"], row["id"]))
        self.times = [row["at"] for row in self.events]
        self.coverage = sorted(coverage, key=lambda row: row["start"])
        self.activations = []
        previous = None
        for row in self.events:
            if row["kind"] == "state" and row["state"] == "on" and previous and previous["state"] == "off":
                if self.covered(previous["at"], row["at"]):
                    self.activations.append(row["at"])
            previous = row if row["kind"] not in {"restored", "removed"} else None

    def covered(self, start, end):
        if any(row["status"] != "observed" and row["start"] <= end and row["end"] >= start for row in self.coverage):
            return False
        cursor = start
        for row in self.coverage:
            if row["status"] != "observed" or row["end"] < cursor:
                continue
            if row["start"] > cursor:
                return False
            cursor = max(cursor, row["end"])
            if cursor >= end:
                return True
        return False

    def state_at(self, timestamp):
        index = bisect_right(self.times, timestamp) - 1
        if index < 0:
            return None
        row = self.events[index]
        if row["kind"] in {"restored", "removed"} or not self.covered(row["at"], timestamp):
            return None
        return row["state"]


def episodes(times):
    result = []
    for timestamp in times:
        if not result or timestamp - result[-1] >= COOLDOWN:
            result.append(timestamp)
    return result


def evaluate(times, trigger, action, zone):
    eligible, delays, unknown, already_on, days = 0, [], 0, 0, set()
    used = set()
    for timestamp in times:
        if not trigger.covered(timestamp, timestamp + WINDOW) or not action.covered(timestamp, timestamp + WINDOW):
            unknown += 1
            continue
        before = action.state_at(timestamp)
        if before == "on":
            already_on += 1
            continue
        if before != "off":
            unknown += 1
            continue
        eligible += 1
        days.add(datetime.fromtimestamp(timestamp, zone).date().isoformat())
        index = bisect_right(action.activations, timestamp)
        if index < len(action.activations):
            outcome = action.activations[index]
            if outcome <= timestamp + WINDOW and outcome not in used:
                delays.append(outcome - timestamp)
                used.add(outcome)
    return {"opportunities": eligible, "matches": len(delays), "days": len(days),
            "match_fraction": len(delays) / eligible if eligible else None,
            "unknown": unknown, "already_on": already_on,
            "median_delay_seconds": median(delays) if delays else None}


def related_automations(definitions, trigger_id, action_id):
    """Conservative duplication warning, not a claim of semantic equivalence."""
    matches = []
    for source, definition in definitions.items():
        triggers = definition.get("triggers", definition.get("trigger", []))
        if isinstance(triggers, dict):
            triggers = [triggers]
        if not isinstance(triggers, list):
            continue
        found = any(isinstance(item, dict) and item.get("trigger", item.get("platform")) == "state"
                    and trigger_id in ([item.get("entity_id")] if isinstance(item.get("entity_id"), str) else item.get("entity_id", []))
                    and item.get("to") == "on" for item in triggers if isinstance(item, dict) and isinstance(item.get("entity_id"), (str, list)))
        if not found:
            continue
        stack = [definition.get("actions", definition.get("action", []))]
        budget = 1000
        while stack and budget:
            budget -= 1
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item[:100])
            elif isinstance(item, dict):
                target = item.get("target", {})
                ids = target.get("entity_id", []) if isinstance(target, dict) else []
                ids = [ids] if isinstance(ids, str) else ids
                if item.get("action", item.get("service")) in {"light.turn_on", "homeassistant.turn_on"} and isinstance(ids, list) and action_id in ids:
                    matches.append(source)
                    break
                stack.extend(value for value in item.values() if isinstance(value, (dict, list)))
    return sorted(matches)


def analyze(inventory, definitions, snapshot, *, timezone="UTC", excluded=()):
    zone = UTC if timezone == "UTC" else ZoneInfo(timezone)
    report = {"algorithm": VERSION, "recommendations": [], "reviewed": [], "candidate_count": 0,
              "truncated": bool(snapshot.get("truncated")), "period": [snapshot["start"], snapshot["end"]],
              "limitations": ["Local evidence, not AI-generated or proof of causality or desirability.",
                              "Only motion/occupancy to same-area light-on patterns are supported.",
                              "Only owned observations are analyzed; Recorder backfill is not available.",
                              "Fixed screening thresholds are not calibrated confidence; multi-candidate statistical significance is not established.",
                              "Static direct references are checked; dynamic, area-targeted and external automations may remain unresolved."]}
    if report["truncated"]:
        report["status"] = "input_limit"
        return report
    excluded = set(excluded)
    entities = [row for row in inventory["entities"] if not row.get("disabled") and row["id"] not in excluded
                and not row["id"].startswith("unregistered:")]
    triggers = [row for row in entities if row["entity_id"].startswith("binary_sensor.") and row.get("device_class") in {"motion", "occupancy"}]
    lights = [row for row in entities if row["entity_id"].startswith("light.")]
    grouped, coverages = {}, {}
    for row in snapshot["events"]:
        grouped.setdefault(row["identity"], []).append(row)
    for row in snapshot["coverage"]:
        coverages.setdefault(row["identity"], []).append(row)
    series = {identity: Series(rows, coverages.get(identity, [])) for identity, rows in grouped.items()}
    split = snapshot["start"] + (snapshot["end"] - snapshot["start"]) * 2 / 3
    for trigger in triggers:
        for light in lights:
            if not trigger.get("area_id") or trigger.get("area_id") != light.get("area_id"):
                continue
            if report["candidate_count"] >= MAX_CANDIDATES:
                report["truncated"] = True
                break
            report["candidate_count"] += 1
            reason = None
            source, target = series.get(trigger["id"]), series.get(light["id"])
            candidate = {"id": sha256(f'{VERSION}:{trigger["id"]}:{light["id"]}'.encode()).hexdigest(),
                         "trigger": {"identity": trigger["id"], "entity_id": trigger["entity_id"], "name": trigger["name"]},
                         "action": {"identity": light["id"], "entity_id": light["entity_id"], "name": light["name"]}}
            if not source or not target:
                reason = "Not enough recorded activity yet"
            elif any(row.get("mapping", {}).get("area_id") != trigger["area_id"] for row in source.events + target.events):
                reason = "Location changed or historical location is unknown; this detector will not combine different room histories"
            else:
                times = episodes(source.activations)
                boundary = bisect_left(times, split)
                train = evaluate([stamp for stamp in times[:boundary] if stamp + WINDOW < split], source, target, zone)
                holdout = evaluate(times[boundary:], source, target, zone)
                controls = []
                for offset in (-7, -1, 1, 7):
                    shifted = []
                    for stamp in times[boundary:]:
                        local = datetime.fromtimestamp(stamp, zone) + timedelta(days=offset)
                        shifted_stamp = local.timestamp()
                        if split <= shifted_stamp and shifted_stamp + WINDOW <= snapshot["end"]:
                            shifted.append(shifted_stamp)
                    controls.append(evaluate(episodes(sorted(shifted)), source, target, zone))
                usable = [row for row in controls if row["opportunities"] >= 4]
                baseline = max((row["match_fraction"] for row in usable), default=None)
                candidate["evidence"] = {"training": train, "holdout": holdout, "split_at": split,
                                         "time_matched_controls": controls, "conservative_baseline": baseline,
                                         "window_seconds": WINDOW, "timezone": timezone}
                if train["opportunities"] < 6 or train["days"] < 3 or holdout["opportunities"] < 6 or holdout["days"] < 3:
                    reason = "More independently observed days are needed for training and later validation"
                elif baseline is None:
                    reason = "Not enough comparable days to rule out a shared daily schedule"
                elif train["match_fraction"] < .7 or holdout["match_fraction"] < .7 or holdout["match_fraction"] - baseline < .3:
                    reason = "Pattern did not pass the later-period and same-time-on-other-days checks"
                else:
                    existing = related_automations(definitions, trigger["entity_id"], light["entity_id"])
                    if existing:
                        candidate["existing_automations"] = existing
                        reason = "Related automation already exists; review its conditions before proposing a duplicate"
            if reason:
                candidate["reason"] = reason
                report["reviewed"].append(candidate)
            else:
                candidate.update(title=f'Consider turning on {light["name"]} after {trigger["name"]}',
                                 risk="Review the actual light/load and desired conditions before use",
                                 next_action="Review evidence and choose conditions; no automation has been installed",
                                 replay_status="Not replayed", origin="local_behavior",
                                 automation={"alias": f'Motion lighting: {light["name"]}', "mode": "single",
                                             "triggers": [{"trigger": "state", "entity_id": trigger["entity_id"], "from": "off", "to": "on"}],
                                             "conditions": [{"condition": "state", "entity_id": light["entity_id"], "state": "off"}],
                                             "actions": [{"action": "light.turn_on", "target": {"entity_id": light["entity_id"]}}]})
                report["recommendations"].append(candidate)
    report["status"] = "ready" if report["recommendations"] else "insufficient_evidence"
    return report
