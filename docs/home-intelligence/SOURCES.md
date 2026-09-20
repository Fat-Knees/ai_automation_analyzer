# Primary references checked
Checked September 15, 2026. Documentation can move; verify the installed HA release and current APIs again at implementation time. These sources support platform facts; proposed algorithms, resource limits, product design, and acceptance thresholds are engineering requirements, not source-backed performance claims.

| Key | Source | Relevance |
|---|---|---|
| S01 | [Official Codex Windows documentation](https://developers.openai.com/codex/windows/) | Native Windows sandbox, PowerShell, permission exceptions and WSL options; currently redirects to the official ChatGPT Learn documentation |
| S02 | [Official AGENTS.md documentation](https://developers.openai.com/codex/guides/agents-md/) | Instruction discovery, precedence and default 32 KiB combined project limit |
| S03 | [GitHub CLI: gh repo fork](https://cli.github.com/manual/gh_repo_fork) | Fork/clone behavior and remotes/default repository caveat |
| S04 | [Official Terminal & SSH app documentation](https://github.com/home-assistant/addons/blob/master/ssh/DOCS.md) | App container, `/config`, HA CLI, authentication and port mapping |
| S05 | [Microsoft: OpenSSH key management](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_keymanagement) | Client keys, passphrases, SSH agent and key protection |
| S06 | [HA WebSocket API](https://developers.home-assistant.io/docs/api/websocket/) | Authentication and command/result model |
| S07 | [HA entity registry API implementation](https://github.com/home-assistant/core/blob/dev/homeassistant/components/config/entity_registry.py) | Registry operations and authorization; inspect the installed release tag before use |
| S08 | [HAOS common tasks](https://www.home-assistant.io/common-tasks/os/) | HA CLI and the scope of configuration checking |
| S09 | [Grouping assets](https://www.home-assistant.io/docs/organizing/) · [Areas](https://www.home-assistant.io/docs/organizing/areas/) · [Floors](https://www.home-assistant.io/docs/organizing/floors/) | Organization hierarchy, inheritance and action targeting |
| S10 | [Recorder](https://www.home-assistant.io/integrations/recorder) | Detailed retention, default 10 days and purge settings |
| S11 | [History](https://www.home-assistant.io/integrations/history/) | Detailed history versus qualifying long-term statistics |
| S12 | [Backup](https://www.home-assistant.io/integrations/backup/) | Backup and restore mechanisms |
| S13 | [OpenAI: ChatGPT and API billing](https://help.openai.com/en/articles/9039756-billing-settings-in-chatgpt-vs-platform) | Separate billing systems |
| S14 | [Customizing entities](https://www.home-assistant.io/docs/configuration/customizing-devices) | Display names, entity IDs, related references and naming settings |
| S15 | [Blocking operations with asyncio](https://developers.home-assistant.io/docs/asyncio_blocking_operations/) | Offloading blocking work and HA event-loop requirements |
| S16 | [Upstream README](https://github.com/ITSpecialist111/ai_automation_suggester/blob/main/README.md) | Snapshot/provider/suggestion pipeline used as the starting point |
| S17 | [Upstream pyproject](https://github.com/ITSpecialist111/ai_automation_suggester/blob/main/pyproject.toml) · [manifest](https://github.com/ITSpecialist111/ai_automation_suggester/blob/main/custom_components/ai_automation_suggester/manifest.json) | Current test/lint metadata and integration identity/dependencies |

## Source snapshots actually inspected

Upstream README blob SHA: `e9571a29cbcaf38c7cef8a984b34ebf6be98669e` (selected architecture lines).

Upstream pyproject blob SHA: `24735045415a9a6fd6b759f9d7d96c4c6a15855d` (pytest settings and Ruff target `py39`).

Upstream manifest blob SHA: `ef179530f2acf0ced28b3d1118a98da83fdabde3` (declares domain `ai_automation_suggester` and version `1.6.0`; this is a source snapshot, not verification of the latest published release).

Official SSH documentation blob SHA: `ef0febab01e3fa8252a73a82cdf0f095cae56fc2`.

No repository test suite or live HA instance was run during preparation of this instruction pack. The next Codex baseline must inspect the full current code and record its own commit/version/test results.
