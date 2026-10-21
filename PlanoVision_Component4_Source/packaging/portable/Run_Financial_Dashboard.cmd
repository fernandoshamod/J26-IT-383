@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run Setup_Windows.cmd first from this extracted folder.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\research_pipeline\launch_financial_dashboard.py %*
pause
