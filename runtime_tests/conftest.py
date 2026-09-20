"""Real HA fixture suite. Never import the sibling tests/conftest.py stubs."""
import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Allow the real loader to discover this custom component."""
