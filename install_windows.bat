@echo off
cd /d "%~dp0"
echo Creating virtual environment...
py -3 -m venv venv || python -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Done. Start the assistant with run.bat
pause
