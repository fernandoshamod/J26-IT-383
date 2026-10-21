@echo off
setlocal
cd /d "%~dp0"
echo This explicitly downloads the official local CPU runtime and report model if missing.
echo No cloud API key is required. Initial setup needs internet; inference runs locally.
"work\component4_ml_venv\Scripts\python.exe" "scripts\research_pipeline\setup_local_ai.py"
pause
