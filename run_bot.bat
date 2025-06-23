@echo off

:: Show downloading message
cls
setlocal enabledelayedexpansion

echo Downloading content...

:: Install all required packages (hide output)
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt >nul 2>&1

:: Clear the screen after download
cls

echo Starting the bot...
python monitor_account.py

pause 