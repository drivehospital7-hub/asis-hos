@echo off
title Asis-HOS Development Server
color 0A

echo ========================================
echo   Asis-HOS - Modo Desarrollo
echo ========================================
echo.

cd /d %~dp0

wsl -e bash -c "cd /home/papsivi/asis-hos && source venv/bin/activate && python run_dev.py"

pause