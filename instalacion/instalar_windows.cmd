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

if not exist "config_dte_onlinegeneration.ini" (
  copy /Y "config\config_dte_onlinegeneration.example.ini" "config_dte_onlinegeneration.ini" >nul
  echo Se creo config_dte_onlinegeneration.ini.
  echo Completa Oracle, endpoint y credenciales antes de usar el flujo.
)

python "src\etl_emision_dte_onlinegeneration_real.py" --version
python "src\extraer_candidatos_oracle.py" --version
echo Instalacion terminada.
endlocal
