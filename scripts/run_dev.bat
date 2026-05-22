@echo off
title Control System - Dev Server
color 0A

echo ========================================
echo   Control System - Modo Desarrollo
echo ========================================
echo.

cd /d %~dp0..
echo URL: http://127.0.0.1:5000
echo.

python run_dev.py

pause