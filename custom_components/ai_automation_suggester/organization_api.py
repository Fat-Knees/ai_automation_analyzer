"""Admin-only organization inventory and durable virtual preview API."""
from __future__ import annotations

import asyncio
import copy
from datetime import datetime, timezone
from pathlib import Path

from aiohttp import web
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.helpers import area_registry, device_registry, entity_registry, floor_registry, label_registry
from homeassistant.helpers.http import KEY_HASS
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .organization import build_audit, classify, overlay

LOCAL_PROVIDER = "Local audit (no AI)"
MAX_INVENTORY = 5000
MAX_MAPPINGS = 20000
STATE_KEY = "organization_state"


def definition_snapshot(value, budget, depth=0):
    """Bound validated YAML conversion; HA Template/timedelta objects stay unknown."""
    budget[0] -= 1
    if budget[0] < 0 or depth > 25:
        raise ValueError("Automation definitions exceed the bounded audit scan")
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, dict):
        return {str(k): definition_snapshot(v, budget, depth+1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [definition_snapshot(v, budget, depth+1) for v in value]
    return "{{ unsupported runtime value }}"


def collect_inventory(hass):
    """Copy allowlisted registry metadata; never return raw state attributes."""
    er = entity_registry.async_get(hass)
    dr = device_registry.async_get(hass)
    ar = area_registry.async_get(hass)
    fr = floor_registry.async_get(hass)
    lr = label_registry.async_get(hass)
    devices = list(dr.devices) + list(dr.child_devices)
    if any(len(rows) > MAX_INVENTORY for rows in (er.entities, dr.devices, ar.areas, fr.floors, lr.labels)):
        raise ValueError("Inventory exceeds the 5,000-per-registry audit limit; no partial target report was produced")
    if len(devices) > MAX_INVENTORY:
        raise ValueError("Device inventory including child devices exceeds the audit limit")
    inventory = {
        "areas": [{"id": a.id, "name": a.name, "floor_id": a.floor_id, "aliases": sorted(a.aliases), "labels": sorted(a.labels)} for a in ar.areas.values()],
        "floors": [{"id": f.floor_id, "name": f.name} for f in fr.floors.values()],
        "labels": [{"id": label.label_id, "name": label.name} for label in lr.labels.values()],
        "devices": [{"id": d.id, "name": d.name_by_user or d.name or d.id, "area_id": d.area_id,
                     "parent_device_id": getattr(d, "parent_device_id", None), "labels": sorted(d.labels)} for d in devices],
        "entities": [],
    }
    for entry in er.entities.values():
        state = hass.states.get(entry.entity_id)
        entity = {"id": entry.id, "entity_id": entry.entity_id,
                  "name": entry.name or entry.original_name or entry.entity_id,
                  "device_id": entry.device_id, "explicit_area_id": entry.area_id,
                  "labels": sorted(entry.labels), "disabled": entry.disabled_by is not None,
                  "platform": entry.platform, "identity_confidence": "registry identity",
                  "device_class": entry.device_class or entry.original_device_class or (state.attributes.get("device_class") if state else None),
                  "entity_category": entry.entity_category.value if entry.entity_category else None}
        entity.update(classify(entity))
        inventory["entities"].append(entity)
    for state in hass.states.async_all():
        if state.entity_id in er.entities:
            continue
        if len(inventory["entities"]) >= MAX_INVENTORY:
            raise ValueError("Inventory exceeds the 5,000-entity audit limit")
        entity = {"id": f"unregistered:{state.entity_id}", "entity_id": state.entity_id,
                  "name": state.attributes.get("friendly_name", state.entity_id), "device_id": None,
                  "explicit_area_id": None, "labels": [], "disabled": False,
                  "identity_confidence": "unregistered; rename continuity unavailable",
                  "device_class": state.attributes.get("device_class"), "entity_category": None}
        entity.update(classify(entity))
        inventory["entities"].append(entity)
    for values in inventory.values():
        values.sort(key=lambda row: row["id"])
    definitions, limitations = {}, []
    definition_budget = [10000]
    for domain in ("automation", "script"):
        component = hass.data.get(domain)
        entities = getattr(component, "entities", None)
        if entities is None:
            limitations.append(f"{domain} definitions unavailable; dependencies are unknown")
            continue
        for entity in entities:
            raw = getattr(entity, "raw_config", None)
            if isinstance(raw, dict):
                definitions[entity.entity_id] = definition_snapshot(raw, definition_budget)
            else:
                limitations.append(f"Definition unavailable: {entity.entity_id}")
    return inventory, definitions, limitations


class OrganizationState:
    """Serialize scans/reviews and persist bounded identity mappings with HA Store."""

    def __init__(self, hass):
        self.hass = hass
        self.store = Store(hass, 1, f"{DOMAIN}.organization")
        self.lock = asyncio.Lock()
        self.data = None

    async def load(self):
        if self.data is None:
            self.data = await self.store.async_load() or {"preferences": {}, "mappings": [], "mapping_truncated": False}

    async def report(self):
        await self.load()
        inventory, definitions, limitations = collect_inventory(self.hass)
        report = await self.hass.async_add_executor_job(build_audit, inventory, definitions, self.data["preferences"], limitations)
        candidate = copy.deepcopy(self.data)
        latest = {row["id"]: row for row in candidate["mappings"]}
        area_floors = {area["id"]: area.get("floor_id") for area in inventory["areas"]}
        now = datetime.now(timezone.utc).isoformat()
        changed = False
        for entity in report["inventory"]["entities"]:
            mapping = {key: entity.get(key) for key in ("id", "entity_id", "name", "device_id", "area_id")}
            mapping["floor_id"] = area_floors.get(entity["area_id"])
            prior = latest.get(entity["id"])
            if prior is None or any(prior.get(key) != value for key, value in mapping.items()):
                candidate["mappings"].append({**mapping, "observed_at": now})
                changed = True
        if len(candidate["mappings"]) > MAX_MAPPINGS:
            candidate["mappings"] = candidate["mappings"][-MAX_MAPPINGS:]
            candidate["mapping_truncated"] = True
        if changed:
            await self.store.async_save(candidate)
            self.data = candidate
        report["limitations"].append("Identity mappings are observed at audit time, not continuous historical tracking.")
        if self.data["mapping_truncated"]:
            report["limitations"].append("Old identity observations expired at the 20,000-record retention limit.")
        return report


class OrganizationView(HomeAssistantView):
    url = "/api/ai_automation_suggester/organization"
    name = "api:ai_automation_suggester:organization"
    requires_auth = True

    @staticmethod
    def state(request):
        user = request.get("hass_user")
        if user is None or not user.is_admin:
            raise web.HTTPForbidden(reason="Organization audit requires an administrator")
        hass = request.app[KEY_HASS]
        state = hass.data[DOMAIN].get(STATE_KEY)
        if state is None:
            raise web.HTTPServiceUnavailable(reason="Organization audit is not configured")
        return state

    async def get(self, request):
        state = self.state(request)
        async with state.lock:
            try:
                report = await state.report()
            except ValueError as err:
                return self.json({"error": str(err)}, status_code=422)
        return self.json(report)

    async def post(self, request):
        state = self.state(request)
        # A small streamed limit applies even to chunked requests.
        import json
        payload = bytearray()
        async for chunk in request.content.iter_chunked(8192):
            payload.extend(chunk)
            if len(payload) > 65536:
                raise web.HTTPRequestEntityTooLarge(max_size=65536, actual_size=len(payload))
        try:
            body = json.loads(payload)
            if not isinstance(body, dict) or set(body) != {"revision", "operations", "reviews"}:
                raise ValueError("Expected revision, operations and reviews only")
            reviews = body["reviews"]
            if not isinstance(reviews, dict) or len(reviews) > 200 or any(not isinstance(k, str) or v not in ("accepted", "rejected") for k, v in reviews.items()):
                raise ValueError("Invalid review decisions")
            async with state.lock:
                report = await state.report()
                if body["revision"] != report["revision"]:
                    return self.json({"error": "Inventory or preview changed. Refresh before saving."}, status_code=409)
                if set(reviews) - {p["id"] for p in report["proposals"]}:
                    raise ValueError("Unknown proposal review")
                overlay(report["inventory"], body["operations"])
                preferences = {"operations": body["operations"], "reviews": reviews}
                old = state.data["preferences"]
                state.data["preferences"] = preferences
                try:
                    await state.store.async_save(state.data)
                except Exception:
                    state.data["preferences"] = old
                    raise
                return self.json(await state.report())
        except (ValueError, TypeError) as err:
            return self.json({"error": str(err)}, status_code=400)


async def async_setup_organization(hass):
    """Register a credential-free audit API and a public, data-free card asset."""
    if STATE_KEY in hass.data[DOMAIN]:
        return
    state = OrganizationState(hass)
    await state.load()
    await hass.http.async_register_static_paths([StaticPathConfig(
        "/ai_automation_suggester/home-intelligence-card.js",
        str(Path(__file__).parent / "www" / "ai_automation_suggester" / "home-intelligence-card.js"), False)])
    hass.http.register_view(OrganizationView())
    hass.data[DOMAIN][STATE_KEY] = state
