@echo off
setlocal
cd /d "%~dp0"
"work\component4_ml_venv\Scripts\python.exe" "scripts\research_pipeline\run_planner_cli_venue.py" %*
if not defined C4_NO_PAUSE pause
