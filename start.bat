@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Knowledge Vault - Starting...

set "ROOT_DIR=%~dp0"
set "VENV_PYTHON=%ROOT_DIR%.venv\Scripts\python.exe"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "BACKEND_DIR=%ROOT_DIR%backend"

echo ========================================
echo   Knowledge Vault - Starting...
echo ========================================
echo.

if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found: "%VENV_PYTHON%"
    echo Please create .venv and install backend dependencies first.
    echo.
    pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%\node_modules" (
    echo [ERROR] Frontend dependencies not found: "%FRONTEND_DIR%\node_modules"
    echo Please run "npm install" in the frontend directory first.
    echo.
    pause
    exit /b 1
)

echo Checking port 5000...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5000.*LISTENING"') do (
    echo Stopping process %%a on port 5000...
    taskkill /f /pid %%a >nul 2>&1
)

echo Checking port 3000...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":3000.*LISTENING"') do (
    echo Stopping process %%a on port 3000...
    taskkill /f /pid %%a >nul 2>&1
)

echo.
timeout /t 1 /nobreak >nul

echo [1/2] Starting backend...
start "KnowledgeVault-Backend" cmd /k "cd /d %BACKEND_DIR% && ""%VENV_PYTHON%"" run.py"

timeout /t 2 /nobreak >nul

echo [2/2] Starting frontend...
start "KnowledgeVault-Frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

echo.
echo ========================================
echo Services started!
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:3000
echo ========================================
echo.

timeout /t 3 /nobreak >nul
start http://localhost:3000

echo Press any key to close this window (services will keep running)
pause >nul
