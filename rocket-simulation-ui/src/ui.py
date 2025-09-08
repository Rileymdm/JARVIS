from PyQt5 import QtWidgets, QtGui, QtCore
import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from simulation import run_simulation
# import polars as pl  # Removed because it is unused and causes import error

# === FULL RETRO PIXEL STYLE ===
retro_style = """
QWidget {
    background-color: #e0d7c6;
    font-family: 'Press Start 2P', monospace;
    font-size: 12px;
    color: #2c2c2c;
}

QLineEdit {
    background-color: #f4efe6;
    border: 2px solid #a89f91;
    border-radius: 4px;
    padding: 4px;
    color: #1e1e1e;
}

QPushButton {
    background-color: #d6c9b5;
    border: 2px solid #8b8171;
    border-radius: 6px;
    padding: 6px;
    font-weight: bold;
    color: #2a2a2a;
}

QPushButton:hover {
    background-color: #f0e4cd;
    border: 2px solid #ff6600;
}

QLabel {
    font-weight: bold;
    color: #3a2f1e;
}

QSplitter::handle {
    background-color: #a89f91;
}
"""
# === END RETRO STYLE ===

class RocketSimulationUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Rocket Simulation')

        main_layout = QtWidgets.QHBoxLayout(self)

        # Left panel: Inputs
        left_widget = QtWidgets.QWidget()
        left_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        left_layout = QtWidgets.QVBoxLayout(left_widget)

        form_layout = QtWidgets.QFormLayout()
        self.mass_input = QtWidgets.QLineEdit()
        self.cd_input = QtWidgets.QLineEdit()
        self.area_input = QtWidgets.QLineEdit()
        self.rho_input = QtWidgets.QLineEdit()
        # self.burn_time_input = QtWidgets.QLineEdit()  # Removed: burn time is now derived
        self.fin_count_input = QtWidgets.QLineEdit()
        self.fin_thickness_input = QtWidgets.QLineEdit()
        self.fin_length_input = QtWidgets.QLineEdit()
        self.body_diameter_input = QtWidgets.QLineEdit()
        self.chute_height_input = QtWidgets.QLineEdit()
        self.chute_size_input = QtWidgets.QLineEdit()

        for widget in [self.mass_input, self.cd_input, self.area_input, self.rho_input,
                       self.fin_count_input, self.fin_thickness_input, self.fin_length_input,
                       self.body_diameter_input, self.chute_height_input, self.chute_size_input]:
            widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        form_layout.addRow("Mass (kg):", self.mass_input)
        form_layout.addRow("Drag Coefficient (Cd):", self.cd_input)
        form_layout.addRow("Cross-sectional Area (m²):", self.area_input)
        form_layout.addRow("Air Density (kg/m³):", self.rho_input)
        form_layout.addRow("Fin Count:", self.fin_count_input)
        form_layout.addRow("Fin Thickness (mm):", self.fin_thickness_input)
        form_layout.addRow("Fin Length (mm):", self.fin_length_input)
        form_layout.addRow("Body Diameter (mm):", self.body_diameter_input)
        form_layout.addRow("Chute Deploy Height (m):", self.chute_height_input)
        form_layout.addRow("Chute Size (m²):", self.chute_size_input)

        left_layout.addLayout(form_layout)

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

        # Results label
        self.result_label = QtWidgets.QLabel('Results will be displayed here.')
        self.result_label.setWordWrap(True)
        self.result_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        left_layout.addWidget(self.result_label)

        left_layout.addStretch()

        # Right panel: Graph
        right_widget = QtWidgets.QWidget()
        right_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        right_layout = QtWidgets.QVBoxLayout(right_widget)

        self.figure = plt.Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        right_layout.addWidget(self.canvas)

        # Splitter for resizable panels
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 1000])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

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

    def start_simulation(self):
        try:
            m = float(self.mass_input.text())
            Cd = float(self.cd_input.text())
            A = float(self.area_input.text())
            rho = float(self.rho_input.text())

            # burn_time is now derived from thrust curve in simulation.py
            if self.thrust_curve_path:
                results = run_simulation(m, Cd, A, rho, thrust_curve_path=self.thrust_curve_path)
            else:
                results = run_simulation(m, Cd, A, rho)

            self.display_results(results)
            self.plot_results(results)

        except ValueError:
            self.result_label.setText("Please enter valid numbers.")

    def display_results(self, results):
        if results:
            max_alt = max(r['altitude'] for r in results)
            self.result_label.setText(f"Apogee: {max_alt:.2f} m\nTotal Time: {results[-1]['time']:.2f} s")

    def plot_results(self, results):
        self.figure.clear()
        if not results:
            return

        ax = self.figure.add_subplot(111)

        # Retro pixel-style graph
        ax.set_facecolor("#f4efe6")
        self.figure.patch.set_facecolor("#e0d7c6")
        ax.grid(color="#8b8171", linestyle=':', linewidth=1)
        for spine in ax.spines.values():
            spine.set_color("#8b8171")
        ax.tick_params(axis='both', colors='#2c2c2c', labelsize=10)

        times = [r['time'] for r in results]
        altitudes = [r['altitude'] for r in results]
        velocities = [r['velocity'] for r in results]
        masses = [r['mass'] for r in results] if 'mass' in results[0] else None

        ax.plot(times, altitudes, label='Altitude (m)')
        ax.plot(times, velocities, label='Velocity (m/s)')
        if masses:
            ax.plot(times, masses, label='Mass (kg)')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Value')
        ax.legend()
        ax.figure.tight_layout()
        self.canvas.draw()

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(retro_style)
    app.setFont(QtGui.QFont("Press Start 2P", 12))  # pixel font

    window = RocketSimulationUI()
    window.showMaximized()  # fills the screen
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
