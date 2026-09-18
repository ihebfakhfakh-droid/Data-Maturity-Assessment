@echo off
cd /d "%~dp0"
set ACCEPTANCE_CRITERIA_PORT=8003
py -3 -m uvicorn api_server:app --host 0.0.0.0 --port %ACCEPTANCE_CRITERIA_PORT%
pause
