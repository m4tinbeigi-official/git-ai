@echo off
REM git-ai launcher for Windows (double-click to run).
REM Auto-installs requirements, then starts the graphical app.
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
  set PY=python
) else (
  where py >nul 2>nul && set PY=py
)
if "%PY%"=="" (
  echo Python 3 not found. Install it from https://www.python.org/downloads/
  pause
  exit /b 1
)

%PY% -m pip install --upgrade pip >nul 2>nul
%PY% -m pip install -r requirements.txt
%PY% git_ai_gui.py
pause
