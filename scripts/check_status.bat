@echo off
REM ========================================
REM Verificar estado del servidor Flask
REM ========================================

cd /d %~dp0..

echo.
echo ========================================
echo    Flask Environment Status
echo ========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado
    exit /b 1
)
echo [OK] Python instalado
python --version

echo.
echo Configuraciones disponibles:
echo.

if exist "config\dev.py" (
    echo [OK] DevConfig: config\dev.py
) else (
    echo [MISSING] DevConfig: config\dev.py
)

if exist "config\prod.py" (
    echo [OK] ProdConfig: config\prod.py
) else (
    echo [MISSING] ProdConfig: config\prod.py
)

echo.
echo Scripts disponibles:
echo.

if exist "run_dev.py" (
    echo [OK] run_dev.py
) else (
    echo [MISSING] run_dev.py
)

if exist "run_prod.py" (
    echo [OK] run_prod.py
) else (
    echo [MISSING] run_prod.py
)

echo.
echo ========================================
echo Para iniciar entornos:
echo   - DEV:  scripts\run_dev.bat
echo   - PROD: scripts\run_prod.bat
echo   - AMBOS: scripts\run_both.bat
echo ========================================
echo.
pause
