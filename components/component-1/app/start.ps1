$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Run .\setup.ps1 first.' }
& $python (Join-Path $PSScriptRoot 'verify_portable.py')
if ($LASTEXITCODE -ne 0) { throw 'Portable preflight failed; no service was started.' }
& $python (Join-Path $PSScriptRoot 'launcher.py') start
exit $LASTEXITCODE
