"""Opt-in bounded local observation; no device actions or provider requests."""
from __future__ import annotations

import asyncio
import math
import time

from homeassistant.core import callback
from homeassistant.helpers import area_registry, device_registry, entity_registry

from .history_store import HistoryStore, observation

DISCRETE_STATES = {"on", "off", "open", "closed", "opening", "closing", "locked", "unlocked", "unknown", "unavailable"}
DOMAINS = {"sensor", "binary_sensor", "light", "switch", "fan", "cover", "lock"}


class ObservationController:
    """One listener/consumer per integration, with visible loss and failure state."""

    def __init__(self, hass, organization):
        self.hass = hass
        self.organization = organization
        self.store = HistoryStore(hass.config.path(".storage", "ai_automation_suggester.history.sqlite"))
        self.queue = asyncio.Queue(maxsize=2000)
        self.unsubscribe = None
        self.task = None
        self.started_at = None
        self.error = None
        self.overflow = 0
        self.skipped = 0
        self.observed = {}
        self.last_snapshot = {"events": 0, "coverage": []}

    async def initialize(self):
        try:
            await self.hass.async_add_executor_job(self.store.initialize)
            self.last_snapshot = await self.hass.async_add_executor_job(self.store.diagnostics)
        except Exception as err:
            self.error = f"Observation storage unavailable ({type(err).__name__}); organization remains available."
        self.hass.bus.async_listen_once("homeassistant_stop", self.shutdown)

    async def shutdown(self, _event):
        await self.stop()

    @property
    def running(self):
        return self.unsubscribe is not None

    async def start(self):
        if self.running:
            return
        if self.error:
            raise ValueError(self.error)
        self.started_at = time.time()
        self.observed = {}
        self.overflow = 0
        self.unsubscribe = self.hass.bus.async_listen("state_changed", self.receive)
        self.task = self.hass.async_create_background_task(self.consume(), "Home Intelligence observations")

    @callback
    def receive(self, event):
        new = event.data.get("new_state")
        old = event.data.get("old_state")
        state = new or old
        if state is None or state.domain not in DOMAINS:
            return
        if state.state not in DISCRETE_STATES:
            try:
                if state.domain != "sensor" or not math.isfinite(float(state.state)):
                    return
            except ValueError:
                return
        registry = entity_registry.async_get(self.hass)
        entry = registry.async_get(state.entity_id)
        # Unregistered identities have no durable rename/recreation continuity.
        if entry is None:
            self.skipped += 1
            return
        policies = self.organization.data["preferences"].get("layout", {}).get("entity_policies", {})
        policy = policies.get(entry.id, {})
        if policy.get("privacy_excluded") or policy.get("analysis") == "ignore" or entry.disabled_by:
            self.skipped += 1
            return
        kind = "removed" if new is None else "seed" if old is None else "state" if old.state != new.state else "attribute"
        if new is not None and new.attributes.get("restored"):
            kind = "restored"
        context = state.context
        origin = "user-associated" if context.user_id else "parent-context" if context.parent_id else "unknown"
        at = event.time_fired.timestamp() if new is None else new.last_updated.timestamp()
        value = observation(entry.id, at, "absent" if new is None else new.state, state.attributes, kind=kind, origin=origin)
        if kind == "attribute" and old is not None:
            prior = observation(entry.id, at, old.state, old.attributes, kind=kind, origin=origin)
            if prior["attributes"] == value["attributes"]:
                return
        devices = device_registry.async_get(self.hass)
        device = devices.async_get(entry.device_id) if entry.device_id else None
        area_id = entry.area_id or (device_registry.async_get_effective_area_id(self.hass, device) if device else None)
        area = area_registry.async_get(self.hass).async_get_area(area_id) if area_id else None
        mapping = {"entity_id": entry.entity_id, "area_id": area_id, "floor_id": area.floor_id if area else None, "observed_at": at}
        try:
            self.queue.put_nowait((value, mapping))
            self.observed.setdefault(entry.id, at)
        except asyncio.QueueFull:
            self.overflow += 1

    async def consume(self):
        try:
            while True:
                item = await self.queue.get()
                if item is None:
                    break
                batch = [item]
                stop = False
                while len(batch) < 500 and not self.queue.empty():
                    item = self.queue.get_nowait()
                    if item is None:
                        stop = True
                        break
                    batch.append(item)
                values = [item[0] for item in batch]
                # A batch can contain moves; preserve mapping per observation.
                await self.hass.async_add_executor_job(self._persist, batch)
                self.last_snapshot["latest_event"] = max(value["at"] for value in values)
                if stop:
                    break
        except Exception as err:
            self.error = f"Observation paused after storage failure ({type(err).__name__}). Buffered observations may be missing."
            if self.unsubscribe:
                self.unsubscribe()
                self.unsubscribe = None

    def _persist(self, batch):
        self.store.append([value for value, _ in batch], job="live", checkpoint=max(value["at"] for value, _ in batch),
                          mappings={value["id"]: mapping for value, mapping in batch})

    async def stop(self):
        if self.unsubscribe:
            self.unsubscribe()
            self.unsubscribe = None
        if self.task and not self.task.done():
            signal = asyncio.create_task(self.queue.put(None))
            await asyncio.wait((signal, self.task), return_when=asyncio.FIRST_COMPLETED)
            if not signal.done():
                signal.cancel()
            await asyncio.gather(signal, return_exceptions=True)
            await self.task
        self.task = None
        while not self.queue.empty():
            self.queue.get_nowait()
        if self.started_at is not None and not self.error:
            end = time.time()
            status = "gap" if self.overflow else "observed"
            reason = "Live listener queue overflow" if self.overflow else "Live listener active; selected state/attributes only"
            for identity, first_observed in self.observed.items():
                await self.hass.async_add_executor_job(self.store.mark_coverage, identity, first_observed, end, status, reason)
        self.started_at = None

    async def diagnostics(self):
        if not self.error:
            self.last_snapshot = await self.hass.async_add_executor_job(self.store.diagnostics)
        return {**self.last_snapshot, "running": self.running, "error": self.error, "queue": self.queue.qsize(),
                "overflow": self.overflow, "skipped": self.skipped, "source": "live selected states only",
                "limitations": ["Recorder backfill is not connected yet; earlier history is unavailable here.",
                                "Unregistered entities, free-text states, device events and non-allowlisted attributes are not collected.",
                                "Observation does not establish manual control, causality or a desirable automation."]}
