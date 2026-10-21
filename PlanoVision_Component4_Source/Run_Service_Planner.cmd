@echo off
setlocal
set "C4_PROJECT_ROOT=%~dp0"
if not exist "%C4_PROJECT_ROOT%work\component4_ml_venv\Scripts\python.exe" set "C4_PROJECT_ROOT=C:\Users\User\Documents\ChatGPT\ML\"
if not exist "%C4_PROJECT_ROOT%work\component4_ml_venv\Scripts\python.exe" (
  echo Existing project Python environment was not found.
  echo Expected: "%C4_PROJECT_ROOT%work\component4_ml_venv\Scripts\python.exe"
  echo Run this launcher from the complete project folder, not a standalone download.
  if not defined C4_NO_PAUSE pause
  exit /b 1
)
if not exist "%C4_PROJECT_ROOT%scripts\research_pipeline\run_service_planner.py" (
  echo Planner script missing from "%C4_PROJECT_ROOT%".
  if not defined C4_NO_PAUSE pause
  exit /b 1
)
cd /d "%C4_PROJECT_ROOT%"
"%C4_PROJECT_ROOT%work\component4_ml_venv\Scripts\python.exe" "%C4_PROJECT_ROOT%scripts\research_pipeline\run_service_planner.py" %*
set "C4_EXIT_CODE=%ERRORLEVEL%"
if not defined C4_NO_PAUSE pause
exit /b %C4_EXIT_CODE%
