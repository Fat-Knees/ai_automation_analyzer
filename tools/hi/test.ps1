[CmdletBinding()]
param(
    [switch]$SkipRuntime
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

function Invoke-Checked {
    param([string]$Command, [string[]]$Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command exited with code $LASTEXITCODE"
    }
}

$python = $null
$venvPython = Join-Path $repo '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython -PathType Leaf) { $python = $venvPython }
if (-not $python) { $python = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $python) { $python = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $python) { throw 'Python 3 is required for local checks.' }

Push-Location $repo
try {
    Invoke-Checked $python @('-m', 'pytest', 'tests')
    Invoke-Checked $python @('-m', 'ruff', 'check', 'custom_components', 'tools', 'tests')

    $node = (Get-Command node -ErrorAction SilentlyContinue).Source
    if (-not $node) { throw 'Node.js is required for the frontend check.' }
    Invoke-Checked $node @('frontend_tests/home-intelligence-card.test.mjs')

    if (-not $SkipRuntime) {
        throw 'Linux Home Assistant runtime tests were not run. Re-run with -SkipRuntime for local checks only, or use the CI runtime job.'
    }
    Write-Host 'Runtime tests explicitly skipped (-SkipRuntime); Linux CI remains the runtime evidence source.'
} finally {
    Pop-Location
}
