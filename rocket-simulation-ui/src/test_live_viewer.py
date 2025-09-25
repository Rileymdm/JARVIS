#!/usr/bin/env python3
"""
Standalone test for the Live Code Viewer window
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5 import QtWidgets
from live_code_viewer import LiveCodeViewer

def test_live_code_viewer():
    """Test the Live Code Viewer as a standalone window"""
    app = QtWidgets.QApplication(sys.argv)
    
    print("Creating Live Code Viewer window...")
    viewer = LiveCodeViewer()
    
    print("Showing window...")
    viewer.show()
    viewer.raise_()
    viewer.activateWindow()
    
    print("Window should be visible now. Check your screen!")
    print("Press Ctrl+C or close the window to exit.")
    
    # Run the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    test_live_code_viewer()