@echo off
title Pre-Session Checklist - Trading
cd /d "%~dp0"
echo Starting Pre-Session Checklist...
echo.
echo App will open at: http://localhost:8501
echo Close this window to stop the server.
echo.
py -m streamlit run app.py --server.port 8501
pause
