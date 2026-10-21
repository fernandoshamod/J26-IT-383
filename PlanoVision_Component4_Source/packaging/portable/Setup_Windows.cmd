@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 goto pythonfallback
py -3.12 -m venv .venv
if errorlevel 1 goto failed
goto install
:pythonfallback
python -c "import sys; assert sys.version_info[:2] == (3,12), 'Install Python 3.12 (64-bit)'"
if errorlevel 1 goto failed
python -m venv .venv
if errorlevel 1 goto failed
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\research_pipeline\verify_portable_package.py
if errorlevel 1 goto failed
echo.
echo SETUP PASSED. Run Run_Financial_Dashboard.cmd to open PlanoVision.
if /i not "%~1"=="--no-pause" pause
exit /b 0
:failed
echo.
echo SETUP FAILED. Install Python 3.12 64-bit and check the error above.
echo Internet access is required for the initial pip installation.
pause
exit /b 1
