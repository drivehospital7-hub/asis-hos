@echo off
REM Backup completo de asis_hos, excluyendo evidencias y auditoría (solo datos, no estructura)
REM Uso: scripts\backup_db.bat [output_file.sql]

set DB_NAME=asis_hos
set OUTPUT=%~1
if "%OUTPUT%"=="" set OUTPUT=backup_%DB_NAME%_%DATE:~-4%%DATE:~4,2%%DATE:~7,2%.sql

set PGDUMP="C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"

echo Backupeando %DB_NAME% a %OUTPUT% ...
echo (excluyendo datos de evidencias y resultados_auditoria)

%PGDUMP% -U postgres -d %DB_NAME% -p 5433 ^
    --exclude-table-data=evidencias ^
    --exclude-table-data=resultados_auditoria ^
    --file=%OUTPUT%

if %ERRORLEVEL% equ 0 (
    echo OK - %OUTPUT%
) else (
    echo ERROR al backupear
    exit /b 1
)
