@echo off

:: Optional: Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

:: Install requirements and pyinstaller
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

:: Build the executable
pyinstaller --onefile --add-data "licenses.json;." monitor_account.py

echo.
echo Build complete! Your executable is in the dist folder.
pause 