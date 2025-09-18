from PyQt5 import QtWidgets, QtGui, QtCore
import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from simulation import run_simulation
import os
import json
import numpy as np
import random
import traceback

# === FULL RETRO PIXEL STYLE ===
retro_style = """
from scipy.ndimage import rotate
QProgressBar {
    background-color: #FDF6E3;
    border: 2px solid #BCA16A;
    border-radius: 8px;
    height: 18px;
    color: #3C2F1E;
}
QProgressBar::chunk {
    background-color: #E94F37;
    width: 8px;
}

QToolBar {
    background-color: #F8F5E3;
    border: 2px solid #BCA16A;
    color: #3C2F1E;
    font-family: 'Press Start 2P', monospace;
    font-size: 12px;
}
QWidget {
    background-color: #F8F5E3; /* 8BitDo beige */
    font-family: 'Press Start 2P', monospace;
    font-size: 12px;
    color: #3C2F1E; /* dark brown */
}

QLineEdit {
    background-color: #FDF6E3; /* lighter beige */
    border: 2px solid #BCA16A; /* brown accent */
    border-radius: 4px;
    padding: 4px;
    color: #3C2F1E;
}

QPushButton {
    background-color: #E94F37; /* 8BitDo red */
    border: 2px solid #3C2F1E;
    border-radius: 6px;
    padding: 6px;
    font-weight: bold;
    color: #F8F5E3;
}

QPushButton:hover {
    background-color: #FFD447; /* 8BitDo yellow */
    border: 2px solid #E94F37;
    color: #3C2F1E;
}

QLabel {
    font-weight: bold;
    color: #3C2F1E;
}

QSplitter::handle {
    background-color: #BCA16A;
}
"""
# === END RETRO STYLE ===

class CrashImageDialog(QtWidgets.QDialog):
    def __init__(self, image_path, error_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Program Crashed!')
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel('The program has crashed!')
        label.setStyleSheet('font-size: 18px; color: #E94F37; font-weight: bold;')
        layout.addWidget(label)
        pixmap = QtGui.QPixmap(image_path)
        img_label = QtWidgets.QLabel()
        img_label.setPixmap(pixmap.scaledToWidth(400, QtCore.Qt.SmoothTransformation))
        layout.addWidget(img_label)
        error_box = QtWidgets.QTextEdit()
        error_box.setReadOnly(True)
        error_box.setText(error_text)
        error_box.setStyleSheet('color: #E94F37; background: #F8F5E3;')
        layout.addWidget(error_box)
        self.setLayout(layout)

class RocketSimulationUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self._rocket_img_cache = {}
        # Set window and taskbar icon (use .ico for best Windows compatibility)
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), 'JARVIS.ico')))
        self.init_ui()
        self.load_inputs()  # Load inputs on startup
        self.showMaximized()


    def init_ui(self):
        self.setWindowTitle('JARVIS')
        main_layout = QtWidgets.QHBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        main_panel = QtWidgets.QWidget()
        main_panel_layout = QtWidgets.QHBoxLayout(main_panel)

        # Left panel: Inputs
        left_widget = QtWidgets.QWidget()
        left_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        left_layout = QtWidgets.QVBoxLayout(left_widget)

        form_layout = QtWidgets.QFormLayout()
        # Input fields
        self.mass_input = QtWidgets.QLineEdit()
        self.mass_unit = QtWidgets.QComboBox(); self.mass_unit.addItems(["kg", "g", "lb"])
        mass_row = QtWidgets.QHBoxLayout(); mass_row.addWidget(self.mass_input); mass_row.addWidget(self.mass_unit)

        self.cd_input = QtWidgets.QLineEdit()

        self.area_input = QtWidgets.QLineEdit()
        self.area_unit = QtWidgets.QComboBox(); self.area_unit.addItems(["m²", "cm²", "ft²"])
        area_row = QtWidgets.QHBoxLayout(); area_row.addWidget(self.area_input); area_row.addWidget(self.area_unit)

        self.rho_input = QtWidgets.QLineEdit()
        self.rho_unit = QtWidgets.QComboBox(); self.rho_unit.addItems(["kg/m³", "g/cm³", "lb/ft³"])
        rho_row = QtWidgets.QHBoxLayout(); rho_row.addWidget(self.rho_input); rho_row.addWidget(self.rho_unit)

        self.timestep_input = QtWidgets.QLineEdit()
        self.timestep_input.setPlaceholderText("Time Step")
        self.timestep_input.setText("0.1")
        self.timestep_unit = QtWidgets.QComboBox(); self.timestep_unit.addItems(["s", "ms"])
        timestep_row = QtWidgets.QHBoxLayout(); timestep_row.addWidget(self.timestep_input); timestep_row.addWidget(self.timestep_unit)

        self.fin_count_input = QtWidgets.QLineEdit()
        self.fin_thickness_input = QtWidgets.QLineEdit()
        self.fin_thickness_unit = QtWidgets.QComboBox(); self.fin_thickness_unit.addItems(["m", "mm", "in"])
        fin_thickness_row = QtWidgets.QHBoxLayout(); fin_thickness_row.addWidget(self.fin_thickness_input); fin_thickness_row.addWidget(self.fin_thickness_unit)

        self.fin_length_input = QtWidgets.QLineEdit()
        self.fin_length_unit = QtWidgets.QComboBox(); self.fin_length_unit.addItems(["m", "mm", "in"])
        fin_length_row = QtWidgets.QHBoxLayout(); fin_length_row.addWidget(self.fin_length_input); fin_length_row.addWidget(self.fin_length_unit)

        self.body_diameter_input = QtWidgets.QLineEdit()
        self.body_diameter_unit = QtWidgets.QComboBox(); self.body_diameter_unit.addItems(["m", "mm", "in"])
        body_diameter_row = QtWidgets.QHBoxLayout(); body_diameter_row.addWidget(self.body_diameter_input); body_diameter_row.addWidget(self.body_diameter_unit)

        self.chute_height_input = QtWidgets.QLineEdit()
        self.chute_height_unit = QtWidgets.QComboBox(); self.chute_height_unit.addItems(["m", "ft"])
        chute_height_row = QtWidgets.QHBoxLayout(); chute_height_row.addWidget(self.chute_height_input); chute_height_row.addWidget(self.chute_height_unit)

        self.chute_size_input = QtWidgets.QLineEdit()
        self.chute_size_unit = QtWidgets.QComboBox(); self.chute_size_unit.addItems(["m²", "ft²"])
        chute_size_row = QtWidgets.QHBoxLayout(); chute_size_row.addWidget(self.chute_size_input); chute_size_row.addWidget(self.chute_size_unit)

        # Set size policies
        for widget in [self.mass_input, self.cd_input, self.area_input, self.rho_input,
                   self.timestep_input,
                   self.fin_count_input, self.fin_thickness_input, self.fin_length_input, self.body_diameter_input,
                   self.chute_height_input, self.chute_size_input]:
            widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Add rows to form layout
        form_layout.addRow("Mass:", mass_row)
        form_layout.addRow("Drag Coefficient (Cd):", self.cd_input)
        form_layout.addRow("Cross-sectional Area:", area_row)
        form_layout.addRow("Air Density:", rho_row)
        form_layout.addRow("Time Step:", timestep_row)
        form_layout.addRow("Fin Count:", self.fin_count_input)
        form_layout.addRow("Fin Thickness:", fin_thickness_row)
        form_layout.addRow("Fin Length:", fin_length_row)
        form_layout.addRow("Body Tube Diameter:", body_diameter_row)
        form_layout.addRow("Parachute Deploy Height:", chute_height_row)
        form_layout.addRow("Parachute Size:", chute_size_row)
        # New row for parachute drag coefficient
        self.chute_cd_input = QtWidgets.QLineEdit()
        self.chute_cd_input.setPlaceholderText("Parachute Cd")
        self.chute_cd_input.setText("1.5")
        form_layout.addRow("Parachute Drag Coefficient (Cd):", self.chute_cd_input)

        left_layout.addLayout(form_layout)

        # Thematic progress bar for flight phase
        self.phase_progress = QtWidgets.QProgressBar()
        self.phase_progress.setMinimum(0)
        self.phase_progress.setMaximum(100)
        self.phase_progress.setValue(0)
        self.phase_progress.setTextVisible(True)
        self.phase_progress.setAlignment(QtCore.Qt.AlignCenter)
        # Retro style: background beige, chunk red, text inverse (beige on red)
        self.phase_progress.setStyleSheet('''
            QProgressBar {
                background-color: #FDF6E3;
                border: 2px solid #BCA16A;
                border-radius: 8px;
                height: 24px;
                color: #3C2F1E;
                font-weight: bold;
                font-size: 14px;
            }
            QProgressBar::chunk {
                background-color: #E94F37;
                color: #FDF6E3;
                font-weight: bold;
                font-size: 14px;
            }
        ''')
        left_layout.addWidget(self.phase_progress)

        # Buttons
        self.thrust_curve_path = None
        self.select_thrust_button = QtWidgets.QPushButton('Select Thrust Curve CSV')
        self.select_thrust_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.select_thrust_button.clicked.connect(self.select_thrust_curve)
        left_layout.addWidget(self.select_thrust_button)

        self.start_button = QtWidgets.QPushButton('Start Simulation')
        self.start_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.start_button.clicked.connect(self.start_simulation)
        left_layout.addWidget(self.start_button)

        # Az/5 kill button
        self.kill_button = QtWidgets.QPushButton('Az/5')
        self.kill_button.setStyleSheet('background-color: #E94F37; color: #F8F5E3; font-weight: bold; border-radius: 6px;')
        self.kill_button.setToolTip('Emergency stop: immediately exit the program')
        self.kill_button.clicked.connect(QtWidgets.QApplication.quit)
        left_layout.addWidget(self.kill_button)

        # Results label
        self.result_label = QtWidgets.QLabel('Results will be displayed here.')
        self.result_label.setWordWrap(True)
        self.result_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.result_label.setTextFormat(QtCore.Qt.RichText)
        self.result_label.setStyleSheet('''
            QLabel {
                background-color: #FDF6E3;
                border: 2px solid #E94F37;
                border-radius: 10px;
                padding: 10px;
                color: #3C2F1E;
                font-family: 'Press Start 2P', monospace;
                font-size: 13px;
            }
        ''')
        left_layout.addWidget(self.result_label)

        # Error/warning label
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: red; font-weight: bold;")
        left_layout.addWidget(self.error_label)

        left_layout.addStretch()

        # Right panel: Graph only (remove wireframe)
        right_widget = QtWidgets.QWidget()
        right_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        right_layout = QtWidgets.QVBoxLayout(right_widget)

        self.figure = plt.Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        right_layout.addWidget(self.canvas)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background-color: #F8F5E3; border: 2px solid #BCA16A; color: #3C2F1E; font-family: 'Press Start 2P', monospace; font-size: 12px;")
        right_layout.addWidget(self.toolbar)

        # --- Animation Controls ---
        anim_controls_layout = QtWidgets.QHBoxLayout()
        self.anim_pause_button = QtWidgets.QPushButton('Pause')
        self.anim_pause_button.setCheckable(True)
        self.anim_pause_button.setChecked(False)
        self.anim_pause_button.clicked.connect(self.toggle_fbd_animation)
        anim_controls_layout.addWidget(self.anim_pause_button)

        anim_controls_layout.addWidget(QtWidgets.QLabel('Speed:'))
        self.anim_speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.anim_speed_slider.setMinimum(1)
        self.anim_speed_slider.setMaximum(100)
        self.anim_speed_slider.setValue(30)  # Default to 30ms per frame
        self.anim_speed_slider.setTickInterval(10)
        self.anim_speed_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.anim_speed_slider.valueChanged.connect(self.set_fbd_anim_speed)
        anim_controls_layout.addWidget(self.anim_speed_slider)
        right_layout.addLayout(anim_controls_layout)

        right_widget.setLayout(right_layout)

        # Splitter for resizable panels
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 1000])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        main_panel_layout.addWidget(splitter)
        self.tabs.addTab(main_panel, "Simulation")

        # Settings tab for units
        settings_widget = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout(settings_widget)
        self.unit_select = QtWidgets.QComboBox()
        self.unit_select.addItems(["Metric (m, kg)", "Imperial (ft, lb)"])
        settings_layout.addWidget(QtWidgets.QLabel("Units:"))
        settings_layout.addWidget(self.unit_select)
        settings_layout.addStretch()
        self.tabs.addTab(settings_widget, "Settings")

        # Launch Conditions Tab
        launch_tab = QtWidgets.QWidget()
        launch_layout = QtWidgets.QFormLayout(launch_tab)
        self.start_altitude_input = QtWidgets.QLineEdit()
        self.start_altitude_input.setPlaceholderText("Start Altitude (m)")
        self.start_altitude_input.setText("0")
        launch_layout.addRow("Start Altitude (m):", self.start_altitude_input)
        self.temperature_input = QtWidgets.QLineEdit()
        self.temperature_input.setPlaceholderText("Temperature (°C)")
        self.temperature_input.setText("15")
        launch_layout.addRow("Temperature (°C):", self.temperature_input)
        self.humidity_input = QtWidgets.QLineEdit()
        self.humidity_input.setPlaceholderText("Humidity (%)")
        self.humidity_input.setText("50")
        launch_layout.addRow("Humidity (%):", self.humidity_input)
        self.start_altitude_input.textChanged.connect(self.update_air_density)
        self.temperature_input.textChanged.connect(self.update_air_density)
        self.humidity_input.textChanged.connect(self.update_air_density)
        self.tabs.addTab(launch_tab, "Launch Conditions")

        # Add Launch tab last (to the right)
        launch_anim_tab = QtWidgets.QWidget()
        launch_anim_layout = QtWidgets.QVBoxLayout(launch_anim_tab)

        wind_group = QtWidgets.QGroupBox("Wind Simulation")
        wind_layout = QtWidgets.QFormLayout(wind_group)

        self.wind_speed_input = QtWidgets.QDoubleSpinBox()
        self.wind_speed_input.setRange(0, 100)
        self.wind_speed_input.setValue(0)
        self.wind_speed_input.setSuffix(" m/s")
        wind_layout.addRow("Wind Speed:", self.wind_speed_input)

        self.wind_direction_input = QtWidgets.QDial()
        self.wind_direction_input.setMinimum(0)
        self.wind_direction_input.setMaximum(359)
        self.wind_direction_input.setNotchesVisible(True)
        wind_dir_label = QtWidgets.QLabel("Wind Direction: 0° (East)")
        wind_dir_label.setAlignment(QtCore.Qt.AlignCenter)
        self.wind_direction_input.valueChanged.connect(lambda v: wind_dir_label.setText(f"Wind Direction: {v}°"))
        wind_layout.addRow(wind_dir_label, self.wind_direction_input)

        launch_anim_layout.addWidget(wind_group)
        # Stability controls
        stability_group = QtWidgets.QGroupBox("Rocket Stability")
        stability_layout = QtWidgets.QFormLayout(stability_group)

        self.rocket_length_input = QtWidgets.QDoubleSpinBox()
        self.rocket_length_input.setRange(0.1, 10.0)
        self.rocket_length_input.setValue(1.0)
        self.rocket_length_input.setSuffix(" m")
        stability_layout.addRow("Rocket Length:", self.rocket_length_input)

        self.center_of_mass_input = QtWidgets.QDoubleSpinBox()
        self.center_of_mass_input.setRange(0.0, 10.0)
        self.center_of_mass_input.setValue(0.5)
        self.center_of_mass_input.setSuffix(" m")
        stability_layout.addRow("Center of Mass:", self.center_of_mass_input)

        self.center_of_pressure_input = QtWidgets.QDoubleSpinBox()
        self.center_of_pressure_input.setRange(0.0, 10.0)
        self.center_of_pressure_input.setValue(0.7)
        self.center_of_pressure_input.setSuffix(" m")
        stability_layout.addRow("Center of Pressure:", self.center_of_pressure_input)

        self.stability_status_label = QtWidgets.QLabel("Stability Margin: 0.2 m (Stable)")
        self.stability_status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.stability_status_label.setStyleSheet("font-size:14px;color:#2E8B57;font-weight:bold;")
        stability_layout.addRow(self.stability_status_label)

        # Update stability margin when inputs change
        def update_stability():
            margin = self.center_of_pressure_input.value() - self.center_of_mass_input.value()
            status = "Stable" if margin > 0.05 else "Unstable"
            color = "#2E8B57" if status == "Stable" else "#E94F37"
            self.stability_status_label.setText(f"Stability Margin: {margin:.2f} m ({status})")
            self.stability_status_label.setStyleSheet(f"font-size:14px;font-weight:bold;color:{color};")
        self.rocket_length_input.valueChanged.connect(update_stability)
        self.center_of_mass_input.valueChanged.connect(update_stability)
        self.center_of_pressure_input.valueChanged.connect(update_stability)
        update_stability()

        launch_anim_layout.addWidget(stability_group)

        # Rocket launch animation canvas
        self.launch_fig = plt.Figure(figsize=(8, 6))
        self.launch_fig.patch.set_facecolor('#F8F5E3')  # Match retro theme
        self.launch_canvas = FigureCanvas(self.launch_fig)
        self.launch_canvas.setMinimumSize(400, 300)
        launch_anim_layout.addWidget(self.launch_canvas)

        # Retro styled Launch button
        self.launch_button = QtWidgets.QPushButton('Launch!')
        self.launch_button.setStyleSheet('''
            QPushButton {
                background-color: #E94F37;
                border: 2px solid #3C2F1E;
                border-radius: 10px;
                padding: 12px 32px;
                font-weight: bold;
                font-size: 20px;
                color: #F8F5E3;
                margin-top: 16px;
            }
            QPushButton:hover {
                background-color: #FFD447;
                color: #3C2F1E;
                border: 2px solid #E94F37;
            }
        ''')
        self.launch_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.launch_button.clicked.connect(self.start_launch_animation)
        launch_anim_layout.addWidget(self.launch_button, alignment=QtCore.Qt.AlignCenter)

        # Animation variables
        self.launch_time = 0.0
        self.is_launching = False
        self.launch_timer = QtCore.QTimer()
        self.launch_timer.timeout.connect(self.update_launch_frame)

        def update_launch_animation():
            """Update static preview of launch trajectory using real simulation parameters"""
            if self.is_launching:
                return  # Don't update static view during animation
                
            ax = self.launch_fig.gca()
            ax.clear()
            
            # Get rocket parameters from Simulation tab
            try:
                m, Cd, A, rho, time_step, fin_thickness, fin_length, body_diameter, chute_height, chute_size, chute_deploy_time, chute_cd = self.get_inputs_for_simulation()
                if m <= 0 or Cd <= 0 or A <= 0 or rho <= 0:
                    raise ValueError("Invalid simulation parameters")
            except:
                # Fallback to default values if simulation inputs are invalid
                m, Cd, A, rho = 5.0, 0.7, 0.004560, 1.225
            
            # Get wind and stability parameters
            wind_speed = self.wind_speed_input.value()
            wind_dir_deg = self.wind_direction_input.value()
            margin = self.center_of_pressure_input.value() - self.center_of_mass_input.value()
            stable = margin > 0.05
            color = '#2E8B57' if stable else '#E94F37'
            
            import math
            from scipy.interpolate import interp1d
            
            # Setup thrust curve data
            thrust_data = []
            if hasattr(self, 'thrust_curve_path') and self.thrust_curve_path:
                # Load thrust curve from file
                import csv
                try:
                    with open(self.thrust_curve_path, newline='') as csvfile:
                        reader = csv.reader(csvfile)
                        for row in reader:
                            if not row or len(row) < 2:
                                continue
                            try:
                                t_thrust = float(row[0])
                                thrust = float(row[1])
                                thrust_data.append((t_thrust, thrust))
                            except:
                                continue
                except:
                    thrust_data = []
            
            if not thrust_data:
                # Default thrust curve
                thrust_data = [
                    (0.124, 816.849), (0.375, 796.043), (0.626, 781.861), (0.877, 767.440),
                    (1.129, 759.627), (1.380, 735.948), (1.631, 714.454), (1.883, 701.582),
                    (2.134, 674.667), (2.385, 656.493), (2.637, 636.076), (2.889, 612.409),
                    (3.140, 587.801), (3.391, 567.170), (3.642, 559.971), (3.894, 534.157),
                    (4.145, 444.562), (4.396, 280.510), (4.648, 216.702), (4.899, 163.136),
                    (5.150, 120.571), (5.402, 86.544), (5.653, 59.990), (5.904, 39.527),
                    (6.156, 25.914), (6.408, 0.000)
                ]
            
            times_thrust, thrusts = zip(*thrust_data)
            thrust_func = interp1d(times_thrust, thrusts, bounds_error=False, fill_value=0.0)
            burn_time = times_thrust[-1]
            
            # Simulate trajectory preview using real physics
            g = 9.81
            dt = 0.1  # Time step for preview
            max_time = 15.0  # Preview up to 15 seconds
            
            # Initialize
            velocity = 0.0
            altitude = 0.0
            x_pos = 0.0
            mass = m
            
            times = []
            x_traj = []
            y_traj = []
            
            # Wind drift
            drift_factor = wind_speed * 0.01
            angle_rad = wind_dir_deg * math.pi / 180
            x_drift_per_sec = drift_factor * math.cos(angle_rad)
            
            t = 0
            while t < max_time and altitude >= 0:
                times.append(t)
                x_traj.append(x_pos)
                y_traj.append(altitude)
                
                # Get thrust at current time
                current_thrust = float(thrust_func(t)) if t <= burn_time else 0.0
                
                # Calculate drag force
                drag_force = 0.5 * rho * (velocity ** 2) * Cd * A if velocity > 0 else 0
                
                # Net force and acceleration
                net_force = current_thrust - drag_force - (mass * g)
                acceleration = net_force / mass
                
                # Add instability
                if not stable:
                    wobble = 0.3 * math.sin(t * 8) * (1 + t * 0.05)
                    acceleration += wobble
                
                # Update motion
                velocity += acceleration * dt
                altitude += velocity * dt
                x_pos += x_drift_per_sec * dt
                
                if altitude < 0:
                    altitude = 0
                    break
                    
                t += dt
            
            # Plot trajectory
            ax.plot(x_traj, y_traj, '--', color=color, alpha=0.7, linewidth=2, label='Predicted Path')
            
            # Draw rocket at launch pad
            ax.plot([0], [0], color=color, marker='^', markersize=15, label=f'Rocket ({"Stable" if stable else "Unstable"})')
            
            # Draw wind arrow if there's wind
            if wind_speed > 0:
                ax.arrow(-0.5, 0.2, x_drift_per_sec * 50, 0, 
                        head_width=0.15, head_length=0.15, 
                        fc='#4682B4', ec='#4682B4', linewidth=3, 
                        label=f'Wind: {wind_speed:.1f} m/s')
            
            # Auto-scale based on trajectory
            if x_traj and y_traj:
                max_x = max(max(x_traj), abs(min(x_traj)))
                max_y = max(y_traj)
                ax.set_xlim(-max(2, max_x * 1.2), max(2, max_x * 1.2))
                ax.set_ylim(0, max(3, max_y * 1.1))
            else:
                ax.set_xlim(-2, 2)
                ax.set_ylim(0, 3)
            
            ax.set_xlabel('Drift (m)', color='#3C2F1E')
            ax.set_ylabel('Altitude (m)', color='#3C2F1E')
            ax.grid(True, alpha=0.3, color='#BCA16A')
            ax.legend(loc='upper left')
            ax.set_facecolor('#FDF6E3')  # Light beige background
            
            # Add stability warning text
            if not stable:
                ax.text(0, 2.5, 'UNSTABLE ROCKET!', 
                       ha='center', va='center', fontsize=16, 
                       color='red', fontweight='bold',
                       bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))
            
            # Force canvas to update
            self.launch_canvas.draw()

        # Connect all relevant inputs to update animation
        self.wind_speed_input.valueChanged.connect(update_launch_animation)
        self.wind_direction_input.valueChanged.connect(update_launch_animation)
        self.center_of_mass_input.valueChanged.connect(update_launch_animation)
        self.center_of_pressure_input.valueChanged.connect(update_launch_animation)
        self.rocket_length_input.valueChanged.connect(update_launch_animation)
        
        # Initial animation update
        update_launch_animation()

        self.tabs.addTab(launch_anim_tab, "Launch")

        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

        # Connect fin count, thickness, and body diameter inputs to area update
        self.fin_count_input.textChanged.connect(self.update_area)
        self.fin_thickness_input.textChanged.connect(self.update_area)
        self.body_diameter_input.textChanged.connect(self.update_area)
        self.body_diameter_unit.currentIndexChanged.connect(self.update_area)
        self.fin_length_input.textChanged.connect(self.update_area)
        self.fin_length_unit.currentIndexChanged.connect(self.update_area)
        self.fin_thickness_input.textChanged.connect(self.update_area)
        self.fin_thickness_unit.currentIndexChanged.connect(self.update_area)

        # Dropdown for graph selection
        self.graph_select = QtWidgets.QComboBox()
        self.graph_select.addItems(["Altitude", "Velocity", "Mass", "Acceleration", "Thrust", "Drag"])
        self.graph_select.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        left_layout.addWidget(QtWidgets.QLabel("Select variable to graph:"))
        left_layout.addWidget(self.graph_select)
        self.graph_select.currentIndexChanged.connect(self.update_graph)

        # Multi-variable graphing checkboxes
        self.graph_vars = {
            "Altitude": QtWidgets.QCheckBox("Altitude"),
            "Velocity": QtWidgets.QCheckBox("Velocity"),
            "Mass": QtWidgets.QCheckBox("Mass"),
            "Acceleration": QtWidgets.QCheckBox("Acceleration"),
            "Thrust": QtWidgets.QCheckBox("Thrust"),
            "Drag": QtWidgets.QCheckBox("Drag")
        }
        graph_var_layout = QtWidgets.QHBoxLayout()
        graph_var_layout.addWidget(QtWidgets.QLabel("Variables to graph:"))
        for cb in self.graph_vars.values():
            cb.setChecked(False)
            cb.stateChanged.connect(self.update_graph)
            graph_var_layout.addWidget(cb)
        left_layout.addLayout(graph_var_layout)

        # Connect unit dropdowns to conversion update
        self.mass_unit.currentIndexChanged.connect(lambda: self.update_conversions('mass'))
        self.area_unit.currentIndexChanged.connect(lambda: self.update_conversions('area'))
        self.rho_unit.currentIndexChanged.connect(lambda: self.update_conversions('rho'))
        self.timestep_unit.currentIndexChanged.connect(lambda: self.update_conversions('timestep'))
        self.fin_thickness_unit.currentIndexChanged.connect(lambda: self.update_conversions('fin_thickness'))
        self.fin_length_unit.currentIndexChanged.connect(lambda: self.update_conversions('fin_length'))
        self.body_diameter_unit.currentIndexChanged.connect(lambda: self.update_conversions('body_diameter'))
        self.chute_height_unit.currentIndexChanged.connect(lambda: self.update_conversions('chute_height'))
        self.chute_size_unit.currentIndexChanged.connect(lambda: self.update_conversions('chute_size'))

    def toggle_fbd_animation(self):
        if hasattr(self, '_fbd_timer') and self._fbd_timer is not None:
            if self.anim_pause_button.isChecked():
                self.anim_pause_button.setText('Resume')
                self._fbd_timer.stop()
            else:
                self.anim_pause_button.setText('Pause')
                self._fbd_timer.start(self.anim_speed_slider.value())

    def start_launch_animation(self):
        """Start the rocket launch animation"""
        if self.is_launching:
            return
            
        # Reset physics variables for new launch
        self.launch_velocity = 0.0
        self.launch_altitude = 0.0
        self.launch_x_pos = 0.0
        self.position_history = []  # Reset trail
        self.prev_acceleration = 0.0  # Reset acceleration smoothing
        
        # Reset camera smoothing
        self.smooth_center_x = 0.0
        self.smooth_center_y = 1.5
        self.smooth_zoom = 1.0
        self.smooth_flame_intensity = 0.0
        try:
            m, _, _, _, _, _, _, _, _, _, _, _ = self.get_inputs_for_simulation()
            self.launch_mass = m
        except:
            self.launch_mass = 5.0  # Default mass
            
        self.is_launching = True
        self.launch_time = 0.0
        self.launch_button.setText('Launching...')
        self.launch_button.setEnabled(False)
        self.launch_timer.start(33)  # ~30fps for smoother animation (was 50ms/20fps)

    def update_launch_frame(self):
        """Update each frame of the launch animation using real simulation parameters"""
        ax = self.launch_fig.gca()
        ax.clear()
        
        # Get rocket parameters from Simulation tab
        try:
            m, Cd, A, rho, time_step, fin_thickness, fin_length, body_diameter, chute_height, chute_size, chute_deploy_time, chute_cd = self.get_inputs_for_simulation()
            if m <= 0 or Cd <= 0 or A <= 0 or rho <= 0:
                raise ValueError("Invalid simulation parameters")
        except:
            # Fallback to default values if simulation inputs are invalid
            m, Cd, A, rho = 5.0, 0.7, 0.004560, 1.225
        
        # Get wind and stability parameters
        wind_speed = self.wind_speed_input.value()
        wind_dir_deg = self.wind_direction_input.value()
        margin = self.center_of_pressure_input.value() - self.center_of_mass_input.value()
        stable = margin > 0.05
        color = '#2E8B57' if stable else '#E94F37'
        
        import math
        from scipy.interpolate import interp1d
        
        # Setup thrust curve data (same as simulation.py)
        thrust_data = []
        if hasattr(self, 'thrust_curve_path') and self.thrust_curve_path:
            # Load thrust curve from file
            import csv
            try:
                with open(self.thrust_curve_path, newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        if not row or len(row) < 2:
                            continue
                        try:
                            t_thrust = float(row[0])
                            thrust = float(row[1])
                            thrust_data.append((t_thrust, thrust))
                        except:
                            continue
            except:
                thrust_data = []
        
        if not thrust_data:
            # Default thrust curve
            thrust_data = [
                (0.124, 816.849), (0.375, 796.043), (0.626, 781.861), (0.877, 767.440),
                (1.129, 759.627), (1.380, 735.948), (1.631, 714.454), (1.883, 701.582),
                (2.134, 674.667), (2.385, 656.493), (2.637, 636.076), (2.889, 612.409),
                (3.140, 587.801), (3.391, 567.170), (3.642, 559.971), (3.894, 534.157),
                (4.145, 444.562), (4.396, 280.510), (4.648, 216.702), (4.899, 163.136),
                (5.150, 120.571), (5.402, 86.544), (5.653, 59.990), (5.904, 39.527),
                (6.156, 25.914), (6.408, 0.000)
            ]
        
        times_thrust, thrusts = zip(*thrust_data)
        thrust_func = interp1d(times_thrust, thrusts, bounds_error=False, fill_value=0.0)
        burn_time = times_thrust[-1]
        
        # Current simulation time
        t = self.launch_time
        
        # Get thrust at current time
        current_thrust = float(thrust_func(t)) if t <= burn_time else 0.0
        
        # Physics simulation with real parameters
        g = 9.81
        
        # Wind drift calculation
        drift_factor = wind_speed * 0.01  # Scale for demo
        angle_rad = wind_dir_deg * math.pi / 180
        x_drift_per_sec = drift_factor * math.cos(angle_rad)
        y_drift_per_sec = drift_factor * math.sin(angle_rad)
        
        # Integrate motion using simplified physics with smoothing
        # Use stored velocity and position if available, otherwise initialize
        if not hasattr(self, 'launch_velocity'):
            self.launch_velocity = 0.0
            self.launch_altitude = 0.0
            self.launch_x_pos = 0.0
            self.launch_mass = m
            self.prev_acceleration = 0.0  # For smoothing
            
        dt = 0.025  # Smaller time step for smoother physics (25ms)
        
        # Perform multiple small integration steps for smoother motion
        for _ in range(2):  # 2 steps of 25ms each = 50ms total
            # Calculate drag force: F_drag = 0.5 * rho * v^2 * Cd * A
            drag_force = 0.5 * rho * (self.launch_velocity ** 2) * Cd * A if self.launch_velocity > 0 else 0
            
            # Net force: thrust - drag - weight
            net_force = current_thrust - drag_force - (self.launch_mass * g)
            acceleration = net_force / self.launch_mass
            
            # Add instability if rocket is unstable (but smoother)
            if not stable:
                # Smoother wobble that increases with time and velocity
                wobble_magnitude = 0.3 * math.sin(t * 8) * (1 + t * 0.05)
                acceleration += wobble_magnitude
            
            # Smooth acceleration changes to avoid jerky motion
            acceleration_smoothing = 0.3
            self.prev_acceleration += (acceleration - self.prev_acceleration) * acceleration_smoothing
            
            # Update velocity and position with smoothed acceleration
            self.launch_velocity += self.prev_acceleration * dt
            self.launch_altitude += self.launch_velocity * dt
            
            # Add wind drift (smaller steps for smoother movement)
            self.launch_x_pos += x_drift_per_sec * dt
            
            # Don't go below ground
            if self.launch_altitude < 0:
                self.launch_altitude = 0
                self.launch_velocity = max(0, self.launch_velocity * -0.3)  # Bounce with energy loss
        
        # Use calculated positions
        x_pos = self.launch_x_pos
        y_pos = self.launch_altitude
            
        y_pos = max(0, y_pos)  # Don't go below ground
        
        # Calculate camera following parameters with smoothing
        # Smooth camera movement using exponential moving average
        if not hasattr(self, 'smooth_center_x'):
            self.smooth_center_x = x_pos
            self.smooth_center_y = y_pos
            self.smooth_zoom = 1.0
        
        # Camera smoothing parameters
        camera_smoothing = 0.15  # Lower = smoother, higher = more responsive
        zoom_smoothing = 0.08    # Slower zoom changes for smoother experience
        
        # Smooth camera position
        self.smooth_center_x += (x_pos - self.smooth_center_x) * camera_smoothing
        target_center_y = max(1.5, y_pos)
        self.smooth_center_y += (target_center_y - self.smooth_center_y) * camera_smoothing
        
        # Smooth zoom with altitude
        target_zoom = max(1.0, y_pos * 0.35)  # Reduced zoom rate for smoother feel
        self.smooth_zoom += (target_zoom - self.smooth_zoom) * zoom_smoothing
        
        # Apply smoothed values
        center_x = self.smooth_center_x
        center_y = self.smooth_center_y
        view_width = 2 * self.smooth_zoom
        view_height = 2 * self.smooth_zoom
        
        # Draw trajectory trail using stored positions
        if not hasattr(self, 'position_history'):
            self.position_history = []
        
        # Store current position
        self.position_history.append((x_pos, y_pos))
        
        # Keep only last 20 positions for trail
        if len(self.position_history) > 20:
            self.position_history = self.position_history[-20:]
        
        # Draw trail with fading alpha
        for i in range(len(self.position_history)-1):
            alpha = (i+1) / len(self.position_history) * 0.7
            x1, y1 = self.position_history[i]
            x2, y2 = self.position_history[i+1]
            ax.plot([x1, x2], [y1, y2], 
                   color=color, alpha=alpha, linewidth=2)
        
        # Draw current rocket position
        if y_pos > 0:
            ax.plot([x_pos], [y_pos], color=color, marker='^', markersize=20, 
                   markeredgecolor='black', markeredgewidth=2)
            
            # Add thrust flame based on actual thrust with smoothing
            if not hasattr(self, 'smooth_flame_intensity'):
                self.smooth_flame_intensity = 0.0
                
            max_thrust = max(thrusts) if thrusts else 1000  # Normalize flame size
            target_flame_intensity = current_thrust / max_thrust if max_thrust > 0 else 0
            
            # Smooth flame intensity changes
            flame_smoothing = 0.2
            self.smooth_flame_intensity += (target_flame_intensity - self.smooth_flame_intensity) * flame_smoothing
            
            flame_length = self.smooth_flame_intensity * 0.5  # Scale flame length
            if flame_length > 0.02:  # Only show flame if significant thrust
                # Add slight flame flicker for realism
                flicker = 1.0 + 0.1 * math.sin(t * 25) * self.smooth_flame_intensity
                actual_flame_length = flame_length * flicker
                
                ax.plot([x_pos, x_pos], [y_pos - 0.1, y_pos - 0.1 - actual_flame_length], 
                       color='orange', linewidth=max(1, int(8 * self.smooth_flame_intensity)), alpha=0.8)
                ax.plot([x_pos, x_pos], [y_pos - 0.1, y_pos - 0.1 - actual_flame_length * 0.7], 
                       color='yellow', linewidth=max(1, int(4 * self.smooth_flame_intensity)), alpha=0.9)
        
        # Draw wind arrow
        if wind_speed > 0:
            ax.arrow(-0.5, y_pos + 0.2, x_drift_per_sec * 20, 0, 
                    head_width=0.15, head_length=0.15, 
                    fc='#4682B4', ec='#4682B4', linewidth=3, alpha=0.7)
        
        # Draw ground line and launch pad
        ground_x = [center_x - view_width, center_x + view_width]
        ground_y = [0, 0]
        ax.plot(ground_x, ground_y, color='#8B4513', linewidth=4, label='Ground')
        
        # Launch pad at origin
        ax.plot([0], [0], 's', color='gray', markersize=15, label='Launch Pad')
        
        # Styling with dynamic camera following
        ax.set_xlim(center_x - view_width, center_x + view_width)
        ax.set_ylim(center_y - view_height*0.3, center_y + view_height*0.7)
        ax.set_title(f'Rocket Launch - T+{t:.1f}s - Alt: {y_pos:.1f}m', fontsize=14, fontweight='bold', color='#3C2F1E')
        ax.set_xlabel('Drift (m)', color='#3C2F1E')
        ax.set_ylabel('Altitude (m)', color='#3C2F1E')
        ax.grid(True, alpha=0.3, color='#BCA16A')
        ax.set_facecolor('#FDF6E3')
        
        # Add status text
        if not stable and y_pos > 0:
            ax.text(0, 2.7, 'UNSTABLE!', ha='center', va='center', 
                   fontsize=12, color='red', fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))
        
        if y_pos <= 0 and t > 1:
            ax.text(x_pos, 0.3, 'IMPACT!', ha='center', va='center', 
                   fontsize=14, color='red', fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='orange', alpha=0.9))
        
        self.launch_canvas.draw()
        
        # Update time
        self.launch_time += 0.05
        
        # End animation after 8 seconds or if rocket hits ground
        if self.launch_time > 8 or (y_pos <= 0 and t > 1):
            self.launch_timer.stop()
            self.is_launching = False
            self.launch_button.setText('Launch Again!')
            self.launch_button.setEnabled(True)

    def set_fbd_anim_speed(self):
        if hasattr(self, '_fbd_timer') and self._fbd_timer is not None:
            if not self.anim_pause_button.isChecked():
                # Map slider value (0-100) to speed multiplier (0.5x-5x)
                slider_val = self.anim_speed_slider.value()
                # 0 = 0.5x, 50 = 1x, 100 = 5x
                speed_mult = 0.5 + (slider_val / 100.0) * 4.5
                # Base interval (ms) for 1x speed (e.g., 15ms for smoother animation)
                base_interval = 15
                interval = int(base_interval / speed_mult)
                self._fbd_timer.start(interval)

    def update_conversions(self, field):
        # Only convert value if the user changes the unit, not on load
        if not hasattr(self, '_last_unit_indices'):
            self._last_unit_indices = {}
        unit_defs = {
            'mass':    (self.mass_input, self.mass_unit, ['kg', 'g', 'lb'], [1, 0.001, 0.453592]),
            'area':    (self.area_input, self.area_unit, ['m²', 'cm²', 'ft²'], [1, 0.0001, 0.092903]),
            'rho':     (self.rho_input, self.rho_unit, ['kg/m³', 'g/cm³', 'lb/ft³'], [1, 1000, 16.0185]),
            'timestep':(self.timestep_input, self.timestep_unit, ['s', 'ms'], [1, 0.001]),
            'fin_thickness': (self.fin_thickness_input, self.fin_thickness_unit, ['m', 'mm', 'in'], [1, 0.001, 0.0254]),
            'fin_length':    (self.fin_length_input, self.fin_length_unit, ['m', 'mm', 'in'], [1, 0.001, 0.0254]),
            'body_diameter': (self.body_diameter_input, self.body_diameter_unit, ['m', 'mm', 'in'], [1, 0.001, 0.0254]),
            'chute_height':  (self.chute_height_input, self.chute_height_unit, ['m', 'ft'], [1, 0.3048]),
            'chute_size':    (self.chute_size_input, self.chute_size_unit, ['m²', 'ft²'], [1, 0.092903]),
        }
        if field in unit_defs:
            input_widget, unit_widget, units, factors = unit_defs[field]
            idx = unit_widget.currentIndex()
            last_idx = self._last_unit_indices.get(field, idx)
            if idx != last_idx:
                try:
                    val = float(input_widget.text())
                except Exception:
                    self._last_unit_indices[field] = idx
                    return
                # Convert from last unit to new unit
                val_base = val * factors[last_idx]
                val_new = val_base / factors[idx]
                input_widget.setText(str(val_new))
            self._last_unit_indices[field] = idx

    # Unit selection change
    # self.unit_select.currentIndexChanged.connect(self.update_units)

    def select_thrust_curve(self):
        options = QtWidgets.QFileDialog.Options()
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Thrust Curve CSV",
            "",
            "CSV Files (*.csv);;All Files (*)",
            options=options
        )
        if fileName:
            self.thrust_curve_path = fileName
            self.result_label.setText(f"Selected thrust curve: {fileName}")

    def get_value_in_base_unit(self, value, unit_idx, factors):
        try:
            return float(value) * factors[unit_idx]
        except Exception:
            return 0.0

    def get_inputs_for_simulation(self):
        # Convert all values to base units for simulation
        m = self.get_value_in_base_unit(self.mass_input.text(), self.mass_unit.currentIndex(), [1, 0.001, 0.453592])
        Cd = float(self.cd_input.text()) if self.cd_input.text() else 0.0
        A = self.get_value_in_base_unit(self.area_input.text(), self.area_unit.currentIndex(), [1, 0.0001, 0.092903])
        rho = self.get_value_in_base_unit(self.rho_input.text(), self.rho_unit.currentIndex(), [1, 1000, 16.0185])
        time_step = self.get_value_in_base_unit(self.timestep_input.text(), self.timestep_unit.currentIndex(), [1, 0.001])
        fin_thickness = self.get_value_in_base_unit(self.fin_thickness_input.text(), self.fin_thickness_unit.currentIndex(), [1, 0.001, 0.0254])
        fin_length = self.get_value_in_base_unit(self.fin_length_input.text(), self.fin_length_unit.currentIndex(), [1, 0.001, 0.0254])
        body_diameter = self.get_value_in_base_unit(self.body_diameter_input.text(), self.body_diameter_unit.currentIndex(), [1, 0.001, 0.0254])
        chute_height = self.get_value_in_base_unit(self.chute_height_input.text(), self.chute_height_unit.currentIndex(), [1, 0.3048])
        chute_size = self.get_value_in_base_unit(self.chute_size_input.text(), self.chute_size_unit.currentIndex(), [1, 0.092903])
        try:
            chute_cd = float(self.chute_cd_input.text())
        except Exception:
            chute_cd = 1.5
        chute_deploy_time = random.uniform(0.5, 5.0)
        return m, Cd, A, rho, time_step, fin_thickness, fin_length, body_diameter, chute_height, chute_size, chute_deploy_time, chute_cd

    def start_simulation(self):
        try:
            self.save_inputs()
            m, Cd, A, rho, time_step, fin_thickness, fin_length, body_diameter, chute_height, chute_size, chute_deploy_time, chute_cd = self.get_inputs_for_simulation()
            
            # Input validation
            errors = []
            if m <= 0:
                errors.append("Mass must be positive.")
            if Cd <= 0:
                errors.append("Drag coefficient must be positive.")
            if A <= 0:
                errors.append("Area must be positive.")
            if rho <= 0:
                errors.append("Air density must be positive.")
            if errors:
                self.error_label.setText("; ".join(errors))
                return
            else:
                self.error_label.setText("")

            # Advanced parachute modeling: get both parachute settings
            try:
                chute_height = float(self.chute_height_input.text()) if self.chute_height_input.text() else None
                chute_size = float(self.chute_size_input.text()) if self.chute_size_input.text() else None
            except Exception:
                chute_height = chute_size = None
            # Get time step from UI
            try:
                time_step = float(self.timestep_input.text())
            except Exception:
                time_step = 0.1
            sim_kwargs = {
                'thrust_curve_path': self.thrust_curve_path,
                'chute_height': chute_height,
                'chute_size': chute_size,
                'time_step': time_step,
                'chute_deploy_start': chute_deploy_time,
                'chute_cd': chute_cd
            }
            results = run_simulation(m, Cd, A, rho, **sim_kwargs)
            # Error handling for simulation results
            if isinstance(results, dict) and 'error' in results:
                self.error_label.setText(results['error'])
                return
            if not isinstance(results, list):
                self.error_label.setText("Simulation returned unexpected data.")
                return
            self.display_results(results)
            self.plot_results(results)

        except ValueError:
            self.error_label.setText("Please enter valid numbers.")

    def get_local_speed_of_sound(self):
        try:
            temp_c = float(self.temperature_input.text())
            humidity = float(self.humidity_input.text())
            altitude = float(self.start_altitude_input.text())
            # Calculate speed of sound (approximate, dry air)
            temp_k = temp_c + 273.15
            # Use formula: a = sqrt(gamma * R * T)
            gamma = 1.4
            R = 287.05
            a = (gamma * R * temp_k) ** 0.5
            return a
        except Exception:
            return 343.0

    def display_results(self, results):
        if results:
            # Find max values and their times
            max_alt = max(r['altitude'] for r in results)
            max_alt_idx = next(i for i, r in enumerate(results) if r['altitude'] == max_alt)
            max_alt_time = results[max_alt_idx]['time']

            max_vel = max(r['velocity'] for r in results)
            max_vel_idx = next(i for i, r in enumerate(results) if r['velocity'] == max_vel)
            max_vel_time = results[max_vel_idx]['time']

            max_thrust = max(r['thrust'] for r in results)
            max_thrust_idx = next(i for i, r in enumerate(results) if r['thrust'] == max_thrust)
            max_thrust_time = results[max_thrust_idx]['time']

            max_drag = max(r['drag'] for r in results)
            max_drag_idx = next(i for i, r in enumerate(results) if r['drag'] == max_drag)
            max_drag_time = results[max_drag_idx]['time']

            max_mass = max(r['mass'] for r in results)
            max_mass_idx = next(i for i, r in enumerate(results) if r['mass'] == max_mass)
            max_mass_time = results[max_mass_idx]['time']

            # Mach calculation using local speed of sound
            local_a = self.get_local_speed_of_sound()
            machs = [r['velocity']/local_a if local_a else 0 for r in results]
            max_mach = max(machs)
            max_mach_idx = machs.index(max_mach)
            max_mach_time = results[max_mach_idx]['time']

            vel_unit = 'm/s'
            alt_unit = 'm'
            thrust_unit = 'N'
            drag_unit = 'N'
            mass_unit = 'kg'
            if self.unit_select.currentIndex() == 1:
                max_vel_disp = max_vel * 3.28084
                vel_unit = 'ft/s'
                max_alt_disp = max_alt * 3.28084
                alt_unit = 'ft'
                max_thrust_disp = max_thrust * 0.224809
                thrust_unit = 'lbf'
                max_drag_disp = max_drag * 0.224809
                drag_unit = 'lbf'
                max_mass_disp = max_mass * 2.20462
                mass_unit = 'lb'
            else:
                max_vel_disp = max_vel
                max_alt_disp = max_alt
                max_thrust_disp = max_thrust
                max_drag_disp = max_drag
                max_mass_disp = max_mass

            # Dragstrip-style stat: show all max times in a single line
            dragstrip = (
                f"[Max Times] Apogee: {max_alt_time:.2f}s | Velocity: {max_vel_time:.2f}s | Mach: {max_mach_time:.2f}s | Thrust: {max_thrust_time:.2f}s | Drag: {max_drag_time:.2f}s | Mass: {max_mass_time:.2f}s"
            )

            stats_html = f"""
<div style='width:100vw;height:100vh;display:flex;align-items:center;justify-content:center;background:#181818;'>
    <table style='width:98vw;max-width:900px;height:92vh;min-height:400px;border-collapse:collapse;font-family:PressStart2P,monospace;font-size:1.2vw;letter-spacing:0.04em;background:#111;color:#111;border:6px solid #FFD447;box-shadow:0 0 24px #000;overflow:hidden;text-align:center;'>
        <tr>
            <td style='vertical-align:top; text-align:center; width:50%; padding:2vw 1vw 2vw 2vw; border-right:4px solid #FFD447;'>
                <table style='width:100%;font-size:inherit;border-collapse:collapse;text-align:center;'>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>TIME</td><td style='text-align:center;'>{results[-1]['time']:.2f} S</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>APOGEE</td><td style='text-align:center;'>{max_alt_disp:.2f} {alt_unit.upper()}</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>VELOCITY</td><td style='text-align:center;'>{max_vel_disp:.2f} {vel_unit.upper()}</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>MACH</td><td style='text-align:center;'>{max_mach:.2f}</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>THRUST</td><td style='text-align:center;'>{max_thrust_disp:.2f} {thrust_unit.upper()}</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>DRAG</td><td style='text-align:center;'>{max_drag_disp:.2f} {drag_unit.upper()}</td></tr>
                    <tr><td style='font-weight:bold;text-align:center;'>MASS</td><td style='text-align:center;'>{max_mass_disp:.2f} {mass_unit.upper()}</td></tr>
                </table>
            </td>
            <td style='vertical-align:top; text-align:center; width:50%; padding:2vw 2vw 2vw 1vw;'>
                <table style='width:100%;font-size:inherit;border-collapse:collapse;text-align:center;'>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>MAX APOGEE</td><td style='text-align:center;'>{max_alt_disp:.2f} {alt_unit.upper()} T={max_alt_time:.2f} S</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>MAX VELOCITY</td><td style='text-align:center;'>{max_vel_disp:.2f} {vel_unit.upper()} T={max_vel_time:.2f} S</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>MAX MACH</td><td style='text-align:center;'>{max_mach:.2f} T={max_mach_time:.2f} S</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>MAX THRUST</td><td style='text-align:center;'>{max_thrust_disp:.2f} {thrust_unit.upper()} T={max_thrust_time:.2f} S</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>MAX DRAG</td><td style='text-align:center;'>{max_drag_disp:.2f} {drag_unit.upper()} T={max_drag_time:.2f} S</td></tr>
                    <tr><td style='font-weight:bold;text-align:center;'>MAX MASS</td><td style='text-align:center;'>{max_mass_disp:.2f} {mass_unit.upper()} T={max_mass_time:.2f} S</td></tr>
                </table>
            </td>
        </tr>
    </table>
</div>
"""
            self.result_label.setText(stats_html)
        else:
            self.result_label.setText("No results to display.")

    def plot_results(self, results):
        self._last_results = results
        self.figure.clear()
        if not results:
            return

        ax = self.figure.add_subplot(111)

        # Retro pixel-style graph
        ax.set_facecolor("#FDF6E3")  # lighter beige
        self.figure.patch.set_facecolor("#F8F5E3")  # main beige
        ax.grid(color="#BCA16A", linestyle=':', linewidth=1)  # brown accent
        for spine in ax.spines.values():
            spine.set_color("#E94F37")  # red border for graph
            spine.set_linewidth(2)
        ax.tick_params(axis='both', colors='#3C2F1E', labelsize=10)  # dark brown

        times = [r['time'] for r in results]
        # 8BitDo inspired colors
        colors = ["#E94F37", "#1C77C3", "#FFD447", "#3C2F1E", "#A7C7E7", "#F8F5E3"]
        labels = ["Altitude", "Velocity", "Mass", "Acceleration", "Thrust", "Drag"]
        keys = ["altitude", "velocity", "mass", "acceleration", "thrust", "drag"]
        # Plot selected variable(s), but default to altitude for tooltip
        plotted = False
        tooltip_label = 'Altitude'
        tooltip_values = [r['altitude'] for r in results]
        for i, (label, key) in enumerate(zip(labels, keys)):
            if self.graph_vars[label].isChecked():
                values = [r.get(key, 0) for r in results]
                if label == 'Drag':
                    ax.plot(times, values, label=label, color='#A259F7')  # purple
                else:
                    ax.plot(times, values, label=label, color=colors[i % len(colors)])
                if not plotted:
                    tooltip_label = label
                    tooltip_values = values
                plotted = True
        if not plotted:
            # Default to altitude if nothing selected
            ax.plot(times, tooltip_values, label=tooltip_label, color=colors[0])
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Value')
        ax.legend()
        ax.figure.tight_layout()
        self.canvas.draw()

        # === FBD Animation Overlay ===
        import matplotlib.patches as mpatches
        from matplotlib.lines import Line2D
        from PyQt5.QtCore import QTimer

        # Remove previous FBD artists if any
        if hasattr(self, '_fbd_artists'):
            for artist in self._fbd_artists:
                try:
                    artist.remove()
                except Exception:
                    pass
        self._fbd_artists = []

        # Get time and altitude arrays
        times = [r['time'] for r in results]
        altitudes = [r['altitude'] for r in results]

        # Fixed rocket size in data units (e.g., 2 seconds wide, 10 meters tall)
        rocket_width = 2.0  # seconds (x-axis units)
        rocket_height = 10.0  # meters (y-axis units)

        # Initial position (first point on curve)
        x_pos = times[0]
        y_pos = altitudes[0]

        import matplotlib.image as mpimg
        from matplotlib.offsetbox import OffsetImage, AnnotationBbox
        rocket_img = mpimg.imread(os.path.join(os.path.dirname(__file__), 'Rocket.png'))
        self._rocket_img = rocket_img  # Store for animation
        self._rocket_zoom = 0.08
        imagebox = OffsetImage(rocket_img, zoom=self._rocket_zoom)  # Adjust zoom for desired size
        rocket_artist = AnnotationBbox(
            imagebox,
            (x_pos, y_pos),
            frameon=False,
            pad=0,
            zorder=15
        )
        ax.add_artist(rocket_artist)
        self._rocket_artist = rocket_artist

        # Offset for force arrows (to the right of the rocket)
        arrow_x_offset = rocket_width * 1.5

        # Force arrows (Line2D)
        thrust_line, = ax.plot([x_pos + arrow_x_offset, x_pos + arrow_x_offset], [y_pos, y_pos], color='g', linewidth=3, marker='^', markersize=10, label='Thrust', zorder=12)
        drag_line, = ax.plot([x_pos + arrow_x_offset, x_pos + arrow_x_offset], [y_pos + rocket_height, y_pos + rocket_height], color='r', linewidth=3, marker='v', markersize=10, label='Drag', zorder=12)
        gravity_line, = ax.plot([x_pos + arrow_x_offset, x_pos + arrow_x_offset], [y_pos + rocket_height/2, y_pos + rocket_height/2 - rocket_height*0.08], color='b', linewidth=3, marker='v', markersize=10, label='Gravity', zorder=12)

        self._fbd_artists = [rocket_artist, thrust_line, drag_line, gravity_line]

        # Precompute max values for normalization
        max_thrust = max((r['thrust'] for r in results if r['thrust'] > 0), default=1)
        max_drag = max((r['drag'] for r in results if r['drag'] > 0), default=1)

        # Animation state
        self._fbd_frame = 0
        self._fbd_results = results

        from utils import get_flight_phase
        def fbd_anim_step():
            # Interpolate between data points for smooth animation
            frame = self._fbd_frame
            n_frames = len(self._fbd_results)
            subframe = getattr(self, '_fbd_subframe', 0.0)
            subframes_per_frame = 5
            if frame >= n_frames - 1:
                self._fbd_timer.stop()
                self.phase_progress.setValue(100)
                self.phase_progress.setFormat('LANDED')
                self.phase_progress.setStyleSheet(self.phase_progress.styleSheet() + 'QProgressBar::chunk { background-color: #3C2F1E; color: #FFD447; }')
                return
            result_a = self._fbd_results[frame]
            result_b = self._fbd_results[min(frame+1, n_frames-1)]
            t_a = result_a['time']
            t_b = result_b['time']
            alt_a = result_a['altitude']
            alt_b = result_b['altitude']
            frac = subframe / subframes_per_frame
            x_pos = t_a + (t_b - t_a) * frac
            y_pos = alt_a + (alt_b - alt_a) * frac
            # Interpolate velocity vector for angle
            if frame > 0:
                prev_a = self._fbd_results[frame-1]
                dx_a = t_a - prev_a['time']
                dy_a = alt_a - prev_a['altitude']
                dx_b = t_b - t_a
                dy_b = alt_b - alt_a
                dx = dx_a + (dx_b - dx_a) * frac
                dy = dy_a + (dy_b - dy_a) * frac
                angle = np.degrees(np.arctan2(dy, dx))
            else:
                angle = 90.0
            # Advance subframe
            subframe += 1
            if subframe >= subframes_per_frame:
                subframe = 0
                self._fbd_frame += 1
            self._fbd_subframe = subframe

            # Track apogee and chute deployment
            altitudes = [r['altitude'] for r in self._fbd_results]
            apogee_frame = np.argmax(altitudes)
            chute_frame = next((i for i, r in enumerate(self._fbd_results) if r.get('chute_deployed')), None)

            # Flip rocket at apogee (point down)
            if frame >= apogee_frame and (chute_frame is None or frame < chute_frame):
                angle += 180.0
            # Flip back when chute deploys
            if chute_frame is not None and frame >= chute_frame:
                angle -= 180.0

            # Adjust for image orientation (e.g., subtract 90° if rocket.png points right)
            angle -= 90.0

            # Cache rotated images for performance (round to nearest 5°)
            cache_angle = int(round(angle / 5.0) * 5)
            if cache_angle not in self._rocket_img_cache:
                import scipy.ndimage
                self._rocket_img_cache[cache_angle] = scipy.ndimage.rotate(self._rocket_img, cache_angle, reshape=False, mode='nearest')
            rotated_img = self._rocket_img_cache[cache_angle]
            # Clip image data to valid range for imshow
            if rotated_img.dtype == float:
                rotated_img = np.clip(rotated_img, 0, 1)
            else:
                rotated_img = np.clip(rotated_img, 0, 255)
            rotated_imagebox = OffsetImage(rotated_img, zoom=self._rocket_zoom)
            # Remove previous rocket image
            try:
                self._rocket_artist.remove()
            except Exception:
                pass
            new_rocket_artist = AnnotationBbox(
                rotated_imagebox,
                (x_pos, y_pos),
                frameon=False,
                pad=0,
                zorder=15
            )
            ax.add_artist(new_rocket_artist)
            self._rocket_artist = new_rocket_artist
            # Normalize arrow lengths
            thrust_a = result_a['thrust']
            thrust_b = result_b['thrust']
            drag_a = result_a['drag']
            drag_b = result_b['drag']
            thrust_val = (thrust_a + (thrust_b - thrust_a) * frac) / max_thrust if max_thrust else 0
            drag_val = (drag_a + (drag_b - drag_a) * frac) / max_drag if max_drag else 0
            # Update thrust arrow (upwards from rocket base)
            thrust_line.set_data([x_pos + arrow_x_offset, x_pos + arrow_x_offset], [y_pos, y_pos + thrust_val * 0.2])
            # Update drag arrow (downwards from rocket top)
            drag_line.set_data([x_pos + arrow_x_offset, x_pos + arrow_x_offset], [y_pos + rocket_height, y_pos + rocket_height - drag_val * 0.2])
            # Gravity arrow (fixed length, always down from rocket center)
            gravity_line.set_data([x_pos + arrow_x_offset, x_pos + arrow_x_offset], [y_pos + rocket_height/2, y_pos + rocket_height/2 - rocket_height*0.08])

            # Redraw canvas so rocket and arrows move together
            self.canvas.draw_idle()

            # --- Live statistics update ---
            # Units
            vel_a = result_a['velocity']
            vel_b = result_b['velocity']
            mass_a = result_a['mass']
            mass_b = result_b['mass']
            if self.unit_select.currentIndex() == 1:  # Imperial
                alt_disp = y_pos * 3.28084
                alt_unit = 'ft'
                vel_disp = (vel_a + (vel_b - vel_a) * frac) * 3.28084
                vel_unit = 'ft/s'
                mass_disp = (mass_a + (mass_b - mass_a) * frac) * 2.20462
                mass_unit = 'lb'
                thrust_disp = (thrust_a + (thrust_b - thrust_a) * frac) * 0.224809
                thrust_unit = 'lbf'
                drag_disp = (drag_a + (drag_b - drag_a) * frac) * 0.224809
                drag_unit = 'lbf'
            else:
                alt_disp = y_pos
                alt_unit = 'm'
                vel_disp = vel_a + (vel_b - vel_a) * frac
                vel_unit = 'm/s'
                mass_disp = mass_a + (mass_b - mass_a) * frac
                mass_unit = 'kg'
                thrust_disp = thrust_a + (thrust_b - thrust_a) * frac
                thrust_unit = 'N'
                drag_disp = drag_a + (drag_b - drag_a) * frac
                drag_unit = 'N'
            # Mach number
            try:
                mach = (vel_a + (vel_b - vel_a) * frac) / self.get_local_speed_of_sound()
            except Exception:
                mach = 0.0
            # --- Dragstrip-style max time stat (live) ---
            # Compute max times up to current frame
            results_so_far = self._fbd_results[:frame+1]
            def get_max_time(key, arr=results_so_far):
                max_val = max(r[key] for r in arr)
                idx = next(i for i, r in enumerate(arr) if r[key] == max_val)
                return arr[idx]['time']
            local_a = self.get_local_speed_of_sound()
            machs = [r['velocity']/local_a if local_a else 0 for r in results_so_far]
            max_mach = max(machs)
            max_mach_idx = machs.index(max_mach)
            max_mach_time = results_so_far[max_mach_idx]['time']
            dragstrip = (
                f"[Max Times] Apogee: {get_max_time('altitude'):.2f}s | Velocity: {get_max_time('velocity'):.2f}s | Mach: {max_mach_time:.2f}s | Thrust: {get_max_time('thrust'):.2f}s | Drag: {get_max_time('drag'):.2f}s | Mass: {get_max_time('mass'):.2f}s"
            )
            stats_html = f"""
<div style='width:100vw;height:100vh;display:flex;align-items:center;justify-content:center;background:#181818;'>
    <table style='width:98vw;max-width:900px;height:92vh;min-height:400px;border-collapse:collapse;font-family:PressStart2P,monospace;font-size:1.2vw;letter-spacing:0.04em;background:#111;color:#111;border:6px solid #FFD447;box-shadow:0 0 24px #000;overflow:hidden;text-align:center;'>
        <tr>
            <td style='vertical-align:top; text-align:center; width:50%; padding:2vw 1vw 2vw 2vw; border-right:4px solid #FFD447;'>
                <table style='width:100%;font-size:inherit;border-collapse:collapse;text-align:center;'>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>TIME</td><td style='text-align:center;'>{x_pos:.2f} S</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>ALTITUDE</td><td style='text-align:center;'>{alt_disp:.2f} {alt_unit.upper()}</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>VELOCITY</td><td style='text-align:center;'>{vel_disp:.2f} {vel_unit.upper()}</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>MACH</td><td style='text-align:center;'>{mach:.2f}</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>THRUST</td><td style='text-align:center;'>{thrust_disp:.2f} {thrust_unit.upper()}</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>DRAG</td><td style='text-align:center;'>{drag_disp:.2f} {drag_unit.upper()}</td></tr>
                    <tr><td style='font-weight:bold;text-align:center;'>MASS</td><td style='text-align:center;'>{mass_disp:.2f} {mass_unit.upper()}</td></tr>
                </table>
            </td>
            <td style='vertical-align:top; text-align:center; width:50%; padding:2vw 2vw 2vw 1vw;'>
                <table style='width:100%;font-size:inherit;border-collapse:collapse;text-align:center;'>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>MAX APOGEE</td><td style='text-align:center;'>{get_max_time('altitude'):.2f} {alt_unit.upper()} T={get_max_time('altitude'):.2f} S</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>MAX VELOCITY</td><td style='text-align:center;'>{get_max_time('velocity'):.2f} {vel_unit.upper()} T={get_max_time('velocity'):.2f} S</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>MAX MACH</td><td style='text-align:center;'>{max_mach:.2f} T={max_mach_time:.2f} S</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>MAX THRUST</td><td style='text-align:center;'>{get_max_time('thrust'):.2f} {thrust_unit.upper()} T={get_max_time('thrust'):.2f} S</td></tr>
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>MAX DRAG</td><td style='text-align:center;'>{get_max_time('drag'):.2f} {drag_unit.upper()} T={get_max_time('drag'):.2f} S</td></tr>
                    <tr><td style='font-weight:bold;text-align:center;'>MAX MASS</td><td style='text-align:center;'>{get_max_time('mass'):.2f} {mass_unit.upper()} T={get_max_time('mass'):.2f} S</td></tr>
                </table>
            </td>
        </tr>
    </table>
</div>
"""
            self.result_label.setText(stats_html)

            # --- Progress bar update ---
            percent = int(100 * frame / (len(self._fbd_results)-1))
            phase = get_flight_phase(result_a, result_b).upper()
            self.phase_progress.setValue(percent)
            # Inverse color for phase text inside bar
            if phase in ['LIFTOFF', 'POWERED ASCENT', 'COAST', 'APOGEE', 'DESCENT', 'CHUTE DESCENT']:
                self.phase_progress.setFormat(phase)
                # Red chunk, beige text
                self.phase_progress.setStyleSheet(self.phase_progress.styleSheet() + 'QProgressBar::chunk { background-color: #E94F37; color: #FDF6E3; }')
            elif phase == 'LANDED':
                self.phase_progress.setFormat('LANDED')
                # Brown chunk, yellow text
                self.phase_progress.setStyleSheet(self.phase_progress.styleSheet() + 'QProgressBar::chunk { background-color: #3C2F1E; color: #FFD447; }')

            self.canvas.draw_idle()
            self._fbd_frame += 1

        # Use QTimer for animation
        if hasattr(self, '_fbd_timer') and self._fbd_timer is not None:
            self._fbd_timer.stop()
        self._fbd_timer = QTimer()
        self._fbd_timer.timeout.connect(fbd_anim_step)
        self._fbd_frame = 0
        self._fbd_timer.start(self.anim_speed_slider.value())

        # Add popup tooltip on hover (default to altitude, or first selected variable)
        if not hasattr(self, 'tooltip'):
            self.tooltip = QtWidgets.QToolTip
        def on_motion(event):
            if event.inaxes == ax:
                xdata = event.xdata
                ydata = event.ydata
                if xdata is None or ydata is None:
                    self.canvas.setToolTip("")
                    return
                idx = min(range(len(times)), key=lambda i: abs(times[i] - xdata))
                xval = times[idx]
                yval = tooltip_values[idx]
                # Unit conversion for tooltip
                unit_label = tooltip_label
                unit_value = yval
                unit_time = xval
                if self.unit_select.currentIndex() == 1:  # Imperial
                    if tooltip_label == 'Altitude':
                        unit_value = yval * 3.28084
                        unit_label = 'Altitude (ft)'
                    elif tooltip_label == 'Velocity':
                        unit_value = yval * 3.28084
                        unit_label = 'Velocity (ft/s)'
                    elif tooltip_label == 'Mass':
                        unit_value = yval * 2.20462
                        unit_label = 'Mass (lb)'
                    elif tooltip_label == 'Acceleration':
                        unit_value = yval * 3.28084
                        unit_label = 'Acceleration (ft/s²)'
                    elif tooltip_label == 'Thrust' or tooltip_label == 'Drag':
                        unit_value = yval * 0.224809
                        unit_label = f'{tooltip_label} (lbf)'
                    unit_time = xval  # Time stays in seconds
                else:
                    # Metric
                    if tooltip_label == 'Altitude':
                        unit_label = 'Altitude (m)'
                    elif tooltip_label == 'Velocity':
                        unit_label = 'Velocity (m/s)'
                    elif tooltip_label == 'Mass':
                        unit_label = 'Mass (kg)'
                    elif tooltip_label == 'Acceleration':
                        unit_label = 'Acceleration (m/s²)'
                    elif tooltip_label == 'Thrust' or tooltip_label == 'Drag':
                        unit_label = f'{tooltip_label} (N)'
                tooltip_text = f"Time: {unit_time:.2f} s\n{unit_label}: {unit_value:.2f}"
                QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), tooltip_text, self.canvas)
            else:
                QtWidgets.QToolTip.hideText()
        self.canvas.mpl_connect('motion_notify_event', on_motion)

    def save_inputs(self):
        # Save values as entered, in their selected units
        data = {
            'mass': self.mass_input.text(),
            'mass_unit': self.mass_unit.currentIndex(),
            'cd': self.cd_input.text(),
            'area': self.area_input.text(),
            'area_unit': self.area_unit.currentIndex(),
            'rho': self.rho_input.text(),
            'rho_unit': self.rho_unit.currentIndex(),
            'timestep': self.timestep_input.text(),
            'timestep_unit': self.timestep_unit.currentIndex(),
            'fin_count': self.fin_count_input.text(),
            'fin_thickness': self.fin_thickness_input.text(),
            'fin_thickness_unit': self.fin_thickness_unit.currentIndex(),
            'fin_length': self.fin_length_input.text(),
            'fin_length_unit': self.fin_length_unit.currentIndex(),
            'body_diameter': self.body_diameter_input.text(),
            'body_diameter_unit': self.body_diameter_unit.currentIndex(),
            'chute_height': self.chute_height_input.text(),
            'chute_height_unit': self.chute_height_unit.currentIndex(),
            'chute_size': self.chute_size_input.text(),
            'chute_size_unit': self.chute_size_unit.currentIndex(),
            'graph_select': self.graph_select.currentIndex(),
            'chute_cd': self.chute_cd_input.text(),
            'start_altitude': self.start_altitude_input.text(),
            'temperature': self.temperature_input.text(),
            'humidity': self.humidity_input.text(),
        }
        try:
            with open(os.path.join(os.path.dirname(__file__), 'user_settings.json'), 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def load_inputs(self):
        try:
            with open(os.path.join(os.path.dirname(__file__), 'user_settings.json'), 'r') as f:
                data = json.load(f)
            self.mass_input.setText(str(data.get('mass', '')))
            self.mass_unit.setCurrentIndex(data.get('mass_unit', 0))
            self.cd_input.setText(str(data.get('cd', '')))
            self.area_input.setText(str(data.get('area', '')))
            self.area_unit.setCurrentIndex(data.get('area_unit', 0))
            self.rho_input.setText(str(data.get('rho', '')))
            self.rho_unit.setCurrentIndex(data.get('rho_unit', 0))
            self.timestep_input.setText(str(data.get('timestep', '')))
            self.timestep_unit.setCurrentIndex(data.get('timestep_unit', 0))
            self.fin_count_input.setText(str(data.get('fin_count', '')))
            self.fin_thickness_input.setText(str(data.get('fin_thickness', '')))
            self.fin_thickness_unit.setCurrentIndex(data.get('fin_thickness_unit', 0))
            self.fin_length_input.setText(str(data.get('fin_length', '')))
            self.fin_length_unit.setCurrentIndex(data.get('fin_length_unit', 0))
            self.body_diameter_input.setText(str(data.get('body_diameter', '')))
            self.body_diameter_unit.setCurrentIndex(data.get('body_diameter_unit', 0))
            self.chute_height_input.setText(str(data.get('chute_height', '')))
            self.chute_height_unit.setCurrentIndex(data.get('chute_height_unit', 0))
            self.chute_size_input.setText(str(data.get('chute_size', '')))
            self.chute_size_unit.setCurrentIndex(data.get('chute_size_unit', 0))
            self.chute_cd_input.setText(str(data.get('chute_cd', '1.5')))
            self.start_altitude_input.setText(str(data.get('start_altitude', '0')))
            self.temperature_input.setText(str(data.get('temperature', '15')))
            self.humidity_input.setText(str(data.get('humidity', '50')))
            graph_index = data.get('graph_select', 0)
            self.graph_select.setCurrentIndex(graph_index)
        except Exception:
            pass

    def update_graph(self, *args):
        if hasattr(self, '_last_results') and self._last_results:
            self.plot_results(self._last_results)

    def update_area(self):
        try:
            # Convert all inputs to meters first
            body_diameter_m = self.get_value_in_base_unit(
                self.body_diameter_input.text(), 
                self.body_diameter_unit.currentIndex(), 
                [1, 0.001, 0.0254]
            )
            
            # Area for drag = body tube cross-sectional area
            body_radius_m = body_diameter_m / 2
            body_area = np.pi * body_radius_m**2
            
            total_area = body_area

            # Set the main area input field (in the current unit)
            current_area_unit = self.area_unit.currentIndex()
            factors = [1, 0.0001, 0.092903]
            area_in_current_unit = total_area / factors[current_area_unit]
            
            self.area_input.setText(f"{area_in_current_unit:.6f}")
        except (ValueError, ZeroDivisionError):
            self.area_input.setText("0")

    def update_air_density(self):
        try:
            altitude = float(self.start_altitude_input.text())
            temp_c = float(self.temperature_input.text())
            humidity = float(self.humidity_input.text())
            # Calculate pressure at altitude (barometric formula, simplified)
            P0 = 101325  # Pa at sea level
            T0 = 288.15  # K at sea level
            L = 0.0065   # K/m
            R = 287.05   # J/(kg·K)
            g = 9.80665  # m/s²
            temp_k = temp_c + 273.15
            # Pressure at altitude
            P = P0 * (1 - L * altitude / T0) ** (g / (R * L))
            # Saturation vapor pressure (Tetens formula)
            Es = 6.1078 * 10 ** ((7.5 * temp_c) / (237.3 + temp_c))
            # Actual vapor pressure
            E = Es * humidity / 100.0
            # Calculate air density
            rho = (P - E) / (R * temp_k) + (E / (461.495 * temp_k))
            self.rho_input.setText(f"{rho:.3f}")
        except Exception:
            pass


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(retro_style)


    # Splash screen with reliability checks
    gif_path = os.path.join(os.path.dirname(__file__), 'jarvis.gif')
    splash_movie = QtGui.QMovie(gif_path)
    if not splash_movie.isValid():
        print(f"Could not load splash GIF: {gif_path}")
    splash_label = QtWidgets.QLabel()
    splash_label.setMovie(splash_movie)
    splash_label.setWindowFlags(QtCore.Qt.SplashScreen | QtCore.Qt.FramelessWindowHint)
    splash_label.setAttribute(QtCore.Qt.WA_TranslucentBackground)

    splash_movie.start()
    splash_label.movie = splash_movie  # Prevent garbage collection
    splash_label.show()
    app.processEvents()

    gif_path = os.path.join(os.path.dirname(__file__), 'Jarvis.gif')    # Show splash for 3 seconds, then close and show main window
    def show_main():
        splash_label.close()
        splash_movie.stop()
        window.show()

    window = RocketSimulationUI()
    QtCore.QTimer.singleShot(5000, show_main)

    sys.exit(app.exec_())

def excepthook(type_, value, tb):
    error_text = ''.join(traceback.format_exception(type_, value, tb))
    dlg = CrashImageDialog(r'c:/blah blah blah/JARVIS/5cdd0647707b66d1d76174d4ffa47ce1.jpg', error_text)
    dlg.exec_()
    sys.exit(1)

sys.excepthook = excepthook


