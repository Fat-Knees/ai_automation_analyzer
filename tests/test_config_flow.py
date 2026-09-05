"""Configuration schema regression tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
import voluptuous as vol

from custom_components.ai_automation_suggester.config_flow import (
    AIAutomationConfigFlow,
    AIAutomationOptionsFlowHandler,
)
from custom_components.ai_automation_suggester.const import CONF_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT


@pytest.fixture(params=["setup", "options"])
def timeout_schema(request):
    if request.param == "setup":
        schema = AIAutomationConfigFlow()._add_token_fields({})
    else:
        entry = SimpleNamespace(data={"provider": "Ollama"}, options={})
        flow = AIAutomationOptionsFlowHandler(entry)
        form = asyncio.run(flow.async_step_init())
        schema = form["data_schema"].schema
    return vol.Schema({key: validator for key, validator in schema.items() if key.schema == CONF_REQUEST_TIMEOUT})


@pytest.mark.parametrize("seconds", [10, 1800, 1801, 7200, 86400])
def test_timeout_accepts_long_local_requests(timeout_schema, seconds):
    assert timeout_schema({CONF_REQUEST_TIMEOUT: seconds})[CONF_REQUEST_TIMEOUT] == seconds


def test_timeout_default_is_unchanged(timeout_schema):
    assert timeout_schema({})[CONF_REQUEST_TIMEOUT] == DEFAULT_REQUEST_TIMEOUT == 900


@pytest.mark.parametrize("seconds", [-1, 0, 9])
def test_timeout_still_rejects_values_below_minimum(timeout_schema, seconds):
    with pytest.raises(vol.Invalid):
        timeout_schema({CONF_REQUEST_TIMEOUT: seconds})