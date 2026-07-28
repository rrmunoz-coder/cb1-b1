@echo off
setlocal
cd /d "%~dp0\.."

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: No se encontro el launcher "py". Instala Python 3.10 o superior.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r "instalacion\requirements.txt"

if not exist "config_nc_onlinegeneration.ini" (
  copy /Y "config\config_nc_onlinegeneration.example.ini" "config_nc_onlinegeneration.ini" >nul
  echo Se creo config_nc_onlinegeneration.ini. Completa endpoint y credenciales antes de emitir.
)

python "src\etl_emision_nc_onlinegeneration_real.py" --version
echo Instalacion terminada.
endlocal
