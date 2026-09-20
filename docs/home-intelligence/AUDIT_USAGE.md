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
Behavior collection is not implemented yet, so these preferences currently
record intent for that future engine rather than changing upstream providers.

The admin-only `/api/ai_automation_suggester/readiness` endpoint reports the release
commit (or development checkout), HA version, active entries and store schema.
Successful `ha core check` alone is not integration readiness.

Target sets are static estimates. Unknown sources, labels and dynamic behavior
are shown as limitations. A preview is not proof that a change is harmless.

Run Python unit tests with `.venv/Scripts/python.exe -m pytest -q` on Windows.
The Linux runtime suite is separate so the upstream HA module stubs cannot leak
into its process. See the GitHub Actions results for actual runtime evidence.
