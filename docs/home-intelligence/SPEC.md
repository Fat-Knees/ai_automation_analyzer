# Home Intelligence — full advanced implementation specification
Revision 2 · September 15, 2026

This is a product and engineering contract for a fork of AI Automation Suggester. Features below are requirements, not claims that upstream already implements them. Maintain every requirement ID in a traceability matrix. Staging and production approval gates do not reduce the final product scope.

## HI-01 — Product, compatibility, and architecture

Build one coherent Home Assistant experience for organization, entity intelligence, behavior discovery, existing automation analysis, recommendations, and controlled application. Keep the upstream provider abstraction, existing user configuration, review history, useful notifications, filtering, and packaging working. Preserve licensing and attribution. Do not rewrite the entire project for convenience.

Inventory the actual current code and record its commit before changing it. Record actual HA, Python, integration, and frontend versions tested. Verify version-specific registry/Recorder APIs against the installed release, not only the moving `dev` branch. Use a narrow compatibility adapter and tests for each declared HA version. Reevaluate the manifest's dependency/loading strategy so local-only audit can operate without a cloud credential, and lack of Recorder disables history features rather than unrelated organization features.

Use modules with explicit data contracts: inventory/identity; topology planning; dependency/target resolution; proposal/application journal; entity roles; history ingestion; persistence; feature extraction; candidate graph; statistics/routines; automation modeling; replay; recommendation evidence; provider calls; feedback; authenticated frontend APIs; observability; deployment. These are logical boundaries, not a requirement to create dozens of empty modules.

Prefer one in-process integration with an integration-owned local store, not mandatory InfluxDB, MQTT, graph servers, vector databases, or another always-on machine. A bounded off-process analysis worker is an optional measured optimization, not a prerequisite. A graph can be ordinary indexed tables or adjacency maps. Keep UI responsive and progressive while long jobs run. Persist checkpoints and job status.

Preserve the `ai_automation_suggester` domain initially unless an explicit migration is implemented and tested. The upstream integration and a same-domain fork must not both manage competing versions of the same component path. Detect update ownership before deployment. Do not uninstall or change HACS ownership automatically. Package a reproducible build and document a deliberate development-to-release update path.

## HI-02 — Inventory and durable identity

Collect accessible devices, entities, integrations, capabilities, areas, floors, labels, aliases, existing automation/script/scene definitions, groups/helpers, and discoverable dashboard references. Record source, timestamp, confidence category, and scan completeness for each datum. Disabled registry entries and entities with no registry entry need explicit handling; lack of a unique ID can prevent supported registry edits.

Model registered entities with a stable internal key tied to their registry identity, not merely their mutable `entity_id`. Preserve provider identity and domain. Maintain time-versioned entity ID/name, device, area, and floor mappings. An entity moved from Bedroom to Garage must not cause old bedroom observations to become garage history. For unregistered entities, use a documented fallback identity and lower continuity confidence. Deletion/recreation or hardware replacement must not silently merge unrelated histories.

Resolve effective area through supported HA semantics: explicit entity assignment and device inheritance. Preserve explicit versus inherited values. `via_device`/gateway relationships are not evidence of the child device's physical room. Compute effective target membership with version-correct HA behavior rather than assuming labels propagate exactly like areas. Store unresolved/dynamic dependencies as unknown.

Discovery endpoints must return paginated/bounded data, omit secret attributes, and enforce appropriate authorization. Define local evidence IDs so recommendations can point to actual observations without sending every raw record to a model.

## HI-03 — Room, area, and floor planning

Make topology cleanup a first-class feature, not just a dropdown attached to entity renaming. Show the current organization and a proposed organization side by side before any edits.

Recommend missing areas suggested by reliable existing names/assignments or user-confirmed physical spaces; recommend clearer area names, aliases, case/spelling normalization, duplicate consolidation, splitting an overly broad area, moving an area to its actual floor, creating missing physical floors, and correcting floor names/levels. Recommend leaving floors unused when they add no value. Recommend labels for cross-cutting concepts such as Exterior or Infrastructure instead of inventing fake physical floors.

Home Assistant rooms/spaces are represented by areas. Areas may belong to floors; devices/entities are assigned to areas, not directly to floors. Do not invent a native floor → area → subroom registry hierarchy. An open-plan space can remain one area or use distinct areas with labels, according to the user's actual use. Garage and Backyard can be areas; do not automatically turn them into floors. Do not infer floor count, elevation, adjacency, or a floor plan from radio link quality or correlated behavior.

Treat confirmed user layout as authoritative until the user changes it. Preserve intentional synonyms and distinguish similar names that can identify different rooms, such as Bath and Guest Bath. A proposed merge must retain a selected canonical area, identify assignments/references to migrate, and treat deletion of the redundant area as a separate approval. Prefer a non-destructive alias or manual review when identity is ambiguous.

Use independent evidence sources: confirmed layout, existing consistent registry assignments, device/entity names, relevant configured targets, and optionally behavioral evidence. Record contradictory evidence. Multiple names copied from one source are not multiple independent confirmations. Statistical association does not establish physical location. Use labels such as Confirmed, Strong evidence, Tentative, Needs input; numerical likelihoods require actual calibration and supporting methodology.

Provide a batched clarification form: candidate room/floor, evidence, conflicting clues, and a select/edit/unknown choice. Ask the user only about genuinely ambiguous physical facts. An optional user-initiated identify action may be offered only for a known safe supported device and exact approved action; no automatic blinking, switching, unlocking, or alarm testing.

Provide a free-text home-layout description field and structured editor for floor names, area names, aliases, open-plan choices, outdoor spaces, portable devices, and multi-room exceptions. AI may convert a description to a proposal, never silently make it a confirmed fact. No image/floor-plan upload is required for core functionality.

## HI-04 — Names, placement, labels, and entity cleanup

Propose device names, displayed entity names, area/floor names, aliases, icons, and labels consistently. Support short context-aware display names and explain where independent dashboards/voice clients may need more specificity. Keep entity IDs stable by default. Do not equate cosmetic naming with a requirement to regenerate IDs.

When ID changes are explicitly requested, preserve the domain, provider unique ID, and entity identity. `sensor.x` → `binary_sensor.x` is not an allowed naming change. Avoid collisions and invalid IDs. Preview all dependencies and the effect on this integration's history mapping. Prefer HA's existing supported naming settings for future entities when available on the installed version, rather than implementing a competing global naming mechanism. Do not silently change the installation-wide naming format.

Respect portable phones, roaming vacuums, whole-house weather, multi-channel relays, remote sensors, and devices controlling loads in multiple rooms. Assign the device area only when inheritance is appropriate. Preserve intentional entity-level overrides. Do not force every entity into a room.

Identify stale/duplicate/unavailable candidates but never delete or disable them solely from inactivity, low usefulness, or a manufacturer-generated name. Sleeping battery devices, seasonal devices, and rarely triggered safety sensors can be valid. Separate the analysis inclusion policy from HA's enabled/disabled/hidden settings. Keep diagnostic classification reversible and task-specific.

## HI-05 — Dependency analysis and target-impact preview

Scan version-supported automation, script, scene, dashboard, group, helper, and approved configuration sources. Respect YAML includes/packages and supported UI-managed configuration. Use structured parsing where possible. Do not globally replace strings across `/config` or edit core `.storage` JSON manually. Never expand `!secret` values into prompts. If a dashboard/backend has no safe write path, support audit/manual remediation rather than pretend it is automatically migratable.

Separate literal references, device references, area/floor/label targets, and dynamic expressions. A dependency scanner is not a proof of completeness: templates, external Node-RED flows, MQTT consumers, apps, scripts, and third-party dashboards may be unresolved. Report sources scanned, sources unavailable, external dependencies declared by the user, and unresolved cases. Use supported native update mechanisms where available; do not assume every reference is updated automatically.

For ALL topology/label changes, resolve targeted entity sets before and after. Show added and removed targets by affected automation/script/action. Example: moving a plug into Bedroom could make a Bedroom-wide turn-off action affect it. Separate approval of the room fact from acknowledgment of this behavioral effect. Unknown target expansion is a review blocker, not an empty set.

Names and aliases may also be used in templates or voice clients. Mark those dependencies; do not overstate that every display rename is consequence-free. Preserve IDs of canonical areas/floors where possible rather than unnecessary delete-and-recreate operations.

## HI-06 — Approval, application, and recovery

Use typed proposal objects with stable IDs, exact before/after values, evidence IDs, reasoning, scope, risk, dependency/target-impact report, reversibility classification, and unresolved blockers. Persist a canonical plan hash and expected source snapshot revision. Separate generated proposals from user approvals.

Backend writes require an authenticated authorized user, an explicit accepted plan/operation set, fresh preconditions, and enabled mutation mode. LLM text, a forged `approved=true`, or possession of a proposal ID cannot grant permission. Bind approval to plan contents, installation, snapshot, and expiry/revalidation rules. Avoid pretending app-level gates confine arbitrary custom-component Python, which runs with HA privileges.

Implement idempotent application steps and a durable operation journal. Immediately before each write verify that the expected field still matches. Stop on conflict; do not overwrite user edits. Use version-verified HA registry helpers/APIs. Apply known-safe independent operations in controlled batches. Multi-registry operations are a saga with compensating steps, not a promised global ACID transaction.

Provide preview, apply selected, resume, cancel, rollback preview, and conflict resolution. On rollback verify the current value still matches the value written by this batch. If not, require review. Deletions and certain identity changes may not be fully reversible; expose that before approval. Do not promise to reverse physical device effects caused by changed automation targeting. Keep a recovery path outside this integration's own UI.

## HI-07 — Task-aware entity usefulness

Allow multiple roles per entity: trigger, actuator, context, measurement, presence, safety/security, maintenance/diagnostic, infrastructure, unknown. Show relevance by task, not one universal usefulness score. The same battery sensor can be irrelevant to lighting routines and valuable to maintenance. A smoke/leak sensor remains important with zero transitions. A switch's actual load can make it dangerous regardless of domain.

Use metadata, capabilities, manual preferences, meaningful state/attribute changes, availability, active days, configured references, device/area context, and observed relationships. Separate relevance, data quality, privacy eligibility, and actuation risk. High event frequency is not automatically useful; low event frequency is not automatically useless.

Support always analyze, high priority, automatic, low priority, and ignore. Explicit privacy exclusions override automatic promotion. Periodically sample eligible borderline entities within resource limits; explain why relevance rises or falls. State-change events are not the only useful source: brightness changes, button events, and other attributes/events may matter where explicitly supported and available. Publish capability and history-availability limits for those sources.

## HI-08 — Accurate Recorder ingestion

Use a version-tested Recorder/history adapter, executing database work in the proper executor/session lifecycle. No direct Recorder writes and no unbounded scans. Verify installed API signatures; internal APIs are not assumed stable contracts. Report Recorder disabled, excluded entities, missing database access, and unsupported versions explicitly.

Backfill available detailed data in bounded entity/time chunks. Retrieve the pre-window seed state when possible and treat it as state initialization, not an event within the window. Preserve only necessary context/attributes; an unconditional `no_attributes` policy would lose brightness and other requested features. Select attributes by entity role and privacy allowlist.

Treat timestamps in UTC for storage and the instance's configured timezone for local routines. Use the HA timezone, not the laptop timezone. Handle daylight-saving folds/gaps, unavailable/unknown states, deletion, rename, reorder, and late arrivals. Distinguish a state value change, attribute change, update-only event, and boot-restored state. Do not count a restart as an actual household action without evidence.

Establish explicit coverage intervals and gaps per entity/data type. Oldest returned state is not proof of continuous coverage. Configured retention is not proof that the entity existed or was recorded throughout it. Do not fabricate events before current retention; increasing retention only helps future data unless a separate verified historical source exists.

Coordinate live subscription and backfill using watermarks, bounded overlap, deduplication, and restart-safe checkpoints. Capture live events during backfill with a bounded buffer or equivalent correct reconciliation. Overflows produce visible gaps and a Recorder catch-up attempt, not silent loss. Atomically persist ingestion effects and checkpoint progression so restarts do not inflate counts. Do not use context ID alone as a globally unique event ID.

## HI-09 — Long-term behavioral persistence

Use an integration-owned compact local store with schema versions, indexes, bounded writes, migrations, corruption detection, recovery, and verified backup integration. Small preferences can use HA Store; benchmark before choosing Store for large time-series data. SQLite is a reasonable candidate for indexed behavioral data, not a mandatory separate server. Never modify Recorder's schema.

Distinguish recent selected events/attributes, daily features, aggregate relationship/routine evidence, and longer-term baselines. Start with proposed recent-data retention around 30–60 days, daily summaries around a year, and longer-term compact summaries only within a configurable total storage cap. Defaults must be measured and adjustable; no promise of infinite history or constant disk use.

A historical histogram cannot recover arbitrary event sequences. Retained relationship counters preserve only relations already measured. Store feature/algorithm versions and mark which outputs are recomputable, approximate, stale, or impossible to reconstruct after raw-data expiry. Keep enough bounded fine-grained information for supported replay; when it is gone, disable exact replay for that interval instead of faking it.

Track observations before/after algorithm changes without silently mixing incompatible counters. Preserve time-versioned organization and entity identities. Support export of sanitized summaries, user-requested deletion by entity/period, resetting learned preferences, deletion on uninstall by explicit choice, and retention policy changes. Honor privacy deletion across events, aggregates, caches, and prompts where locally retained; document external-provider retention limits.

Test consistent backup of the owned database, including WAL/sidecars or use a supported consistent snapshot. Merely placing a file under `/config` is not sufficient proof of restore correctness. Verify inclusion in an actual backup/restore exercise on staging. Do not copy an open database with ordinary file copy and assume consistency. Downgrades must check schema compatibility; code-only rollback may require a compatible store snapshot.

## HI-10 — Local relationship and routine engine

Generate bounded candidates from semantic compatibility, confirmed organization, configured references, and previous evidence. Add a small documented exploration budget for eligible cross-area relationships. Do not attempt uncontrolled all-to-all sequence enumeration. Cap depth, candidate count, context partitions, time windows, and per-job work; expose truncation and effects on recall.

Analyze event episodes, not every motion retrigger as independent evidence. Define eligible opportunities, window boundaries, initial state, action already-on exclusions, cooldown/debounce, and whether an outcome can match more than one trigger. Compute support across distinct days as well as raw count, conditional match fraction, baseline probability, lift, delay distribution, stability, and coverage. Display numerators/denominators and distinguish these metrics from probability that an automation is desirable.

Use matched contextual baselines and time-aware null models to avoid discovering that unrelated devices both run at 7 PM. Preserve temporal autocorrelation, occupancy, and time-of-day structure in null evaluation. Apply multiple-comparison control to large candidate sets. Tune thresholds only on training periods and evaluate on chronological holdouts, not random future-leaking splits. Report uncertainty and failures as well as successful patterns.

Support pairwise A→B, repeated A→B→C sequences, conditional routines, typical durations, and absence-of-expected-action opportunities where coverage supports them. Use entity-type-informed but configurable windows, then fit delay distributions with bounds. Avoid discovering arbitrarily long sequences from a handful of examples. Separate familiar routine completion from anomaly detection.

An interpretable numeric feature layer should use units, hysteresis, sustained duration, robust thresholds, quantiles, slopes, peaks, and appliance-power episodes. Select thresholds on training data. Do not treat every tenth-degree update as a new independent event. Attribute-level user adjustments, such as brightness after auto-on, require corresponding retained attributes; otherwise mark the analysis unsupported.

Context can include occupancy, time, weekday/weekend, daylight, illumination, temperature/humidity, weather, media state, doors/windows, HVAC, tariffs, and season when present and consented. Missing context reduces eligibility/coverage rather than becoming false. Do not infer an annual seasonal pattern from ten days of data. Preserve household-level privacy; infer named personal routines only with an explicit need and consent.

## HI-11 — Automation understanding and attribution

Inventory existing enabled and disabled automations, scripts, scenes, helpers, groups, and discoverable blueprint expansion. Model static triggers, conditions, targets, actions, and relevant modes/overlaps. Publish unsupported templates, dynamic service names/targets, integrations, and externally managed automations. Do not equate simple YAML parsing with full semantic understanding.

Use context IDs/user IDs/parent context and traces where actually available to classify origin: supported user association, supported automation/script chain, device/integration, or unknown. Absence of a user/parent ID does not prove physical/manual control. Some button actions are events rather than state changes; publish source limitations. Context attribution and temporal association are different forms of evidence.

Mark candidate behavior as confirmed explained, probably explained, not found in inspected sources, or unknown. Lack of a discovered automation is not proof that none exists. Suppress redundant new suggestions while still detecting repeated overrides, schedule/brightness corrections, flapping, missed conditions, or duplicate/conflicting actions. Version analysis when automation definitions change.

## HI-12 — Historical replay and shadow mode

Build a safe declarative intermediate representation and publish a tested support matrix for triggers, conditions, timing, and effects. Start with state/numeric/time/sun/zone constructs only when implemented and supported by historical data; expand deliberately. Timezone and sun/zone calculations require the relevant historical configuration/data. Unsupported arbitrary Jinja, dynamic actions, device triggers, wait/repeat/parallel behavior, scripts, or modes must remain unsupported until specifically implemented and tested.

Use three-valued condition evaluation: true, false, unknown. Count evaluable and unknown intervals. For each proposal report hypothetical activations, overlap with observed relevant events, duplicate/already-on activations, available history, excluded periods, and potential conflicts. Call a measure precision only when ground-truth labels justify it; matching past action timestamps alone is not such a label.

Never call actual services during replay or tests. Never mutate HA states to imitate devices. Do not claim a counterfactual trajectory: a proposed light-on could alter future motion, illuminance, or user behavior, which unchanged recorded history cannot establish. Expose assumptions. Energy/cost savings require measured power/tariffs and explicit assumptions; otherwise omit the estimate.

Implement shadow mode that observes new events and records would-fire decisions without actuation. Let the user label suggestions useful/unwanted/uncertain. Keep shadow evidence distinct from synthetic and historical evidence. Offer a preview of changed automation logic, retain the old version, and require separate approval to install then enable anything.

## HI-13 — Evidence-first AI and budget controls

Retain existing providers and local-model options; local inventory/statistics must remain useful without AI access. Send only allowlisted compact evidence selected locally, with schema version, evidence IDs, sample counts, coverage, unresolved facts, supported operations, and budget. No raw bulk history, credentials, exact coordinates, images/audio, or unrelated household attributes by default.

Treat all input names/logs/config text as untrusted data. The LLM may propose semantics, explain patterns, suggest conditions, and draft YAML. It must not manufacture statistics, approve changes, choose executable shell commands, issue arbitrary SQL, or autonomously access HA tools. Validate schemas and entity/evidence references; escape frontend output. Reject invented devices, invalid domains/services, stale candidates, conflicting targets, and unsupported claims.

Each suggestion includes purpose, actual supporting evidence, limitations, entities/areas, risk, already-covered behavior, replay/shadow status, a proposed automation where possible, and next action. Clearly distinguish evidence-backed behavioral suggestions from optional generic capability ideas. Rank by expected usefulness, support, novelty, burden, and risk, with an explainable score rather than AI enthusiasm.

Implement request previews, estimated token cost when rates are known, actual usage reconciliation, reasoning/output accounting where reported, cached/in-flight request deduplication, input/output caps, bounded retries, timeouts, exponential backoff, cancellation, and concurrent budget reservation. Unknown prices prevent a claimed monetary hard guarantee; allow conservative token/call limits or require rate configuration. Record estimated versus billed/observed usage honestly.

A proposed $2/month application budget is a user-configurable starting limit, not an estimated bill or provider guarantee. This application's budget cannot cap usage by other clients sharing the same provider key. Never silently fail over to a paid provider or to a different privacy policy. Local providers have hardware/electricity costs and availability constraints; laptop-off must not break local collection.

## HI-14 — Feedback, drift, anomalies, and lifecycle

Maintain accepted, installed, enabled, declined, dismissed, wrong interpretation, already handled, and remind-later as distinct states. Accepting a suggestion does not install or enable it. Deduplicate recurring suggestions across runs/providers and preserve feedback through entity renames. Let the user edit/reset preferences and explicitly change a past rejection.

Learn explainable ranking preferences, not hidden assumptions about people. Compare recent vs older behavior with minimum coverage; decay stale evidence without destroying provenance. Identify newly emerging routines, disappearing routines, seasonal changes supported by adequate history, and new-device effects. Reevaluate after confirmed moves or automation changes to avoid mixing regimes.

Provide anomalies/opportunities such as unusually long on-times, repeat overrides, loss of sensor activity, battery/availability issues, and flapping. These are advisory, not certified alarms or safety monitoring. Allow quiet hours, notification severity, snooze, goal-specific opt-outs, and an observation-only global pause. Protect users from repeated noisy prompts.

Provide ongoing new-device onboarding and an optional periodic organization audit, explicitly enabled by the user. Recommendations about new rooms or labels remain proposals, not automatic structure changes.

## HI-15 — Frontend and workflow

Build a responsive, accessible Home Assistant panel/card experience, reusing existing frontend infrastructure where sensible. Avoid a second login, exposed service, or separate database UI. Use authenticated HA API communication and server-side admin checks for sensitive views/actions. Support multiple users with appropriate permissions; never hide a button while leaving its endpoint writable.

Ship a useful read-only UI early, not after all research algorithms. The first slice shows real inventory or clearly labeled fixture data, current/proposed topology, evidence, ambiguity questions, and target-impact preview. Add functional review/edit/reject controls before live apply. Preserve intentional user corrections.

Final sections: Overview; Organization; Entity Explorer; Behaviors/Routines; Existing Automations; Recommendations; Replay/Shadow; Feedback; Settings; Diagnostics. Include coverage bars, stale-data warnings, event timelines, understandable metrics, before/after diffs, per-entity task relevance, and accessible progress/cancel states. Synthetic examples must have an unmistakable label.

Add optional natural-language questions such as “Why was this suggested?” or “What changed in the kitchen this week?” through a bounded read-only query layer over prepared facts. Do not give the model raw shell/SQL access. Answers cite local evidence and acknowledge unavailable history. Do not let this optional feature delay the core workflow.

## HI-16 — Security and deployment contract

Use local Codex on the laptop for development; the runtime integration stays in HA. SSH is a deployment/admin channel, not a requirement for runtime intelligence. The official Terminal & SSH app is not host debugging access, but its `/config` and CLI privileges are broad. Do not promise a one-folder sandbox. Default to approve-on-use remote commands. Do not expose SSH to the internet, enable agent forwarding, disable host-key checking, or weaken protection modes for convenience.

Normal integration inventory uses HA registry helpers and frontend authentication, not a separately stored all-powerful token. An optional external diagnostics client requires a separately authorized credential injected outside the model; registry mutation may require administrator privileges. Do not imply long-lived tokens are automatically read-only. Do not use SSH access to extract auth tokens.

Treat deployments as explicit approved operations with build hash, target, path, data-schema compatibility, maintenance window, and a limited restart budget. Require local tests plus isolated real-HA runtime verification. Use synthetic staging without household credentials, radio devices, actuators, or copied live automations. A restored full production config is not a harmless staging fixture.

Deployment tooling must check native-process exit codes, timeouts, paths, available disk, expected current version, ownership, symlinks/archive traversal, and hashes; maintain a lock across worktrees. Verify the backup job actually completed. Preserve the old component and a consistent owned-data snapshot when needed. Upload to staging; swap only after approved preflight. On pre-restart check failure, restore changed files without restart. On approved restart, verify HA readiness and integration build/schema/config-entry status, not simply a TCP port or one grep line.

Allow at most one automatic rollback attempt when authorized and safe. Do not repeatedly restart. Refuse blind schema downgrade. A full HA restore can overwrite unrelated changes and requires separate confirmation; do not use it as a routine response to every error. Provide a manual recovery document using the independent SSH app or local console when the integration UI fails.

## HI-17 — Acceptance, performance, and operations

Keep a requirement-to-code-to-tests matrix and honest capability status. Run original regression tests plus the acceptance scenarios in `ACCEPTANCE_TESTS.md`. Use a real HA test harness for setup/unload/config-flow/store/API integration; mocks alone are not enough. Run compatibility testing on declared HA/Python versions. Add frontend behavior/security tests, storage/restart/fault tests, and provider schema/error fixtures with no paid calls in CI.

Benchmark resource use. Proposed acceptance targets, to be confirmed on the recorded test machine: stream one million synthetic relevant events across 1,000 entities without loading all events at once; under 256 MiB incremental analyzer memory; steady callback enqueue p95 below 5 ms at 50 incoming events/second; publish additional event-loop latency against baseline; bound default candidate and disk budgets. These are engineering targets, not measured results or promises for every host. Document a justified adjustment rather than silently changing targets or presenting unrun benchmarks as passed.

A proposed initial owned-store cap of 512 MiB must be configurable, with a reserve/retention policy that stops growth, preserves integrity, and reports losses of historical detail. Disk-full must disable collection gracefully without breaking HA. Bound queues, task counts, run durations, retry attempts, and cloud budgets. Verify unload unregisters listeners/tasks and repeated reloads do not multiply work. Include user-visible pause and emergency disable.

Track last checkpoint, true coverage, input rate, skipped/excluded entities, detected/retained candidates, runtime by stage, peak memory, store size/schema, queue overflow, provider use, failed approvals, migrations, and readiness. Keep diagnostics redacted and export preview available. Never automatically export whole databases or secrets to GitHub.

## HI-18 — Milestones and definition of done

M0 — Baseline and architecture: current code inspected, upstream tests executed, compatibility and threat model documented, traceability matrix created. Not the stopping point.

M1 — Read-only organization product: HI-02/03 inventory and current/proposed topology, HI-04/05 naming/assignment/impact proposals, initial HI-07 explanations, functional HI-15 review UI, and real HA lifecycle tests. No provider required. This should already be useful.

M2 — Controlled organization application: HI-06 authorization/journaling/conflict recovery, staged approval UI, dependencies, and synthetic rollback/fault tests. First live mutation is a small separately approved batch, never a bulk clean.

M3 — Accurate observation and memory: HI-08/09 ingestion, concurrent live/backfill correctness, coverage, identity history, retention, backup/restore, performance, and visible diagnostics. Start with currently available Recorder data.

M4 — Behavior and existing automation intelligence: HI-10/11 validated local patterns, routines, contexts, numeric thresholds, attribution limits, existing automation suppression/improvement candidates, and chronological evaluation.

M5 — Replay, evidence-backed AI, and feedback: HI-12/13/14 implemented support matrix, safe shadow mode, provider/cost controls, validated YAML proposals, feedback and drift. No silent actuation.

M6 — Full advanced polish and release: complete HI-15 UI and optional read-only questions, long-running/performance/privacy tests, HI-16 tested deployment/recovery, full HI-17 evidence, release packaging, update ownership, and maintenance documentation.

Implement independent pieces while approvals are pending. No requirement can be marked complete merely because its interface exists. Production validation is distinct from local/HA fixture validation. Continue until the required capabilities are genuinely implemented or explicitly blocked with a precise explanation and next action. Do not silently replace a difficult capability with an AI guess.
