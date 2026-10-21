$ErrorActionPreference = 'Stop'
$package = $PSScriptRoot
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) { throw 'Install Python 3.12 x64 and enable the py launcher, then rerun setup.ps1.' }
& py -3.12 --version
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required.' }
$nodeCommand = $env:PP1_NODE
if (-not $nodeCommand) { $node = Get-Command node -ErrorAction SilentlyContinue; if ($node) { $nodeCommand=$node.Source } }
if (-not $nodeCommand) { throw 'Install Node.js 22 x64 and add node/npm to PATH, then rerun setup.ps1.' }
$nodeVersion = (& $nodeCommand --version).Trim()
if ($nodeVersion -notmatch '^v22\.') { throw "Node.js 22 is required; found $nodeVersion" }
$nodeDir = Split-Path -Parent $nodeCommand
$env:PATH = "$nodeDir;$env:PATH"
$npmCommand = $env:PP1_NPM
if (-not $npmCommand) { $npm = Get-Command npm -ErrorAction SilentlyContinue; if ($npm) { $npmCommand=$npm.Source } }
if (-not $npmCommand) { throw 'Install npm with Node.js 22, then rerun setup.ps1.' }
if (-not (Test-Path (Join-Path $package '.venv\Scripts\python.exe'))) {
  & py -3.12 -m venv (Join-Path $package '.venv')
  if ($LASTEXITCODE -ne 0) { throw 'Could not create package-local Python environment.' }
}
$python = Join-Path $package '.venv\Scripts\python.exe'
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip bootstrap failed.' }
& $python -m pip install -r (Join-Path $package 'requirements-cpu.txt')
if ($LASTEXITCODE -ne 0) { throw 'CPU dependency installation failed.' }
Push-Location (Join-Path $package 'frontend')
try {
  & $npmCommand ci
  if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
  & $npmCommand run build
  if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
& $python (Join-Path $package 'build_portable_manifest.py')
if ($LASTEXITCODE -ne 0) { throw 'Could not create portable source manifest.' }
& $python (Join-Path $package 'verify_portable.py')
if ($LASTEXITCODE -ne 0) { throw 'Portable preflight failed.' }
Write-Host 'Setup complete. Run .\start.ps1 from this folder.'
