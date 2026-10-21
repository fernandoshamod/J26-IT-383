@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run Setup_Windows.cmd first.
  pause
  exit /b 1
)
echo This explicitly downloads the local CPU runtime/model if missing.
echo No cloud API key is required. Internet is needed only for initial downloads.
".venv\Scripts\python.exe" "scripts\research_pipeline\setup_local_ai.py"
pause
