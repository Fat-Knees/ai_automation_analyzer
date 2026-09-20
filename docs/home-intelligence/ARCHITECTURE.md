# Implementation decisions

Baseline: `71ff7d6c72a09eb2dacfb9970456c444b4aba2e4`, upstream domain
`ai_automation_suggester`, integration version 1.6.0. Preserve providers and history.

## First slice

- `organization.py` is a deterministic pure analysis module. It has no HA imports,
  credentials, shell, registry-write adapter, or device-action capability.
- `organization_api.py` copies allowlisted registry metadata on the event loop,
  then runs report computation in HA's executor. The admin-only endpoint serves
  current/proposed inventory and saves a virtual overlay in an integration-owned
  HA Store. There is no production apply route.
- A content revision binds inventory, inspected definitions and saved preferences.
  Concurrent reviews serialize behind a lock; stale revisions fail with HTTP 409.
- Stable registered identity uses the entity registry entry ID. Audit-time identity
  observations retain old names/assignments, bounded to 20,000 observations. This
  is not continuous identity history and cannot backdate a move between scans.
  Unregistered entities disclose weaker continuity.
- The initial inventory is bounded to 5,000 rows per registry; oversized inventories
  fail explicitly instead of producing misleading partial target reports.
- Static area/device/floor/entity target membership is a conservative estimate.
  Labels, groups, runtime capability filtering, templates, external systems,
  scenes and unavailable sources remain explicitly unresolved. Nothing can apply
  this estimate to production.
- Preview operations keep entity IDs stable. An explicit entity area overrides a
  device area; clearing the override restores device inheritance. Gateway links
  are not used to infer rooms. No physical floors are inferred.
- A custom HA dashboard card uses the existing authenticated connection. The JS
  asset contains no inventory and may be served publicly; the inventory endpoint
  checks administrator authorization independently.
- The local audit config entry requires no provider credential and makes no AI
  call. Existing manifest provider dependencies remain for compatibility; reducing
  dependency installation requires a separate provider-loading migration.

## Threat model and outstanding gates

Names and definitions are untrusted text, never code. Input operations have an
exact allowlist and bounded request size. Preview acceptance is not live approval.
The custom component still runs with HA privileges; these checks do not sandbox
arbitrary Python. Existing upstream suggestion routes are separate from this audit.

The old unit suite injects fake HA modules and bypasses `__init__.py`. Preserve it
as regression coverage, but run real HA tests in a separate Linux process that
never loads `tests/conftest.py`. A successful unit run is not runtime compatibility.

Later milestones require a mutation journal, continuous identity tracking,
Recorder reconciliation, bounded event storage, measured pattern discovery,
replay/shadow support and deployment recovery. None is implied by the first card.
