# Review of the previous proposal

## Assessment

The previous proposal was adequate as a product vision, but not as a production implementation contract. Keep the ambition and most major features; correct the assumptions and define verification gates. This review assesses the proposal and selected current upstream documentation/configuration, not a completed codebase or a live Home Assistant installation.

## Retain

Keep the existing integration as the starting point, local-first statistics, provider reuse, cleanup approval, behavioral memory, entity classification, routines, contextual recommendations, automation auditing, feedback, diagnostics, and laptop-driven deployment.

## Corrections and additions

**Rooms/areas/floors are a first-class planning stage.** Recommend missing areas, duplicate consolidation, splits, area-to-floor assignments, aliases, and grouping labels, not just device location assignments. An HA area represents a room or physical space; floors represent levels. Do not create a fictional house layout or force exterior areas into fake floors.

**Area/floor/label changes are behavior changes.** Existing action targets and templates may expand to different entities after reassignment. Even a non-ID cleanup needs a before/after target-impact report. Human confirmation of location does not itself approve the resulting changes to automation reach.

**SSH is powerful.** The official app exposes `/config` and the HA CLI, not one restricted integration folder. The previous permissions diagram and AGENTS text were not enforced access controls. An SSH alias changes convenience, not permissions.

**Windows editing and HA runtime testing are different.** Use local Codex conveniently, but verify the real integration on a compatible Linux HA runtime. The current upstream Ruff target is `py39`; that is not evidence that a current HA release runs on Python 3.9.

**Configuration validation is insufficient.** `ha core check` does not certify successful config-entry setup, event handling, frontend registration, database migration, or useful behavioral output. Require lifecycle tests and post-start readiness.

**Rollbacks are conditional.** Registry operations across stores are not promised to be atomic. Record steps and compensating operations; detect later edits. Code rollback and behavioral-database rollback must be version compatible. File restoration cannot reverse a light, lock, or other physical action that already occurred.

**History is not unlimited.** Longer Recorder retention cannot recreate purged data. Daily aggregates cannot support arbitrary future sequence mining or exact replay of lost events. Keep bounded selected event data, versioned aggregates, explicit coverage, and known loss of detail.

**AI confidence and statistical confidence are different.** Do not let a model invent a 98% location probability. Keep empirical match rates separate from confidence in the interpretation. Historical coincidence with observed actions is not proof that users would welcome an automation.

**Replay has a defined subset.** Unknown history, unsupported templates/actions, and counterfactual effects must remain unknown. Dry-run evaluation must never call live services.

**Approvals must be enforceable in the application.** Backend authorization, stale-plan detection, scoped plan approval, and operation allowlists are required, not just a confirmation button or a prompt rule.

**Full scope needs tracked completion.** Use requirement IDs, capability status, chronological holdouts, fault-injection tests, measured resource limits, independent reviews, and working UI slices. Do not mark a module complete because a file exists or a test with mocks passes.

Primary technical references are in `SOURCES.md`.
