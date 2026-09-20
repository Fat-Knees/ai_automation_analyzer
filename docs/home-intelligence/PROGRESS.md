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

Latest local audit verification: 129 Python tests passed (exit 0).
The Node frontend test file passed (exit 0), checking request/review behavior and
safe text rendering using a lightweight harness. Actual Chrome 153.0.8010.48
browser checks also passed at 1280px and 390px: accept/reject restoration, inherited
area clearing, exact save payload, literal injection text, and no horizontal overflow.
Read-only SSH discovery confirmed Core 2026.9.3 and that this component is absent.
No production deployment, paid provider request, registry write or device control occurred.

Release metadata confirms Core 2026.9.3 needs Python >=3.14.2. The separate Linux
workflow pins Python 3.14.2, Home Assistant 2026.9.3 and
pytest-homeassistant-custom-component 0.13.366. User sign-in resolved the Git push
blocker. The first run exposed missing async fixture handling; the runtime command
now explicitly uses `-o asyncio_mode=auto`.

Verified runtime code commit: `0e9a1a87f28266e0d5a2704a3814439a6fbc4c15`.
[Linux runtime run](https://github.com/Fat-Knees/ai_automation_analyzer/actions/runs/35540710375):
**4 runtime tests passed**, exit 0, on Python 3.14.2 / HA 2026.9.3. Tests exercise real
config-entry setup/reload/unload, registry and child-device inheritance, persisted
virtual previews without registry mutation, stale revisions, and non-admin denial.
The frontend job passed in that run. The separate
[unit/lint run](https://github.com/Fat-Knees/ai_automation_analyzer/actions/runs/35540710389)
also passed. These bounded tests do not complete every acceptance scenario.

During release-source review, fixed the new and existing HTTP views to use HA's
typed `KEY_HASS` application key. Also distinguished native child-device area
inheritance from gateway `via_device` relationships. Both are relevant to 2026.9.3.

## Known unfinished M1 work

- Applying confirmed topology, missing-floor proposals, canonical merges/splits,
  and enforcing entity policy overrides in future behavioral ingestion.
- Complete native service target equivalence, labels, scenes, dashboards,
  YAML includes, blueprint and external dependency reporting.
- Continuous identity mapping, deletion/recreation lifecycle and migration tests.
- Paginated discovery for installations beyond the explicit inventory cap.
- Full browser accessibility/mobile testing, performance measurements and broader
  HA lifecycle/security acceptance coverage beyond the four passing runtime tests.

## Remaining milestones

M2: scoped live approval, journal, conflicts and compensating rollback.
M3: Recorder ingestion, reliable live/backfill reconciliation and bounded memory.
M4: evaluated behavior/routine discovery and existing automation understanding.
M5: supported replay, non-actuating shadow, validated AI budgets and feedback.
M6: complete UI, performance/soak, packaging and tested deployment/recovery.

No milestone is complete based only on files or mocked tests.

## Work in progress

The admin sidebar and authenticated build/schema readiness are implemented.
Confirmed layout editing now persists descriptions, explicit physical spaces,
aliases, optional floors, outdoor flags and stable-identity entity preferences.
It identifies confirmed missing areas and consolidation candidates, preserves
distinct bathrooms, and does not infer a floor from an outdoor label. Layout
confirmation is not approval to modify HA registries. This covers part of T02;
consolidation execution and historical policy enforcement remain unfinished.
The next CI run will exercise an extracted release archive, its verified file
hashes, preview persistence, and the actual credential-free user flow.
Deployment tooling is under review; no release approval is implied by passing
local audit tests. The requested scope remains all milestones M0 through M6.
