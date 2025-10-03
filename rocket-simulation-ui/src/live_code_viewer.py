from PyQt5 import QtWidgets, QtCore, QtGui

class LiveCodeViewer(QtWidgets.QDialog):
    """Minimal placeholder implementation of the Live Code Viewer.
    This avoids ModuleNotFoundError and provides a simple resizable window
    that could later be extended to tail a file, show code updates, etc.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Live Code Viewer (Placeholder)")
        self.setMinimumSize(600, 400)
        self.setWindowFlag(QtCore.Qt.Window)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        info = QtWidgets.QLabel(
            "This is a placeholder Live Code Viewer.\n"
            "Future version can: tail log files, show executing code, highlight active functions, etc." )
        info.setAlignment(QtCore.Qt.AlignCenter)
        info.setStyleSheet("font-weight:bold; padding:8px;")
        layout.addWidget(info)

        self.text = QtWidgets.QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        self.text.setPlainText("No live stream active.\nUse run_demo() or future hooks to populate this view.")
        layout.addWidget(self.text, 1)

        btn_row = QtWidgets.QHBoxLayout()
        self.clear_btn = QtWidgets.QPushButton("Clear")
        self.clear_btn.clicked.connect(lambda: self.text.clear())
        self.demo_btn = QtWidgets.QPushButton("Demo Append")
        self.demo_btn.clicked.connect(self.run_demo)
        btn_row.addStretch(1)
        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(self.demo_btn)
        layout.addLayout(btn_row)

    def append_line(self, line: str):
        """Append a line of text to the viewer."""
        self.text.appendPlainText(line.rstrip('\n'))
        # Auto-scroll to bottom
        cursor = self.text.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.text.setTextCursor(cursor)

    def run_demo(self):
        """Very small demo that appends a few sample lines with a timer."""
        self.append_line("[demo] Starting demo output...")
        self.demo_count = 0
        if hasattr(self, '_demo_timer'):
            self._demo_timer.stop()
        self._demo_timer = QtCore.QTimer(self)
        self._demo_timer.timeout.connect(self._demo_tick)
        self._demo_timer.start(500)

    def _demo_tick(self):
        self.demo_count += 1
        self.append_line(f"[demo] Line {self.demo_count}")
        if self.demo_count >= 10:
            self.append_line("[demo] Demo complete.")
            self._demo_timer.stop()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    w = LiveCodeViewer()
    w.show()
    app.exec_()
