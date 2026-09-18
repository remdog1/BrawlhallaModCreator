@echo off
cd /d "%~dp0"
py "%~dp0main.py"
if errorlevel 1 pause
