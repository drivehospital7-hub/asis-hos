@echo off
title Flask PROD Server
cd /d %~dp0..
echo Starting Production Server...
echo Environment: PRODUCTION
echo URL: http://0.0.0.0:5001
python run_prod.py
