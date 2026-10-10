@echo off
REM Builds a single windowless DesktopAIAgent.exe (no console, no taskbar entry)
cd /d "%~dp0"
call venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller --noconfirm --onefile --noconsole --collect-data qtawesome --name DesktopAIAgent main.py
echo.
echo Built: dist\DesktopAIAgent.exe
pause
