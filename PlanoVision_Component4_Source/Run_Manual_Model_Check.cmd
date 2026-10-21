@echo off
setlocal
cd /d "%~dp0"
if not exist "work\component4_ml_venv\Scripts\python.exe" (
  echo Existing ML Python environment was not found. See README_MANUAL_MODEL_CHECK.md.
  pause
  exit /b 1
)
"work\component4_ml_venv\Scripts\python.exe" "scripts\research_pipeline\run_manual_model_check.py"
pause
