@echo off
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Ejecuta primero instalacion\instalar_windows.cmd
  exit /b 1
)
".venv\Scripts\python.exe" -m unittest discover -s tests -v
endlocal
