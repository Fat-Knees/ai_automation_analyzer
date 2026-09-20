"""Actual config-entry setup, registry inventory and authenticated HTTP tests."""
from pathlib import Path

import homeassistant.core
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import area_registry, device_registry, entity_registry, floor_registry, label_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components import ai_automation_suggester as integration
from custom_components.ai_automation_suggester.const import CONFIG_VERSION, DOMAIN
from custom_components.ai_automation_suggester.organization_api import STATE_KEY

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
    for _ in range(3):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.data[DOMAIN][STATE_KEY] is state
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.entry_id not in hass.data[DOMAIN]


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


async def test_non_admin_cannot_read_or_save(hass, hass_client, hass_read_only_access_token):
    await setup_local(hass)
    client = await hass_client(hass_read_only_access_token)
    response = await client.get("/api/ai_automation_suggester/organization")
    assert response.status == 403
    response = await client.post("/api/ai_automation_suggester/organization", json={"approved": True})
    assert response.status == 403
