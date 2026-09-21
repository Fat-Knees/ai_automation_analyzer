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

## Chrome stale-interface repair prepared

The user supplied a screenshot of the old Organization preview interface and
confirmed the exact /home-intelligence address. Reloading and opening a new tab
in their normal Chrome did not solve it. The server independently returns the
new guided JavaScript and installed build 07d3945. Earlier in-app verification
does not establish correct rendering in the user's Chrome.

Prepared isolated branch codex/panel-cache-fix from the installed 07d3945 build.
Candidate a10fb4e87da8f2286a409fa6af776f29ec76e224 changes only panel registration
to include the release commit in the JavaScript URL. It does not include the
unreleased history timeline. Archive SHA-256:
96c6eb4e3cad330569eb43d790c2358d4b9cb7cd3b25a6ea904a627345c9be3d.
171 local tests, Ruff and Node pass. GitHub unit run 35545782603 and the frontend
job of runtime run 35545782579 passed; the HA job is still pending completion.
No production repair or additional restart has been performed. Exact-build
approval is still required. Main development branch contains the same fix as
daa900a; its 172-test suite also passed. The existing UI-only updater intentionally
refuses this API-file change; installation must preserve equivalent verification,
backup, pre-restart restoration and no-repeat-on-uncertain-restart behavior.

Final cache-fix CI result: both run 35545782603 (unit) and run 35545782579
(Linux HA plus desktop/mobile frontend) completed successfully. Exact-build
repair approval was requested; installation is pending the user's answer.

## Recommendation workflow implementation (not deployed)

Implemented a bounded local motion-to-light detector with explicit coverage,
seed/restored-state handling, episode debounce, already-on exclusions,
chronological holdout, local-time day-shift controls, original-area checks and
conservative related-automation warnings. Six synthetic tests pass. This is one
screening detector, not the full HI-10 benchmark or calibrated causal inference.

Added a recommendation-first page, owned-history analysis endpoint and native
Home Assistant OpenAI AI Task bridge. The bridge uses the user's existing AI Task
without reading its key. Exact request preview and administrator confirmation
precede any cloud request; no attachments or HA control tools are supplied.
Only bounded selected metadata and current summarized evidence are sent. Response
schemas, entity/evidence references and sizes are checked. Durable pending records
prevent duplicate retries after uncertainty, with 3/day and 30/month call limits.
These limits are not a dollar cap; native-provider output billing is external.
AI ideas are persisted separately from installation/enabling and generic ideas
are labeled as capabilities rather than learned habits.

Local validation: 186 tests passed, Ruff and Node passed; Chrome 153 desktop1280
and mobile390 passed recommendation rendering, inert text, explicit preview/send,
exact approval payload and no actuation. New real-HA tests cover native-task
preview/consent/dedup and analysis authorization; Linux validation pending.
Full Recorder backfill, numeric/sequence routines, replay, feedback/application
and full monetary accounting remain unfinished. Production remains 07d3945.
The previously approved a10fb4e cache-only repair has NOT been deployed and its
restart budget has not been consumed; it does not authorize this broader build.

Recommendation release candidate f90058dbe9f38e9e57c87d60e12a8b5d68142caa:
archive SHA-256 10d754ea5723aea0339f5b329eb84298240608b6c371c832ca393785bcd2e4e6.
GitHub unit run 35547229030 succeeded; Linux HA/native-AI/runtime and frontend
run 35547228943 succeeded. Earlier native-import failures were missing pinned
conversation/camera test dependencies, now included. Tests invoke a fake native
provider response and make no paid calls. Fresh encrypted pre-installation backup
completed and its local copy matched the remote SHA-256. Requested approval to
replace the still-pending cache-only build with this build, one restart total,
and optionally one bounded OpenAI AI Task request for selected metadata.
No new production build, restart or paid request has occurred yet.


## Approved recommendation deployment and failed live request

Installed f90058dbe9f38e9e57c87d60e12a8b5d68142caa after exact-build approval.
Fresh encrypted backup 186ef812 was copied and SHA-256 verified before installation.
Staging, file verification, preservation of prior code and core check completed.
The single restart command timed out at 90 seconds (runner exit 1); no second
restart was issued. Subsequent UI verified the installed build and all files,
and observation remained paused (1118 prior stored observations, no overflow).
The new Recommendations page discovered the existing OpenAI AI Task and displayed
an 80-entity, 11653-byte metadata-only preview with empty behavioral evidence.
One generation button submission by this agent returned a failure. No validated
ideas were displayed or installed. Billing outcome is unknown; no retry was made.
The UI discarded Home Assistant's structured error body, while the backend kept
only failed_or_unknown, so the original reason cannot be recovered from that journal.
Redacted scans of 200 then 2000 core log lines yielded no OpenAI-specific diagnostic.
The native provider uses recommended settings; these were inspected without saving.

Follow-up local changes preserve fixed failure categories without provider text,
surface HA error bodies, retain failures in read-only status, and request native
structured JSON output while retaining strict entity/evidence validation. This is
not a confirmed root-cause fix. Failed/pending requests still cannot retry implicitly.
These changes are not deployed. All larger unfinished requirements remain open.

The follow-up also adds explicit one-attempt retry approval bound to the latest
failed journal record. Pending requests remain blocked; old retry approvals cannot
be replayed, every attempt counts against the existing call caps, and errors never
automatically retry. Native structured-output schema serialization and failure/retry
behavior are covered by new runtime tests. Local 187 tests, Ruff, Node and desktop/
mobile browser smoke passed; new Linux runtime results remain pending.

Repair CI 35548699346: 11 runtime tests passed and one test failed because its
new assertion imported the obsolete voluptuous_openapi serializer. HA 2026.9.3
uses probatio.to_openapi; corrected that test to the installed-version serializer.
This CI failure is separate from the still-unidentified live request failure.
