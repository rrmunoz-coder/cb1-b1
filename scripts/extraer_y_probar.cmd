@echo off
setlocal
cd /d "%~dp0\.."

call "scripts\extraer_oracle.cmd"
if errorlevel 1 exit /b 1

for /f %%A in ('find /v /c "" ^< "reporte_diario.csv"') do set "LINEAS=%%A"
if "%LINEAS%"=="1" (
  echo ADVERTENCIA: reporte_diario.csv no contiene candidatos validos.
  echo Revisa salida_extraccion\candidatos_rechazados.csv
  exit /b 2
)

call "scripts\ejecutar_prueba.cmd" "reporte_diario.csv"
endlocal
