"""Admin-only organization inventory and durable virtual preview API."""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from aiohttp import web
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.helpers import area_registry, device_registry, entity_registry, floor_registry, label_registry
from homeassistant.helpers.http import KEY_HASS
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .layout import validate_layout
from .organization import build_audit, classify, overlay

LOCAL_PROVIDER = "Local audit (no AI)"
MAX_INVENTORY = 5000
MAX_MAPPINGS = 20000
STATE_KEY = "organization_state"
PANEL_PATH = "home-intelligence"


def read_build():
    """Read only the release marker; source checkouts identify as development."""
    marker = Path(__file__).with_name("_build.json")
    if not marker.exists():
        return {"commit": None, "format_version": 1, "source": "development"}
    metadata = json.loads(marker.read_text(encoding="utf-8"))
    if metadata.get("format_version") != 1 or not re.fullmatch(r"[0-9a-f]{40}", str(metadata.get("commit", ""))):
        raise ValueError("Invalid release identity")
    files = metadata.get("files")
    if not isinstance(files, dict) or not files or len(files) > 500:
        raise ValueError("Invalid release file manifest")
    root = marker.parent.resolve()
    for name, digest in files.items():
        path = root / name
        if not isinstance(name, str) or "\\" in name or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Invalid release file path")
        if not path.is_file() or path.stat().st_size > 10_000_000 or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Release files do not match the tested build")
    return {"commit": metadata["commit"], "format_version": metadata["format_version"], "source": "release", "files_verified": True}


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
                  "hidden": getattr(entry, "hidden_by", None) is not None,
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
        self.active_entries = set()
        self.build = None
        self.observer = None
        self.analysis_cache = None
        self.analysis_cache_at = 0
        self.ai_request_lock = asyncio.Lock()

    async def load(self):
        if self.data is None:
            self.data = await self.store.async_load() or {"preferences": {}, "mappings": [], "mapping_truncated": False}

    async def report(self):
        await self.load()
        inventory, definitions, limitations = collect_inventory(self.hass)
        report = await self.hass.async_add_executor_job(build_audit, inventory, definitions, self.data["preferences"], limitations)
        report["build"] = self.build
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
        if state is None or not state.active_entries:
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
                preferences = {**state.data["preferences"], "operations": body["operations"], "reviews": reviews}
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
    state.build = await hass.async_add_executor_job(read_build)
    from .observation import ObservationController

    state.observer = ObservationController(hass, state)
    await state.observer.initialize()
    await hass.http.async_register_static_paths([StaticPathConfig(
        "/ai_automation_suggester/home-intelligence-card.js",
        str(Path(__file__).parent / "www" / "ai_automation_suggester" / "home-intelligence-card.js"), False)])
    hass.http.register_view(OrganizationView())
    hass.http.register_view(OrganizationReadinessView())
    hass.http.register_view(OrganizationLayoutView())
    hass.http.register_view(OrganizationObservationView())
    hass.http.register_view(OrganizationTimelineView())
    hass.http.register_view(OrganizationRecommendationsView())
    hass.http.register_view(OrganizationAIView())
    hass.data[DOMAIN][STATE_KEY] = state


class OrganizationRecommendationsView(OrganizationView):
    url = "/api/ai_automation_suggester/recommendations"
    name = "api:ai_automation_suggester:recommendations"

    async def get(self, request):
        from .behavior import analyze
        from .organization import with_effective_areas

        state = self.state(request)
        if request.query:
            return self.json({"error": "No query parameters are supported"}, status_code=400)
        async with state.lock:
            if not state.observer or state.observer.error:
                raise web.HTTPServiceUnavailable(reason="Local history is unavailable")
            inventory, definitions, limitations = collect_inventory(state.hass)
            inventory = with_effective_areas(inventory)
            policies = state.data["preferences"].get("layout", {}).get("entity_policies", {})
            excluded = [identity for identity, policy in policies.items() if policy.get("privacy_excluded") or policy.get("analysis") == "ignore"]
            revision = hashlib.sha256(json.dumps([inventory, definitions, excluded], sort_keys=True).encode()).hexdigest()
            now = time.time()
            if state.analysis_cache and state.analysis_cache[0] == revision and now - state.analysis_cache_at < 60:
                return self.json(state.analysis_cache[1])
            identities = [row["id"] for row in inventory["entities"] if row["id"] not in excluded and not row.get("disabled")
                          and (row["entity_id"].startswith("light.") or (row["entity_id"].startswith("binary_sensor.") and row.get("device_class") in {"motion", "occupancy"}))]
            if len(identities) > 128:
                return self.json({"error": "More than 128 eligible entities; select a smaller analysis scope before analysis"}, status_code=400)
            snapshot = await state.hass.async_add_executor_job(state.observer.store.analysis_snapshot, identities, now - 30 * 86400, now)
            result = await state.hass.async_add_executor_job(
                lambda: analyze(inventory, definitions, snapshot, timezone=state.hass.config.time_zone, excluded=excluded))
            result["limitations"].extend(limitations)
            result["analyzed_at"] = now
            state.analysis_cache, state.analysis_cache_at = (revision, result), now
            return self.json(result)

    async def post(self, request):
        self.state(request)
        raise web.HTTPMethodNotAllowed("POST", ["GET"])


def ai_context(state):
    from .recommendation_ai import prepare

    inventory, definitions, _ = collect_inventory(state.hass)
    from .organization import with_effective_areas

    inventory = with_effective_areas(inventory)
    policies = state.data["preferences"].get("layout", {}).get("entity_policies", {})
    excluded = [identity for identity, policy in policies.items() if policy.get("privacy_excluded") or policy.get("analysis") == "ignore"]
    revision = hashlib.sha256(json.dumps([inventory, definitions, excluded], sort_keys=True).encode()).hexdigest()
    behavior = state.analysis_cache[1] if state.analysis_cache and state.analysis_cache[0] == revision and time.time() - state.analysis_cache_at < 300 else None
    return prepare(inventory, behavior=behavior, excluded=excluded)


def ai_tasks(hass):
    registry = entity_registry.async_get(hass)
    tasks = []
    for entry in registry.entities.values():
        if entry.entity_id.startswith("ai_task.") and entry.platform == "openai_conversation" and not entry.disabled_by:
            value = hass.states.get(entry.entity_id)
            if value and value.state != "unavailable" and int(value.attributes.get("supported_features", 0)) & 1:
                tasks.append({"entity_id": entry.entity_id, "name": entry.name or entry.original_name or entry.entity_id, "provider": "OpenAI"})
    return tasks


class OrganizationAIView(OrganizationView):
    """Explicit preview/approval; native AI task has no HA tools or attachments."""
    url = "/api/ai_automation_suggester/recommendation_ai"
    name = "api:ai_automation_suggester:recommendation_ai"

    async def get(self, request):
        state = self.state(request)
        async with state.lock:
            preview = ai_context(state)
            journal = state.data.get("ai_recommendation_journal", [])
            allowed = {row["entity_id"] for row in preview["payload"]["entities"]}
            history = [{**row, "ideas": [idea for idea in row.get("ideas", []) if set(idea["entity_ids"]).issubset(allowed)]}
                       for row in journal if row.get("status") == "completed"]
            last_failure = next((row.get("failure", {"code": "unknown", "message": "A previous AI request failed. This older build did not retain its failure details; it will not be automatically retried."})
                                 for row in reversed(journal) if row.get("status") == "failed_or_unknown"), None)
            return self.json({"tasks": ai_tasks(state.hass), "history": history[-10:], "running": state.ai_request_lock.locked(),
                              "last_failure": last_failure,
                              "limits": "At most 3 requests per UTC day and 30 per month. No automatic retries. This is a call limit, not a dollar guarantee; provider billing and output limits apply."})

    async def post(self, request):
        from .recommendation_ai import failure_details, response_structure, validate_response

        state = self.state(request)
        raw = bytearray()
        async for chunk in request.content.iter_chunked(2048):
            raw.extend(chunk)
            if len(raw) > 4096:
                raise web.HTTPRequestEntityTooLarge(max_size=4096, actual_size=len(raw))
        try:
            body = json.loads(raw)
            if not isinstance(body, dict) or body.get("action") not in {"preview", "generate"}:
                raise ValueError("Choose preview or generate")
            expected = {"action", "task"} if body["action"] == "preview" else {"action", "task", "digest", "approve_cloud_request"}
            if body["action"] == "generate" and "retry_of" in body:
                expected.add("retry_of")
                if not isinstance(body["retry_of"], str):
                    raise ValueError("Unsupported retry approval")
            if set(body) != expected or not isinstance(body["task"], str):
                raise ValueError("Unsupported AI request fields")
            tasks = ai_tasks(state.hass)
            if body["task"] not in {row["entity_id"] for row in tasks}:
                raise ValueError("Choose an available OpenAI AI Task")
            async with state.lock:
                preview = ai_context(state)
            bound_digest = hashlib.sha256((body["task"] + preview["digest"]).encode()).hexdigest()
            if body["action"] == "preview":
                async with state.lock:
                    prior = next((row for row in reversed(state.data.get("ai_recommendation_journal", [])) if row["digest"] == bound_digest), None)
                retry_of = hashlib.sha256(json.dumps(prior, sort_keys=True).encode()).hexdigest() if prior and prior.get("status") == "failed_or_unknown" else None
                return self.json({"task": body["task"], "provider": "OpenAI", **preview,
                                  "retry_of": retry_of,
                                  "digest": bound_digest,
                                  "notice": "Sends only the displayed selected entity names, IDs, device classes, area names and any displayed summarized behavioral evidence to OpenAI. No raw history, credentials, images or device-control tools. API charges may apply. Ideas without behavioral evidence are labeled capability ideas."})
            if body["approve_cloud_request"] is not True or body["digest"] != bound_digest:
                return self.json({"error": "Approve a fresh, unchanged request preview"}, status_code=409)
        except (ValueError, TypeError, KeyError) as err:
            return self.json({"error": str(err)}, status_code=400)
        if state.ai_request_lock.locked():
            return self.json({"error": "An AI request is already running"}, status_code=409)
        async with state.ai_request_lock:
            now = datetime.now(timezone.utc)
            async with state.lock:
                current = ai_context(state)
                if hashlib.sha256((body["task"] + current["digest"]).encode()).hexdigest() != bound_digest:
                    return self.json({"error": "Home information changed; preview the request again"}, status_code=409)
                journal = state.data.get("ai_recommendation_journal", [])
                prior = next((row for row in reversed(journal) if row["digest"] == bound_digest), None)
                if prior:
                    if prior["status"] == "completed":
                        return self.json({"ideas": prior["ideas"], "cached": True})
                    retry_token = hashlib.sha256(json.dumps(prior, sort_keys=True).encode()).hexdigest()
                    if prior["status"] != "failed_or_unknown" or body.get("retry_of") != retry_token:
                        return self.json({"error": "This request was already attempted. Preview it again and explicitly approve a new potentially billable attempt; pending requests cannot be retried."}, status_code=409)
                elif "retry_of" in body:
                    return self.json({"error": "Retry approval is no longer current"}, status_code=409)
                month = now.strftime("%Y-%m")
                day = now.strftime("%Y-%m-%d")
                monthly = [row for row in journal if row["date"].startswith(month)]
                if len(monthly) >= 30 or sum(row["date"] == day for row in monthly) >= 3:
                    return self.json({"error": "AI request allowance reached"}, status_code=429)
                updated = copy.deepcopy(state.data)
                attempt = hashlib.sha256((bound_digest + now.isoformat()).encode()).hexdigest()
                updated["ai_recommendation_journal"] = monthly + [{"digest": bound_digest, "attempt": attempt, "task": body["task"], "date": day, "status": "pending"}]
                await state.store.async_save(updated)
                state.data = updated
            failure_stage = "provider"
            try:
                from homeassistant.components.ai_task import async_generate_data
                from homeassistant.core import Context

                async with asyncio.timeout(90):
                    response = await async_generate_data(state.hass, task_name="Home Intelligence recommendations",
                                                         entity_id=body["task"], instructions=preview["instructions"],
                                                         structure=response_structure(),
                                                         attachments=None, llm_api=None,
                                                         context=Context(user_id=request["hass_user"].id))
                failure_stage = "validation"
                ideas = validate_response(response.data, preview)
            except Exception as err:
                failure = failure_details(err, failure_stage)
                async with state.lock:
                    updated = copy.deepcopy(state.data)
                    record = next(row for row in updated["ai_recommendation_journal"] if row.get("attempt") == attempt)
                    record["status"] = "failed_or_unknown"
                    record["failure"] = failure
                    await state.store.async_save(updated)
                    state.data = updated
                return self.json({"error": failure["message"]}, status_code=502)
            async with state.lock:
                updated = copy.deepcopy(state.data)
                record = next(row for row in updated["ai_recommendation_journal"] if row.get("attempt") == attempt)
                record.update(status="completed", ideas=ideas)
                await state.store.async_save(updated)
                state.data = updated
            return self.json({"ideas": ideas, "cached": False})


class OrganizationLayoutView(OrganizationView):
    """Save explicitly confirmed physical facts separately from proposed edits."""

    url = "/api/ai_automation_suggester/layout"
    name = "api:ai_automation_suggester:layout"

    async def post(self, request):
        state = self.state(request)
        payload = bytearray()
        async for chunk in request.content.iter_chunked(8192):
            payload.extend(chunk)
            if len(payload) > 65536:
                raise web.HTTPRequestEntityTooLarge(max_size=65536, actual_size=len(payload))
        try:
            body = json.loads(payload)
            if not isinstance(body, dict) or set(body) != {"revision", "layout"}:
                raise ValueError("Expected revision and confirmed layout only")
            async with state.lock:
                report = await state.report()
                if body["revision"] != report["revision"]:
                    return self.json({"error": "Inventory or preview changed. Refresh before confirming layout."}, status_code=409)
                layout = validate_layout(body["layout"], report["inventory"])
                candidate = copy.deepcopy(state.data)
                candidate["preferences"]["layout"] = layout
                await state.store.async_save(candidate)
                state.data = candidate
                if state.observer and not state.observer.error:
                    exclusions = [identity for identity, policy in layout["entity_policies"].items() if policy["privacy_excluded"]]
                    await state.hass.async_add_executor_job(state.observer.store.sync_exclusions, exclusions)
                return self.json(await state.report())
        except (ValueError, TypeError) as err:
            return self.json({"error": str(err)}, status_code=400)


class OrganizationObservationView(OrganizationView):
    url = "/api/ai_automation_suggester/observation"
    name = "api:ai_automation_suggester:observation"

    async def get(self, request):
        state = self.state(request)
        return self.json(await state.observer.diagnostics())

    async def post(self, request):
        state = self.state(request)
        payload = bytearray()
        async for chunk in request.content.iter_chunked(1024):
            payload.extend(chunk)
            if len(payload) > 2048:
                raise web.HTTPRequestEntityTooLarge(max_size=2048, actual_size=len(payload))
        try:
            body = json.loads(payload)
            if not isinstance(body, dict) or set(body) != {"enabled"} or type(body["enabled"]) is not bool:
                raise ValueError("Expected an explicit enabled boolean only")
            async with state.lock:
                if body["enabled"]:
                    await state.observer.start()
                else:
                    await state.observer.stop()
            return self.json(await state.observer.diagnostics())
        except (ValueError, TypeError) as err:
            return self.json({"error": str(err)}, status_code=400)


class OrganizationTimelineView(OrganizationView):
    """Admin-only, one-identity pages from the owned store, never Recorder."""

    url = "/api/ai_automation_suggester/timeline"
    name = "api:ai_automation_suggester:timeline"

    async def get(self, request):
        state = self.state(request)
        try:
            if set(request.query) - {"identity", "before_at", "before_id"}:
                raise ValueError("Unsupported timeline parameters")
            identity = request.query.get("identity", "")
            if not identity or len(identity) > 255:
                raise ValueError("Select a registered entity")
            before = None
            if "before_at" in request.query or "before_id" in request.query:
                at = float(request.query.get("before_at", "nan"))
                event_id = request.query.get("before_id", "")
                if not math.isfinite(at) or not re.fullmatch(r"[0-9a-f]{64}", event_id):
                    raise ValueError("Invalid timeline cursor")
                before = (at, event_id)
            async with state.lock:
                if not state.observer or state.observer.error:
                    return self.json({"error": "Local observation storage is unavailable."}, status_code=503)
                policies = state.data["preferences"].get("layout", {}).get("entity_policies", {})
                if policies.get(identity, {}).get("privacy_excluded"):
                    return self.json({"error": "This entity is excluded from local history."}, status_code=403)
                result = await state.hass.async_add_executor_job(state.observer.store.timeline, identity, before)
                return self.json(result)
        except (ValueError, TypeError) as err:
            return self.json({"error": str(err)}, status_code=400)

    async def post(self, request):
        self.state(request)
        raise web.HTTPMethodNotAllowed("POST", ["GET"])


class OrganizationReadinessView(OrganizationView):
    """Authenticated release/build readiness, not a mere open TCP port."""

    url = "/api/ai_automation_suggester/readiness"
    name = "api:ai_automation_suggester:readiness"

    async def get(self, request):
        from homeassistant.const import __version__

        state = self.state(request)
        return self.json({"ready": True, "build": state.build, "ha_version": __version__,
                          "store_schema": 1, "mode": "organization_preview",
                          "registry_mutation_enabled": False, "active_entries": len(state.active_entries)})

    async def post(self, request):
        self.state(request)
        raise web.HTTPMethodNotAllowed("POST", ["GET"])


async def async_activate_organization(hass, entry_id):
    """Show the audit in the HA sidebar while at least one entry is loaded."""
    from homeassistant.components.panel_custom import async_register_panel

    state = hass.data[DOMAIN][STATE_KEY]
    if not state.active_entries:
        # A new release needs a new module URL even when the browser retains
        # a previously imported custom-panel resource.
        version = (state.build or {}).get("commit") or "development"
        await async_register_panel(hass, frontend_url_path=PANEL_PATH,
                                   webcomponent_name="home-intelligence-card",
                                   sidebar_title="Home Intelligence", sidebar_icon="mdi:home-search",
                                   module_url=f"/ai_automation_suggester/home-intelligence-card.js?v={version}",
                                   require_admin=True)
    state.active_entries.add(entry_id)


async def async_deactivate_organization(hass, entry_id):
    from homeassistant.components.frontend import async_remove_panel

    state = hass.data[DOMAIN][STATE_KEY]
    state.active_entries.discard(entry_id)
    if not state.active_entries and state.observer:
        await state.observer.stop()
    if not state.active_entries:
        async_remove_panel(hass, PANEL_PATH)
