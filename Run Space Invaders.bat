@echo off
cd /d "%~dp0"
python "space invaders.py"
if errorlevel 1 (
    echo.
    echo The game could not start. Read the error above.
    pause
)
