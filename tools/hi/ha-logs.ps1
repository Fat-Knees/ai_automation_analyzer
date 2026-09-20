[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { $python = (Get-Command python -ErrorAction Stop).Source }
& $python (Join-Path $PSScriptRoot 'logs.py')
exit $LASTEXITCODE
