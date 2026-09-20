# Organization audit development preview

This is a development slice, not an approved production release.

In an isolated HA test instance, install the component and add **AI Automation
Suggester**, selecting **Local audit (no AI)**. No provider key is needed. Existing
provider entries can also use the organization endpoint.

Add a JavaScript module dashboard resource:
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

Target sets are static estimates. Unknown sources, labels and dynamic behavior
are shown as limitations. A preview is not proof that a change is harmless.

Run Python unit tests with `.venv/Scripts/python.exe -m pytest -q` on Windows.
The Linux runtime suite is separate so the upstream HA module stubs cannot leak
into its process. See the GitHub Actions results for actual runtime evidence.
