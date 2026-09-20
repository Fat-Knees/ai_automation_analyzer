# Implementation evidence

## Baseline — 2026-09-20

- Git base: `71ff7d6c72a09eb2dacfb9970456c444b4aba2e4`.
- Branch: `codex/home-intelligence`; origin is Fat-Knees/ai_automation_analyzer.
- Supplied ZIP checksums verified before extracting. Local context is ignored.
- Target reported by owner: HA OS, Core 2026.9.3. No live verification performed.
- Windows bundled Python 3.12.14, isolated repository `.venv`.
- `.venv/Scripts/python.exe -m pytest -q`: 89 passed, exit 0 before code changes.
- `.venv/Scripts/python.exe -m ruff check .`: passed, exit 0 before code changes.
- Tool installation was confined to the project virtual environment.

## Current slice

Local credential-free config flow, admin-only inventory/preview endpoint, bounded
registry snapshot, stable registry IDs, inherited area handling, metadata-based
roles, conservative static target comparisons, whitespace recommendations,
ambiguous duplicate-name questions, persistent preview reviews and audit-time
identity observations are implemented. This is partial M1, not the full advanced
system. `CAPABILITIES.json` tracks all 18 requirement groups.

Latest local verification: 118 Python tests passed (exit 0); lint passed (exit 0).
The Node frontend test file passed (exit 0), checking request/review behavior and
safe text rendering using a lightweight harness. This is not a browser-layout test.
No production deployment, remote HA connection, paid provider request, registry
write or device control occurred.

Release metadata confirms Core 2026.9.3 needs Python >=3.14.2. The separate Linux
workflow pins Python 3.14.2, Home Assistant 2026.9.3 and
pytest-homeassistant-custom-component 0.13.366. User sign-in resolved the Git push
blocker. The first run exposed missing async fixture handling; the runtime command
now explicitly uses `-o asyncio_mode=auto`.

Verified code commit: `4b6ba4fe631f9ba45ec5a9d0aa62ad896631bd4f`.
[Linux runtime run](https://github.com/Fat-Knees/ai_automation_analyzer/actions/runs/35539633985):
**3 passed in 0.36s**, exit 0, on Python 3.14.2 / HA 2026.9.3. Tests exercise real
config-entry setup/reload/unload, registry and child-device inheritance, persisted
virtual previews without registry mutation, stale revisions, and non-admin denial.
The frontend job passed in that run. The separate
[unit/lint run](https://github.com/Fat-Knees/ai_automation_analyzer/actions/runs/35539633944)
also passed. These bounded tests do not complete every acceptance scenario.

During release-source review, fixed the new and existing HTTP views to use HA's
typed `KEY_HASS` application key. Also distinguished native child-device area
inheritance from gateway `via_device` relationships. Both are relevant to 2026.9.3.

## Known unfinished M1 work

- Confirmed layout authoring and missing-room/floor proposals, aliases,
  canonical merges/splits and persistent entity policy overrides.
- Complete native service target equivalence, labels, scenes, dashboards,
  YAML includes, blueprint and external dependency reporting.
- Continuous identity mapping, deletion/recreation lifecycle and migration tests.
- Paginated discovery for installations beyond the explicit inventory cap.
- Full browser accessibility/mobile testing, performance measurements and broader
  HA lifecycle/security acceptance coverage beyond the three passing runtime tests.

## Remaining milestones

M2: scoped live approval, journal, conflicts and compensating rollback.
M3: Recorder ingestion, reliable live/backfill reconciliation and bounded memory.
M4: evaluated behavior/routine discovery and existing automation understanding.
M5: supported replay, non-actuating shadow, validated AI budgets and feedback.
M6: complete UI, performance/soak, packaging and tested deployment/recovery.

No milestone is complete based only on files or mocked tests.
