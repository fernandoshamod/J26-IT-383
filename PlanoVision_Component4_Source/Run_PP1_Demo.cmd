@echo off
setlocal
cd /d "%~dp0"
if not exist "work\component4_ml_venv\Scripts\python.exe" (
  echo Existing project ML environment not found. Use the PP1 README commands.
  pause
  exit /b 1
)
"work\component4_ml_venv\Scripts\python.exe" "scripts\research_pipeline\build_pp1_evidence.py" --interactive
pause
