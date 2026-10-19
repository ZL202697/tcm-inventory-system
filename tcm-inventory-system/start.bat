@echo off
title TCM Inventory Management System

echo ============================================================
echo    TCM Herb Inventory Management System
echo    Info System Development Training Project
echo ============================================================
echo.

cd /d "%~dp0backend"

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    echo Download: https://www.python.org/downloads/
    echo Remember to check "Add Python to PATH" during installation
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo       Python %%i

echo.
echo [2/4] Installing dependencies...
pip install -q Flask pymysql 2>nul
if errorlevel 1 (
    echo [WARN] Trying mirror...
    pip install -q Flask pymysql -i https://pypi.tuna.tsinghua.edu.cn/simple 2>nul
)
echo       Dependencies ready

echo.
echo [3/4] Initializing database (SQLite, no MySQL needed)...
if exist "herb_management.db" (
    echo       Database exists, skipping init
) else (
    python init_db.py
    if errorlevel 1 (
        echo.
        echo [ERROR] Database init failed!
        pause
        exit /b 1
    )
)

echo.
echo [4/4] Starting server...
echo.
echo ============================================================
echo    Server started successfully!
echo.
echo    URL: http://127.0.0.1:5000
echo.
echo    Default accounts:
echo      admin   / 123456  (Administrator - full access)
echo      doctor  / 123456  (Doctor - prescriptions, purchase)
echo.
echo    Close this window to stop the server
echo ============================================================
echo.

start "" "http://127.0.0.1:5000"

python app.py

pause
