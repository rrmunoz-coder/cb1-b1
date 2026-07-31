@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Ejecuta primero instalacion\instalar_windows.cmd
  exit /b 1
)

if not exist "tests\test_etl.py" (
  echo ERROR: Falta tests\test_etl.py
  exit /b 1
)

rem Ejecuta exclusivamente la suite oficial. Así archivos test_*.py residuales
rem de versiones anteriores no afectan la validación del ETL actual.
".venv\Scripts\python.exe" "tests\test_etl.py" -v
set "RC=%ERRORLEVEL%"

endlocal & exit /b %RC%
