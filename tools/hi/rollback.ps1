[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })] [string]$Artifact,
    [Parameter(Mandatory = $true)] [ValidatePattern('^[0-9a-f]{64}$')] [string]$ApproveBuild,
    [Parameter(Mandatory = $true)] [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')] [string]$BackupSlug,
    [Parameter(Mandatory = $true)] [ValidateSet('homeassistant-ai')] [string]$ConfirmHost,
    [Parameter(Mandatory = $true)] [ValidateScript({ $_ -eq '/config/custom_components/ai_automation_suggester' })] [string]$ConfirmPath,
    [Parameter(Mandatory = $true)] [string]$ConfirmWindow,
    [Parameter(Mandatory = $true)] [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$')] [string]$SessionId,
    [Parameter(Mandatory = $true)] [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$')] [string]$ConfirmSessionId,
    [Parameter(Mandatory = $true)] [ValidateSet(1)] [int]$MaxRestarts,
    [Parameter(Mandatory = $true)] [switch]$ConfirmFirstInstall,
    [switch]$AllowRollbackRestart,
    [string]$ExpectedAddress,
    [string]$ExpectedHAVersion = '2026.9.3'
)

$ErrorActionPreference = 'Stop'
if (-not $ConfirmFirstInstall) { throw 'ConfirmFirstInstall is required for the first-install rollback transaction.' }
$artifactPath = (Resolve-Path -LiteralPath $Artifact).Path
$actual = (Get-FileHash -LiteralPath $artifactPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $ApproveBuild.ToLowerInvariant()) { throw 'ApproveBuild does not match the local artifact SHA-256.' }

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = $null
$venvPython = Join-Path $repo '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython -PathType Leaf) { $python = $venvPython }
if (-not $python) { $python = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $python) { $python = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $python) { throw 'Python 3 is required for rollback.' }
$release = Join-Path $PSScriptRoot 'release.py'
$arguments = @($release, 'rollback', $artifactPath, '--host', $ConfirmHost, '--approve-build', $ApproveBuild.ToLowerInvariant(), '--backup-slug', $BackupSlug, '--session-id', $SessionId, '--confirm-session-id', $ConfirmSessionId, '--confirm-host', $ConfirmHost, '--confirm-path', $ConfirmPath, '--confirm-window', $ConfirmWindow, '--max-restarts', [string]$MaxRestarts, '--expected-ha-version', $ExpectedHAVersion, '--confirm-first-install')
if ($ExpectedAddress) { $arguments += @('--expected-address', $ExpectedAddress) }
if ($AllowRollbackRestart) { $arguments += '--allow-rollback-restart' }
& $python @arguments
exit $LASTEXITCODE
