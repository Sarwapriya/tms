@echo off
setlocal
title Martech TMS - Python App

echo ===================================================
echo   MARTECH TMS - STARTING APPLICATION
echo ===================================================
echo.

cd /d "%~dp0"
set "PYTHONPATH=%~dp0;%PYTHONPATH%"

:: Ensure Git automatically executes version updater hooks on commits
git config core.hooksPath .githooks >nul 2>&1

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH!
    echo Please install Python or add it to system PATH.
    pause
    exit /b 1
)

tasklist /fi "imagename eq mysqld.exe" 2>nul | find /i "mysqld.exe" >nul
if errorlevel 1 (
    echo [NOTICE] MySQL process mysqld.exe is not running.
    echo If database connection fails, please start MySQL in XAMPP.
    echo.
)

echo Starting Python application (run.py)...
echo.
python run.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with error.
    pause
)
