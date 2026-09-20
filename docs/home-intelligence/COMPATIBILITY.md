# Verified release source, not a runtime pass

Reviewed 2026-09-20 for the owner's reported Core 2026.9.3:

- [Release package metadata](https://pypi.org/pypi/homeassistant/2026.9.3/json):
  Python >=3.14.2.
- [Pinned test harness metadata](https://pypi.org/pypi/pytest-homeassistant-custom-component/0.13.366/json):
  requires Home Assistant 2026.9.3.
- [HTTP helpers](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/helpers/http.py):
  `KEY_HASS` is an aiohttp `AppKey`, not the literal string `hass`.
- [HTTP server](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/components/http/server.py):
  `async_register_static_paths` with `StaticPathConfig`.
- [Device registry](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/helpers/device_registry.py):
  native child devices may inherit a parent's area. This differs from the
  `via_device` gateway relationship, which provides no physical-location evidence.
- [Automation component](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/components/automation/__init__.py)
  and [scripts](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/components/script/__init__.py):
  loaded component entities expose `raw_config`. Missing definitions remain unknown.

The Linux workflow must pass before declaring runtime compatibility. Windows
Python 3.12.14 runs only the independent algorithm/regression tests. No production
compatibility, successful installation or completed acceptance gate is claimed.
