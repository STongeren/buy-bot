@echo off

:: Upgrade pip to latest version
python -m pip install --upgrade pip

:: Install all required packages
python -m pip install -r requirements.txt

echo Starting the bot...
python monitor_account.py

pause 