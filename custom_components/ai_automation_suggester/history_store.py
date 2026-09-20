"""Bounded owned observation storage; never opens or writes Recorder tables.

All methods are blocking and must run in HA's executor. Each transaction opens
its own connection so callbacks never share a thread-bound SQLite connection.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = 1
MAX_BATCH = 500
ATTRIBUTES = {"brightness", "temperature", "humidity", "illuminance", "unit_of_measurement"}
KINDS = {"state", "attribute", "seed", "restored", "removed"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def observation(identity, timestamp, state, attributes, *, kind="state", origin="unknown"):
    """Normalize selected facts, dropping unapproved state attributes/context IDs."""
    if not isinstance(identity, str) or not identity or len(identity) > 255:
        raise ValueError("Invalid stable observation identity")
    if not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp):
        raise ValueError("Observation timestamp must be finite UTC epoch seconds")
    if not isinstance(state, str) or len(state) > 255 or kind not in KINDS:
        raise ValueError("Invalid observation state or kind")
    if origin not in {"unknown", "user-associated", "parent-context", "integration"}:
        raise ValueError("Unsupported origin evidence")
    selected = {key: value for key, value in attributes.items()
                if key in ATTRIBUTES and isinstance(value, (str, int, float, bool)) and len(str(value)) <= 100}
    value = {"identity": identity, "at": float(timestamp), "state": state, "attributes": selected, "kind": kind}
    # Origin enrichment is not identity: live/Recorder copies must deduplicate.
    value["id"] = hashlib.sha256(canonical(value).encode()).hexdigest()
    value["origin"] = origin
    return value


class HistoryStore:
    """Atomic event/checkpoint commits with explicit coverage and consistent backup."""

    def __init__(self, path, *, cap_bytes=512 * 1024 * 1024):
        self.path = Path(path)
        if not 1024 * 1024 <= cap_bytes <= 4 * 1024**3:
            raise ValueError("History cap must be between 1 MiB and 4 GiB")
        self.cap_bytes = cap_bytes

    @contextmanager
    def connect(self):
        if self.path.is_symlink():
            raise ValueError("Owned history path may not be a symlink")
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA journal_mode=DELETE")
            page_size = connection.execute("PRAGMA page_size").fetchone()[0]
            connection.execute(f"PRAGMA max_page_count={self.cap_bytes // page_size}")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, SCHEMA):
                raise ValueError("Unsupported owned history schema; refusing downgrade")
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY, identity TEXT NOT NULL, at REAL NOT NULL,
                    kind TEXT NOT NULL, state TEXT NOT NULL, attributes TEXT NOT NULL,
                    origin TEXT NOT NULL, mapping TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS event_time ON events(at);
                CREATE INDEX IF NOT EXISTS entity_time ON events(identity, at);
                CREATE TABLE IF NOT EXISTS checkpoints (job TEXT PRIMARY KEY, at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS coverage (
                    identity TEXT NOT NULL, start REAL NOT NULL, end REAL NOT NULL,
                    status TEXT NOT NULL, reason TEXT NOT NULL,
                    PRIMARY KEY(identity, start, end, status));
                CREATE TABLE IF NOT EXISTS exclusions (identity TEXT PRIMARY KEY);
            """)
            connection.execute(f"PRAGMA user_version={SCHEMA}")

    def append(self, events, *, job, checkpoint, mappings):
        if len(events) > MAX_BATCH or not isinstance(job, str) or not job or len(job) > 255:
            raise ValueError("Invalid bounded observation batch")
        if not isinstance(checkpoint, (float, int)) or not math.isfinite(checkpoint):
            raise ValueError("Checkpoint must be finite")
        with self.connect() as connection:
            for event in events:
                normalized = observation(event["identity"], event["at"], event["state"], event["attributes"], kind=event["kind"], origin=event["origin"])
                if event != normalized:
                    raise ValueError("Observation was modified after normalization")
                if connection.execute("SELECT 1 FROM exclusions WHERE identity=?", (event["identity"],)).fetchone():
                    continue
                mapping = mappings.get(event["id"], mappings.get(event["identity"], {}))
                allowed_mapping = {key: mapping.get(key) for key in ("entity_id", "area_id", "floor_id", "observed_at")}
                connection.execute("INSERT OR IGNORE INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                   (event["id"], event["identity"], event["at"], event["kind"], event["state"],
                                    canonical(event["attributes"]), event["origin"], canonical(allowed_mapping)))
            connection.execute("INSERT INTO checkpoints VALUES (?, ?) ON CONFLICT(job) DO UPDATE SET at=MAX(at, excluded.at)", (job, checkpoint))

    def mark_coverage(self, identity, start, end, status, reason):
        if status not in {"observed", "gap", "unknown", "expired"} or not math.isfinite(start) or not math.isfinite(end) or end < start:
            raise ValueError("Invalid coverage interval")
        if len(reason) > 200 or len(identity) > 255:
            raise ValueError("Coverage metadata exceeds limits")
        with self.connect() as connection:
            if connection.execute("SELECT 1 FROM exclusions WHERE identity=?", (identity,)).fetchone():
                return
            connection.execute("INSERT OR REPLACE INTO coverage VALUES (?, ?, ?, ?, ?)", (identity, start, end, status, reason))

    def page(self, *, identity=None, before=None, limit=100):
        if not 1 <= limit <= 500:
            raise ValueError("History page limit must be 1–500")
        clauses, params = [], []
        if identity is not None:
            clauses.append("identity=?")
            params.append(identity)
        if before is not None:
            clauses.append("(at < ? OR (at = ? AND id < ?))")
            params.extend((before[0], before[0], before[1]))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.connect() as connection:
            rows = connection.execute(f"SELECT * FROM events{where} ORDER BY at DESC, id DESC LIMIT ?", (*params, limit)).fetchall()
            return [{**dict(row), "attributes": json.loads(row["attributes"]), "mapping": json.loads(row["mapping"])} for row in rows]

    def diagnostics(self):
        with self.connect() as connection:
            count, earliest, latest = connection.execute("SELECT COUNT(*), MIN(at), MAX(at) FROM events").fetchone()
            return {"schema": SCHEMA, "events": count, "earliest_event": earliest, "latest_event": latest,
                    "bytes": self.path.stat().st_size, "cap_bytes": self.cap_bytes,
                    "checkpoints": dict(connection.execute("SELECT job, at FROM checkpoints")),
                    "coverage": [dict(row) for row in connection.execute("SELECT * FROM coverage ORDER BY end DESC LIMIT 500")],
                    "coverage_note": "Returned event bounds do not establish continuous history coverage."}

    def exclude(self, identity):
        """Privacy removal and future ingestion refusal commit together."""
        with self.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO exclusions VALUES (?)", (identity,))
            connection.execute("DELETE FROM events WHERE identity=?", (identity,))
            connection.execute("DELETE FROM coverage WHERE identity=?", (identity,))

    def sync_exclusions(self, identities):
        with self.connect() as connection:
            connection.execute("DELETE FROM exclusions")
            for identity in identities:
                connection.execute("INSERT INTO exclusions VALUES (?)", (identity,))
                connection.execute("DELETE FROM events WHERE identity=?", (identity,))
                connection.execute("DELETE FROM coverage WHERE identity=?", (identity,))

    def snapshot(self, destination):
        destination = Path(destination)
        if destination.exists() or destination.is_symlink():
            raise ValueError("Snapshot destination must be new")
        with self.connect() as source, sqlite3.connect(destination) as target:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Owned history snapshot failed integrity validation")
