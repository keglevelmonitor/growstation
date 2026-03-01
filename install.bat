@echo off
SETLOCAL EnableDelayedExpansion
SET "PROJECT_DIR=%~dp0"
IF %PROJECT_DIR:~-1%==\ SET "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
SET "VENV_DIR=%PROJECT_DIR%\venv"
SET "DATA_DIR=%USERPROFILE%\growstation-data"
SET "SHORTCUT_PATH=%USERPROFILE%\Desktop\GrowStation.lnk"
SET "SCRIPT_PATH=%PROJECT_DIR%\src\main_kivy.py"

echo.
echo ==========================================
echo    GrowStation Installer (Windows)
echo ==========================================
echo.

IF NOT EXIST "%DATA_DIR%" mkdir "%DATA_DIR%"

IF NOT EXIST "%VENV_DIR%" (
    python -m venv "%VENV_DIR%"
)
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV_DIR%\Scripts\python.exe" -m pip install -r "%PROJECT_DIR%\requirements.txt"

powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%');$s.TargetPath='%VENV_DIR%\Scripts\pythonw.exe';$s.Arguments='\"%SCRIPT_PATH%\"';$s.WorkingDirectory='%PROJECT_DIR%\src';$s.Save()"
echo Shortcut created: %SHORTCUT_PATH%
echo.
pause
