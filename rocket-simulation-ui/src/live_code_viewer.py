"""
Live Code Viewer for JARVIS Rocket Simulation
Displays executing code in real-time for presentation purposes
"""

from PyQt5 import QtWidgets, QtGui, QtCore
import sys
import inspect
import threading
import time
from collections import deque
import os

class LiveCodeViewer(QtWidgets.QWidget):
    """A popout window that shows live code execution"""
    
    # Signal for thread-safe updates
    code_updated = QtCore.pyqtSignal(str, str, str)  # function_name, code, status
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.executing_functions = deque(maxlen=10)  # Keep last 10 function calls
        self.current_line = 0
        
        # Get screen information for scaling
        screen = QtWidgets.QApplication.desktop().screenGeometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        self.dpi_scale = QtWidgets.QApplication.desktop().logicalDpiX() / 96.0
        
        self.setup_ui()
        self.setup_styles()
        
        # Connect signal
        self.code_updated.connect(self.update_display)
        
        # Start monitoring thread
        self.monitor_thread = None
        self.monitoring = False
        
    def setup_ui(self):
        """Setup the live code viewer UI"""
        self.setWindowTitle("🚀 JARVIS Live Code Execution")
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), 'JARVIS.ico')))
        
        # Scale window size based on screen resolution
        if self.screen_width >= 2560:  # 4K or ultrawide
            width, height = int(1200 * self.dpi_scale), int(800 * self.dpi_scale)
        elif self.screen_width >= 1920:  # 1080p
            width, height = int(1000 * self.dpi_scale), int(700 * self.dpi_scale)
        else:  # Lower resolution
            width, height = int(800 * self.dpi_scale), int(600 * self.dpi_scale)
        
        self.resize(width, height)
        
        # Make window stay on top and more visible
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        
        layout = QtWidgets.QVBoxLayout(self)
        spacing = int(5 * self.dpi_scale)
        margins = int(10 * self.dpi_scale)
        layout.setSpacing(spacing)
        layout.setContentsMargins(margins, margins, margins, margins)
        
        # Header
        header_layout = QtWidgets.QHBoxLayout()
        
        title_label = QtWidgets.QLabel("🔴 LIVE CODE EXECUTION")
        title_label.setObjectName("title")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Control buttons
        self.start_stop_btn = QtWidgets.QPushButton("Start Monitoring")
        self.start_stop_btn.setObjectName("control_btn")
        self.start_stop_btn.clicked.connect(self.toggle_monitoring)
        header_layout.addWidget(self.start_stop_btn)
        
        self.demo_btn = QtWidgets.QPushButton("🎯 Demo Mode")
        self.demo_btn.setObjectName("demo_btn")
        self.demo_btn.setToolTip("Run a simulation demo to show live code execution")
        self.demo_btn.clicked.connect(self.run_demo)
        header_layout.addWidget(self.demo_btn)
        
        clear_btn = QtWidgets.QPushButton("Clear")
        clear_btn.setObjectName("control_btn")
        clear_btn.clicked.connect(self.clear_display)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # Status bar
        self.status_label = QtWidgets.QLabel("📡 Ready to monitor simulation code...")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)
        
        # Main content area
        content_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        # Left panel - Function call stack
        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        
        stack_label = QtWidgets.QLabel("📋 Function Call Stack")
        stack_label.setObjectName("panel_header")
        left_layout.addWidget(stack_label)
        
        self.function_list = QtWidgets.QListWidget()
        self.function_list.setObjectName("function_list")
        self.function_list.itemClicked.connect(self.on_function_selected)
        left_layout.addWidget(self.function_list)
        
        content_splitter.addWidget(left_panel)
        
        # Right panel - Code display
        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        
        code_label = QtWidgets.QLabel("💻 Executing Code")
        code_label.setObjectName("panel_header")
        right_layout.addWidget(code_label)
        
        # Code display with syntax highlighting
        self.code_display = QtWidgets.QTextEdit()
        self.code_display.setObjectName("code_display")
        self.code_display.setReadOnly(True)
        
        # Scale font size based on DPI
        font_size = max(9, int(11 * self.dpi_scale))
        font = QtGui.QFont("Consolas", font_size)
        if not font.exactMatch():
            font = QtGui.QFont("Monaco", font_size)
        if not font.exactMatch():
            font = QtGui.QFont("Courier New", font_size)
        
        self.code_display.setFont(font)
        right_layout.addWidget(self.code_display)
        
        # Execution info
        info_layout = QtWidgets.QHBoxLayout()
        
        self.current_function_label = QtWidgets.QLabel("🎯 Current: None")
        self.current_function_label.setObjectName("current_function")
        info_layout.addWidget(self.current_function_label)
        
        info_layout.addStretch()
        
        self.execution_time_label = QtWidgets.QLabel("⏱️ Time: 0.00s")
        self.execution_time_label.setObjectName("execution_time")
        info_layout.addWidget(self.execution_time_label)
        
        right_layout.addLayout(info_layout)
        
        content_splitter.addWidget(right_panel)
        content_splitter.setSizes([300, 700])
        
        layout.addWidget(content_splitter)
        
        # Performance metrics
        metrics_layout = QtWidgets.QHBoxLayout()
        
        self.calls_count_label = QtWidgets.QLabel("📊 Total Calls: 0")
        self.calls_count_label.setObjectName("metric")
        metrics_layout.addWidget(self.calls_count_label)
        
        self.avg_time_label = QtWidgets.QLabel("📈 Avg Time: 0.00ms")
        self.avg_time_label.setObjectName("metric")
        metrics_layout.addWidget(self.avg_time_label)
        
        metrics_layout.addStretch()
        
        layout.addLayout(metrics_layout)
        
    def setup_styles(self):
        """Apply JARVIS-themed styling with responsive sizing"""
        # Calculate responsive sizes
        title_font_size = max(14, int(18 * self.dpi_scale))
        button_font_size = max(10, int(12 * self.dpi_scale))
        header_font_size = max(12, int(14 * self.dpi_scale))
        list_font_size = max(9, int(11 * self.dpi_scale))
        status_font_size = max(10, int(12 * self.dpi_scale))
        metric_font_size = max(9, int(11 * self.dpi_scale))
        
        padding = max(4, int(8 * self.dpi_scale))
        button_padding_v = max(6, int(8 * self.dpi_scale))
        button_padding_h = max(12, int(16 * self.dpi_scale))
        border_radius = max(2, int(4 * self.dpi_scale))
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: #0F1419;
                color: #00D4FF;
                font-family: 'Consolas', 'Monaco', monospace;
            }}
            
            #title {{
                font-size: {title_font_size}px;
                font-weight: bold;
                color: #00FF41;
                padding: {padding}px;
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #1A252F, stop: 1 #0F1419);
                border: 1px solid #00FF41;
                border-radius: {border_radius}px;
            }}
            
            #demo_btn {{
                background-color: #00FF41;
                border: 1px solid #0F1419;
                border-radius: {border_radius}px;
                padding: {button_padding_v}px {button_padding_h}px;
                font-weight: bold;
                color: #0F1419;
                font-size: {button_font_size}px;
            }}
            
            #demo_btn:hover {{
                background-color: #32CD32;
                border: 2px solid #00D4FF;
            }}
            
            #control_btn {{
                background-color: #E94F37;
                border: 1px solid #00D4FF;
                border-radius: {border_radius}px;
                padding: {button_padding_v}px {button_padding_h}px;
                font-weight: bold;
                color: #FFFFFF;
                font-size: {button_font_size}px;
            }}
            
            #control_btn:hover {{
                background-color: #FF6B35;
                border: 2px solid #00FF41;
            }}
            
            #status {{
                background-color: #1A252F;
                border: 1px solid #00D4FF;
                border-radius: {border_radius}px;
                padding: {padding}px;
                color: #ECF0F1;
                font-size: {status_font_size}px;
            }}
            
            #panel_header {{
                font-size: {header_font_size}px;
                font-weight: bold;
                color: #00FF41;
                padding: {max(2, int(4 * self.dpi_scale))}px;
                background-color: #1A252F;
                border: 1px solid #00D4FF;
                border-radius: {max(1, int(3 * self.dpi_scale))}px;
            }}
            
            #function_list {{
                background-color: #1A252F;
                border: 1px solid #00D4FF;
                border-radius: {border_radius}px;
                alternate-background-color: #2C3E50;
                selection-background-color: #00D4FF;
                selection-color: #0F1419;
                font-size: {list_font_size}px;
            }}
            
            #function_list::item {{
                padding: {max(2, int(4 * self.dpi_scale))}px {padding}px;
                border-bottom: 1px solid #34495E;
            }}
            
            #function_list::item:selected {{
                background-color: #00FF41;
                color: #0F1419;
                font-weight: bold;
            }}
            
            #code_display {{
                background-color: #1A252F;
                border: 2px solid #00D4FF;
                border-radius: {max(3, int(6 * self.dpi_scale))}px;
                color: #ECF0F1;
                selection-background-color: #00D4FF;
                selection-color: #0F1419;
                line-height: 1.4;
            }}
            
            #current_function {{
                color: #00FF41;
                font-weight: bold;
                font-size: {status_font_size}px;
            }}
            
            #execution_time {{
                color: #FF6B35;
                font-weight: bold;
                font-size: {status_font_size}px;
            }}
            
            #metric {{
                color: #00D4FF;
                font-size: {metric_font_size}px;
                padding: {max(2, int(4 * self.dpi_scale))}px {padding}px;
                background-color: #1A252F;
                border: 1px solid #34495E;
                border-radius: {max(1, int(3 * self.dpi_scale))}px;
                margin: {max(1, int(2 * self.dpi_scale))}px;
            }}
            
            QSplitter::handle {{
                background-color: #00D4FF;
                width: {max(1, int(2 * self.dpi_scale))}px;
            }}
        """)
    
    def toggle_monitoring(self):
        """Start/stop code monitoring"""
        if not self.monitoring:
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def start_monitoring(self):
        """Start monitoring code execution"""
        self.monitoring = True
        self.start_stop_btn.setText("⏹️ Stop Monitoring")
        self.start_stop_btn.setStyleSheet(self.start_stop_btn.styleSheet() + 
                                        "QPushButton { background-color: #FF3333; }")
        self.status_label.setText("🔴 Monitoring active - Tracking simulation execution...")
        
        # Install trace function
        sys.settrace(self.trace_calls)
        
        # Reset metrics
        self.total_calls = 0
        self.total_time = 0.0
        self.start_time = time.time()
        
    def stop_monitoring(self):
        """Stop monitoring code execution"""
        self.monitoring = False
        self.start_stop_btn.setText("▶️ Start Monitoring")
        self.start_stop_btn.setStyleSheet(self.start_stop_btn.styleSheet().replace(
            "background-color: #FF3333;", "background-color: #E94F37;"))
        self.status_label.setText("⏸️ Monitoring stopped")
        
        # Remove trace function
        sys.settrace(None)
    
    def run_demo(self):
        """Run a demonstration of the simulation with live code tracking"""
        if not self.monitoring:
            self.start_monitoring()
        
        # Change demo button to show it's running
        self.demo_btn.setText("🔄 Running Demo...")
        self.demo_btn.setEnabled(False)
        
        # Run demo directly (no threading to avoid Qt issues)
        try:
            self._demo_simulation()
        except Exception as e:
            print(f"Demo error: {e}")
        
        # Reset demo button
        self._reset_demo_button()
    
    def _demo_simulation(self):
        """Run a demonstration simulation to show code execution"""
        try:
            # Simulate some rocket physics calculations for demo
            self._demo_physics_calculations()
            
            # Simulate thrust curve parsing
            self._demo_thrust_curve_parsing()
            
            # Simulate flight dynamics
            self._demo_flight_dynamics()
            
        except Exception as e:
            print(f"Demo error: {e}")
        finally:
            # Re-enable demo button using QTimer for thread safety
            self._reset_demo_button()
    
    def _reset_demo_button(self):
        """Reset the demo button state"""
        self.demo_btn.setText("🎯 Demo Mode")
        self.demo_btn.setEnabled(True)
    
    def _demo_physics_calculations(self):
        """Demo function showing physics calculations"""
        # Some example physics calculations that will show in the live viewer
        mass = 5.0  # kg
        drag_coefficient = 0.7
        cross_sectional_area = 0.004  # m²
        air_density = 1.225  # kg/m³
        
        # Calculate drag force
        velocity = 100.0  # m/s
        drag_force = 0.5 * air_density * (velocity ** 2) * drag_coefficient * cross_sectional_area
        
        # Calculate acceleration
        gravity = 9.81  # m/s²
        thrust = 800.0  # N
        net_force = thrust - drag_force - (mass * gravity)
        acceleration = net_force / mass
        
        return acceleration
    
    def _demo_thrust_curve_parsing(self):
        """Demo function showing thrust curve parsing"""
        # Simulate parsing a thrust curve
        thrust_data = []
        for t in range(0, 10):
            time_val = t * 0.1
            thrust_val = 800 * (1 - time_val/10) if time_val < 6 else 0
            thrust_data.append((time_val, thrust_val))
        
        # Simulate interpolation
        times = [point[0] for point in thrust_data]
        thrusts = [point[1] for point in thrust_data]
        
        return times, thrusts
    
    def _demo_flight_dynamics(self):
        """Demo function showing flight dynamics simulation"""
        # Simulate a flight dynamics step
        dt = 0.1  # time step
        altitude = 0.0
        velocity = 0.0
        
        for step in range(20):  # Reduced iterations to avoid blocking
            # Get current acceleration from physics
            acceleration = self._demo_physics_calculations()
            
            # Update velocity and position
            velocity += acceleration * dt
            altitude += velocity * dt
            
            # Simple drag and gravity effects
            if altitude < 0:
                altitude = 0
                velocity = 0
                break
        
        return altitude, velocity

    def trace_calls(self, frame, event, arg):
        """Trace function calls for live monitoring"""
        if not self.monitoring:
            return None
            
        # Only track calls from our simulation modules or demo functions
        filename = frame.f_code.co_filename
        func_name = frame.f_code.co_name
        
        # Include demo functions and simulation-related code
        should_track = (
            'simulation' in filename.lower() or 
            'main.py' in filename or
            '_demo_' in func_name or
            func_name in ['run_simulation', 'start_simulation', 'update_launch_frame'] or
            'rocket' in filename.lower()
        )
        
        if not should_track:
            return None
            
        if event == 'call':
            file_name = os.path.basename(filename)
            line_no = frame.f_lineno
            
            # Get function source code
            try:
                source_lines, start_line = inspect.getsourcelines(frame.f_code)
                source_code = ''.join(source_lines)
                
                # Add function context information
                context_info = f"# Function: {func_name}()\n# File: {file_name}\n# Starting at line: {start_line}\n\n"
                full_code = context_info + source_code
                
                # Highlight current line relative to function start
                current_line_in_func = line_no - start_line + 1
                highlighted_code = self.highlight_current_line(full_code, current_line_in_func + 4)  # +4 for context lines
                
                # Update display
                self.code_updated.emit(
                    f"{file_name}::{func_name}() [Line {line_no}]",
                    highlighted_code,
                    f"🚀 Executing {func_name}()"
                )
                
                self.total_calls += 1
                
            except Exception as e:
                # Fallback for functions we can't get source for
                fallback_code = f"""# Function: {func_name}()
# File: {file_name}
# Line: {line_no}
# Status: Executing...

def {func_name}():
    # Source code not available for this function
    # This is likely a built-in or compiled function
    pass

>>> CURRENTLY EXECUTING: {func_name}() <<<"""

                self.code_updated.emit(
                    f"{file_name}::{func_name}() [Line {line_no}]",
                    fallback_code,
                    f"🚀 Executing {func_name}()"
                )
        
        return self.trace_calls
    
    def highlight_current_line(self, code, current_line):
        """Add highlighting to the current executing line"""
        lines = code.split('\n')
        if 0 < current_line <= len(lines):
            lines[current_line - 1] = f">>> {lines[current_line - 1]}  <<<< EXECUTING"
        
        return '\n'.join(lines)
    
    def update_display(self, function_name, code, status):
        """Update the display with new execution info (thread-safe)"""
        # Update function list
        self.function_list.addItem(f"⚡ {function_name}")
        self.function_list.scrollToBottom()
        
        # Keep list manageable
        if self.function_list.count() > 50:
            self.function_list.takeItem(0)
        
        # Update code display
        self.code_display.setPlainText(code)
        
        # Highlight executing line
        cursor = self.code_display.textCursor()
        format = QtGui.QTextCharFormat()
        format.setBackground(QtGui.QColor("#00FF41"))
        format.setForeground(QtGui.QColor("#000000"))
        
        # Find executing line
        text = self.code_display.toPlainText()
        executing_line = -1
        for i, line in enumerate(text.split('\n')):
            if 'EXECUTING' in line:
                executing_line = i
                break
        
        if executing_line >= 0:
            # Move cursor to executing line
            cursor.movePosition(QtGui.QTextCursor.Start)
            for _ in range(executing_line):
                cursor.movePosition(QtGui.QTextCursor.Down)
            cursor.select(QtGui.QTextCursor.LineUnderCursor)
            cursor.setCharFormat(format)
            self.code_display.setTextCursor(cursor)
        
        # Update status
        self.current_function_label.setText(f"🎯 Current: {function_name}")
        
        # Update metrics
        elapsed = time.time() - self.start_time if hasattr(self, 'start_time') else 0
        self.execution_time_label.setText(f"⏱️ Time: {elapsed:.2f}s")
        self.calls_count_label.setText(f"📊 Total Calls: {self.total_calls}")
        
        if self.total_calls > 0:
            avg_time = (elapsed / self.total_calls) * 1000
            self.avg_time_label.setText(f"📈 Avg Time: {avg_time:.2f}ms")
    
    def on_function_selected(self, item):
        """Handle function selection from the list"""
        # Could implement showing specific function details here
        pass
    
    def clear_display(self):
        """Clear all displays"""
        self.function_list.clear()
        self.code_display.clear()
        self.current_function_label.setText("🎯 Current: None")
        self.execution_time_label.setText("⏱️ Time: 0.00s")
        self.calls_count_label.setText("📊 Total Calls: 0")
        self.avg_time_label.setText("📈 Avg Time: 0.00ms")
        self.total_calls = 0
        self.total_time = 0.0
    
    def closeEvent(self, event):
        """Handle window close"""
        self.stop_monitoring()
        
        # Reset parent button text if parent exists
        if self.parent_app and hasattr(self.parent_app, 'live_code_button'):
            self.parent_app.live_code_button.setText('🔴 Live Code Viewer')
        
        event.accept()