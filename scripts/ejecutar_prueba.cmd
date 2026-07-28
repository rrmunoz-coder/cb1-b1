@echo off
setlocal
cd /d "%~dp0\.."
set "PY=.venv\Scripts\python.exe"
set "INPUT=%~1"
if "%INPUT%"=="" (
  if exist "reporte_diario.csv" (
    set "INPUT=reporte_diario.csv"
  ) else (
    set "INPUT=examples\reporte_diario_ejemplo.csv"
  )
)

if not exist "%PY%" (
  echo ERROR: Ejecuta primero instalacion\instalar_windows.cmd
  exit /b 1
)
if not exist "%INPUT%" (
  echo ERROR: No existe el archivo de entrada: %INPUT%
  exit /b 1
)
if not exist "config_dte_onlinegeneration.ini" (
  echo ERROR: Falta config_dte_onlinegeneration.ini
  exit /b 1
)

"%PY%" "src\etl_emision_dte_onlinegeneration_real.py" ^
  --input "%INPUT%" ^
  --out "salida_dte_prueba" ^
  --config "config_dte_onlinegeneration.ini" ^
  --procesar-todos

endlocal
