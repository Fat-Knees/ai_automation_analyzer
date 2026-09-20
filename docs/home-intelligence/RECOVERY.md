# Development first-install recovery

Only the first installation into an absent integration directory is supported by
the current tooling. An existing installation is refused. Upgrade/store-schema
migration and complete post-start health automation remain unfinished.

The deploy command requires the approved archive SHA-256, target alias, exact
component path, maintenance window, session identifier and a completed recent
backup containing the matching HA version. The recovery key stays outside this
repository. Approval must come from the owner; these arguments are not approval.

The tool verifies the archive locally, verifies SSH's effective destination,
acquires a shared lock, checks capacity and backup metadata, transfers to staging,
checks the transfer digest and verifies the extracted file tree before swapping.
It preserves the upstream LICENSE with the installed component.

If the configuration check fails before restart, verified installed files move
to `/config/.hi-quarantine` and the original absence is restored. Changed or
unexpected files block automatic movement so later user edits are preserved.
An uncertain restart result stops for investigation; it never loops restarts.
One recovery restart is possible only within its explicit approval. No full HA
restore or integration-owned data deletion is performed by these tools.

After an initial successful restart, use HA's authenticated UI to add AI Automation
Suggester with Local audit (no AI). Verify its authenticated readiness endpoint:
the expected commit, verified files, matching HA version, schema 1 and an active
entry must all match. Until then the tool reports awaiting setup, not ready.

If the UI cannot load, the independently running Terminal & SSH app or local
console is the recovery channel. Inspect the reported state before repeating any
command. Do not delete a stale deployment lock until the previous process and
restart outcome are known. Do not force a rollback over changed files or delete
owned stores. An incompatible future schema needs its own tested recovery plan.

`rollback.ps1` accepts the same approved artifact and scope, verifies installed
hashes, and quarantines that exact first-install tree. It leaves owned data intact.
Its restart requires `-AllowRollbackRestart`; repeated rollback against an absent
component is refused. A new deployment/restart outside the approved session needs
new approval.
