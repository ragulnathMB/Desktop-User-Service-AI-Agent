@echo off
cd /d "%~dp0"
if not exist venv\Scripts\pythonw.exe (
  echo Virtual environment not found. Run install_windows.bat first.
  pause & exit /b 1
)
start "" venv\Scripts\pythonw.exe main.py
