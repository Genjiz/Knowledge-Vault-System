@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title Knowledge Vault - Stopping...

echo ========================================
echo   Knowledge Vault - Stopping...
echo ========================================
echo.

set "BACKEND_STOPPED=0"
set "FRONTEND_STOPPED=0"

echo Stopping backend (port 5000)...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5000.*LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
    if !errorlevel! EQU 0 set "BACKEND_STOPPED=1"
)
if "%BACKEND_STOPPED%"=="1" (
    echo Backend stopped.
) else (
    echo No backend process found on port 5000.
)

echo Stopping frontend (port 3000)...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":3000.*LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
    if !errorlevel! EQU 0 set "FRONTEND_STOPPED=1"
)
if "%FRONTEND_STOPPED%"=="1" (
    echo Frontend stopped.
) else (
    echo No frontend process found on port 3000.
)

echo.
echo ========================================
echo All services stopped.
echo ========================================
echo.
pause
