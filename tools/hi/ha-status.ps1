[CmdletBinding()]
param(
    [ValidateSet('homeassistant-ai')]
    [string]$HostAlias = 'homeassistant-ai'
)

$ErrorActionPreference = 'Stop'

function Invoke-ReadOnly {
    param([string[]]$Arguments)
    & ssh @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "read-only Home Assistant check exited with code $LASTEXITCODE"
    }
}

Invoke-ReadOnly @($HostAlias, 'ha', 'core', 'info')
Invoke-ReadOnly @($HostAlias, 'ha', 'info')
