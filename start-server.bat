@echo off
title ScriptCutAI Server
color 0A

echo ========================================
echo        ScriptCutAI Server
echo ========================================
echo.

cd /d "%~dp0backend"

echo Activating Python environment...
call venv\Scripts\activate.bat

echo.
echo Starting server on http://127.0.0.1:8000
echo.
echo Keep this window open while using the Premiere extension.
echo Press Ctrl+C to stop the server.
echo.
echo ========================================
echo.

uvicorn app.main:app --host 127.0.0.1 --port 8000

pause

