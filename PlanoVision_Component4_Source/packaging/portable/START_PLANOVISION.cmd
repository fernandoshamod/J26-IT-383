@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto run
echo First run: preparing the local Python environment. Internet is required.
call Setup_Windows.cmd --no-pause
if errorlevel 1 exit /b 1
:run
".venv\Scripts\python.exe" scripts\research_pipeline\launch_financial_dashboard.py %*
if errorlevel 1 echo Could not start. Read the error above. No mock results were substituted.
pause
