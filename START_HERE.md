# Home Intelligence — Codex development pack, revision 2
Prepared September 15, 2026.

This is a revised setup guide and implementation specification, not an implemented Home Assistant integration. No production connection, deployment, Home Assistant runtime test, or behavioral benchmark has been performed by creating this pack.

## Use the pack

Open `docs/home-intelligence/SETUP_GUIDE.md` first. Establish your local Codex workspace and optionally the dedicated Home Assistant SSH connection. Copy this pack's files into your existing fork of `ITSpecialist111/ai_automation_suggester`, preserving their relative paths. Do not overwrite existing work. Merge an existing `AGENTS.md` with the supplied operating rules instead of discarding it.

Merge `.gitignore.home-intelligence.snippet` into the repository's existing `.gitignore` before creating any private files. Copy `home-intelligence.local.example.json` to `home-intelligence.local.json` and edit the non-secret environment details you know. This is development metadata for Codex; it is not an existing Home Assistant configuration format or proof of permission.

Open the repository root in your local Codex environment and paste `prompts/home-intelligence/START.txt`. Codex must explicitly read the specification and acceptance tests; they are not automatically loaded merely because they are in the repository. Use `CONTINUE.txt` for later sessions.

## Included materials

| File | Purpose |
|---|---|
| `AGENTS.md` | Persistent operating rules and production approval boundaries |
| `docs/home-intelligence/SETUP_GUIDE.md` | Windows, repository, SSH, testing, privacy, deployment, and cost setup |
| `docs/home-intelligence/SPEC.md` | Full advanced product requirements with requirement IDs |
| `docs/home-intelligence/ACCEPTANCE_TESTS.md` | Testable acceptance scenarios and release gates |
| `docs/home-intelligence/REVIEW.md` | What was retained, corrected, and strengthened from the previous proposal |
| `docs/home-intelligence/SOURCES.md` | Primary sources checked for the guide |
| `prompts/home-intelligence/START.txt` | Initial Codex instruction |
| `prompts/home-intelligence/CONTINUE.txt` | Resume without losing scope or inventing completed work |
| `home-intelligence.local.example.json` | Non-secret local environment template |
| `.gitignore.home-intelligence.snippet` | Entries to merge, not a replacement `.gitignore` |

All feature descriptions in this pack are requirements unless explicitly described as verified upstream behavior. Example rooms, metrics, limits, and budgets are illustrative or proposed defaults, not observations of your home. Full capability is the target; phased acceptance prevents unfinished features from being presented as production-ready.
