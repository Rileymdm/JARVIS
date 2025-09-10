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
        # ...existing code...
        # DROGUE CHUTE UI (after other input widgets, before adding rows to form_layout)
        self.drogue_enable_checkbox = QtWidgets.QCheckBox("Enable Drogue Chute")
        self.drogue_enable_checkbox.setChecked(False)
        self.drogue_enable_checkbox.stateChanged.connect(self.toggle_drogue_ui)

        self.drogue_size_input = QtWidgets.QLineEdit()
        self.drogue_size_input.setPlaceholderText("Drogue Size")
        self.drogue_size_unit = QtWidgets.QComboBox(); self.drogue_size_unit.addItems(["m²", "ft²"])
        drogue_size_row = QtWidgets.QHBoxLayout(); drogue_size_row.addWidget(self.drogue_size_input); drogue_size_row.addWidget(self.drogue_size_unit)

        self.drogue_cd_input = QtWidgets.QLineEdit()
        self.drogue_cd_input.setPlaceholderText("Drogue Cd")
        self.drogue_cd_input.setText("1.5")

        self.drogue_deploy_mode = QtWidgets.QComboBox(); self.drogue_deploy_mode.addItems(["At Apogee", "At Altitude"])
        self.drogue_deploy_altitude_input = QtWidgets.QLineEdit()
        self.drogue_deploy_altitude_input.setPlaceholderText("Deploy Altitude")
        self.drogue_deploy_altitude_unit = QtWidgets.QComboBox(); self.drogue_deploy_altitude_unit.addItems(["m", "ft"])
        drogue_deploy_altitude_row = QtWidgets.QHBoxLayout(); drogue_deploy_altitude_row.addWidget(self.drogue_deploy_altitude_input); drogue_deploy_altitude_row.addWidget(self.drogue_deploy_altitude_unit)

        # Drogue chute UI container
        self.drogue_widget = QtWidgets.QWidget()
        drogue_layout = QtWidgets.QFormLayout(self.drogue_widget)
        drogue_layout.addRow("Drogue Size:", drogue_size_row)
        drogue_layout.addRow("Drogue Cd:", self.drogue_cd_input)
        drogue_layout.addRow("Drogue Deploy Mode:", self.drogue_deploy_mode)
        drogue_layout.addRow("Drogue Deploy Altitude:", drogue_deploy_altitude_row)
        self.drogue_widget.setVisible(False)
        self.init_ui()
        self.load_inputs()  # Load inputs on startup

    def toggle_drogue_ui(self, state):
        self.drogue_widget.setVisible(state == QtCore.Qt.Checked)
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_inputs()  # Load inputs on startup


    def init_ui(self):
        self.setWindowTitle('Rocket Simulation')
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
    # Drogue chute UI
    form_layout.addRow(self.drogue_enable_checkbox)
    form_layout.addRow(self.drogue_widget)
    def toggle_drogue_ui(self, state):
        self.drogue_widget.setVisible(state == QtCore.Qt.Checked)

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

    def set_fbd_anim_speed(self):
        if hasattr(self, '_fbd_timer') and self._fbd_timer is not None:
            if not self.anim_pause_button.isChecked():
                self._fbd_timer.start(self.anim_speed_slider.value())

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

        # Rocket and force arrow parameters
        rocket_width = 10
        rocket_height = 100
        nose_height = 10
        fin_height = 3
        fin_width = 3

        # Get time and altitude arrays
        times = [r['time'] for r in results]
        altitudes = [r['altitude'] for r in results]

        # Initial position (first point on curve)
        x_pos = times[0]
        y_pos = altitudes[0]

        # Body
        body = mpatches.Rectangle((x_pos - rocket_width/2, y_pos), rocket_width, rocket_height, color='#E94F37', zorder=10)
        ax.add_patch(body)
        # Nose cone (triangle)
        nose = mpatches.Polygon([[x_pos - rocket_width/2, y_pos + rocket_height],
                                 [x_pos + rocket_width/2, y_pos + rocket_height],
                                 [x_pos, y_pos + rocket_height + nose_height]],
                                 closed=True, color='#FFD447', zorder=11)
        ax.add_patch(nose)
        # Left fin
        left_fin = mpatches.Polygon([[x_pos - rocket_width/2, y_pos],
                                     [x_pos - rocket_width/2 - fin_width, y_pos - fin_height],
                                     [x_pos - rocket_width/2, y_pos + 0.03]],
                                     closed=True, color='#3C2F1E', zorder=9)
        ax.add_patch(left_fin)
        # Right fin
        right_fin = mpatches.Polygon([[x_pos + rocket_width/2, y_pos],
                                      [x_pos + rocket_width/2 + fin_width, y_pos - fin_height],
                                      [x_pos + rocket_width/2, y_pos + 0.03]],
                                      closed=True, color='#3C2F1E', zorder=9)
        ax.add_patch(right_fin)

        # Offset for force arrows (to the right of the rocket)
        arrow_x_offset = rocket_width * 1.5

        # Force arrows (Line2D)
        thrust_line, = ax.plot([x_pos + arrow_x_offset, x_pos + arrow_x_offset], [y_pos, y_pos], color='g', linewidth=3, marker='^', markersize=10, label='Thrust', zorder=12)
        drag_line, = ax.plot([x_pos + arrow_x_offset, x_pos + arrow_x_offset], [y_pos + rocket_height, y_pos + rocket_height], color='r', linewidth=3, marker='v', markersize=10, label='Drag', zorder=12)
        gravity_line, = ax.plot([x_pos + arrow_x_offset, x_pos + arrow_x_offset], [y_pos + rocket_height/2, y_pos + rocket_height/2 - 0.08], color='b', linewidth=3, marker='v', markersize=10, label='Gravity', zorder=12)

        self._fbd_artists = [body, nose, left_fin, right_fin, thrust_line, drag_line, gravity_line]

        # Precompute max values for normalization
        max_thrust = max((r['thrust'] for r in results if r['thrust'] > 0), default=1)
        max_drag = max((r['drag'] for r in results if r['drag'] > 0), default=1)

        # Animation state
        self._fbd_frame = 0
        self._fbd_results = results

        from utils import get_flight_phase
        def fbd_anim_step():
            frame = self._fbd_frame
            if frame >= len(self._fbd_results):
                self._fbd_timer.stop()
                # Set progress bar to 100% and "Landed" at end
                self.phase_progress.setValue(100)
                self.phase_progress.setFormat('LANDED')
                self.phase_progress.setStyleSheet(self.phase_progress.styleSheet() + 'QProgressBar::chunk { background-color: #3C2F1E; color: #FFD447; }')
                return
            result = self._fbd_results[frame]
            prev_result = self._fbd_results[frame-1] if frame > 0 else None
            x_pos = result['time']
            y_pos = result['altitude']
            # Move rocket
            body.set_xy((x_pos - rocket_width/2, y_pos))
            nose.set_xy([[x_pos - rocket_width/2, y_pos + rocket_height],
                         [x_pos + rocket_width/2, y_pos + rocket_height],
                         [x_pos, y_pos + rocket_height + nose_height]])
            left_fin.set_xy([[x_pos - rocket_width/2, y_pos],
                             [x_pos - rocket_width/2 - fin_width, y_pos - fin_height],
                             [x_pos - rocket_width/2, y_pos + 0.03]])
            right_fin.set_xy([[x_pos + rocket_width/2, y_pos],
                              [x_pos + rocket_width/2 + fin_width, y_pos - fin_height],
                              [x_pos + rocket_width/2, y_pos + 0.03]])
            # Normalize arrow lengths
            thrust_val = result['thrust'] / max_thrust if max_thrust else 0
            drag_val = result['drag'] / max_drag if max_drag else 0
            # Update thrust arrow (upwards from rocket base)
            thrust_line.set_data([x_pos + arrow_x_offset, x_pos + arrow_x_offset], [y_pos, y_pos + thrust_val * 0.2])
            # Update drag arrow (downwards from rocket top)
            drag_line.set_data([x_pos + arrow_x_offset, x_pos + arrow_x_offset], [y_pos + rocket_height, y_pos + rocket_height - drag_val * 0.2])
            # Gravity arrow (fixed length, always down from rocket center)
            gravity_line.set_data([x_pos + arrow_x_offset, x_pos + arrow_x_offset], [y_pos + rocket_height/2, y_pos + rocket_height/2 - 0.08])

            # --- Live statistics update ---
            # Units
            if self.unit_select.currentIndex() == 1:  # Imperial
                alt_disp = result['altitude'] * 3.28084
                alt_unit = 'ft'
                vel_disp = result['velocity'] * 3.28084
                vel_unit = 'ft/s'
                mass_disp = result['mass'] * 2.20462
                mass_unit = 'lb'
                thrust_disp = result['thrust'] * 0.224809
                thrust_unit = 'lbf'
                drag_disp = result['drag'] * 0.224809
                drag_unit = 'lbf'
            else:
                alt_disp = result['altitude']
                alt_unit = 'm'
                vel_disp = result['velocity']
                vel_unit = 'm/s'
                mass_disp = result['mass']
                mass_unit = 'kg'
                thrust_disp = result['thrust']
                thrust_unit = 'N'
                drag_disp = result['drag']
                drag_unit = 'N'
            # Mach number
            try:
                mach = result['velocity'] / self.get_local_speed_of_sound()
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
                    <tr style="border-bottom:3px solid #FFD447;"><td style='font-weight:bold;text-align:center;'>TIME</td><td style='text-align:center;'>{result['time']:.2f} S</td></tr>
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
            phase = get_flight_phase(result, prev_result).upper()
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
    window = RocketSimulationUI()
    window.show()
    sys.exit(app.exec_())

def excepthook(type_, value, tb):
    error_text = ''.join(traceback.format_exception(type_, value, tb))
    dlg = CrashImageDialog(r'c:/blah blah blah/JARVIS/5cdd0647707b66d1d76174d4ffa47ce1.jpg', error_text)
    dlg.exec_()
    sys.exit(1)

sys.excepthook = excepthook


