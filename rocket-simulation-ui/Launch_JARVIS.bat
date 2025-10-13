@echo off
echo.
echo 🚀 JARVIS Rocket Simulation App
echo ===============================
echo.
echo Starting application...
echo.

REM Change to the directory containing this script
cd /d "%~dp0"

REM Run the executable
if exist "dist\JARVIS.exe" (
    start "" "dist\JARVIS.exe"
    echo ✅ Application launched successfully!
) else if exist "JARVIS.exe" (
    start "" "JARVIS.exe"
    echo ✅ Application launched successfully!
) else (
    echo ❌ Error: JARVIS.exe not found!
    echo Please ensure the executable is in the same folder as this launcher.
    pause
    exit /b 1
)

echo.
echo 🎯 Tip: You can also run the .exe directly by double-clicking it
echo.
timeout /t 3 >nul