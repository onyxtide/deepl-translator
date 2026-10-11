@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment. Is Python installed?
        pause
        exit /b 1
    )
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Stopping any previous instance on port 8010...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":8010 .*LISTENING"') do taskkill /f /pid %%p >nul 2>&1

echo Starting DeepL Article Translator at http://localhost:8010
echo Press Ctrl+C to stop.
echo.
".venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8010

pause
