@echo off
setlocal
cd /d "%~dp0\.."
set "PY=.venv\Scripts\python.exe"
set "INPUT=%~1"
if "%INPUT%"=="" set "INPUT=reporte_diario.csv"

if not exist "%PY%" (
  echo ERROR: Ejecuta primero instalacion\instalar_windows.cmd
  exit /b 1
)
if not exist "%INPUT%" (
  echo ERROR: No existe el archivo de entrada: %INPUT%
  exit /b 1
)
if not exist "config_nc_onlinegeneration.ini" (
  echo ERROR: Falta config_nc_onlinegeneration.ini
  exit /b 1
)

echo ADVERTENCIA: esta opcion emite DTE 33, 39 o 61 reales.
echo Archivo: %INPUT%
echo Por seguridad se procesaran como maximo 2 documentos.
set /p "CONFIRMACION=Escribe EMITIR para continuar: "
if /I not "%CONFIRMACION%"=="EMITIR" (
  echo Operacion cancelada.
  exit /b 1
)

"%PY%" "src\etl_emision_dte_onlinegeneration_real.py" ^
  --input "%INPUT%" ^
  --out "salida_dte" ^
  --config "config_nc_onlinegeneration.ini" ^
  --emitir-real ^
  --max-docs 2 ^
  --permitir-mas-de-max

endlocal
