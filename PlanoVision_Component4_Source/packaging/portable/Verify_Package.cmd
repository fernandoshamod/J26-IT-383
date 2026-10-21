@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run Setup_Windows.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\research_pipeline\verify_portable_package.py --http
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto failed
echo PACKAGE AND INCLUDED TESTS PASSED.
pause
exit /b 0
:failed
echo Verification failed. Read the error above; no mock prediction was substituted.
pause
exit /b 1
