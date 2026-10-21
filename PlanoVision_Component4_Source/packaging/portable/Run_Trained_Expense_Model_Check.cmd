@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run Setup_Windows.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\research_pipeline\check_expense_model.py %*
pause
