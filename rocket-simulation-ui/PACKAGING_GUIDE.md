# JARVIS Rocket Simulation - Packaging Instructions

## Building the Executable

This directory contains everything needed to package the JARVIS Rocket Simulation app into a standalone .exe file.

### Quick Start

1. **Run the build script:**
   ```bash
   python build_exe.py
   ```

2. **Find your executable:**
   - The .exe file will be created in the `dist/` folder
   - File name: `JARVIS_Rocket_Simulation.exe`
   - This is a completely standalone executable that includes Python and all dependencies

### Manual Build (Alternative)

If you prefer to build manually:

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
pyinstaller --onefile --windowed --icon=src/JARVIS.ico --name="JARVIS_Rocket_Simulation" src/main.py

# Add data files
pyinstaller --onefile --windowed --icon=src/JARVIS.ico --name="JARVIS_Rocket_Simulation" --add-data "src/JARVIS.ico;." --add-data "src/jarvis.gif;." --add-data "src/Rocket.png;." --add-data "thrust_curves;thrust_curves" src/main.py
```

### What's Included

The executable includes:
- ✅ Complete Python runtime
- ✅ All required packages (PyQt5, matplotlib, numpy, pandas, scipy)
- ✅ App icons and images
- ✅ Sample thrust curve files
- ✅ Font files for retro theme
- ✅ All app modules and dependencies

### Distribution

The final .exe file is completely portable:
- 📦 Single file - no installation required
- 🖥️ Runs on any Windows machine (Windows 7+)
- 📁 Size: ~150-200 MB (includes full Python environment)
- 🚀 Double-click to run

### Troubleshooting

**Build Issues:**
- Make sure you're in the rocket-simulation-ui directory
- Ensure all Python dependencies are installed (`pip install -r requirements.txt`)
- Try running Python directly first: `python src/main.py`

**Runtime Issues:**
- The exe includes debug console output for troubleshooting
- Check Windows Defender/antivirus (may flag new executables)
- Run from command line to see any error messages

### Advanced Options

For smaller file size, you can create a directory distribution instead:
```bash
pyinstaller --windowed --icon=src/JARVIS.ico --name="JARVIS_Rocket_Simulation" src/main.py
```
This creates a folder with the exe and supporting files (smaller individual files, but multiple files to distribute).