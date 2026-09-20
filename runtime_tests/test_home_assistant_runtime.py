"""Actual config-entry setup, registry inventory and authenticated HTTP tests."""
import os
from pathlib import Path

import homeassistant.core
import pytest
from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import area_registry, device_registry, entity_registry, floor_registry, label_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components import ai_automation_suggester as integration
from custom_components.ai_automation_suggester.const import CONFIG_VERSION, DOMAIN
from custom_components.ai_automation_suggester.organization_api import STATE_KEY, OrganizationState

pytestmark = pytest.mark.asyncio


async def setup_local(hass):
    assert Path(homeassistant.core.__file__).is_file()
    assert Path(integration.__file__).name == "__init__.py"
    entry = MockConfigEntry(domain=DOMAIN, data={"provider": "Local audit (no AI)"},
                            version=CONFIG_VERSION, title="Synthetic local audit")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


async def test_actual_setup_reload_unload_without_provider(hass):
    entry = await setup_local(hass)
    assert STATE_KEY in hass.data[DOMAIN]
    state = hass.data[DOMAIN][STATE_KEY]
    assert "home-intelligence" in hass.data[frontend.DATA_PANELS]
    for _ in range(3):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.data[DOMAIN][STATE_KEY] is state
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.entry_id not in hass.data[DOMAIN]
    assert not state.active_entries
    assert "home-intelligence" not in hass.data[frontend.DATA_PANELS]


async def test_readiness_and_card_resource(hass, hass_client):
    entry = await setup_local(hass)
    client = await hass_client()
    response = await client.get("/api/ai_automation_suggester/readiness")
    assert response.status == 200
    ready = await response.json()
    assert ready["ready"] is True
    assert ready["ha_version"] == "2026.9.3"
    assert ready["store_schema"] == 1
    assert ready["registry_mutation_enabled"] is False
    assert ready["active_entries"] == 1
    if expected_commit := os.environ.get("HI_EXPECTED_BUILD_COMMIT"):
        assert ready["build"]["commit"] == expected_commit
        assert ready["build"]["source"] == "release"
        assert ready["build"]["files_verified"] is True
    response = await client.get("/ai_automation_suggester/home-intelligence-card.js")
    assert response.status == 200
    assert 'customElements.define("home-intelligence-card"' in await response.text()
    await hass.config_entries.async_unload(entry.entry_id)
    response = await client.get("/api/ai_automation_suggester/readiness")
    assert response.status == 503


async def test_real_registry_preview_and_stale_revision(hass, hass_client):
    entry = await setup_local(hass)
    areas = area_registry.async_get(hass)
    floor = floor_registry.async_get(hass).async_create("Synthetic Ground")
    label = label_registry.async_get(hass).async_create("Synthetic Label")
    office = areas.async_create("Synthetic Office", floor_id=floor.floor_id, labels={label.label_id})
    bedroom = areas.async_create("Synthetic Bedroom")
    devices = device_registry.async_get(hass)
    device = devices.async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, "synthetic-relay")}, name="Synthetic relay")
    devices.async_update_device(device.id, area_id=office.id)
    child = devices.async_get_or_create_child(config_entry_id=entry.entry_id,
                                             identifiers={(DOMAIN, "synthetic-child")},
                                             parent_device_id=device.id, name="Synthetic child")
    entities = entity_registry.async_get(hass)
    entity = entities.async_get_or_create("switch", DOMAIN, "synthetic-desk", device_id=device.id)
    child_entity = entities.async_get_or_create("sensor", DOMAIN, "synthetic-child-sensor", device_id=child.id)
    client = await hass_client()
    response = await client.get("/api/ai_automation_suggester/organization")
    assert response.status == 200
    report = await response.json()
    actual = next(row for row in report["inventory"]["entities"] if row["id"] == entity.id)
    assert actual["area_id"] == office.id
    assert next(row for row in report["inventory"]["entities"] if row["id"] == child_entity.id)["area_id"] == office.id
    assert report["inventory"]["floors"] == [{"id": floor.floor_id, "name": floor.name}]
    assert report["inventory"]["labels"] == [{"id": label.label_id, "name": label.name}]
    body = {"revision": report["revision"], "operations": [{"kind": "entity_area", "subject_id": entity.id, "after": bedroom.id}], "reviews": {}}
    response = await client.post("/api/ai_automation_suggester/organization", json=body)
    assert response.status == 200
    preview = await response.json()
    assert next(row for row in preview["proposed"]["entities"] if row["id"] == entity.id)["area_id"] == bedroom.id
    assert entities.async_get(entity.entity_id).area_id is None
    assert devices.async_get(device.id).area_id == office.id
    response = await client.post("/api/ai_automation_suggester/organization", json=body)
    assert response.status == 409
    await hass.config_entries.async_reload(entry.entry_id)
    response = await client.get("/api/ai_automation_suggester/organization")
    assert (await response.json())["operations"] == body["operations"]
    restored = OrganizationState(hass)
    await restored.load()
    assert restored.data["preferences"]["operations"] == body["operations"]


async def test_local_user_flow_needs_no_provider_key(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"}, data={"provider": "Local audit (no AI)"})
    assert result["type"] == "create_entry"
    assert result["data"] == {"provider": "Local audit (no AI)"}
    await hass.async_block_till_done()


async def test_confirmed_layout_persists_without_registry_mutation(hass, hass_client):
    await setup_local(hass)
    areas = area_registry.async_get(hass)
    living = areas.async_create("Living Room")
    lounge = areas.async_create("Lounge")
    client = await hass_client()
    report = await (await client.get("/api/ai_automation_suggester/organization")).json()
    layout = {"description": "An open-plan living space", "floors": [], "entity_policies": {},
              "areas": [{"key": "living", "name": "Living Room", "floor_key": None, "aliases": ["Lounge"],
                         "registry_area_ids": [living.id, lounge.id], "outdoor": False}]}
    body = {"revision": report["revision"], "layout": layout}
    response = await client.post("/api/ai_automation_suggester/layout", json=body)
    assert response.status == 200
    saved = await response.json()
    assert saved["layout"] == layout
    assert saved["layout_findings"][0]["kind"] == "consolidation"
    assert areas.async_get_area(lounge.id).name == "Lounge"
    assert (await client.post("/api/ai_automation_suggester/layout", json=body)).status == 409
    response = await client.post("/api/ai_automation_suggester/organization", json={
        "revision": saved["revision"], "operations": [], "reviews": {}})
    assert (await response.json())["layout"] == layout
    restored = OrganizationState(hass)
    await restored.load()
    assert restored.data["preferences"]["layout"] == layout


async def test_target_preview_matches_native_registry_expansion(hass):
    from homeassistant.const import EntityCategory
    from homeassistant.helpers.target import TargetSelection, async_extract_referenced_entity_ids

    from custom_components.ai_automation_suggester.organization import expand_target, with_effective_areas
    from custom_components.ai_automation_suggester.organization_api import collect_inventory

    entry = await setup_local(hass)
    label = label_registry.async_get(hass).async_create("Target label")
    floor = floor_registry.async_get(hass).async_create("Target floor")
    area = area_registry.async_get(hass).async_create("Target area", floor_id=floor.floor_id)
    devices = device_registry.async_get(hass)
    parent = devices.async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, "target-parent")})
    devices.async_update_device(parent.id, area_id=area.id, labels={label.label_id})
    child = devices.async_get_or_create_child(config_entry_id=entry.entry_id, identifiers={(DOMAIN, "target-child")}, parent_device_id=parent.id)
    entities = entity_registry.async_get(hass)
    normal = entities.async_get_or_create("switch", DOMAIN, "target-normal", device_id=parent.id)
    entities.async_get_or_create("switch", DOMAIN, "target-child", device_id=child.id)
    diagnostic = entities.async_get_or_create("switch", DOMAIN, "target-diagnostic", device_id=parent.id, entity_category=EntityCategory.DIAGNOSTIC)
    hidden = entities.async_get_or_create("switch", DOMAIN, "target-hidden", device_id=parent.id)
    entities.async_update_entity(diagnostic.entity_id, labels={label.label_id})
    entities.async_update_entity(hidden.entity_id, hidden_by=entity_registry.RegistryEntryHider.USER, labels={label.label_id})
    inventory = with_effective_areas(collect_inventory(hass)[0])
    for target in ({"device_id": parent.id}, {"area_id": area.id}, {"floor_id": floor.floor_id},
                   {"label_id": label.label_id}, {"entity_id": [normal.entity_id, hidden.entity_id, diagnostic.entity_id]}):
        native = async_extract_referenced_entity_ids(hass, TargetSelection(target), expand_group=False)
        predicted, unknown = expand_target(target, inventory, "homeassistant.turn_off")
        assert not unknown
        assert predicted == native.referenced | native.indirectly_referenced


async def test_local_observation_opt_in_dedup_privacy_and_unload(hass, hass_client):
    entry = await setup_local(hass)
    state = hass.data[DOMAIN][STATE_KEY]
    assert not state.observer.running
    registry = entity_registry.async_get(hass)
    entity = registry.async_get_or_create("light", DOMAIN, "observed-light")
    excluded = registry.async_get_or_create("switch", DOMAIN, "excluded-load")
    state.data["preferences"]["layout"] = {"entity_policies": {
        excluded.id: {"privacy_excluded": True, "analysis": "always", "location": "fixed"}}}
    client = await hass_client()
    response = await client.post("/api/ai_automation_suggester/observation", json={"enabled": True})
    assert response.status == 200
    assert (await response.json())["running"]
    hass.states.async_set(entity.entity_id, "off")
    await hass.async_block_till_done()
    hass.states.async_set(entity.entity_id, "on", {"brightness": 80, "secret": "must not persist"})
    hass.states.async_set(excluded.entity_id, "on")
    await hass.async_block_till_done()
    response = await client.post("/api/ai_automation_suggester/observation", json={"enabled": False})
    assert response.status == 200
    assert (await response.json())["running"] is False
    rows = await hass.async_add_executor_job(state.observer.store.page)
    assert len(rows) == 2
    assert {row["kind"] for row in rows} == {"seed", "state"}
    assert all(row["identity"] == entity.id for row in rows)
    assert all("secret" not in row["attributes"] for row in rows)
    await state.observer.start()
    await hass.config_entries.async_unload(entry.entry_id)
    assert not state.observer.running
    assert state.observer.task is None


async def test_non_admin_cannot_read_or_save(hass, hass_client, hass_read_only_access_token):
    await setup_local(hass)
    client = await hass_client(hass_read_only_access_token)
    response = await client.get("/api/ai_automation_suggester/organization")
    assert response.status == 403
    response = await client.post("/api/ai_automation_suggester/layout", json={})
    assert response.status == 403
    response = await client.post("/api/ai_automation_suggester/observation", json={"enabled": True})
    assert response.status == 403
    response = await client.get("/api/ai_automation_suggester/readiness")
    assert response.status == 403
    response = await client.post("/api/ai_automation_suggester/organization", json={"approved": True})
    assert response.status == 403
