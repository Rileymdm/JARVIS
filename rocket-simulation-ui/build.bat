@echo off
echo 🚀 Building JARVIS Rocket Simulation Executable...
echo.

REM Change to the project directory
cd /d "%~dp0"

REM Clean previous builds
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del "*.spec"

echo 🧹 Cleaned previous builds
echo.

REM Use the virtual environment Python
set PYTHON_EXE=..\..\.venv\Scripts\python.exe
set PYINSTALLER_EXE=..\..\.venv\Scripts\pyinstaller.exe

REM Check if virtual environment exists
if not exist "%PYTHON_EXE%" (
    echo ❌ Virtual environment Python not found at %PYTHON_EXE%
    echo Please make sure the virtual environment is set up correctly.
    pause
    exit /b 1
)

if not exist "%PYINSTALLER_EXE%" (
    echo ❌ PyInstaller not found at %PYINSTALLER_EXE%
    echo Installing PyInstaller...
    "%PYTHON_EXE%" -m pip install pyinstaller
)

echo 🔨 Building executable...
echo.

REM Build the executable
"%PYINSTALLER_EXE%" ^
    --onefile ^
    --windowed ^
    --name=JARVIS ^
    --icon=src\JARVIS.ico ^
    --clean ^
    --noconfirm ^
    --add-data "src\JARVIS.ico;." ^
    --add-data "src\jarvis.gif;." ^
    --add-data "src\Rocket.png;." ^
    --add-data "thrust_curves;thrust_curves" ^
    --hidden-import=PyQt5.QtCore ^
    --hidden-import=PyQt5.QtGui ^
    --hidden-import=PyQt5.QtWidgets ^
    --hidden-import=matplotlib.backends.backend_qt5agg ^
    src\main.py

if %ERRORLEVEL% NEQ 0 (
    echo ❌ Build failed!
    echo Check the error messages above.
    pause
    exit /b 1
)

REM Check if executable was created
if exist "dist\JARVIS.exe" (
    echo ✅ Build completed successfully!
    echo.
    echo 📁 Executable location: dist\JARVIS.exe
    
    REM Get file size
    for %%A in ("dist\JARVIS.exe") do (
        set /a "size=%%~zA / 1048576"
        echo 📏 File size: !size! MB
    )
    
    echo.
    echo 🎉 Your JARVIS Rocket Simulation app is ready!
    echo 💡 To test: Right-click the .exe file and select "Run as administrator" if needed
    echo 🚀 To run normally: Double-click the .exe file
    
    REM Ask if user wants to test it
    set /p test="🤖 Would you like to test the executable now? (y/n): "
    if /i "%test%"=="y" (
        echo.
        echo 🧪 Testing executable...
        start "" "dist\JARVIS.exe"
        echo ✅ Executable launched! Check if the app window opens properly.
    )
) else (
    echo ❌ JARVIS.exe not found after build!
    echo Something went wrong during the build process.
)

echo.
pause