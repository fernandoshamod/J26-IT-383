@echo off
setlocal
cd /d "%~dp0"
if not exist "work\component4_ml_venv\Scripts\python.exe" (
  echo Existing ML Python environment missing. See README_LKR_RESEARCH.md.
  pause
  exit /b 1
)
"work\component4_ml_venv\Scripts\python.exe" "scripts\research_pipeline\run_planner_cli_lkr.py"
pause
