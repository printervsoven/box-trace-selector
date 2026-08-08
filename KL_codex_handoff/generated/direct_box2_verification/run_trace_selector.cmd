@echo off
setlocal

set "TRACE_SCRIPT=%~dp0trace_selector_web.py"

py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 (
    py -3 "%TRACE_SCRIPT%" %*
    exit /b %errorlevel%
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 (
    python "%TRACE_SCRIPT%" %*
    exit /b %errorlevel%
)

set "CODEX_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PYTHON%" (
    "%CODEX_PYTHON%" "%TRACE_SCRIPT%" %*
    exit /b %errorlevel%
)

echo Python 3.10 or newer could not be found.
echo Install Python 3.10+ or run trace_selector_web.py with a compatible interpreter.
exit /b 1
