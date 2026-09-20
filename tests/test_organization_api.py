"""Focused authorization and persistence checks for the organization API."""

from __future__ import annotations

import asyncio
import importlib
import json
import sys
import types
from types import SimpleNamespace

import pytest
from aiohttp import web


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code


class FakeView:
    def json(self, payload, status_code=200):
        return FakeResponse(payload, status_code)


class FakeContent:
    def __init__(self, body):
        self.body = body

    async def iter_chunked(self, _size):
        yield self.body


class FakeRequest(dict):
    def __init__(self, hass, user, body=None):
        super().__init__(hass_user=user)
        self.app = {"hass": hass}
        if body is not None:
            self.content = FakeContent(body)


class FakeUser:
    def __init__(self, is_admin):
        self.is_admin = is_admin


class FakeStore:
    def __init__(self, error=None):
        self.error = error
        self.saved = []

    async def async_save(self, data):
        if self.error:
            raise self.error
        self.saved.append(data.copy())


def _report(revision="revision-1"):
    return {
        "revision": revision,
        "inventory": {"areas": [], "floors": [], "labels": [], "devices": [], "entities": []},
        "proposals": [],
    }


class FakeState:
    def __init__(self, report, *, store=None):
        self.lock = asyncio.Lock()
        self.data = {"preferences": {"before": "value"}}
        self._report = report
        self.store = store or FakeStore()

    async def report(self):
        await asyncio.sleep(0)
        return self._report


def _request(state, body=None, *, is_admin=True):
    hass = SimpleNamespace(data={"ai_automation_suggester": {"organization_state": state}})
    return FakeRequest(hass, FakeUser(is_admin), body)


@pytest.fixture
def api(monkeypatch):
    """Import the API against per-test HA module stubs without changing conftest."""
    http = types.ModuleType("homeassistant.components.http")

    class HomeAssistantView(FakeView):
        pass

    http.HomeAssistantView = HomeAssistantView
    http.StaticPathConfig = lambda *args: args

    helpers = sys.modules["homeassistant.helpers"]
    components = sys.modules["homeassistant.components"]
    monkeypatch.setitem(sys.modules, "homeassistant.components.http", http)
    monkeypatch.setattr(components, "http", http, raising=False)
    monkeypatch.setattr(helpers, "floor_registry", types.ModuleType("homeassistant.helpers.floor_registry"), raising=False)
    monkeypatch.setattr(helpers, "label_registry", types.ModuleType("homeassistant.helpers.label_registry"), raising=False)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.floor_registry", helpers.floor_registry)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.label_registry", helpers.label_registry)
    module_name = "custom_components.ai_automation_suggester.organization_api"
    monkeypatch.delitem(sys.modules, module_name, raising=False)
    module = importlib.import_module(module_name)
    yield module
    monkeypatch.delitem(sys.modules, module_name, raising=False)


def test_non_admin_is_rejected_before_state_lookup(api):
    state = FakeState(_report())
    request = _request(state, is_admin=False)

    with pytest.raises(web.HTTPForbidden) as error:
        api.OrganizationView.state(request)

    assert error.value.status == 403


@pytest.mark.parametrize(
    "body",
    [
        {"revision": "revision-1", "operations": [], "reviews": {}, "forged_approval": True},
        {"revision": "revision-1", "operations": [], "reviews": {}},
    ],
)
def test_post_accepts_only_the_exact_top_level_payload(api, body):
    state = FakeState(_report())
    response = asyncio.run(api.OrganizationView().post(_request(state, json.dumps(body).encode())))

    expected_status = 400 if "forged_approval" in body else 200
    assert response.status_code == expected_status
    if expected_status == 400:
        assert "only" in response.payload["error"]


def test_post_rejects_forged_operation_fields(api):
    state = FakeState(_report())
    body = {
        "revision": "revision-1",
        "operations": [{"kind": "entity_area", "subject_id": "entity", "after": "area", "approved": True}],
        "reviews": {},
    }

    response = asyncio.run(api.OrganizationView().post(_request(state, json.dumps(body).encode())))

    assert response.status_code == 400
    assert "Invalid preview operation fields" in response.payload["error"]


def test_post_rejects_a_stale_review_after_another_save(api):
    old_report = _report("revision-1")
    new_report = _report("revision-2")

    class ConcurrentState(FakeState):
        def __init__(self):
            super().__init__(old_report)
            self.calls = 0

        async def report(self):
            self.calls += 1
            await asyncio.sleep(0)
            return old_report if self.calls == 1 else new_report

    state = ConcurrentState()
    body = json.dumps({"revision": "revision-1", "operations": [], "reviews": {}}).encode()

    async def run_posts():
        return await asyncio.gather(
            api.OrganizationView().post(_request(state, body)),
            api.OrganizationView().post(_request(state, body)),
        )

    first, second = asyncio.run(run_posts())

    assert sorted((first.status_code, second.status_code)) == [200, 409]
    stale = first if first.status_code == 409 else second
    assert stale.payload["error"].startswith("Inventory or preview changed")


def test_persistence_failure_restores_previous_preferences(api):
    state = FakeState(_report(), store=FakeStore(OSError("disk full")))
    previous = state.data["preferences"].copy()
    body = json.dumps({"revision": "revision-1", "operations": [], "reviews": {}}).encode()

    with pytest.raises(OSError, match="disk full"):
        asyncio.run(api.OrganizationView().post(_request(state, body)))

    assert state.data["preferences"] == previous


def test_collect_inventory_returns_registry_allowlist_without_state_attributes(api, monkeypatch):
    area = SimpleNamespace(id="office", name="Office", floor_id=None, aliases=set(), labels=set())
    floor = SimpleNamespace(floor_id="ground", name="Ground")
    label = SimpleNamespace(label_id="critical", name="Critical")
    device = SimpleNamespace(id="device-1", name_by_user=None, name="Relay", area_id="office", labels=set())
    entity = SimpleNamespace(
        id="entity-1",
        entity_id="switch.secret",
        name=None,
        original_name="Secret switch",
        device_id="device-1",
        area_id=None,
        labels=set(),
        disabled_by=None,
        platform="demo",
        device_class=None,
        original_device_class=None,
        entity_category=None,
    )
    registries = {
        "area": SimpleNamespace(areas={area.id: area}),
        "floor": SimpleNamespace(floors={floor.floor_id: floor}),
        "label": SimpleNamespace(labels={label.label_id: label}),
        "device": SimpleNamespace(devices={device.id: device}, child_devices=[]),
        "entity": SimpleNamespace(entities={entity.entity_id: entity}),
    }
    monkeypatch.setattr(api.area_registry, "async_get", lambda _hass: registries["area"])
    monkeypatch.setattr(api.floor_registry, "async_get", lambda _hass: registries["floor"], raising=False)
    monkeypatch.setattr(api.label_registry, "async_get", lambda _hass: registries["label"], raising=False)
    monkeypatch.setattr(api.device_registry, "async_get", lambda _hass: registries["device"])
    monkeypatch.setattr(api.entity_registry, "async_get", lambda _hass: registries["entity"])

    state = SimpleNamespace(entity_id=entity.entity_id, attributes={"device_class": "switch", "secret": "should not escape"})
    hass = SimpleNamespace(
        data={},
        states=SimpleNamespace(get=lambda _entity_id: state, async_all=lambda: [state]),
    )

    inventory, definitions, limitations = api.collect_inventory(hass)

    assert definitions == {}
    assert any("automation definitions unavailable" in item for item in limitations)
    assert inventory["entities"][0]["entity_id"] == "switch.secret"
    assert "should not escape" not in json.dumps(inventory)
    assert set(inventory["entities"][0]) == {
        "id",
        "entity_id",
        "name",
        "device_id",
        "explicit_area_id",
        "labels",
        "disabled",
        "platform",
        "identity_confidence",
        "device_class",
        "entity_category",
        "roles",
        "reasons",
        "risk",
    }
