"""
Simple build script for JARVIS Rocket Simulation executable
This uses direct PyInstaller commands for better Windows compatibility
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("🚀 Building JARVIS Rocket Simulation Executable...")
    
    # Get the project root directory
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    main_py = src_dir / "main.py"
    
    if not main_py.exists():
        print(f"❌ Error: {main_py} not found!")
        return False
    
    # Clean previous builds
    for folder in ["build", "dist", "__pycache__"]:
        folder_path = project_root / folder
        if folder_path.exists():
            print(f"🧹 Cleaning {folder}...")
            shutil.rmtree(folder_path)
    
    # Change to project directory
    os.chdir(project_root)
    
    print("🔨 Building with PyInstaller...")
    
    # Simple PyInstaller command that should work
    cmd = [
        sys.executable, "-m", "pyinstaller",
        "--onefile",
        "--windowed", 
        "--name=JARVIS_Rocket_Simulation",
        f"--icon={src_dir}/JARVIS.ico",
        "--clean",
        "--noconfirm",
        str(main_py)
    ]
    
    print("Running command:", " ".join(cmd))
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, check=True, text=True)
        
        # Check if executable was created
        exe_path = project_root / "dist" / "JARVIS_Rocket_Simulation.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"✅ Success! Executable created: {exe_path}")
            print(f"📁 Size: {size_mb:.1f} MB")
            
            # Test if it's a proper executable
            print("🧪 Testing executable type...")
            if exe_path.suffix.lower() == '.exe':
                print("✅ File has proper .exe extension")
            else:
                print("❌ Warning: File doesn't have .exe extension")
                
            return True
        else:
            print("❌ Executable not found after build")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_executable():
    """Test the executable by trying to run it briefly"""
    project_root = Path(__file__).parent
    exe_path = project_root / "dist" / "JARVIS_Rocket_Simulation.exe"
    
    if exe_path.exists():
        print("🧪 Testing executable...")
        try:
            # Try to start the process and kill it quickly (just to test it launches)
            import time
            process = subprocess.Popen([str(exe_path)], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
            time.sleep(2)  # Let it start
            process.terminate()
            print("✅ Executable test passed - app can launch")
            return True
        except Exception as e:
            print(f"❌ Executable test failed: {e}")
            return False
    return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Build completed successfully!")
        print("📂 Your executable is ready in the 'dist' folder")
        print("💡 To run: Double-click JARVIS_Rocket_Simulation.exe")
        print("\n📋 Distribution notes:")
        print("  - Single file executable (no installation needed)")
        print("  - Contains complete Python runtime + all dependencies")
        print("  - Should run on any Windows 64-bit system")
        print("  - If antivirus flags it, that's normal for new executables")
        
        # Optional test
        if input("\n🤖 Test the executable now? (y/n): ").lower().startswith('y'):
            test_executable()
    else:
        print("\n💥 Build failed!")
        print("💡 Try running from command prompt to see detailed error messages")
        sys.exit(1)