@echo off
echo Starting Telegram Contract Monitor Bot...
echo.
echo Installing required packages...
pip install python-dotenv telethon colorama
echo.
echo Starting the bot...
"C:\Users\stefa\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\python.exe" monitor_account.py
echo.
echo If you see any errors above, please let me know.
pause 