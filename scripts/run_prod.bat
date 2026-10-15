@echo off
title Flask PROD Server
cd /d %~dp0..
if not exist "logs" mkdir "logs"
set STAMP=%RANDOM%
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set DTS=%%I
if defined DTS set STAMP=%DTS:~0,8%_%DTS:~8,6%
if "%STAMP%"=="" set STAMP=%RANDOM%%RANDOM%
if "%STAMP%"=="_" set STAMP=%RANDOM%%RANDOM%
set LOGFILE=logs\prod-%STAMP%.log
echo Starting Production Server... [log: %LOGFILE%]
echo Environment: PRODUCTION
echo URL: http://0.0.0.0:5001
echo [%DATE% %TIME%] Starting Production Server (PROD) >> %LOGFILE%
python -u run_prod.py >> %LOGFILE% 2>&1
pause