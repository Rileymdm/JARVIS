#!/usr/bin/env python3
"""
Quick test script to verify theme switching functionality works without crashing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5 import QtWidgets
from main import RocketSimulationUI

def test_theme_switching():
    """Test that theme switching doesn't crash the application"""
    app = QtWidgets.QApplication(sys.argv)
    
    try:
        # Create the main window
        window = RocketSimulationUI()
        print("✓ Application initialized successfully")
        
        # Test switching to professional theme
        print("Testing theme switch to 'professional'...")
        window.on_theme_changed('professional')
        print("✓ Successfully switched to professional theme")
        
        # Test switching back to retro theme  
        print("Testing theme switch to 'retro'...")
        window.on_theme_changed('retro')
        print("✓ Successfully switched to retro theme")
        
        # Test switching to an invalid theme (should handle gracefully)
        print("Testing invalid theme switch...")
        window.on_theme_changed('invalid_theme')
        print("✓ Invalid theme handled gracefully")
        
        print("\n🎉 All theme switching tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Theme switching test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        app.quit()

if __name__ == "__main__":
    success = test_theme_switching()
    sys.exit(0 if success else 1)