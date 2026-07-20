@echo off
REM Privilege — double-click launcher (Windows)
REM Opens the local viewer in your browser. Requires Python 3.11+ on the machine.
REM First run installs a local .venv (may take a minute).

setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  set "PYTHON=py -3.11"
) else (
  where python >nul 2>&1
  if %ERRORLEVEL%==0 (
    set "PYTHON=python"
  ) else (
    echo Privilege needs Python 3.11 or newer.
    echo Install from https://www.python.org/downloads/ then double-click again.
    pause
    exit /b 1
  )
)

if not exist .venv (
  echo Creating local virtualenv…
  %PYTHON% -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install -q -e ".[files]"

set "DB=demo\demo-vault.sqlite3"
if not exist "%DB%" set "DB=%USERPROFILE%\.privilege\vault.sqlite3"

if "%OPENAI_API_KEY%"=="" if "%PRIVILEGE_MOCK%"=="" set PRIVILEGE_MOCK=1

set PORT=7077
set URL=http://127.0.0.1:%PORT%

start "" "%URL%"
echo Privilege is starting at %URL%
echo Vault: %DB%
echo Close this window to stop the server.
python -m src.server_http --db "%DB%" --port %PORT%
pause
