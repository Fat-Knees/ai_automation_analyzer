"""Sensor platform regression tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.ai_automation_suggester import sensor as sensor_module
from custom_components.ai_automation_suggester.const import (
    CONF_LITELLM_MODEL,
    DEFAULT_MODELS,
    SENSOR_KEY_MODEL,
    SENSOR_KEY_STATUS,
)


def test_every_provider_has_a_model_key():
    """Every provider with a default model must resolve to a config key.

    The model sensor falls back to "Unknown Model Key" for providers missing
    here, so a provider added to const.py without updating this map ships a
    broken sensor and a warning on every update.
    """
    missing = sorted(set(DEFAULT_MODELS) - set(sensor_module.PROVIDER_TO_MODEL_KEY_MAP))
    assert not missing, f"providers missing from PROVIDER_TO_MODEL_KEY_MAP: {missing}"


def test_litellm_resolves_to_its_model_key():
    """LiteLLM was absent from the map, so its model sensor never resolved."""
    assert sensor_module.PROVIDER_TO_MODEL_KEY_MAP["LiteLLM"] == CONF_LITELLM_MODEL


def test_litellm_sensor_reports_configured_model():
    entry = SimpleNamespace(
        entry_id="test",
        version=3,
        data={"provider": "LiteLLM", CONF_LITELLM_MODEL: "openai/gpt-4o-mini"},
        options={},
    )
    sensor = sensor_module.AIModelSensor(
        SimpleNamespace(), entry, sensor_module.SensorEntityDescription(key=SENSOR_KEY_MODEL)
    )

    assert sensor._attr_native_value == "openai/gpt-4o-mini"


@pytest.mark.parametrize("request_succeeded,last_error,refresh_succeeded,expected", [
    (None, None, True, "initializing"),
    (True, None, True, "connected"),
    (False, "Provider request failed", True, "error"),
    (True, "Provider request failed", True, "error"),
    (None, None, False, "error"),
])
def test_provider_status_tracks_request_outcome(request_succeeded, last_error, refresh_succeeded, expected):
    coordinator = SimpleNamespace(
        last_update_success=refresh_succeeded,
        data={"request_succeeded": request_succeeded, "last_error": last_error},
    )
    entry = SimpleNamespace(entry_id="test", version=3, data={"provider": "Anthropic"}, options={})
    sensor = sensor_module.AIProviderStatusSensor(
        coordinator, entry, sensor_module.SensorEntityDescription(key=SENSOR_KEY_STATUS)
    )

    assert sensor._attr_native_value == expected
    assert sensor._attr_extra_state_attributes["last_error_message"] == last_error
