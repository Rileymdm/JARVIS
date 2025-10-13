"""
Test script to verify the JARVIS Rocket Simulation executable works properly
"""

import subprocess
import sys
import time
from pathlib import Path

def main():
    print("🧪 Testing JARVIS Rocket Simulation Executable...")
    print("=" * 50)
    
    # Find the executable
    project_root = Path(__file__).parent
    exe_path = project_root / "dist" / "JARVIS_Rocket_Simulation.exe"
    
    if not exe_path.exists():
        print(f"❌ Executable not found: {exe_path}")
        print("Please build the executable first using build.bat or the pyinstaller command.")
        return False
    
    # Check file properties
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"📁 Executable found: {exe_path}")
    print(f"📏 Size: {size_mb:.1f} MB")
    print(f"🗓️ Modified: {time.ctime(exe_path.stat().st_mtime)}")
    
    # Test if it's a proper executable
    if exe_path.suffix.lower() != '.exe':
        print("❌ Warning: File doesn't have .exe extension")
        return False
    
    print("✅ File appears to be a proper Windows executable")
    print()
    
    # Ask user if they want to test launch
    try:
        response = input("🚀 Would you like to test launch the executable? (y/n): ").lower().strip()
        if response.startswith('y'):
            print("🏃 Launching executable...")
            
            # Launch the executable
            process = subprocess.Popen(
                [str(exe_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            print(f"✅ Process started with PID: {process.pid}")
            print("🕐 Waiting 3 seconds to see if it stays running...")
            
            # Wait a moment to see if it crashes immediately
            time.sleep(3)
            
            # Check if process is still running
            poll_result = process.poll()
            if poll_result is None:
                print("✅ Process is still running - executable appears to work!")
                print("🎯 You should see the JARVIS app window open.")
                print("🛑 The test will now terminate the process.")
                
                # Terminate the test process
                process.terminate()
                try:
                    process.wait(timeout=5)
                    print("✅ Process terminated cleanly")
                except subprocess.TimeoutExpired:
                    process.kill()
                    print("⚠️ Process had to be force-killed")
                
                return True
            else:
                print(f"❌ Process exited immediately with code: {poll_result}")
                stdout, stderr = process.communicate()
                if stdout:
                    print(f"📜 STDOUT: {stdout.decode()}")
                if stderr:
                    print(f"🚨 STDERR: {stderr.decode()}")
                return False
                
    except KeyboardInterrupt:
        print("\n🛑 Test cancelled by user")
        return False
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print()
    if success:
        print("🎉 Executable test PASSED!")
        print("📦 Your JARVIS Rocket Simulation app is ready for distribution!")
        print()
        print("📋 Next steps:")
        print("  1. Copy the .exe to any Windows computer")
        print("  2. Double-click to run (no installation needed)")
        print("  3. If antivirus flags it, add to exceptions")
        print("  4. Share with your users!")
    else:
        print("💥 Executable test FAILED!")
        print("🔧 Try rebuilding with the latest pyinstaller command")
    
    input("\nPress Enter to exit...")