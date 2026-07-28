@echo off
setlocal
cd /d "%~dp0\.."
set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo ERROR: Ejecuta primero instalacion\instalar_windows.cmd
  exit /b 1
)

if not exist "config_dte_onlinegeneration.ini" (
  echo ERROR: Falta config_dte_onlinegeneration.ini
  exit /b 1
)

"%PY%" "src\extraer_candidatos_oracle.py" ^
  --config "config_dte_onlinegeneration.ini" ^
  --sql "sql\candidatos_entrada_etl.sql" ^
  --output "reporte_diario.csv" ^
  --rechazados "salida_extraccion\candidatos_rechazados.csv"

if errorlevel 1 exit /b 1

echo.
echo Extraccion terminada.
echo Entrada ETL: reporte_diario.csv
echo Rechazados: salida_extraccion\candidatos_rechazados.csv
endlocal
