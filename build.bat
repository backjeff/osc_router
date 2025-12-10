@echo off
setlocal

REM Go to the directory where this .bat file is located
cd /d "%~dp0"

REM Activate virtual environment (relative path)
call ".\venv\Scripts\activate.bat"

REM Run PyInstaller using the venv installation
pyinstaller --onefile --noconsole --icon=favicon.ico --add-data "favicon.ico;." osc_router.py

pause
