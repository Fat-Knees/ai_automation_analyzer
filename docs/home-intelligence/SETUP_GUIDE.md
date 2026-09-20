# Revised Codex setup guide
Windows laptop → local Codex → dedicated SSH connection → Home Assistant OS

Prepared September 15, 2026. This guide provides setup instructions and a full implementation contract. It does not mean the integration has been built or tested against your home. Source keys below refer to `SOURCES.md`.

## 1. Understand the two environments

Use Codex in a local workspace on your Windows laptop, through its supported desktop/IDE/CLI environment. Current official documentation supports native PowerShell with a Windows sandbox; WSL is not mandatory for editing and local commands. Keep normal sandbox restrictions and approve specific exceptions instead of enabling unrestricted access. [S01]

Home Assistant runtime testing is separate. Ask Codex to detect an existing compatible Linux container/WSL/test environment, or configure an authorized Linux CI job. It must use a compatible HA/Python version, not assume Windows-only tests prove deployment compatibility. New WSL, Docker, system packages, or chargeable runners require your approval. Until available, algorithm/unit work can continue, but the real-HA test gate remains unpassed.

The laptop needs to be awake and connected to the permitted network for its SSH deployments. The finished integration should continue observation locally in HA when the laptop is off. This chat itself does not acquire a connection merely because you set up SSH for local Codex.

## 2. Open your existing fork, or create one

Use the existing repository when you have already started. Do not create a competing copy or overwrite previous work. Check the tools from PowerShell:

```powershell
git --version
gh --version
ssh -V
```

Install missing Git/GitHub CLI/OpenSSH client tooling from their official installers or Windows optional features. You do not need to install an SSH server on the laptop. Sign in to GitHub interactively:

```powershell
gh auth login
```

For a NEW workspace only:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\Projects" | Out-Null
Set-Location "$env:USERPROFILE\Projects"
gh repo fork ITSpecialist111/ai_automation_suggester --clone
# Continue after the preceding command succeeds.
Set-Location .\ai_automation_suggester
git remote -v
git status --short
```

GitHub CLI supports fork-and-clone. Verify `origin` is your fork and `upstream` is the original. GitHub CLI's default repository can still be upstream; Codex must use an explicit verified repository for pull requests or other writes. Let Codex create the feature branch and manage ordinary commits/pushes after checking existing work. Never give it a blanket instruction to force-push or rewrite history. [S03]

## 3. Put the revised instructions into that repository

Copy the contents of this pack into the fork root, retaining the `docs/home-intelligence/` and `prompts/home-intelligence/` paths. Do not overwrite conflicting files blindly. Merge existing `AGENTS.md` instructions, retaining applicable upstream rules.

The new `AGENTS.md` is intentionally compact. Codex automatically discovers these instruction files subject to size/precedence rules; the current default combined project-instruction limit is 32 KiB. The much longer product specification must be read explicitly by the startup prompt. [S02]

Merge `.gitignore.home-intelligence.snippet` into the existing `.gitignore`. Then:

```powershell
Copy-Item .\home-intelligence.local.example.json .\home-intelligence.local.json
```

Run that command only when the destination does not already contain your settings. Edit the ignored copy with the SSH alias, known HA URL/version, and any confirmed room/floor names. Leave unknown values null/empty. This is Codex development context, not a currently implemented integration config. Do not put tokens, passwords, or private keys in it. Git ignore prevents accidental commits; it does not stop an agent from reading a file it can access.

## 4. Establish recovery before remote changes

Use Home Assistant's backup UI to create a current backup before the first production deployment. Retain a recovery copy away from the HA machine and retain the required recovery/encryption information separately. Confirm you know how to restore it. Later automated deployment must verify backup completion and test owned-database restoration; a backup command returning is not enough. [S12]

No new code is deployed by copying this pack into your laptop repository.

## 5. Enable the dedicated SSH connection

On HAOS install the official **Terminal & SSH** app from Settings → Apps → Install app. On versions with older wording, the store may be under Add-ons. Enable profile Advanced Mode if needed to expose the app. The app provides a container session with `/config` and the `ha` CLI. It is not a narrow one-folder permission boundary. [S04]

On Windows create a dedicated key, with a passphrase, rather than reuse a broadly privileged key. Do not overwrite an existing key:

```powershell
$key = Join-Path $env:USERPROFILE '.ssh\ha_codex'
New-Item -ItemType Directory -Force (Split-Path $key) | Out-Null
if ((Test-Path $key) -or (Test-Path "$key.pub")) {
    throw 'A Home Assistant key already exists. Reuse or review it; do not overwrite it.'
}
ssh-keygen -t ecdsa -b 521 -f $key -C 'codex-homeassistant'
if ($LASTEXITCODE -ne 0) { throw 'SSH key creation failed.' }
Get-Content "$key.pub"
```

The `.pub` content is the public key; the extensionless file is private. Paste only the public key into the app's `authorized_keys`. Keep `password` empty and TCP forwarding disabled. Set the app's Network mapping for SSH to an unused LAN port such as `2222`, then start/restart that app. Do not change router port-forwarding or disable HAOS protections. [S04, S05]

The example follows the official app's ECDSA recommendation; it is not a claim that other supported key types are inherently unsafe. Preserve any other authorized keys intentionally used by you.

To avoid repeatedly entering the passphrase, use the Windows SSH agent. In an administrator PowerShell window, when the service is present:

```powershell
Set-Service ssh-agent -StartupType Automatic
Start-Service ssh-agent
```

Then from your normal Windows account:

```powershell
ssh-add "$env:USERPROFILE\.ssh\ha_codex"
```

This is a client-side setup, not a reason to install Windows SSH Server. Keep the private key protected. [S05]

Append the following to `%USERPROFILE%\.ssh\config`, replacing the LAN IP and Windows username. Do not overwrite unrelated host entries:

```sshconfig
Host homeassistant-ai
    HostName YOUR_HA_LAN_IP
    User root
    Port 2222
    IdentityFile C:/Users/YOUR_WINDOWS_USERNAME/.ssh/ha_codex
    IdentitiesOnly yes
    ForwardAgent no
    ConnectTimeout 10
```

Test from normal PowerShell:

```powershell
ssh homeassistant-ai "ha info"
ssh homeassistant-ai "ha core info"
```

Verify the server host fingerprint through your trusted HA app/console on the first connection. Do not bypass an unexpected changed-host-key warning. Use the actual LAN address you already know; do not ask Codex to scan your network. `homeassistant-ai` is only a local SSH nickname.

In Codex, initially approve only the specific read-only SSH commands requested. The Windows sandbox may need an explicit exception for the SSH client/network or access to its client configuration. Do not solve that by copying private keys into the project, making them readable by everyone, disabling host-key checks, or turning off the sandbox. Agent access can differ between your normal Windows session and the sandbox; test it instead of assuming it works. [S01]

Revoke access later by removing the dedicated public key from the app, or disable its mapped SSH port. Keep internet exposure off. Unrestricted HAOS host SSH is not needed for this workflow.

## 6. Do not create an all-powerful HA token by default

SSH deployment and registry access are different channels. The running custom integration should use HA's in-process registry helpers and its frontend's existing authenticated connection. It does not need a second global token stored on the laptop just to produce its own inventory UI.

An optional external diagnostics client can use the HA WebSocket API, but it needs a separately authorized credential; some registry mutations require administrator access. Do not call such a token read-only unless its actual account permissions enforce that. Keep any token outside the repository and model conversation, inject it through an approved local client, and revoke it when no longer needed. Do not extract tokens from `.storage` or log them. [S06, S07]

## 7. Start with a useful read-only audit

Open the fork root in local Codex. Use an available capable coding model and sufficient reasoning for architecture/testing, without hard-coding a changing model name. Paste `prompts/home-intelligence/START.txt`.

The first implemented result should be a usable organization view, not just an architecture document. It should show the current/proposed room-area-floor structure, names and placement, entity role/usefulness, ambiguous questions, and the effect on existing automation targets. Review/edit/reject should work. Apply remains disabled until the authorization and recovery machinery is actually tested.

The full advanced feature scope remains in `SPEC.md`; the first milestone is deliberately a complete useful slice. This lets you confirm physical facts before the behavioral engine over-interprets the wrong room assignments. History collection can also be implemented independently without waiting for every cosmetic cleanup, provided mappings are time-versioned.

## 8. History retention: measure, then decide

Recorder's documented default detailed retention is 10 days. Extending it does not recreate purged history. Long-term statistics apply to qualifying numeric sensors and are not a replacement for event timelines. [S10, S11]

After measuring database growth and free storage, a reasonable proposal to review is 30 days:

```yaml
recorder:
  purge_keep_days: 30
```

This is a proposal, not an instruction to paste a second `recorder:` block into your configuration. Modify the existing block or include correctly, validate, and approve any required restart. Keep purge behavior enabled unless a separate deliberate policy replaces it. Larger windows are optional after measurement.

The integration's owned store should retain selected compact events and summaries within explicit limits. It must display actual coverage and which older details are no longer reconstructable. There is no requirement for MariaDB/InfluxDB or a new server just to start. That is a design choice for this project, not an assertion that any possible scale fits one host.

## 9. Production deployment must be separately approved

Have Codex implement and test these PowerShell tools; they are requested deliverables, not scripts already supplied in this pack:

| Tool | Required behavior |
|---|---|
| `tools/hi/test.ps1` | Unit, HA-runtime, frontend, and static checks with real exit codes |
| `tools/hi/ha-status.ps1` | Minimal read-only health/version checks |
| `tools/hi/ha-logs.ps1` | Bounded, locally redacted diagnostics |
| `tools/hi/deploy.ps1` | Approved-build staging, backup verification, validation, bounded restart and readiness |
| `tools/hi/rollback.ps1` | Compatible code/data recovery with conflict checks |

The release flow is: test a reproducible artifact in isolated HA; present build/path/window and rollback plan; obtain approval; verify backup completion; stage and hash-check files; swap; run `ha core check`; restart only as approved; verify HA readiness and the integration's exact build/config-entry/schema status. A configuration check validates configuration; it does not prove the new component works. [S08]

A failed pre-restart validation restores changed files without restarting. A runtime failure permits at most the explicitly approved safe rollback attempt. Do not pair old code with an incompatible migrated database. Full HA restore and repeated restarts require separate decisions. Confirm no upstream HACS update will unexpectedly overwrite the development fork; do not install competing same-domain copies.

An approval can be as concrete as: “Deploy build <hash> to homeassistant-ai during this session, observation-only. Permit one normal restart and one recovery restart if the documented rollback is needed. Do not alter registries, automations, or Recorder.” This is an example, not a current approval.

## 10. Cost, convenience, and daily use

Local audit, statistical processing, and storage require no per-call cloud charge, but consume your hardware resources. Cloud recommendation requests are a separate expense from Codex development usage. ChatGPT/Codex entitlement does not automatically pay the HA integration's API bills. [S13]

The proposed starting application budget is $2/month, with cloud calls off until configured. This is a cap to implement and verify, not a bill estimate. Keep explicit token/call ceilings and refuse unknown-price requests unless a conservative policy is chosen. A provider dashboard budget is not a substitute for application-side concurrency/retry control. No paid-provider fallback without consent.

The finished UI should let you inspect evidence, correct rooms, accept/reject naming plans, view routines, simulate supported proposals, run shadow mode, and review YAML without knowing Python. You still supply credentials, resolve ambiguous physical locations, and approve consequential changes. Local Codex handles repository/test/deployment mechanics within those limits.

Use `CONTINUE.txt` to resume later sessions. Require an honest capability matrix and actual test results rather than accepting “done” as evidence. Full advanced capability is a substantial software project; no single prompt guarantees a correct finished system in one run.
