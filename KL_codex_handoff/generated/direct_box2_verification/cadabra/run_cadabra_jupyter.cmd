@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_cadabra_jupyter.ps1"
if errorlevel 1 (
  echo.
  echo Cadabra Jupyter could not be started. See README.md in this folder.
  pause
)
