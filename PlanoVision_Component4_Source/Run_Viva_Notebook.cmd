@echo off
setlocal
cd /d "%~dp0"
set "VIVA_PY=%~dp0work\component4_ml_venv\Scripts\python.exe"
if not exist "%VIVA_PY%" set "VIVA_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%VIVA_PY%" (
  echo Project Python environment was not found.
  pause
  exit /b 1
)
set "VIVA_FOLDER=%~dp0outputs\PlanoVision_Viva_Dataset_Evidence_20261021"
set "JUPYTER_RUNTIME_DIR=%VIVA_FOLDER%\.jupyter\runtime"
set "JUPYTER_DATA_DIR=%VIVA_FOLDER%\.jupyter\data"
set "JUPYTER_CONFIG_DIR=%VIVA_FOLDER%\.jupyter\config"
set "IPYTHONDIR=%VIVA_FOLDER%\.jupyter\ipython"
set "JUPYTER_PATH=%VIVA_FOLDER%\.jupyter\share\jupyter"
"%VIVA_PY%" -m ipykernel install --prefix "%VIVA_FOLDER%\.jupyter" --name planovision-viva --display-name "PlanoVision Research Python"
if errorlevel 1 (
  echo Install Jupyter first using: python -m pip install notebook nbclient nbformat ipykernel
  pause
  exit /b 1
)
"%VIVA_PY%" -m notebook --ServerApp.ip=127.0.0.1 --ServerApp.root_dir="%VIVA_FOLDER%" "%VIVA_FOLDER%\PlanoVision_Dataset_Training_Evidence.ipynb"
pause
