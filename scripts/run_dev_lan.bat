@echo off
title Control System - Dev LAN
color 0A

echo ========================================
echo   Control System - Dev (LAN)
echo ========================================
echo.
cd /d %~dp0..

set DEV_HOST=0.0.0.0
set DEV_PORT=5002

echo Modo:     Desarrollo (LAN)
echo Host:     0.0.0.0
echo Puerto:   %DEV_PORT%
echo URL:      http://localhost:%DEV_PORT%
echo LAN:      http://<tu-ip>:%DEV_PORT%
echo.
echo Ojo: debug mode activo, no usar en produccion
echo ========================================
echo.

python run_dev.py

pause
