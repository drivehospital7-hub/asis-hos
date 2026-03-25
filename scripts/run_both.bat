@echo off
title Flask Dual Environment
cd /d %~dp0..

echo ========================================
echo Starting Dual Environment
echo ========================================
echo DEV:  http://127.0.0.1:5000
echo PROD: http://0.0.0.0:5001
echo ========================================
echo.

start "Flask DEV" cmd /k "python run_dev.py"
timeout /t 2 /nobreak >nul
start "Flask PROD" cmd /k "python run_prod.py"
