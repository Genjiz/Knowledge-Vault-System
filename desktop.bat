@echo off
setlocal
chcp 65001 >nul
title Knowledge Vault

set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo [ERROR] 虚拟环境不存在：%PY%
    pause
    exit /b 1
)

"%PY%" -c "import pystray, PIL" >nul 2>&1
if errorlevel 1 (
    echo 首次使用，正在安装桌面启动器依赖...
    "%PY%" -m pip install --no-cache-dir pystray Pillow
)

start "" "%ROOT%.venv\Scripts\pythonw.exe" "%ROOT%desktop.py"
exit /b 0
