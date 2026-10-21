param([Parameter(Mandatory=$true)][string]$Run)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Package Python environment is missing.' }
& $python (Join-Path $PSScriptRoot 'launcher.py') stop --run $Run
exit $LASTEXITCODE
