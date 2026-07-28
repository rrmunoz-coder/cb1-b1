@echo off
setlocal
cd /d "%~dp0\.."
set "PY=.venv\Scripts\python.exe"
set "INPUT=%~1"
if "%INPUT%"=="" set "INPUT=examples\reporte_diario_ejemplo.csv"

if not exist "%PY%" (
  echo ERROR: Ejecuta primero instalacion\instalar_windows.cmd
  exit /b 1
)
if not exist "config_nc_onlinegeneration.ini" (
  echo ERROR: Falta config_nc_onlinegeneration.ini
  exit /b 1
)

"%PY%" "src\etl_emision_dte_onlinegeneration_real.py" ^
  --input "%INPUT%" ^
  --out "salida_dte_prueba" ^
  --config "config_nc_onlinegeneration.ini" ^
  --procesar-todos

endlocal
