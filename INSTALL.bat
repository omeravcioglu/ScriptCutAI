@echo off
title ScriptCutAI Installer
color 0B

echo.
echo ========================================
echo       ScriptCutAI - INSTALLER
echo ========================================
echo.
echo This will set up ScriptCutAI on this computer.
echo Python will be installed automatically if needed.
echo.
echo Press any key to continue or close this window to cancel...
pause >nul

echo.
echo Starting setup...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0setup-new-computer.ps1"

pause

