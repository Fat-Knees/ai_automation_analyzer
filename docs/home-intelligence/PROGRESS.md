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

Latest local audit verification: 131 audit Python tests passed (exit 0).
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

Verified runtime code commit: `5ad93fd2b048ce8449cc7f8403a28d825850a9c7`.
[Linux runtime run](https://github.com/Fat-Knees/ai_automation_analyzer/actions/runs/35541778368):
**6 runtime tests passed in 0.63s**, exit 0, on Python 3.14.2 / HA 2026.9.3. Tests exercise real
config-entry setup/reload/unload, registry and child-device inheritance, persisted
virtual previews without registry mutation, stale revisions, and non-admin denial.
The frontend job passed in that run. The separate
[unit/lint run](https://github.com/Fat-Knees/ai_automation_analyzer/actions/runs/35541778307)
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
  HA lifecycle/security acceptance coverage beyond the six passing runtime tests.

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

The packaged 5ad93fd build passed genuine HA 2026.9.3 tests, including
confirmed-layout persistence and unchanged native areas. Linux Chrome checks
also passed. Next verification adds differential comparisons against HA native
target expansion for labels, child devices, floors, hidden and diagnostic
entities. Reference: pinned homeassistant/helpers/target.py at Core 2026.9.3.

## Observation and release work in progress

Live observation is now connected behind explicit Start/Pause controls and starts
paused on load. It uses stable registry identities, selected numeric/discrete
states and attributes, immutable per-event location snapshots, a bounded queue,
atomic SQLite event/checkpoint writes, privacy exclusion and a database size cap.
Five store tests cover overlap retries, transactional failure, privacy deletion,
consistent snapshots/schema refusal and same-timestamp pagination. Genuine HA
observation lifecycle verification is pending the next CI run. This is partial
M3: no Recorder backfill, aggregate retention, behavior discovery or replay yet.

Release tooling has 18 local archive/fake-remote tests passing. These do not
substitute for a live release or all T16 scenarios. First-install-only scope and
manual recovery limitations are documented in RECOVERY.md. No production
installation, restart or observation has occurred.

Verified runtime commit af940b4: 8 tests passed in 1.03s on HA 2026.9.3 /
Python 3.14.2; run 35542522113. This includes native target comparison and the
opt-in observer's collection, selected attributes, privacy filtering and unload.
Unit suite: 154 tests passed locally, exit 0. Browser desktop/mobile passed.
Pending small follow-up: finite numeric attribute filtering, HA shutdown draining
and installed-build display in the authenticated panel.

## First install candidate

Commit: 77727c132fef53acb760ee3b0f7248413a6642d4.
Archive SHA-256: 871ea68dde72bc10c6c7c20b5ea70bbd0364a681902bcd86f4da294222507d9e.
Linux HA and browser run: https://github.com/Fat-Knees/ai_automation_analyzer/actions/runs/35542821446
All jobs passed. Downloaded the CI artifact and verified the packaged tar.gz is
byte-for-byte identical to the local candidate. Extra local store-cap and
attribute-filter tests passed; the local wrapper ran 156 tests plus lint/frontend
successfully with the runtime skip explicitly labeled. An additional redacted-log
summary test subsequently passed with the release suite (19 tests).

Remote read-only CLI help verified BusyBox tar requires its documented `-o` flag
for owner suppression; installer now uses that flag. `ha core logs --lines 200`
is supported. The diagnostic helper emits only counts and allowlisted exception
types, never raw household messages. Production installation remains unapproved
at the time this record was written; the owner has been asked about this exact
candidate. Full M0-M6 scope remains incomplete as listed above.

## First production installation — 2026-09-20

The owner approved the previously scoped installation in this session. Created
a fresh encrypted manual backup including HA settings/history and apps; metadata
confirmed protected=true and Core 2026.9.3. Copied the encrypted archive to the
ignored local recovery directory and verified matching source/destination SHA-256.
Private backup identifiers and household addresses are not tracked here.

HACS showed AI Automation Suggester available for download, not installed.
The first deployment attempt stopped before remote changes because Windows
OpenSSH reports strict host checking as `true`, while the tool expected `yes`.
The parser now accepts both equivalent enabled values and rejects no/false/ask/
accept-new. Release tests: 25 passed; Ruff passed, exit 0.

Deployed the exact candidate 77727c132fef53acb760ee3b0f7248413a6642d4 and
archive hash recorded above. Deployment returned exit 0, one normal restart,
no rollback, installed-awaiting-user-setup. Completed the authenticated UI flow
using Local audit (no AI); Home Assistant reported successful configuration.
The live Home Intelligence panel loaded actual inventory and explicitly displayed
the full expected commit with Files verified: yes. Refresh observation status
reported Paused, zero stored observations, zero queued and zero overflow losses.
The bounded redacted log summary found no component error lines among 200 lines;
this is not proof of global HA health. No collection, cloud requests, registry
changes, automation edits or device controls were initiated.

Live validation is limited to first installation, local configuration, inventory
rendering, verified build identity and paused observation diagnostics. The separate
readiness HTTP endpoint, live collection, restore and full M0-M6 behavior have not
all been live validated. The large household inventory also exposes UI usability
work: long expanded lists and excessive location questions need prioritization
and filtering before treating the interface as complete.

## Guided interface revision (live verification below)

Replaced the initial technical wall with Start here, Rooms, Observation and
Advanced review navigation. The landing page explains what to do and clearly
states that behavior-based recommendations are unfinished. Rooms show existing
assignments with collapsed member lists. Users can copy existing rooms/floors
into an editable draft without writes, then explicitly save confirmed facts.
Location questions and target-impact details are optional disclosures.
Draft/review behavior and backend approval gates remain intact.

Chrome 153 desktop 1280px and mobile 390px checks passed: guided navigation,
initially hidden technical controls, inert injected text, proposal decisions,
preview persistence, layout saves, no horizontal overflow, and room import with
zero POSTs until confirmation. Local suite: 170 tests passed, lint and Node passed.
Linux candidate CI is pending. Production still runs the prior 77727c1 build.

Added a narrowly scoped frontend-only update tool. It refuses backend, schema or
license changes, verifies the exact installed tree, preserves previous code, and
restores verified code on pre-restart failures. Seven fake-remote/change-scope
tests cover success, configuration failure, lost install/preserve/restart replies,
changed prior files and backend-change refusal. Post-restart recovery remains a
separate inspected operation; no uncertain restart is repeated automatically.

Guided interface candidate 07d394563ccba199f08a124d6ffd08c3c818e0cf passed Linux
runtime/browser run 35544631724 and unit run 35544631708. Its archive SHA-256 is
1e5c11c350163e146fe5ba2f0f559b9cca1460d2d8c4ec777290336d4e0b1c23.

## Activity evidence view (development, separate from UI-only candidate)

Added an admin-only owned-history timeline endpoint and searchable Recorded
activity page. Pages contain at most 50 observations with a keyset cursor, selected
attributes, original per-event mappings and explicit limitations. Initial/restored
states are labeled separately from changes; missing data is not called inactivity.
Browsing activity cannot start observation or invoke device services. The store
test checks bounded pagination, non-fabricated coverage and exclusion deletion.
Chrome desktop/mobile timeline checks pass; 171 local tests plus lint and Node
pass. A real HA timeline endpoint/admin test is added for the next Linux CI run.
This does not complete Recorder backfill, behavioral detection or recommendations.

## Guided interface deployment verified

The user approved exact build 07d394563ccba199f08a124d6ffd08c3c818e0cf,
the recorded archive digest, a fresh encrypted backup and one restart.
The completed backup was copied locally with matching SHA-256. The updater
preserved previous code and passed installed-file verification and core check.
Its one restart command timed out after 90 seconds (exit 1); no second restart
or automatic rollback was attempted. Home Assistant subsequently reconnected.

The old browser tab retained old JavaScript despite reloads. The server returned
the correct new resource. Refreshing its filesystem timestamp did not resolve
that tab; a new authenticated tab displayed Start here, Rooms, Observation and
Advanced review correctly. Observation displayed the exact approved commit and
Files verified: yes. Status was Paused, 1118 stored observations, zero queued,
zero overflow losses. Collection was not enabled by this deployment; the origin
of observations added since the earlier zero-count check was not investigated.
Do not claim the store remained empty. The new tab was left on Start here.
The bounded redacted 200-line log summary contained no component error lines.
This verifies this UI update, not all Home Intelligence requirements.

Development-only commit 5edf87274dacb402e32c65c3407f2ed53e46c9cc passed
GitHub unit run 35544959107 and Linux HA/runtime/frontend run 35544959098.
Its activity timeline/backend changes have not been deployed. Recorder backfill,
behavior discovery, recommendation evidence and controlled application remain
unfinished. No additional production restart or collection permission is implied.
