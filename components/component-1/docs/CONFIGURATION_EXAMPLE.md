# Configuration template (PowerShell; adapt before use)

These are documented environment overrides, not an automatically loaded .env file. Ordinary default startup needs no overrides. Use distinct available ports; never stop unknown listeners automatically.

```powershell
$env:PP1_FRONTEND_PORT = '5173'
$env:PP1_BACKEND_PORT = '8765'
$env:PP1_COMPANION_PORT = '8768'
$env:PP1_SCENE_PORT = '8769'
# Run from app after setup:
.\start.ps1
# When finished:
.\stop.ps1
```

PP1_RUNTIME_STATE and PP1_PRIVATE_ASSETS are supported by portable_runtime.py, but the launcher explicitly selects app/private-assets for child processes. Do not assume an arbitrary external assets path overrides the launcher. No credentials belong in these configuration files. KNOX image/analysis overrides do not resolve the documented compiler source-root and image-serving defects by themselves.
