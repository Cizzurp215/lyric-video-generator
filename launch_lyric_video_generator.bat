@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="
where py >nul 2>nul
if %errorlevel%==0 set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
  where python >nul 2>nul
  if %errorlevel%==0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  echo Python 3.11+ was not found on PATH.
  echo Install Python, then run this launcher again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  call %PYTHON_CMD% -m venv .venv
  if errorlevel 1 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
  )
)

if not exist ".venv\Scripts\uvicorn.exe" (
  echo Installing requirements...
  call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Failed to install requirements.
    pause
    exit /b 1
  )
)

echo Starting Lyric Video Generator at http://127.0.0.1:8000
start "" http://127.0.0.1:8000
call ".venv\Scripts\python.exe" -m uvicorn app.main:app --reload

echo Server stopped.
pause
