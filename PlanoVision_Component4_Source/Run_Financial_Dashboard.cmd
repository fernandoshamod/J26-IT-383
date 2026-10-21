@echo off
setlocal
set "C4_PROJECT_ROOT=%~dp0"
if not exist "%C4_PROJECT_ROOT%work\component4_ml_venv\Scripts\python.exe" set "C4_PROJECT_ROOT=C:\Users\User\Documents\ChatGPT\ML\"
cd /d "%C4_PROJECT_ROOT%"
if not exist "frontend\dist\index.html" (
  echo Dashboard build missing. Follow README_FINANCIAL_DASHBOARD.md.
  pause
  exit /b 1
)
echo Starting backend and opening Google Chrome automatically...
echo Keep this terminal window open while using the dashboard.
"work\component4_ml_venv\Scripts\python.exe" "scripts\research_pipeline\launch_financial_dashboard.py" %*
pause
