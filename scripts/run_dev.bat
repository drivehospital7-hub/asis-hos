@echo off
title Flask DEV Server
cd /d %~dp0..
echo Starting Development Server...
echo Environment: DEVELOPMENT
echo URL: http://127.0.0.1:5000
python run_dev.py
