# Organization audit development preview

This is a development slice, not an approved production release.

In an isolated HA test instance, install the component and add **AI Automation
Suggester**, selecting **Local audit (no AI)**. No provider key is needed. The
**Home Intelligence** sidebar page appears automatically for administrators.
Existing provider entries can also use the organization endpoint. Unloading the
last entry removes the sidebar page and disables the audit/readiness endpoints.

An optional dashboard card is also available. Add a JavaScript module resource:
`/ai_automation_suggester/home-intelligence-card.js`.
Then add a manual card:

```yaml
type: custom:home-intelligence-card
```

Use an administrator account. The card shows inventory, a virtual proposed
structure, metadata roles, questions and static target changes. Save preview
persists only the integration's own review data. It does not change any HA area,
floor, name, automation or device. Clearing an entity's area override restores
its device's inherited area, rather than forcing it to be unassigned.

The confirmed home-layout editor records physical spaces, aliases, optional
floors and outdoor spaces. Map more than one existing area to a space only when
you know they describe the same physical place; the first selected area is the
proposed canonical one. Saving records your facts and displays missing-space or
consolidation findings. It never merges/deletes areas. Entity placement and
analysis preferences are saved with the layout, tied to registry identity.
The optional local observer honors privacy exclusions and Ignore. Other ranking
preferences record intent for the future routine engine. Existing upstream
provider requests retain their own filters.

Local observation starts paused. Refresh its status, then explicitly start it to
collect selected numeric/discrete states and allowlisted attributes. Pause drains
the bounded queue; unload removes the listener. Reload/restart leaves it paused.
The owned SQLite store commits events and checkpoints together, deduplicates
retries and retains each event's observed area mapping. Storage failure stops
collection while the organization interface remains available. A 512 MiB database
cap is enforced; retention/aggregation and Recorder backfill are not implemented.
No routine recommendations are generated from these observations yet. The
consistent-snapshot helper has local restore tests, not an HA backup restore test.

The admin-only `/api/ai_automation_suggester/readiness` endpoint reports the release
commit (or development checkout), HA version, active entries and store schema.
Successful `ha core check` alone is not integration readiness.

Target sets are static estimates. Unknown sources, labels and dynamic behavior
are shown as limitations. A preview is not proof that a change is harmless.

Run Python unit tests with `.venv/Scripts/python.exe -m pytest -q` on Windows.
The Linux runtime suite is separate so the upstream HA module stubs cannot leak
into its process. See the GitHub Actions results for actual runtime evidence.
