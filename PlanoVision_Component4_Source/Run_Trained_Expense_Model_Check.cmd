@echo off
setlocal
cd /d "%~dp0"
"work\component4_ml_venv\Scripts\python.exe" "scripts\research_pipeline\check_expense_model.py" %*
pause
