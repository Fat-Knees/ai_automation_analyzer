"""Sensor platform regression tests."""

from __future__ import annotations

from custom_components.ai_automation_suggester import sensor as sensor_module
from custom_components.ai_automation_suggester.const import CONF_LITELLM_MODEL, DEFAULT_MODELS


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
