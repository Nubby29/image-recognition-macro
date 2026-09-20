@echo off
REM Image Recognition Macro v0.2.0
cd /d "%~dp0"
python main.py
if errorlevel 1 pause
