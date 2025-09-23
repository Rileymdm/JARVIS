from PyQt5 import QtWidgets, QtGui, QtCore
import sys
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from simulation import run_simulation
import os
import json
import numpy as np
import random
import traceback
import csv
from scipy.interpolate import interp1d
import matplotlib.patches as mpatches

# === FULL RETRO PIXEL STYLE ===
# NOTE: Removed use of a global app stylesheet to avoid forcing retro styles over other themes.
# Theme application is now handled per-widget via apply_theme().
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
        
        # Initialize theme system
        self.current_theme = "retro"  # Default to retro theme
        self.themes = self.setup_themes()
        
        # Set user settings file path
        self.user_settings_file = os.path.join(os.path.dirname(__file__), 'user_settings.json')
        
        # Load saved theme preference
        self.current_theme = self.load_theme_preference()
        
        # Set window and taskbar icon (use .ico for best Windows compatibility)
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), 'JARVIS.ico')))
        self.init_ui()
        self.load_inputs()  # Load inputs on startup
        self.apply_theme(self.current_theme)  # Apply initial theme
        self.showMaximized()

    # ---- THEME-AWARE STYLING HELPERS ----
    def get_plot_style(self):
        """Return a dict of matplotlib styling values based on the current theme."""
        theme = self.themes[self.current_theme]
        if self.current_theme == "retro":
            return {
                'fig_face': theme['plot_bg'],            # #F8F5E3
                'ax_face': theme['colors']['secondary_bg'],  # #FDF6E3
                'grid_color': theme['colors']['accent'],     # #BCA16A
                'grid_alpha': 0.3,
                'spine_color': theme['colors']['button_bg'], # #E94F37
                'spine_lw': 2.0,
                'tick_color': theme['colors']['primary_text'],
                'label_color': theme['colors']['primary_text'],
                'title_color': theme['colors']['primary_text'],
                'legend_face': theme['colors']['secondary_bg'],
                'legend_edge': theme['colors']['accent']
            }
        else:  # professional
            return {
                'fig_face': theme['plot_bg'],             # #1A252F
                'ax_face': theme['colors']['secondary_bg'],  # #34495E
                'grid_color': theme['colors']['primary_bg'], # #2C3E50
                'grid_alpha': 0.35,
                'spine_color': theme['colors']['accent'],    # #00D4FF
                'spine_lw': 1.2,
                'tick_color': theme['colors']['primary_text'], # #ECF0F1
                'label_color': theme['colors']['primary_text'],
                'title_color': theme['colors']['primary_text'],
                'legend_face': '#2C3E50',
                'legend_edge': theme['colors']['accent']
            }

    def style_axes(self, ax):
        """Apply theme-aware styling to a matplotlib Axes."""
        style = self.get_plot_style()
        # Figure and axes backgrounds
        if ax.figure is not None:
            ax.figure.patch.set_facecolor(style['fig_face'])
        ax.set_facecolor(style['ax_face'])
        # Grid
        ax.grid(True, alpha=style['grid_alpha'], color=style['grid_color'], linestyle=':')
        # Spines
        for spine in ax.spines.values():
            spine.set_color(style['spine_color'])
            spine.set_linewidth(style['spine_lw'])
        # Ticks and labels
        ax.tick_params(axis='both', colors=style['tick_color'])
        ax.xaxis.label.set_color(style['label_color'])
        ax.yaxis.label.set_color(style['label_color'])
        ax.title.set_color(style['title_color'])
        # Legend (if exists)
        leg = ax.get_legend()
        if leg is not None:
            leg.get_frame().set_facecolor(style['legend_face'])
            leg.get_frame().set_edgecolor(style['legend_edge'])
            for text in leg.get_texts():
                text.set_color(style['tick_color'])

    def style_toolbar(self):
        """Apply theme-aware styling to the matplotlib navigation toolbar."""
        if not hasattr(self, 'toolbar'):
            return
        theme = self.themes[self.current_theme]
        if self.current_theme == "retro":
            ss = f"""
                QWidget {{
                    background-color: {theme['colors']['primary_bg']};
                    border: 2px solid {theme['colors']['accent']};
                    color: {theme['colors']['primary_text']};
                    font-family: 'Press Start 2P', monospace;
                    font-size: 12px;
                }}
            """
        else:
            # Subtle, dark toolbar with accent border
            ss = f"""
                QWidget {{
                    background-color: {theme['colors']['primary_bg']};
                    border: 1px solid {theme['colors']['accent']};
                    color: {theme['colors']['primary_text']};
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 12px;
                }}
            """
        # Apply the stylesheet to the toolbar
        self.toolbar.setStyleSheet(ss)

    # ---- Launch angle recommendation helpers ----
    def compute_recommended_launch_angle_deg(self):
        """Recommend a small tilt (±0–5°) into the wind. 0° when calm.
        Simple heuristic: angle = clamp(k * wind_speed, 0..5), sign into-wind.
        We interpret positive angle as tilting toward wind direction's coming-from azimuth to reduce drift.
        """
        try:
            ws = float(self.wind_speed_input.value())  # m/s
            wd = float(self.wind_direction_input.value())  # degrees, 0..359
        except Exception:
            return 0.0
        # Map speed to degrees with a gentle slope. Example: 0 deg at 0 m/s, 5 deg at >= 10 m/s
        k = 5.0 / 10.0
        mag = max(0.0, min(5.0, k * ws))
        # Sign convention: positive angle means tilt to the right in our XY view. We can map wind direction to a left/right component.
        # For simplicity in 2D, use cosine to decide sign: wind from 90° (from +X) -> tilt negative (left), from 270° -> tilt positive (right)
        # Compute sign = -cos(wd) so that wind from +X (90°) gives negative tilt; from -X (270°) gives positive.
        sign = -math.cos(math.radians(wd))
        # Normalize sign to -1, 0, 1 threshold to avoid tiny noise
        s = 1.0 if sign > 0.2 else (-1.0 if sign < -0.2 else 0.0)
        return mag * s

    def update_recommended_launch_angle_label(self):
        rec = self.compute_recommended_launch_angle_deg()
        ws = self.wind_speed_input.value()
        if abs(rec) < 0.05:
            txt = f"Recommended: 0.0° (calm)"
        else:
            txt = f"Recommended: {rec:+.1f}° (wind {ws:.1f} m/s)"
        if hasattr(self, 'recommended_angle_label'):
            self.recommended_angle_label.setText(txt)

    def apply_recommended_launch_angle(self):
        rec = self.compute_recommended_launch_angle_deg()
        # Bound to control range just in case
        rec = max(self.launch_angle_input.minimum(), min(self.launch_angle_input.maximum(), rec))
        self.launch_angle_input.setValue(rec)

    def restyle_all_plots(self):
        """Restyle any existing figures/axes and redraw canvases."""
        # Main results figure
        if hasattr(self, 'figure') and hasattr(self, 'canvas'):
            for ax in self.figure.axes:
                self.style_axes(ax)
            self.canvas.draw_idle()
        # Launch/animation figure
        if hasattr(self, 'launch_fig') and hasattr(self, 'launch_canvas'):
            for ax in self.launch_fig.axes:
                self.style_axes(ax)
            self.launch_canvas.draw_idle()

    def setup_themes(self):
        """Define all available themes for the application"""
        return {
            "retro": {
                "name": "JARVIS Retro",
                "description": "Classic 8BitDo retro gaming aesthetic",
                "colors": {
                    "primary_bg": "#F8F5E3",
                    "secondary_bg": "#FDF6E3", 
                    "accent": "#BCA16A",
                    "primary_text": "#3C2F1E",
                    "button_bg": "#E94F37",
                    "button_hover": "#FFD447",
                    "button_text": "#F8F5E3",
                    "success": "#2E8B57",
                    "warning": "#FF6347",
                    "info": "#4169E1"
                },
                "telemetry": {
                    "bg": "#F8F5E3",
                    "border": "#BCA16A",
                    "header_bg": "#3C2F1E",
                    "header_text": "#FFD447",
                    "gauge_bg": "#FFFFFF",
                    "gauge_text": "#3C2F1E",
                    "status_active": "#32CD32",
                    "status_inactive": "#C0C0C0"
                },
                "plot_bg": "#F8F5E3"
            },
            "professional": {
                "name": "Aerospace Professional",
                "description": "Mission control center dark theme",
                "colors": {
                    "primary_bg": "#2C3E50",
                    "secondary_bg": "#34495E",
                    "accent": "#00D4FF",
                    "primary_text": "#ECF0F1",
                    "button_bg": "#E94F37",
                    "button_hover": "#FF6B35",
                    "button_text": "#FFFFFF",
                    "success": "#00FF41",
                    "warning": "#FF6B35",
                    "info": "#0099FF"
                },
                "telemetry": {
                    "bg": "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #2C3E50, stop: 1 #34495E)",
                    "border": "#1A252F",
                    "header_bg": "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #1A252F, stop: 1 #0F1419)",
                    "header_text": "#00D4FF",
                    "gauge_bg": "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 rgba(26, 37, 47, 0.9), stop: 1 rgba(15, 20, 25, 0.9))",
                    "gauge_text": "#ECF0F1",
                    "status_active": "#00FF41",
                    "status_inactive": "#555555"
                },
                "plot_bg": "#1A252F"
            }
        }

    def apply_theme(self, theme_name):
        """Apply the selected theme to the entire application"""
        if theme_name not in self.themes:
            return
            
        self.current_theme = theme_name
        theme = self.themes[theme_name]
        
        # Apply base application style
        if theme_name == "retro":
            self.apply_retro_theme(theme)
        elif theme_name == "professional":
            self.apply_professional_theme(theme)
            
        # Update telemetry dashboard if it exists
        if hasattr(self, 'altitude_display'):
            self.update_telemetry_theme()
            
        # Update plot backgrounds
        if hasattr(self, 'canvas'):
            self.canvas.figure.patch.set_facecolor(theme["plot_bg"])
            self.restyle_all_plots()
        if hasattr(self, 'launch_canvas'):
            self.launch_canvas.figure.patch.set_facecolor(theme["plot_bg"])
            self.restyle_all_plots()

        # Update toolbar styling
        self.style_toolbar()
        
        # Update force diagram styling
        if hasattr(self, 'force_widget'):
            self.setup_force_widget_styling()
            self.setup_force_header()
        if hasattr(self, 'force_canvas'):
            self.force_canvas.figure.patch.set_facecolor(theme["plot_bg"])
            self.update_force_diagram()
            
        # Save theme preference
        self.save_theme_preference()

    def apply_retro_theme(self, theme):
        """Apply the retro JARVIS theme"""
        retro_style = f"""
            QWidget {{
                background-color: {theme['colors']['primary_bg']};
                font-family: 'Press Start 2P', monospace;
                font-size: 12px;
                color: {theme['colors']['primary_text']};
            }}

            QLineEdit {{
                background-color: {theme['colors']['secondary_bg']};
                border: 2px solid {theme['colors']['accent']};
                border-radius: 4px;
                padding: 4px;
                color: {theme['colors']['primary_text']};
            }}

            QPushButton {{
                background-color: {theme['colors']['button_bg']};
                border: 2px solid {theme['colors']['primary_text']};
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
                color: {theme['colors']['button_text']};
            }}

            QPushButton:hover {{
                background-color: {theme['colors']['button_hover']};
                border: 2px solid {theme['colors']['button_bg']};
                color: {theme['colors']['primary_text']};
            }}

            QLabel {{
                font-weight: bold;
                color: {theme['colors']['primary_text']};
            }}

            QSplitter::handle {{
                background-color: {theme['colors']['accent']};
            }}
            
            QTabWidget::pane {{
                border: 2px solid {theme['colors']['accent']};
                border-radius: 4px;
            }}
            
            QTabBar::tab {{
                background-color: {theme['colors']['secondary_bg']};
                border: 2px solid {theme['colors']['accent']};
                padding: 8px 16px;
                margin: 2px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {theme['colors']['button_bg']};
                color: {theme['colors']['button_text']};
            }}
            
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {theme['colors']['accent']};
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 6px;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                background-color: {theme['colors']['primary_bg']};
            }}
            
            QComboBox {{
                background-color: {theme['colors']['secondary_bg']};
                border: 2px solid {theme['colors']['accent']};
                border-radius: 4px;
                padding: 4px;
            }}
        """
        self.setStyleSheet(retro_style)

    def apply_professional_theme(self, theme):
        """Apply the professional aerospace theme"""
        professional_style = f"""
            QWidget {{
                background: {theme['telemetry']['bg']};
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                color: {theme['colors']['primary_text']};
            }}

            QLineEdit {{
                background-color: {theme['colors']['secondary_bg']};
                border: 1px solid {theme['colors']['accent']};
                border-radius: 4px;
                padding: 6px;
                color: {theme['colors']['primary_text']};
            }}

            QPushButton {{
                background-color: {theme['colors']['button_bg']};
                border: 1px solid {theme['colors']['accent']};
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                color: {theme['colors']['button_text']};
            }}

            QPushButton:hover {{
                background-color: {theme['colors']['button_hover']};
                border: 1px solid {theme['colors']['button_bg']};
            }}

            QLabel {{
                color: {theme['colors']['primary_text']};
                font-weight: normal;
            }}

            QSplitter::handle {{
                background-color: {theme['colors']['accent']};
            }}
            
            QTabWidget::pane {{
                border: 1px solid {theme['colors']['accent']};
                border-radius: 4px;
                background: {theme['colors']['primary_bg']};
            }}
            
            QTabBar::tab {{
                background: {theme['colors']['secondary_bg']};
                border: 1px solid {theme['colors']['accent']};
                padding: 8px 16px;
                margin: 1px;
                color: {theme['colors']['primary_text']};
            }}
            
            QTabBar::tab:selected {{
                background-color: {theme['colors']['accent']};
                color: {theme['colors']['primary_bg']};
            }}
            
            QGroupBox {{
                font-weight: bold;
                color: {theme['colors']['accent']};
                border: 1px solid {theme['colors']['accent']};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                background: rgba(26, 37, 47, 0.8);
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px 0 6px;
                background-color: rgba(26, 37, 47, 1);
                border: 1px solid {theme['colors']['accent']};
                border-radius: 2px;
            }}
            
            QComboBox {{
                background-color: {theme['colors']['secondary_bg']};
                border: 1px solid {theme['colors']['accent']};
                border-radius: 4px;
                padding: 6px;
                color: {theme['colors']['primary_text']};
            }}
            
            QComboBox::drop-down {{
                border: none;
            }}
            
            QComboBox::down-arrow {{
                border: none;
                color: {theme['colors']['accent']};
            }}
        """
        self.setStyleSheet(professional_style)

    def on_theme_changed(self):
        """Handle theme selection change"""
        selected_theme = self.theme_select.currentData()
        if selected_theme and selected_theme != self.current_theme:
            self.apply_theme(selected_theme)
            self.update_theme_preview()

    def update_theme_preview(self):
        """Update the theme preview display"""
        if not hasattr(self, 'theme_preview'):
            return
            
        theme = self.themes[self.current_theme]
        if self.current_theme == "retro":
            preview_style = f"""
                QLabel {{
                    background-color: {theme['colors']['primary_bg']};
                    border: 2px solid {theme['colors']['accent']};
                    border-radius: 4px;
                    color: {theme['colors']['primary_text']};
                    font-weight: bold;
                    padding: 8px;
                    qproperty-alignment: AlignCenter;
                }}
            """
            self.theme_preview.setText("🚀 RETRO JARVIS THEME")
        else:
            preview_style = f"""
                QLabel {{
                    background: {theme['telemetry']['bg']};
                    border: 1px solid {theme['telemetry']['border']};
                    border-radius: 4px;
                    color: {theme['colors']['accent']};
                    font-weight: bold;
                    padding: 8px;
                    qproperty-alignment: AlignCenter;
                    font-family: 'Consolas', 'Monaco', monospace;
                }}
            """
            self.theme_preview.setText("🛰️ AEROSPACE PROFESSIONAL")
            
        self.theme_preview.setStyleSheet(preview_style)

    def save_theme_preference(self):
        """Save the current theme preference to user settings"""
        if hasattr(self, 'user_settings_file'):
            try:
                with open(self.user_settings_file, 'r') as f:
                    settings = json.load(f)
            except:
                settings = {}
            
            settings['theme'] = self.current_theme
            
            try:
                with open(self.user_settings_file, 'w') as f:
                    json.dump(settings, f, indent=2)
            except:
                pass

    def load_theme_preference(self):
        """Load the saved theme preference"""
        if hasattr(self, 'user_settings_file'):
            try:
                with open(self.user_settings_file, 'r') as f:
                    settings = json.load(f)
                    return settings.get('theme', 'retro')
            except:
                pass
        return 'retro'

    def update_telemetry_theme(self):
        """Update telemetry dashboard styling based on current theme"""
        if not hasattr(self, 'telemetry_widget'):
            return
        # Stop previous timer if any
        try:
            if hasattr(self, 'telemetry_timer') and self.telemetry_timer is not None:
                self.telemetry_timer.stop()
                self.telemetry_timer.deleteLater()
        except Exception:
            pass
        self.telemetry_timer = None

        # Clear telemetry widget layout and rebuild with current theme
        layout = self.telemetry_widget.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(self.telemetry_widget)

        def clear_layout(lay):
            while lay.count():
                item = lay.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
                else:
                    sub = item.layout()
                    if sub is not None:
                        clear_layout(sub)
        clear_layout(layout)

        # Reapply container/header styling then recreate dashboard
        self.setup_telemetry_widget_styling()
        self.setup_telemetry_header()
        self.create_telemetry_dashboard(layout)
        self.setup_status_display_styling()

    def setup_telemetry_widget_styling(self):
        """Apply theme-aware styling to telemetry widget"""
        theme = self.themes[self.current_theme]
        if self.current_theme == "retro":
            style = f"""
                QWidget {{
                    background-color: {theme['colors']['primary_bg']};
                    border: 2px solid {theme['colors']['accent']};
                    border-radius: 8px;
                    margin: 2px;
                }}
            """
        else:
            style = f"""
                QWidget {{
                    background: {theme['telemetry']['bg']};
                    border: 1px solid {theme['telemetry']['border']};
                    border-radius: 8px;
                    margin: 2px;
                }}
            """
        self.telemetry_widget.setStyleSheet(style)

    def setup_telemetry_header(self):
        """Apply theme-aware styling to telemetry header"""
        theme = self.themes[self.current_theme]
        if self.current_theme == "retro":
            self.telemetry_header.setText("")  # Remove header text
            style = "QLabel { background: transparent; margin: 0px; padding: 0px; }"
        else:
            self.telemetry_header.setText("")  # Remove header text
            style = "QLabel { background: transparent; margin: 0px; padding: 0px; }"
        self.telemetry_header.setStyleSheet(style)
        self.telemetry_header.setMaximumHeight(0)  # Hide completely

    def setup_force_widget_styling(self):
        """Setup theme-aware styling for force widget"""
        theme = self.themes[self.current_theme]
        if self.current_theme == "retro":
            style = f"""
                QWidget {{
                    background-color: {theme['colors']['primary_bg']};
                    border: 2px solid {theme['colors']['accent']};
                    border-radius: 8px;
                    margin: 2px;
                }}
            """
        else:
            style = f"""
                QWidget {{
                    background: {theme['telemetry']['bg']};
                    border: 1px solid {theme['telemetry']['border']};
                    border-radius: 4px;
                    margin: 2px;
                }}
            """
        self.force_widget.setStyleSheet(style)

    def setup_force_header(self):
        """Setup theme-aware force diagram header"""
        theme = self.themes[self.current_theme]
        if self.current_theme == "retro":
            self.force_header.setText("")  # Remove header text
            style = "QLabel { background: transparent; margin: 0px; padding: 0px; }"
        else:
            self.force_header.setText("")  # Remove header text
            style = "QLabel { background: transparent; margin: 0px; padding: 0px; }"
        self.force_header.setStyleSheet(style)
        self.force_header.setMaximumHeight(0)  # Hide completely

    def setup_trajectory_widget_styling(self):
        """Apply theme-aware styling to trajectory widget"""
        theme = self.themes[self.current_theme]
        if self.current_theme == "retro":
            style = f"""
                QWidget {{
                    background-color: {theme['colors']['primary_bg']};
                    border: 2px solid {theme['colors']['accent']};
                    border-radius: 8px;
                    margin: 2px;
                }}
            """
        else:
            style = f"""
                QWidget {{
                    background: {theme['telemetry']['bg']};
                    border: 1px solid {theme['telemetry']['border']};
                    border-radius: 8px;
                    margin: 2px;
                }}
            """
        self.trajectory_widget.setStyleSheet(style)

    def setup_trajectory_header(self):
        """Apply theme-aware styling to trajectory header"""
        theme = self.themes[self.current_theme]
        if self.current_theme == "retro":
            self.trajectory_header.setText("📈 TRAJECTORY VISUALIZATION")
            self.trajectory_header.setAlignment(QtCore.Qt.AlignCenter)
            style = f"""
                QLabel {{
                    background-color: {theme['colors']['primary_text']};
                    color: {theme['colors']['button_hover']};
                    font-size: 16px;
                    font-weight: bold;
                    padding: 8px;
                    border: 2px solid {theme['colors']['accent']};
                    border-radius: 6px;
                    margin-bottom: 8px;
                }}
            """
        else:
            self.trajectory_header.setText("FLIGHT PATH VISUALIZATION")
            self.trajectory_header.setAlignment(QtCore.Qt.AlignCenter)
            style = f"""
                QLabel {{
                    background: {theme['telemetry']['header_bg']};
                    color: {theme['telemetry']['header_text']};
                    font-size: 14px;
                    font-weight: bold;
                    font-family: 'Consolas', 'Monaco', monospace;
                    padding: 12px;
                    border: 1px solid {theme['colors']['secondary_bg']};
                    border-radius: 4px;
                    margin-bottom: 8px;
                    letter-spacing: 2px;
                }}
            """
        self.trajectory_header.setStyleSheet(style)

    def setup_plot_background(self):
        """Set plot background based on current theme"""
        theme = self.themes[self.current_theme]
        self.launch_fig.patch.set_facecolor(theme["plot_bg"])

    def setup_canvas_styling(self):
        """Apply theme-aware styling to canvas"""
        theme = self.themes[self.current_theme]
        if self.current_theme == "retro":
            style = f"""
                QWidget {{
                    border: 1px solid {theme['colors']['accent']};
                    border-radius: 4px;
                }}
            """
        else:
            style = f"""
                QWidget {{
                    border: 1px solid {theme['colors']['secondary_bg']};
                    border-radius: 4px;
                    background-color: {theme['plot_bg']};
                }}
            """
        self.launch_canvas.setStyleSheet(style)

    def setup_group_styling(self, group):
        """Apply theme-aware styling to group boxes"""
        theme = self.themes[self.current_theme]
        if self.current_theme == "retro":
            group.setStyleSheet(f"""
                QGroupBox {{
                    font-size: 12px;
                    font-weight: bold;
                    color: {theme['colors']['primary_text']};
                    border: 2px solid {theme['colors']['accent']};
                    border-radius: 6px;
                    margin-top: 6px;
                    padding-top: 6px;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 8px;
                    padding: 0 4px 0 4px;
                    background-color: {theme['colors']['primary_bg']};
                }}
            """)
        else:
            group.setStyleSheet(f"""
                QGroupBox {{
                    font-size: 11px;
                    font-weight: bold;
                    font-family: 'Consolas', 'Monaco', monospace;
                    color: {theme['colors']['accent']};
                    border: 1px solid {theme['colors']['secondary_bg']};
                    border-radius: 4px;
                    margin-top: 8px;
                    padding-top: 8px;
                    background: rgba(26, 37, 47, 0.8);
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 12px;
                    padding: 0 6px 0 6px;
                    background-color: rgba(26, 37, 47, 1);
                    border: 1px solid {theme['colors']['secondary_bg']};
                    border-radius: 2px;
                }}
            """)

    def setup_status_display_styling(self):
        """Apply theme-aware styling to status displays"""
        theme = self.themes[self.current_theme]
        if self.current_theme == "retro":
            phase_style = f"""
                QLabel {{
                    background-color: {theme['colors']['primary_text']};
                    color: {theme['colors']['button_hover']};
                    font-size: 14px;
                    font-weight: bold;
                    padding: 8px 12px;
                    border: 2px solid {theme['colors']['accent']};
                    border-radius: 6px;
                }}
            """
            time_style = f"""
                QLabel {{
                    background-color: {theme['colors']['success']};
                    color: {theme['colors']['primary_bg']};
                    font-size: 14px;
                    font-weight: bold;
                    padding: 8px 12px;
                    border: 2px solid {theme['colors']['accent']};
                    border-radius: 6px;
                }}
            """
        else:
            phase_style = f"""
                QLabel {{
                    background: {theme['telemetry']['header_bg']};
                    color: {theme['colors']['success']};
                    font-size: 13px;
                    font-weight: bold;
                    font-family: 'Consolas', 'Monaco', monospace;
                    padding: 10px 16px;
                    border: 1px solid {theme['colors']['secondary_bg']};
                    border-radius: 3px;
                    letter-spacing: 1px;
                }}
            """
            time_style = f"""
                QLabel {{
                    background: {theme['telemetry']['header_bg']};
                    color: {theme['colors']['accent']};
                    font-size: 13px;
                    font-weight: bold;
                    font-family: 'Consolas', 'Monaco', monospace;
                    padding: 10px 16px;
                    border: 1px solid {theme['colors']['secondary_bg']};
                    border-radius: 3px;
                    letter-spacing: 1px;
                }}
            """
        
        self.phase_display.setStyleSheet(phase_style)
        self.time_display.setStyleSheet(time_style)

    def create_retro_gauge(self, label, value, unit, color):
        """Create a retro-themed gauge display"""
        widget = QtWidgets.QFrame()
        widget.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        theme = self.themes["retro"]
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['colors']['secondary_bg']};
                border: 2px solid {color};
                border-radius: 8px;
                margin: 2px;
            }}
            QLabel {{
                background-color: transparent;
                color: {theme['colors']['primary_text']};
            }}
        """)
        
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        
        # Label
        label_widget = QtWidgets.QLabel(label)
        label_widget.setAlignment(QtCore.Qt.AlignCenter)
        label_widget.setStyleSheet(f"""
            font-size: 10px; 
            color: {color}; 
            font-weight: bold;
            text-transform: uppercase;
        """)
        
        # Value
        value_text = f"{value} {unit}" if unit else value
        value_widget = QtWidgets.QLabel(value_text)
        value_widget.setAlignment(QtCore.Qt.AlignCenter)
        value_widget.setStyleSheet(f"""
            font-size: 16px; 
            font-weight: bold; 
            color: {theme['colors']['primary_text']};
            padding: 4px;
        """)
        
        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        
        # Store references
        widget.value_label = value_widget
        widget.unit = unit
        widget.gauge_color = color
        
        return widget

    def create_retro_indicator(self, label, icon):
        """Create a retro-themed status indicator"""
        widget = QtWidgets.QFrame()
        theme = self.themes["retro"]
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['colors']['secondary_bg']};
                border: 1px solid {theme['colors']['accent']};
                border-radius: 6px;
                padding: 4px;
            }}
        """)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        
        # Icon and status
        status_layout = QtWidgets.QHBoxLayout()
        
        icon_label = QtWidgets.QLabel(icon)
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 14px;")
        
        circle = QtWidgets.QLabel("●")
        circle.setAlignment(QtCore.Qt.AlignCenter)
        circle.setStyleSheet(f"color: {theme['telemetry']['status_inactive']}; font-size: 12px;")
        
        status_layout.addWidget(icon_label)
        status_layout.addWidget(circle)
        
        # Label
        text = QtWidgets.QLabel(label)
        text.setAlignment(QtCore.Qt.AlignCenter)
        text.setStyleSheet(f"""
            font-size: 9px; 
            color: {theme['colors']['primary_text']}; 
            font-weight: bold;
        """)
        
        layout.addLayout(status_layout)
        layout.addWidget(text)
        
        # Store references
        widget.status_circle = circle
        widget.is_active = False
        
        return widget


    def init_ui(self):
        self.setWindowTitle('JARVIS')
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # No margins on main window
        main_layout.setSpacing(0)  # No spacing
        self.tabs = QtWidgets.QTabWidget()
        main_panel = QtWidgets.QWidget()
        main_panel_layout = QtWidgets.QHBoxLayout(main_panel)
        main_panel_layout.setContentsMargins(0, 0, 0, 0)  # No margins on main panel

        # Left panel: Inputs
        left_widget = QtWidgets.QWidget()
        left_widget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        left_widget.setMaximumWidth(320)  # Limit left panel width
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)  # Minimal margins
        left_layout.setSpacing(4)  # Tight spacing

        form_layout = QtWidgets.QFormLayout()
        form_layout.setVerticalSpacing(2)  # Tight vertical spacing
        form_layout.setHorizontalSpacing(4)  # Minimal horizontal spacing
        form_layout.setContentsMargins(0, 0, 0, 0)  # No margins
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

        # Set size policies and styling for better spacing
        input_style = """
            QLineEdit {
                padding: 6px 8px;
                font-size: 11px;
                border: 1px solid #BCA16A;
                border-radius: 4px;
                background-color: #FDF6E3;
                color: #3C2F1E;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #E94F37;
                background-color: #FFFFFF;
            }
        """
        
        for widget in [self.mass_input, self.cd_input, self.area_input, self.rho_input,
                   self.timestep_input,
                   self.fin_count_input, self.fin_thickness_input, self.fin_length_input, self.body_diameter_input,
                   self.chute_height_input, self.chute_size_input]:
            widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            widget.setStyleSheet(input_style)

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
        self.chute_cd_input.setStyleSheet(input_style)  # Apply same styling
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
        self.select_thrust_button = QtWidgets.QPushButton('Select Thrust Curve File')
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
        right_layout.setContentsMargins(2, 2, 2, 2)  # Minimal margins
        right_layout.setSpacing(2)  # Tight spacing

        # --- Graph/Spreadsheet Tabs ---
        self.graph_tab_widget = QtWidgets.QTabWidget()
        # Graph tab
        graph_tab = QtWidgets.QWidget()
        graph_layout = QtWidgets.QVBoxLayout(graph_tab)
        graph_layout.setContentsMargins(0, 0, 0, 0)  # No margins for max space
        graph_layout.setSpacing(0)  # No spacing
        self.figure = plt.Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        graph_layout.addWidget(self.canvas)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.style_toolbar()
        graph_layout.addWidget(self.toolbar)
        self.graph_tab_widget.addTab(graph_tab, "Graph")

        # Spreadsheet tab
        spreadsheet_tab = QtWidgets.QWidget()
        spreadsheet_layout = QtWidgets.QVBoxLayout(spreadsheet_tab)
        self.spreadsheet_table = QtWidgets.QTableWidget()
        self.spreadsheet_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        spreadsheet_layout.addWidget(self.spreadsheet_table)
        self.graph_tab_widget.addTab(spreadsheet_tab, "Spreadsheet Data")

        right_layout.addWidget(self.graph_tab_widget)

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
        splitter.setSizes([300, 1200])  # Give much more space to visualization
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)  # 4:1 ratio for visualization

        main_panel_layout.addWidget(splitter)
        main_panel_layout.setContentsMargins(2, 2, 2, 2)  # Minimal margins
        self.tabs.addTab(main_panel, "Simulation")

        # Settings tab for units and theme
        settings_widget = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout(settings_widget)
        
        # Theme selection section
        theme_group = QtWidgets.QGroupBox("Interface Theme")
        theme_layout = QtWidgets.QVBoxLayout(theme_group)
        
        self.theme_select = QtWidgets.QComboBox()
        for theme_key, theme_data in self.themes.items():
            self.theme_select.addItem(f"{theme_data['name']} - {theme_data['description']}", theme_key)
        
        # Set current theme as selected
        for i in range(self.theme_select.count()):
            if self.theme_select.itemData(i) == self.current_theme:
                self.theme_select.setCurrentIndex(i)
                break
        
        # Connect to theme change handler using lambda to pass the theme name
        self.theme_select.currentIndexChanged.connect(lambda index: self.on_theme_changed(self.theme_select.itemData(index)))
        
        theme_layout.addWidget(QtWidgets.QLabel("Select Interface Theme:"))
        theme_layout.addWidget(self.theme_select)
        
        # Theme preview
        self.theme_preview = QtWidgets.QLabel()
        self.theme_preview.setFixedHeight(60)
        self.theme_preview.setStyleSheet("border: 1px solid #ccc; border-radius: 4px;")
        self.update_theme_preview()
        theme_layout.addWidget(QtWidgets.QLabel("Preview:"))
        theme_layout.addWidget(self.theme_preview)
        
        settings_layout.addWidget(theme_group)
        
        # Units selection section
        units_group = QtWidgets.QGroupBox("Measurement Units")
        units_layout = QtWidgets.QVBoxLayout(units_group)
        
        self.unit_select = QtWidgets.QComboBox()
        self.unit_select.addItems(["Metric (m, kg)", "Imperial (ft, lb)"])
        units_layout.addWidget(QtWidgets.QLabel("Select Unit System:"))
        units_layout.addWidget(self.unit_select)
        
        settings_layout.addWidget(units_group)
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

        self.launch_angle_input = QtWidgets.QDoubleSpinBox()
        self.launch_angle_input.setRange(-45.0, 45.0)
        self.launch_angle_input.setSingleStep(0.5)
        self.launch_angle_input.setValue(0.0)
        self.launch_angle_input.setSuffix("°")
        self.launch_angle_input.setToolTip("Launch angle as deviation from vertical (0° = vertical). Safety recommendation: keep within ±5° unless site RSO allows more.")
        stability_layout.addRow("Launch Angle (± from vertical):", self.launch_angle_input)

        # Recommended launch angle (±0–5°) based on wind — tilt slightly into the wind
        rec_row = QtWidgets.QHBoxLayout()
        self.recommended_angle_label = QtWidgets.QLabel("Recommended: 0.0° (calm)")
        self.recommended_angle_label.setToolTip("Computed from wind speed and direction; bounded to ±5°")
        self.apply_recommended_btn = QtWidgets.QPushButton("Apply")
        self.apply_recommended_btn.setToolTip("Set launch angle to the recommended value")
        self.apply_recommended_btn.clicked.connect(self.apply_recommended_launch_angle)
        rec_row.addWidget(self.recommended_angle_label)
        rec_row.addStretch(1)
        rec_row.addWidget(self.apply_recommended_btn)
        stability_layout.addRow("Recommendation:", rec_row)

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

        # Update recommended angle label initially and when wind/angle changes
        def _update_rec_label():
            self.update_recommended_launch_angle_label()
        self.wind_speed_input.valueChanged.connect(_update_rec_label)
        self.wind_direction_input.valueChanged.connect(_update_rec_label)
        self.launch_angle_input.valueChanged.connect(_update_rec_label)
        # Initialize recommendation display
        QtCore.QTimer.singleShot(0, self.update_recommended_launch_angle_label)

        launch_anim_layout.addWidget(stability_group)

        # Create horizontal layout for trajectory and telemetry
        trajectory_telemetry_layout = QtWidgets.QHBoxLayout()
        
        # Rocket launch animation canvas (left side)
        trajectory_widget = QtWidgets.QWidget()
        self.trajectory_widget = trajectory_widget  # Store reference for theme updates
        self.setup_trajectory_widget_styling()
        
        trajectory_layout = QtWidgets.QVBoxLayout(trajectory_widget)
        trajectory_layout.setContentsMargins(16, 16, 16, 16)
        trajectory_layout.setSpacing(12)
        
        # Professional header for trajectory
        traj_header = QtWidgets.QLabel()
        self.trajectory_header = traj_header  # Store reference for theme updates
        self.setup_trajectory_header()
        trajectory_layout.addWidget(traj_header)
        
        self.launch_fig = plt.Figure(figsize=(6, 5))
        self.setup_plot_background()
        self.launch_canvas = FigureCanvas(self.launch_fig)
        self.launch_canvas.setMinimumSize(300, 250)
        self.setup_canvas_styling()
        trajectory_layout.addWidget(self.launch_canvas)
        trajectory_telemetry_layout.addWidget(trajectory_widget)

        # Real-time Telemetry Dashboard (right side)
        telemetry_widget = QtWidgets.QWidget()
        self.telemetry_widget = telemetry_widget  # Store reference for theme updates
        self.setup_telemetry_widget_styling()
        
        telemetry_layout = QtWidgets.QVBoxLayout(telemetry_widget)
        telemetry_layout.setContentsMargins(8, 8, 8, 8)
        telemetry_layout.setSpacing(6)
        
        # Professional header with theme-aware styling
        header_label = QtWidgets.QLabel()
        self.telemetry_header = header_label  # Store reference for theme updates
        self.setup_telemetry_header()
        telemetry_layout.addWidget(header_label)
        
        # Create telemetry display panels
        self.create_telemetry_dashboard(telemetry_layout)
        trajectory_telemetry_layout.addWidget(telemetry_widget)
        
        # Force Diagram Widget (third panel)
        force_widget = QtWidgets.QWidget()
        self.force_widget = force_widget  # Store reference for theme updates
        self.setup_force_widget_styling()
        
        force_layout = QtWidgets.QVBoxLayout(force_widget)
        force_layout.setContentsMargins(8, 8, 8, 8)
        force_layout.setSpacing(6)
        
        # Force diagram header
        force_header = QtWidgets.QLabel()
        self.force_header = force_header
        self.setup_force_header()
        force_layout.addWidget(force_header)
        
        # Create force diagram display
        self.create_force_diagram(force_layout)
        trajectory_telemetry_layout.addWidget(force_widget)
        
        # Set size ratios (trajectory:telemetry:forces = 2:1:1)
        trajectory_telemetry_layout.setStretchFactor(trajectory_widget, 2)
        trajectory_telemetry_layout.setStretchFactor(telemetry_widget, 1)
        trajectory_telemetry_layout.setStretchFactor(force_widget, 1)
        
        launch_anim_layout.addLayout(trajectory_telemetry_layout)

        # Retro styled Launch/Stop buttons
        buttons_row = QtWidgets.QHBoxLayout()
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

        self.stop_button = QtWidgets.QPushButton('Stop')
        self.stop_button.setStyleSheet('''
            QPushButton {
                background-color: #3C2F1E;
                border: 2px solid #BCA16A;
                border-radius: 10px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 18px;
                color: #FFD447;
                margin-top: 16px;
            }
            QPushButton:hover {
                background-color: #BCA16A;
                color: #3C2F1E;
                border: 2px solid #3C2F1E;
            }
        ''')
        self.stop_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.stop_button.clicked.connect(self.stop_launch_animation)

        buttons_row.addWidget(self.launch_button)
        buttons_row.addWidget(self.stop_button)
        launch_anim_layout.addLayout(buttons_row)

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
            
            # Load thrust curve data using shared method
            times_thrust, thrusts, thrust_func, burn_time = self.load_thrust_curve_data()
            
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
            
            ax.set_xlabel('Drift (m)')
            ax.set_ylabel('Altitude (m)')
            # Apply theme-aware styling
            self.style_axes(ax)
            ax.legend(loc='upper left')
            
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
        self.launch_angle_input.valueChanged.connect(update_launch_animation)
        
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

    def load_thrust_curve_data(self):
        """Load thrust curve data from file or use default. Returns (times, thrusts, thrust_func, burn_time)"""
        thrust_data = []
        if hasattr(self, 'thrust_curve_path') and self.thrust_curve_path:
            path = self.thrust_curve_path
            _, ext = os.path.splitext(path.lower())
            try:
                if ext == '.csv':
                    thrust_data = self.parse_csv_thrust(path)
                elif ext in ('.eng', '.rasp'):
                    thrust_data = self.parse_rasp_eng_thrust(path)
                else:
                    # Try CSV as a fallback
                    thrust_data = self.parse_csv_thrust(path)
            except Exception:
                thrust_data = []
        
        if not thrust_data or len(thrust_data) < 2:
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
        
        # Deduplicate exact or near-equal times to ensure strictly increasing for interp1d
        deduped = []
        last_t = None
        for t, y in sorted(thrust_data, key=lambda p: p[0]):
            if last_t is None or t > last_t + 1e-9:
                deduped.append((t, y))
                last_t = t
            else:
                # Replace previous with latest value at same timestamp
                deduped[-1] = (t, y)
                last_t = t
        times_thrust, thrusts = zip(*deduped)
        thrust_func = interp1d(times_thrust, thrusts, bounds_error=False, fill_value=0.0)
        burn_time = times_thrust[-1]
        return times_thrust, thrusts, thrust_func, burn_time

    def parse_csv_thrust(self, path):
        data = []
        with open(path, 'r', newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                # skip commented/header lines starting with a non-numeric token
                first = row[0].strip()
                if not first:
                    continue
                if first.startswith('#') or first.startswith(';'):
                    continue
                try:
                    t = float(first)
                    thrust = float(row[1]) if len(row) > 1 else None
                    if thrust is None:
                        continue
                    data.append((t, thrust))
                except Exception:
                    # header line like "time,thrust" -> skip
                    continue
        # ensure sorted and unique by time (keep last occurrence on duplicates)
        data.sort(key=lambda x: x[0])
        deduped = []
        last_t = None
        for t, y in data:
            if last_t is None or t > last_t + 1e-9:
                deduped.append((t, y))
                last_t = t
            else:
                deduped[-1] = (t, y)
                last_t = t
        return deduped

    def parse_rasp_eng_thrust(self, path):
        """Parse a simple RASP/ENG motor file. We read the first motor block's time/thrust pairs.
        Lines starting with ';' or '#' are comments. The first non-comment line is header. Following lines until a blank/comment are time thrust pairs."""
        data = []
        with open(path, 'r') as f:
            lines = f.readlines()
        # strip whitespace
        lines = [ln.strip() for ln in lines]
        # skip initial comments
        i = 0
        while i < len(lines) and (not lines[i] or lines[i].startswith(';') or lines[i].startswith('#')):
            i += 1
        if i >= len(lines):
            return data
        # header line (ignored for now)
        i += 1
        # read pairs
        while i < len(lines):
            ln = lines[i]
            if not ln or ln.startswith(';') or ln.startswith('#'):
                # stop at blank/comment -> end of first motor block
                break
            parts = ln.split()
            if len(parts) < 2:
                break
            try:
                t = float(parts[0])
                thrust = float(parts[1])
                data.append((t, thrust))
            except Exception:
                # stop on parse failure for safety
                break
            i += 1
        data.sort(key=lambda x: x[0])
        # dedup
        deduped = []
        last_t = None
        for t, y in data:
            if last_t is None or t > last_t + 1e-9:
                deduped.append((t, y))
                last_t = t
            else:
                deduped[-1] = (t, y)
                last_t = t
        return deduped

    def create_telemetry_dashboard(self, layout):
        """Create a professional mission control-style telemetry dashboard"""
        
        # Initialize telemetry data storage
        self.telemetry_data = {
            'altitude': 0.0,
            'velocity': 0.0,
            'acceleration': 0.0,
            'thrust': 0.0,
            'mass': 0.0,
            'g_force': 0.0,
            'drag_force': 0.0,
            'mach_number': 0.0,
            'flight_phase': 'Standby',
            'time': 0.0
        }
        
        theme = self.themes[self.current_theme]
        
        # Create main scoreboard container with theme-aware styling
        scoreboard = QtWidgets.QFrame()
        if self.current_theme == "retro":
            scoreboard.setStyleSheet(f"""
                QFrame {{
                    background: {theme['colors']['secondary_bg']};
                    border: 2px solid {theme['colors']['accent']};
                    border-radius: 8px;
                    margin: 4px;
                }}
            """)
        else:
            scoreboard.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                        stop: 0 #1A252F, stop: 1 #0F1419);
                    border: 2px solid {theme['colors']['accent']};
                    border-radius: 8px;
                    margin: 4px;
                }}
            """)
        
        scoreboard_layout = QtWidgets.QVBoxLayout(scoreboard)
        scoreboard_layout.setContentsMargins(12, 8, 12, 8)
        scoreboard_layout.setSpacing(6)
        
        # Mission status header
        status_header = QtWidgets.QLabel("MISSION TELEMETRY")
        status_header.setAlignment(QtCore.Qt.AlignCenter)
        status_header.setStyleSheet("""
            QLabel {
                color: #00D4FF;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 2px;
                padding: 4px 0px;
                border-bottom: 1px solid #00D4FF;
                margin-bottom: 8px;
            }
        """)
        scoreboard_layout.addWidget(status_header)
        
        # Primary metrics in a grid
        metrics_grid = QtWidgets.QGridLayout()
        metrics_grid.setSpacing(8)
        
        # Create metric displays (theme-aware)
        if self.current_theme == "retro":
            self.altitude_display = self.create_retro_gauge("ALT", "0.0", "m", theme['colors']['success'])
            self.velocity_display = self.create_retro_gauge("VEL", "0.0", "m/s", theme['colors']['info'])
            self.acceleration_display = self.create_retro_gauge("ACCEL", "0.0", "m/s²", theme['colors']['warning'])
            self.g_force_display = self.create_retro_gauge("G-FORCE", "0.0", "G", "#FF3333")
        else:
            self.altitude_display = self.create_professional_metric("ALT", "0.0", "m", "#00FF41")
            self.velocity_display = self.create_professional_metric("VEL", "0.0", "m/s", "#0099FF") 
            self.acceleration_display = self.create_professional_metric("ACCEL", "0.0", "m/s²", "#FF6B35")
            self.g_force_display = self.create_professional_metric("G-FORCE", "0.0", "G", "#FF3333")
        
        metrics_grid.addWidget(self.altitude_display, 0, 0)
        metrics_grid.addWidget(self.velocity_display, 0, 1)
        metrics_grid.addWidget(self.acceleration_display, 1, 0)
        metrics_grid.addWidget(self.g_force_display, 1, 1)
        
        scoreboard_layout.addLayout(metrics_grid)
        
        # Secondary metrics row
        secondary_grid = QtWidgets.QGridLayout()
        secondary_grid.setSpacing(8)
        
        if self.current_theme == "retro":
            self.thrust_display = self.create_retro_gauge("THRUST", "0.0", "N", theme['colors']['success'])
            self.mass_display = self.create_retro_gauge("MASS", "0.0", "kg", theme['colors']['primary_text']) 
            self.drag_display = self.create_retro_gauge("DRAG", "0.0", "N", theme['colors']['warning'])
            self.mach_display = self.create_retro_gauge("MACH", "0.0", "", "#FF4500")
        else:
            self.thrust_display = self.create_professional_metric("THRUST", "0.0", "N", "#32CD32")
            self.mass_display = self.create_professional_metric("MASS", "0.0", "kg", "#FFFFFF")
            self.drag_display = self.create_professional_metric("DRAG", "0.0", "N", "#FFA500") 
            self.mach_display = self.create_professional_metric("MACH", "0.0", "", "#FF69B4")
        
        secondary_grid.addWidget(self.thrust_display, 0, 0)
        secondary_grid.addWidget(self.mass_display, 0, 1)
        secondary_grid.addWidget(self.drag_display, 1, 0)
        secondary_grid.addWidget(self.mach_display, 1, 1)
        
        scoreboard_layout.addLayout(secondary_grid)
        
        # Mission status indicators at bottom
        status_row = QtWidgets.QHBoxLayout()
        
        # Flight phase display
        self.phase_display = QtWidgets.QLabel("STANDBY")
        self.phase_display.setAlignment(QtCore.Qt.AlignCenter)
        self.phase_display.setStyleSheet("""
            QLabel {
                background: rgba(0, 212, 255, 0.1);
                color: #00D4FF;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border: 1px solid #00D4FF;
                border-radius: 4px;
                letter-spacing: 1px;
            }
        """)
        
        # Mission time display
        self.time_display = QtWidgets.QLabel("T+ 000.0")
        self.time_display.setAlignment(QtCore.Qt.AlignCenter)
        self.time_display.setStyleSheet("""
            QLabel {
                background: rgba(0, 255, 65, 0.1);
                color: #00FF41;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border: 1px solid #00FF41;
                border-radius: 4px;
                letter-spacing: 1px;
            }
        """)
        
        status_row.addWidget(self.phase_display)
        status_row.addWidget(self.time_display)
        scoreboard_layout.addLayout(status_row)
        # Ensure status labels adopt current theme styles
        self.setup_status_display_styling()
        
        # Add the complete scoreboard to main layout
        layout.addWidget(scoreboard)
        
        # Status indicators for various systems
        indicators_layout = QtWidgets.QHBoxLayout()
        
        if self.current_theme == "retro":
            self.stable_status = self.create_retro_indicator("STABLE", "⚖️")
        else:
            self.stable_status = self.create_professional_indicator("STABLE")
        
        indicators_layout.addWidget(self.stable_status)
        layout.addLayout(indicators_layout)
        
        # Initialize telemetry update timer
        self.telemetry_timer = QtCore.QTimer()
        self.telemetry_timer.timeout.connect(self.update_telemetry_displays)
        self.telemetry_timer.timeout.connect(self.update_force_diagram)
        self.telemetry_timer.start(100)  # Update every 100ms for smooth display

    def create_professional_metric(self, label, value, unit, color):
        """Create a professional mission control-style metric display"""
        widget = QtWidgets.QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(52, 73, 94, 0.8), 
                    stop: 1 rgba(44, 62, 80, 0.9));
                border: 1px solid {color};
                border-radius: 6px;
                margin: 2px;
            }}
        """)
        
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        
        # Label
        label_widget = QtWidgets.QLabel(label)
        label_widget.setAlignment(QtCore.Qt.AlignCenter)
        label_widget.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 8px;
                font-weight: bold;
                letter-spacing: 1px;
                margin-bottom: 2px;
            }}
        """)
        layout.addWidget(label_widget)
        
        # Value with unit
        value_widget = QtWidgets.QLabel(f"{value} {unit}")
        value_widget.setAlignment(QtCore.Qt.AlignCenter)
        value_widget.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                font-weight: bold;
                background: rgba(0, 0, 0, 0.3);
                padding: 4px;
                border-radius: 3px;
            }
        """)
        layout.addWidget(value_widget)
        
        # Store reference for updates
        widget.value_label = value_widget
        return widget

    def create_force_diagram(self, layout):
        """Create the real-time force vector diagram display"""
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        import matplotlib.patches as patches
        
        # Create matplotlib figure for force diagram
        self.force_fig = Figure(figsize=(4, 6), dpi=80)
        self.force_fig.patch.set_facecolor(self.themes[self.current_theme]["plot_bg"])
        self.force_canvas = FigureCanvas(self.force_fig)
        self.force_canvas.setMinimumSize(200, 300)
        
        # Force diagram visualization
        self.force_ax = self.force_fig.add_subplot(111)
        self.force_ax.set_xlim(-2, 2)
        self.force_ax.set_ylim(-1, 4)
        self.force_ax.set_aspect('equal')
        self.force_ax.axis('off')
        
        # Initialize force vectors
        self.thrust_vector = None
        self.drag_vector = None  
        self.weight_vector = None
        self.net_vector = None
        
        layout.addWidget(self.force_canvas)
        
        # Force magnitude displays
        forces_grid = QtWidgets.QGridLayout()
        forces_grid.setSpacing(8)
        
        # Create force value displays with theme-aware styling
        self.thrust_force_display = self.create_force_display("THRUST", "0.0", "N", "#00FF00")
        self.drag_force_display = self.create_force_display("DRAG", "0.0", "N", "#FF4444") 
        self.chute_drag_display = self.create_force_display("CHUTE", "0.0", "N", "#FF00FF")
        self.weight_force_display = self.create_force_display("WEIGHT", "0.0", "N", "#FFAA00")
        self.net_force_display = self.create_force_display("NET", "0.0", "N", "#00D4FF")
        
        forces_grid.addWidget(self.thrust_force_display, 0, 0)
        forces_grid.addWidget(self.drag_force_display, 0, 1)
        forces_grid.addWidget(self.chute_drag_display, 1, 0)
        forces_grid.addWidget(self.weight_force_display, 1, 1)
        forces_grid.addWidget(self.net_force_display, 2, 0, 1, 2)  # Span both columns
        
        layout.addLayout(forces_grid)
        
        # Initialize force diagram update
        self.setup_initial_force_diagram()

    def create_force_display(self, label, value, unit, color):
        """Create a compact force value display"""
        widget = QtWidgets.QFrame()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        
        # Theme-aware styling
        theme = self.themes[self.current_theme]
        if self.current_theme == "retro":
            widget.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme['colors']['secondary_bg']};
                    border: 1px solid {theme['colors']['accent']};
                    border-radius: 4px;
                }}
                QLabel {{
                    background-color: transparent;
                    color: {theme['colors']['primary_text']};
                }}
            """)
        else:
            widget.setStyleSheet(f"""
                QFrame {{
                    background: {theme['telemetry']['bg']};
                    border: 1px solid {theme['telemetry']['border']};
                    border-radius: 3px;
                }}
                QLabel {{
                    background-color: transparent;
                    color: {theme['telemetry']['gauge_text']};
                    font-family: 'Consolas', 'Monaco', monospace;
                }}
            """)
        
        # Label
        label_widget = QtWidgets.QLabel(label)
        label_widget.setAlignment(QtCore.Qt.AlignCenter)
        label_widget.setStyleSheet(f"font-size: 9px; font-weight: bold; color: {color};")
        layout.addWidget(label_widget)
        
        # Value
        value_widget = QtWidgets.QLabel(f"{value} {unit}")
        value_widget.setAlignment(QtCore.Qt.AlignCenter)
        value_widget.setStyleSheet("font-size: 11px; font-weight: bold;")
        layout.addWidget(value_widget)
        
        # Store references for updates
        widget.label = label_widget
        widget.value = value_widget
        widget.unit = unit
        
        return widget

    def setup_initial_force_diagram(self):
        """Setup the initial force diagram visualization"""
        import matplotlib.patches as patches
        
        self.force_ax.clear()
        self.force_ax.set_xlim(-2, 2)
        self.force_ax.set_ylim(-1, 4)
        self.force_ax.set_aspect('equal')
        self.force_ax.axis('off')
        
        # Initialize airflow particles for animation
        import numpy as np
        self.airflow_particles = []
        for i in range(8):  # Create 8 airflow particles
            particle = {
                'x': np.random.uniform(-1.8, 1.8),
                'y': np.random.uniform(0.5, 3.5),
                'vx': 0.0,
                'vy': 0.0,
                'size': np.random.uniform(15, 30)
            }
            self.airflow_particles.append(particle)
        
        # Draw more realistic rocket shape
        self.draw_rocket_body()
        
        # Add labels for vectors
        theme_color = '#ECF0F1' if self.current_theme == "professional" else '#2C3E50'
        self.force_ax.text(0, 0.5, 'Forces & Airflow', ha='center', va='center',
                          fontsize=9, fontweight='bold', color=theme_color)
        
        self.force_canvas.draw()

    def draw_rocket_body(self):
        """Draw a more realistic rocket shape"""
        import matplotlib.patches as patches
        
        # Main body (cylinder)
        rocket_body = patches.Rectangle((-0.08, 1.5), 0.16, 0.8,
                                      facecolor='#C0C0C0', edgecolor='black', linewidth=1.5)
        self.force_ax.add_patch(rocket_body)
        
        # Nose cone (triangle)
        nose_cone = patches.Polygon([(-0.08, 2.3), (0.08, 2.3), (0, 2.6)],
                                   facecolor='#A0A0A0', edgecolor='black', linewidth=1.5)
        self.force_ax.add_patch(nose_cone)
        
        # Fins (small triangles at base)
        fin_left = patches.Polygon([(-0.08, 1.5), (-0.15, 1.3), (-0.08, 1.4)],
                                  facecolor='#808080', edgecolor='black', linewidth=1)
        fin_right = patches.Polygon([(0.08, 1.5), (0.15, 1.3), (0.08, 1.4)],
                                   facecolor='#808080', edgecolor='black', linewidth=1)
        self.force_ax.add_patch(fin_left)
        self.force_ax.add_patch(fin_right)
        
        # Engine nozzle
        nozzle = patches.Rectangle((-0.04, 1.4), 0.08, 0.1,
                                 facecolor='#404040', edgecolor='black', linewidth=1)
        self.force_ax.add_patch(nozzle)

    def update_airflow_particles(self):
        """Update and draw airflow particles showing air movement past rocket"""
        import numpy as np
        
        if not hasattr(self, 'airflow_particles'):
            return
        
        # Get rocket velocity components for airflow simulation
        v_vertical = getattr(self, 'launch_velocity', 0.0) if hasattr(self, 'is_launching') and self.is_launching else 0.0
        v_horizontal = getattr(self, 'launch_x_vel', 0.0) if hasattr(self, 'is_launching') and self.is_launching else 0.0
        v_total = (v_vertical**2 + v_horizontal**2) ** 0.5
        is_moving = v_total > 0.5
        
        # Update particle positions and velocities
        for particle in self.airflow_particles:
            if is_moving:
                # Calculate airflow direction opposite to rocket motion
                flow_direction_x = -v_horizontal / v_total if v_total > 0 else 0
                flow_direction_y = -v_vertical / v_total if v_total > 0 else 0
                
                # Base flow speed scales with rocket speed
                base_flow_speed = min(v_total * 0.02, 0.15)
                
                # Calculate distance from rocket centerline for flow deflection
                rocket_center_x = 0.0
                rocket_center_y = 2.0
                distance_from_rocket = abs(particle['x'] - rocket_center_x)
                
                # Flow patterns around rocket based on rocket's motion direction
                if particle['y'] > rocket_center_y:
                    # Above rocket - flow around nose cone
                    flow_deflection = 0.3 * np.exp(-distance_from_rocket * 3)
                    particle['vx'] = flow_direction_x * base_flow_speed + np.sign(particle['x'] - rocket_center_x) * flow_deflection
                    particle['vy'] = flow_direction_y * base_flow_speed * (1 + flow_deflection)
                elif particle['y'] < rocket_center_y - 0.3:
                    # Below rocket - wake turbulence
                    particle['vx'] = flow_direction_x * base_flow_speed * 0.7 + np.random.uniform(-0.05, 0.05)
                    particle['vy'] = flow_direction_y * base_flow_speed * 0.7
                else:
                    # Alongside rocket - fastest flow
                    particle['vx'] = flow_direction_x * base_flow_speed * 1.2 + np.sign(particle['x'] - rocket_center_x) * base_flow_speed * 0.3
                    particle['vy'] = flow_direction_y * base_flow_speed * 1.2
            else:
                # No airflow when rocket is stationary
                particle['vx'] = 0
                particle['vy'] = 0
            
            # Update particle position
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            
            # Reset particles that go off screen
            if particle['y'] < 0.5:
                particle['x'] = np.random.uniform(-1.8, 1.8)
                particle['y'] = 3.5
                particle['size'] = np.random.uniform(15, 30)
            elif particle['y'] > 3.5:
                particle['x'] = np.random.uniform(-1.8, 1.8)
                particle['y'] = 0.5
                particle['size'] = np.random.uniform(15, 30)
            elif abs(particle['x']) > 1.8:
                particle['x'] = np.random.uniform(-1.8, 1.8)
                particle['y'] = np.random.uniform(0.5, 3.5)
                particle['size'] = np.random.uniform(15, 30)
        
        # Draw airflow particles
        if is_moving:
            # Draw particles as small circles with motion trails
            for particle in self.airflow_particles:
                # Particle color based on speed
                speed = np.sqrt(particle['vx']**2 + particle['vy']**2)
                alpha = min(0.6, 0.3 + speed * 2)  # More visible when moving faster
                
                if self.current_theme == "professional":
                    color = '#00D4FF'  # Cyan for professional theme
                else:
                    color = '#BCA16A'  # Gold for retro theme
                
                # Draw particle
                self.force_ax.scatter(particle['x'], particle['y'], 
                                    s=particle['size'], c=color, alpha=alpha, marker='o')
                
                # Draw motion trail
                if speed > 0.01:
                    trail_length = min(0.2, speed * 2)
                    trail_x = particle['x'] - particle['vx'] * trail_length * 10
                    trail_y = particle['y'] - particle['vy'] * trail_length * 10
                    self.force_ax.plot([trail_x, particle['x']], [trail_y, particle['y']],
                                     color=color, alpha=alpha*0.5, linewidth=1.5)
        else:
            # Show static air particles when not moving
            for particle in self.airflow_particles:
                color = '#808080'  # Gray for static air
                self.force_ax.scatter(particle['x'], particle['y'],
                                    s=particle['size']*0.5, c=color, alpha=0.2, marker='o')

    def draw_engine_exhaust(self, thrust_force, max_force):
        """Draw animated engine exhaust plume"""
        import numpy as np
        import matplotlib.patches as patches
        
        # Exhaust parameters based on thrust
        exhaust_intensity = thrust_force / max_force if max_force > 0 else 0
        exhaust_length = 0.3 + exhaust_intensity * 0.4  # 0.3 to 0.7 units long
        exhaust_width = 0.06 + exhaust_intensity * 0.04  # Variable width
        
        # Create exhaust plume points (triangle/cone shape)
        nozzle_center_x = 0.0
        nozzle_base_y = 1.4
        
        # Main exhaust cone
        exhaust_points = np.array([
            [nozzle_center_x - exhaust_width/2, nozzle_base_y],
            [nozzle_center_x + exhaust_width/2, nozzle_base_y],
            [nozzle_center_x, nozzle_base_y - exhaust_length]
        ])
        
        # Exhaust colors (gradient from yellow to red)
        exhaust_colors = ['#FFFF00', '#FF8000', '#FF4000']
        
        # Draw multiple exhaust layers for realistic effect
        for i, color in enumerate(exhaust_colors):
            scale_factor = 1.0 - i * 0.25  # Each layer slightly smaller
            scaled_points = exhaust_points.copy()
            
            # Scale the exhaust cone
            center_x = nozzle_center_x
            center_y = nozzle_base_y - exhaust_length/2
            
            for j, point in enumerate(scaled_points):
                if j < 2:  # Only scale width of base points
                    scaled_points[j][0] = center_x + (point[0] - center_x) * scale_factor
                scaled_points[j][1] = center_y + (point[1] - center_y) * scale_factor
            
            # Draw exhaust layer
            exhaust_polygon = patches.Polygon(scaled_points, 
                                            facecolor=color, 
                                            alpha=0.6 - i*0.1,
                                            edgecolor=None)
            self.force_ax.add_patch(exhaust_polygon)
        
        # Add flickering exhaust particles
        for _ in range(3):
            particle_x = nozzle_center_x + np.random.uniform(-exhaust_width/3, exhaust_width/3)
            particle_y = nozzle_base_y - np.random.uniform(0.1, exhaust_length * 0.8)
            
            self.force_ax.scatter(particle_x, particle_y,
                                s=np.random.uniform(20, 50),
                                c='#FFFF00', alpha=0.8, marker='*')

    def draw_parachute(self, rocket_x, rocket_y, open_factor):
        """Draw animated parachute above the rocket"""
        import numpy as np
        import matplotlib.patches as patches
        
        # Parachute position (above rocket)
        chute_x = rocket_x
        chute_y = rocket_y + 0.8 + (0.3 * open_factor)  # Rise as it opens
        
        # Parachute size based on opening factor
        base_radius = 0.25
        chute_radius = base_radius * (0.3 + 0.7 * open_factor)  # 30% to 100% size
        
        # Draw parachute canopy (circle/arc)
        if open_factor > 0.1:
            # Main canopy
            canopy = patches.Circle((chute_x, chute_y), chute_radius,
                                  facecolor='#FF6B6B', edgecolor='#D63031',
                                  alpha=0.7 + 0.3 * open_factor, linewidth=1.5)
            self.force_ax.add_patch(canopy)
            
            # Parachute lines (shroud lines)
            num_lines = 6
            for i in range(num_lines):
                angle = (i * 2 * np.pi / num_lines) - np.pi/2  # Start from top
                line_end_x = chute_x + chute_radius * 0.8 * np.cos(angle)
                line_end_y = chute_y + chute_radius * 0.8 * np.sin(angle)
                
                # Draw line from rocket to parachute edge
                self.force_ax.plot([rocket_x, line_end_x], [rocket_y + 0.5, line_end_y],
                                 color='#2D3436', linewidth=1, alpha=0.8)
            
            # Central line from rocket to parachute center
            self.force_ax.plot([rocket_x, chute_x], [rocket_y + 0.5, chute_y - chute_radius],
                             color='#2D3436', linewidth=1.5, alpha=0.8)
            
            # Add deployment animation details
            if open_factor < 1.0:
                # Show parachute "inflating" with some flutter
                flutter = 0.02 * np.sin(open_factor * 20)  # Small oscillation during opening
                ripple_radius = chute_radius * (0.9 + 0.1 * np.sin(open_factor * 15))
                
                ripple = patches.Circle((chute_x, chute_y), ripple_radius,
                                      facecolor='none', edgecolor='#FF6B6B',
                                      alpha=0.3, linewidth=1, linestyle='--')
                self.force_ax.add_patch(ripple)
            
            # Parachute label
            self.force_ax.text(chute_x + chute_radius + 0.1, chute_y, 'CHUTE',
                             fontsize=8, color='#D63031', fontweight='bold',
                             rotation=0, ha='left', va='center')
        else:
            # Just starting to deploy - show small bundle
            bundle = patches.Circle((chute_x, chute_y), 0.05,
                                  facecolor='#FF6B6B', edgecolor='#D63031',
                                  alpha=0.5, linewidth=1)
            self.force_ax.add_patch(bundle)
            
            # Single line to rocket
            self.force_ax.plot([rocket_x, chute_x], [rocket_y + 0.5, chute_y],
                             color='#2D3436', linewidth=1, alpha=0.6)

    def create_professional_gauge(self, label, value, unit, color):
        """Create a professional aerospace-style gauge display"""
        widget = QtWidgets.QFrame()
        widget.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        widget.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(26, 37, 47, 0.9), 
                    stop: 1 rgba(15, 20, 25, 0.9));
                border: 1px solid #34495E;
                border-radius: 4px;
                margin: 1px;
            }}
            QLabel {{
                background-color: transparent;
                color: #ECF0F1;
            }}
        """)
        
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        
        # Label with professional styling
        label_widget = QtWidgets.QLabel(label)
        label_widget.setAlignment(QtCore.Qt.AlignCenter)
        label_widget.setStyleSheet(f"""
            font-size: 9px; 
            color: {color}; 
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', monospace;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 2px;
        """)
        
        # Value display with larger, prominent font
        value_text = f"{value} {unit}" if unit else value
        value_widget = QtWidgets.QLabel(value_text)
        value_widget.setAlignment(QtCore.Qt.AlignCenter)
        value_widget.setStyleSheet(f"""
            font-size: 16px; 
            font-weight: bold; 
            color: {color};
            font-family: 'Consolas', 'Monaco', monospace;
            padding: 4px;
            border-bottom: 1px solid {color};
        """)
        
        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        
        # Store references for updates
        widget.value_label = value_widget
        widget.unit = unit
        widget.gauge_color = color
        
        return widget

    def create_professional_indicator(self, label):
        """Create a professional status indicator like mission control"""
        widget = QtWidgets.QFrame()
        widget.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(26, 37, 47, 0.9), 
                    stop: 1 rgba(15, 20, 25, 0.9));
                border: 1px solid #34495E;
                border-radius: 4px;
                margin: 1px;
                padding: 4px;
            }
        """)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # Status indicator (LED-style)
        status_container = QtWidgets.QFrame()
        status_container.setFixedHeight(20)
        status_layout = QtWidgets.QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        # LED indicator
        led = QtWidgets.QLabel("●")
        led.setAlignment(QtCore.Qt.AlignCenter)
        led.setFixedSize(16, 16)
        led.setStyleSheet("""
            color: #555555;
            font-size: 14px;
            background: rgba(85, 85, 85, 0.3);
            border-radius: 8px;
        """)
        
        # Status text
        status_text = QtWidgets.QLabel("OFFLINE")
        status_text.setAlignment(QtCore.Qt.AlignCenter)
        status_text.setStyleSheet("""
            font-size: 8px;
            color: #7F8C8D;
            font-family: 'Consolas', 'Monaco', monospace;
            font-weight: bold;
            letter-spacing: 0.5px;
        """)
        
        status_layout.addWidget(led)
        status_layout.addWidget(status_text)
        
        # Label
        label_widget = QtWidgets.QLabel(label)
        label_widget.setAlignment(QtCore.Qt.AlignCenter)
        label_widget.setStyleSheet("""
            font-size: 9px; 
            color: #00D4FF; 
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', monospace;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        """)
        
        layout.addWidget(status_container)
        layout.addWidget(label_widget)
        
        # Store references for updates
        widget.led = led
        widget.status_text = status_text
        widget.is_active = False
        
        return widget

    def update_professional_indicator(self, widget, active, status_text=None):
        """Update professional status indicator"""
        if widget.is_active != active:
            widget.is_active = active
            if active:
                widget.led.setStyleSheet("""
                    color: #00FF41;
                    font-size: 14px;
                    background: rgba(0, 255, 65, 0.2);
                    border-radius: 8px;
                    border: 1px solid #00FF41;
                """)
                widget.status_text.setStyleSheet("""
                    font-size: 8px;
                    color: #00FF41;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-weight: bold;
                    letter-spacing: 0.5px;
                """)
                widget.status_text.setText(status_text or "ACTIVE")
            else:
                widget.led.setStyleSheet("""
                    color: #555555;
                    font-size: 14px;
                    background: rgba(85, 85, 85, 0.3);
                    border-radius: 8px;
                """)
                widget.status_text.setStyleSheet("""
                    font-size: 8px;
                    color: #7F8C8D;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-weight: bold;
                    letter-spacing: 0.5px;
                """)
                widget.status_text.setText("OFFLINE")

    def create_gauge_display(self, label, value, color):
        """Create a clean, professional gauge-style display widget"""
        widget = QtWidgets.QFrame()
        widget.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 2px solid {color};
                border-radius: 8px;
                margin: 2px;
            }}
            QLabel {{
                background-color: transparent;
                color: #3C2F1E;
            }}
        """)
        
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        
        # Label with icon-style formatting
        label_widget = QtWidgets.QLabel(label)
        label_widget.setAlignment(QtCore.Qt.AlignCenter)
        label_widget.setStyleSheet(f"""
            font-size: 10px; 
            color: {color}; 
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
        """)
        
        # Value with larger, prominent display
        value_widget = QtWidgets.QLabel(value)
        value_widget.setAlignment(QtCore.Qt.AlignCenter)
        value_widget.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            color: #2C3E50;
            padding: 4px;
        """)
        
        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        
        # Store value widget for updates
        widget.value_label = value_widget
        widget.gauge_color = color
        
        return widget

    def create_status_light(self, label, icon, active):
        """Create a professional status indicator with icon"""
        widget = QtWidgets.QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #BCA16A;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        
        # Status icon and indicator
        status_layout = QtWidgets.QHBoxLayout()
        
        # Icon
        icon_label = QtWidgets.QLabel(icon)
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 14px;")
        
        # Status circle
        circle = QtWidgets.QLabel("●")
        circle.setAlignment(QtCore.Qt.AlignCenter)
        color = "#32CD32" if active else "#C0C0C0"
        circle.setStyleSheet(f"color: {color}; font-size: 12px;")
        
        status_layout.addWidget(icon_label)
        status_layout.addWidget(circle)
        
        # Label
        text = QtWidgets.QLabel(label)
        text.setAlignment(QtCore.Qt.AlignCenter)
        text.setStyleSheet("""
            font-size: 9px; 
            color: #3C2F1E; 
            font-weight: bold;
            text-transform: uppercase;
        """)
        
        layout.addLayout(status_layout)
        layout.addWidget(text)
        
        # Store circle for updates
        widget.status_circle = circle
        widget.is_active = active
        
        return widget

    def update_status_light(self, widget, active):
        """Update the status of a status light with smooth color transition"""
        if widget.is_active != active:
            widget.is_active = active
            color = "#32CD32" if active else "#C0C0C0"
            widget.status_circle.setStyleSheet(f"color: {color}; font-size: 12px;")

    def update_telemetry_displays(self):
        """Update all telemetry displays with current data using theme-aware formatting"""
        if hasattr(self, 'is_launching') and self.is_launching:
            # Get current simulation state
            try:
                # Update from current animation state
                altitude = getattr(self, 'launch_altitude', 0.0)
                velocity = getattr(self, 'launch_velocity', 0.0)
                time = getattr(self, 'launch_time', 0.0)
                mass = getattr(self, 'launch_mass', 0.0)
                
                # Calculate additional metrics
                acceleration = getattr(self, 'prev_acceleration', 0.0)
                g_force = abs(acceleration) / 9.81
                
                # Get thrust from thrust curve
                try:
                    times_thrust, thrusts, thrust_func, burn_time = self.load_thrust_curve_data()
                    current_thrust = float(thrust_func(time)) if time <= burn_time else 0.0
                except:
                    current_thrust = 0.0
                
                # Calculate drag force (approximation)
                try:
                    _, Cd, A, rho, _, _, _, _, _, _, _, _ = self.get_inputs_for_simulation()
                    drag_force = 0.5 * rho * (velocity ** 2) * Cd * A if velocity > 0 else 0.0
                except:
                    drag_force = 0.0
                
                # Calculate Mach number
                speed_of_sound = 343.0  # m/s at sea level
                mach_number = abs(velocity) / speed_of_sound
                
                # Determine flight phase
                if altitude <= 0 and velocity == 0:
                    phase = "LANDED"
                elif hasattr(self, 'chute_deployed') and self.chute_deployed:
                    phase = "CHUTE DESCENT"
                elif current_thrust > 10:
                    phase = "POWERED ASCENT"
                elif velocity > 0:
                    phase = "COASTING"
                elif velocity < 0:
                    phase = "DESCENT"
                else:
                    phase = "LIFTOFF"
                
                # Update displays with theme-appropriate formatting
                if self.current_theme == "retro":
                    self.altitude_display.value_label.setText(f"{altitude:.1f} m")
                    self.velocity_display.value_label.setText(f"{velocity:.1f} m/s")
                    self.acceleration_display.value_label.setText(f"{acceleration:.1f} m/s²")
                    self.g_force_display.value_label.setText(f"{g_force:.1f} G")
                    self.thrust_display.value_label.setText(f"{current_thrust:.0f} N")
                    self.drag_display.value_label.setText(f"{drag_force:.1f} N")
                    self.mass_display.value_label.setText(f"{mass:.2f} kg")
                    self.mach_display.value_label.setText(f"{mach_number:.2f}")
                    self.time_display.setText(f"T+ {time:.1f}s")
                else:
                    self.altitude_display.value_label.setText(f"{altitude:.1f} m")
                    self.velocity_display.value_label.setText(f"{velocity:.1f} m/s")
                    self.acceleration_display.value_label.setText(f"{acceleration:.1f} m/s²")
                    self.g_force_display.value_label.setText(f"{g_force:.1f} G")
                    self.thrust_display.value_label.setText(f"{current_thrust:.0f} N")
                    self.drag_display.value_label.setText(f"{drag_force:.1f} N")
                    self.mass_display.value_label.setText(f"{mass:.2f} kg")
                    self.mach_display.value_label.setText(f"{mach_number:.2f}")
                    self.time_display.setText(f"T+ {time:06.1f}")
                
                self.phase_display.setText(phase)
                
                # Update status indicators based on theme
                if self.current_theme == "retro":
                    if hasattr(self, 'engine_status'):
                        self.update_retro_indicator(self.engine_status, current_thrust > 10)
                    if hasattr(self, 'chute_status'):
                        self.update_retro_indicator(self.chute_status, getattr(self, 'chute_deployed', False))
                    try:
                        margin = self.center_of_pressure_input.value() - self.center_of_mass_input.value()
                        stable = margin > 0.05
                        self.update_retro_indicator(self.stable_status, stable)
                    except:
                        self.update_retro_indicator(self.stable_status, True)
                else:
                    if hasattr(self, 'engine_status'):
                        self.update_professional_indicator(self.engine_status, current_thrust > 10, "BURN" if current_thrust > 10 else None)
                    if hasattr(self, 'chute_status'):
                        self.update_professional_indicator(self.chute_status, getattr(self, 'chute_deployed', False), "DEPLOYED" if getattr(self, 'chute_deployed', False) else None)
                    try:
                        margin = self.center_of_pressure_input.value() - self.center_of_mass_input.value()
                        stable = margin > 0.05
                        self.update_professional_indicator(self.stable_status, stable, "STABLE" if stable else "UNSTABLE")
                    except:
                        self.update_professional_indicator(self.stable_status, True, "STABLE")
                    
            except Exception as e:
                pass  # Silently handle any telemetry update errors
        else:
            # Reset displays when not launching - theme-appropriate formatting
            if self.current_theme == "retro":
                self.altitude_display.value_label.setText("0.0 m")
                self.velocity_display.value_label.setText("0.0 m/s")
                self.acceleration_display.value_label.setText("0.0 m/s²")
                self.g_force_display.value_label.setText("0.0 G")
                self.thrust_display.value_label.setText("0 N")
                self.drag_display.value_label.setText("0.0 N")
                self.time_display.setText("T+ 0.0s")
            else:
                self.altitude_display.value_label.setText("0.0 m")
                self.velocity_display.value_label.setText("0.0 m/s")
                self.acceleration_display.value_label.setText("0.0 m/s²")
                self.g_force_display.value_label.setText("0.0 G")
                self.thrust_display.value_label.setText("0 N")
                self.drag_display.value_label.setText("0.0 N")
                self.time_display.setText("T+ 000.0")
            
            try:
                m, _, _, _, _, _, _, _, _, _, _, _ = self.get_inputs_for_simulation()
                self.mass_display.value_label.setText(f"{m:.2f} kg")
            except:
                self.mass_display.value_label.setText("0.0 kg")
            
            self.mach_display.value_label.setText("0.00")
            self.phase_display.setText("STANDBY")
            
            # Update status indicators for standby
            if self.current_theme == "retro":
                if hasattr(self, 'engine_status'):
                    self.update_retro_indicator(self.engine_status, False)
                if hasattr(self, 'chute_status'):
                    self.update_retro_indicator(self.chute_status, False)
                try:
                    margin = self.center_of_pressure_input.value() - self.center_of_mass_input.value()
                    stable = margin > 0.05
                    self.update_retro_indicator(self.stable_status, stable)
                except:
                    self.update_retro_indicator(self.stable_status, True)
            else:
                if hasattr(self, 'engine_status'):
                    self.update_professional_indicator(self.engine_status, False)
                if hasattr(self, 'chute_status'):
                    self.update_professional_indicator(self.chute_status, False)
                try:
                    margin = self.center_of_pressure_input.value() - self.center_of_mass_input.value()
                    stable = margin > 0.05
                    self.update_professional_indicator(self.stable_status, stable, "STABLE" if stable else "UNSTABLE")
                except:
                    self.update_professional_indicator(self.stable_status, True, "STABLE")

    def update_force_diagram(self):
        """Update the real-time force vector diagram"""
        if not hasattr(self, 'force_ax') or not hasattr(self, 'force_canvas'):
            return
            
        # Clear and reset the diagram
        self.force_ax.clear()
        self.force_ax.set_xlim(-2, 2)
        self.force_ax.set_ylim(-1, 4)
        self.force_ax.set_aspect('equal')
        self.force_ax.axis('off')
        
        import matplotlib.patches as patches
        
        # Draw enhanced rocket body instead of simple rectangle
        self.draw_rocket_body()
        
        # Update and draw airflow particles
        self.update_airflow_particles()
        
        if hasattr(self, 'is_launching') and self.is_launching:
            # Get current forces from simulation
            try:
                # Calculate current forces
                _, Cd, A, rho, _, _, _, _, _, _, _, _ = self.get_inputs_for_simulation()
                
                # Get current values
                velocity = getattr(self, 'launch_velocity', 0.0)
                mass = getattr(self, 'launch_mass', 0.0)
                time = getattr(self, 'launch_time', 0.0)
                
                # Get thrust from thrust curve
                times_thrust, thrusts, thrust_func, burn_time = self.load_thrust_curve_data()
                thrust_force = float(thrust_func(time)) if time <= burn_time else 0.0
                
                # Calculate drag force
                drag_force = 0.5 * rho * (velocity ** 2) * Cd * A if velocity != 0 else 0.0
                drag_force = abs(drag_force)  # Always positive magnitude
                
                # Check for parachute deployment and calculate parachute drag
                chute_deployed = getattr(self, 'chute_deployed', False)
                chute_drag_force = 0.0
                if chute_deployed:
                    try:
                        chute_cd = 1.5  # Typical parachute drag coefficient
                        _, _, _, _, _, _, _, _, _, chute_size, _, _ = self.get_inputs_for_simulation()
                        if chute_size and chute_size > 0:
                            chute_open_factor = getattr(self, 'chute_open_factor', 1.0)
                            effective_chute_area = chute_size * chute_open_factor
                            chute_drag_force = 0.5 * rho * (velocity ** 2) * chute_cd * effective_chute_area if velocity != 0 else 0.0
                            chute_drag_force = abs(chute_drag_force)
                    except:
                        chute_drag_force = 0.0
                
                # Total drag is body drag + parachute drag
                total_drag_force = drag_force + chute_drag_force
                
                # Weight force
                weight_force = mass * 9.81
                
                # Net force (upward positive) - include parachute drag in calculation
                net_force = thrust_force - total_drag_force - weight_force
                
                # Scale factors for display (normalize to largest force for visibility)
                max_force = max(thrust_force, total_drag_force, weight_force, abs(net_force), 1.0)
                scale = 1.0 / max_force  # Scale to unit vectors, then apply display scale
                display_scale = 0.8  # Maximum arrow length
                
                # Draw parachute if deployed
                if chute_deployed:
                    self.draw_parachute(rocket_center_x, rocket_center_y, chute_open_factor)
                
                # Draw force vectors
                rocket_center_x, rocket_center_y = 0.0, 2.0
                
                # Thrust vector (upward, green)
                if thrust_force > 0:
                    thrust_length = thrust_force * scale * display_scale
                    self.force_ax.arrow(rocket_center_x, rocket_center_y, 0, thrust_length,
                                       head_width=0.08, head_length=0.06, fc='#00FF00', ec='#00FF00',
                                       linewidth=2, alpha=0.8)
                    self.force_ax.text(rocket_center_x + 0.3, rocket_center_y + thrust_length/2,
                                      f'T={thrust_force:.0f}N', fontsize=8, color='#00FF00', fontweight='bold')
                    
                    # Add engine exhaust visualization
                    self.draw_engine_exhaust(thrust_force, max_force)
                
                # Drag vector (downward, red) - body drag only
                if drag_force > 0 and abs(velocity) > 0.1:
                    drag_length = drag_force * scale * display_scale
                    drag_direction = -1 if velocity > 0 else 1  # Oppose motion
                    self.force_ax.arrow(rocket_center_x - 0.3, rocket_center_y, 0, drag_direction * drag_length,
                                       head_width=0.08, head_length=0.06, fc='#FF4444', ec='#FF4444',
                                       linewidth=2, alpha=0.8)
                    self.force_ax.text(rocket_center_x - 0.6, rocket_center_y + (drag_direction * drag_length)/2,
                                      f'D={drag_force:.0f}N', fontsize=8, color='#FF4444', fontweight='bold')
                
                # Parachute drag vector (separate from body drag, purple/magenta)
                if chute_deployed and chute_drag_force > 0 and abs(velocity) > 0.1:
                    chute_drag_length = chute_drag_force * scale * display_scale
                    chute_drag_direction = -1 if velocity > 0 else 1  # Oppose motion
                    self.force_ax.arrow(rocket_center_x - 0.6, rocket_center_y + 0.8, 0, chute_drag_direction * chute_drag_length,
                                       head_width=0.08, head_length=0.06, fc='#FF00FF', ec='#FF00FF',
                                       linewidth=2, alpha=0.8)
                    self.force_ax.text(rocket_center_x - 0.9, rocket_center_y + 0.8 + (chute_drag_direction * chute_drag_length)/2,
                                      f'CD={chute_drag_force:.0f}N', fontsize=8, color='#FF00FF', fontweight='bold')
                
                # Weight vector (downward, orange)
                if weight_force > 0:
                    weight_length = weight_force * scale * display_scale
                    self.force_ax.arrow(rocket_center_x + 0.3, rocket_center_y, 0, -weight_length,
                                       head_width=0.08, head_length=0.06, fc='#FFAA00', ec='#FFAA00',
                                       linewidth=2, alpha=0.8)
                    self.force_ax.text(rocket_center_x + 0.6, rocket_center_y - weight_length/2,
                                      f'W={weight_force:.0f}N', fontsize=8, color='#FFAA00', fontweight='bold')
                
                # Net force vector (cyan, from center)
                if abs(net_force) > 1.0:  # Only show if significant
                    net_length = abs(net_force) * scale * display_scale
                    net_direction = 1 if net_force > 0 else -1
                    self.force_ax.arrow(rocket_center_x, rocket_center_y - 0.8, 0, net_direction * net_length,
                                       head_width=0.12, head_length=0.08, fc='#00D4FF', ec='#00D4FF',
                                       linewidth=3, alpha=0.9)
                    self.force_ax.text(rocket_center_x - 0.8, rocket_center_y - 0.8 + (net_direction * net_length)/2,
                                      f'Net={net_force:.0f}N', fontsize=8, color='#00D4FF', fontweight='bold')
                
                # Update force displays
                if hasattr(self, 'thrust_force_display'):
                    self.thrust_force_display.value.setText(f"{thrust_force:.0f} {self.thrust_force_display.unit}")
                    self.drag_force_display.value.setText(f"{drag_force:.0f} {self.drag_force_display.unit}")
                    self.chute_drag_display.value.setText(f"{chute_drag_force:.0f} {self.chute_drag_display.unit}")
                    self.weight_force_display.value.setText(f"{weight_force:.0f} {self.weight_force_display.unit}")
                    self.net_force_display.value.setText(f"{net_force:.0f} {self.net_force_display.unit}")
                    
                    # Update chute drag display color based on deployment
                    if chute_deployed:
                        self.chute_drag_display.label.setStyleSheet("font-size: 9px; font-weight: bold; color: #FF00FF;")
                    else:
                        self.chute_drag_display.label.setStyleSheet("font-size: 9px; font-weight: bold; color: #808080;")
                
            except Exception as e:
                # On error, show default state
                self.setup_initial_force_diagram()
                return
        else:
            # Standby state - show static rocket with zero forces
            try:
                m, _, _, _, _, _, _, _, _, _, _, _ = self.get_inputs_for_simulation()
                weight_force = m * 9.81
                
                if hasattr(self, 'thrust_force_display'):
                    self.thrust_force_display.value.setText(f"0 {self.thrust_force_display.unit}")
                    self.drag_force_display.value.setText(f"0 {self.drag_force_display.unit}")
                    self.chute_drag_display.value.setText(f"0 {self.chute_drag_display.unit}")
                    self.weight_force_display.value.setText(f"{weight_force:.0f} {self.weight_force_display.unit}")
                    self.net_force_display.value.setText(f"0 {self.net_force_display.unit}")
                    
                    # Gray out chute display when not deployed
                    self.chute_drag_display.label.setStyleSheet("font-size: 9px; font-weight: bold; color: #808080;")
            except:
                if hasattr(self, 'thrust_force_display'):
                    self.thrust_force_display.value.setText(f"0 {self.thrust_force_display.unit}")
                    self.drag_force_display.value.setText(f"0 {self.drag_force_display.unit}")
                    self.chute_drag_display.value.setText(f"0 {self.chute_drag_display.unit}")
                    self.weight_force_display.value.setText(f"0 {self.weight_force_display.unit}")
                    self.net_force_display.value.setText(f"0 {self.net_force_display.unit}")
                    
                    # Gray out chute display
                    self.chute_drag_display.label.setStyleSheet("font-size: 9px; font-weight: bold; color: #808080;")
        
        # Add title
        theme_color = '#ECF0F1' if self.current_theme == "professional" else '#2C3E50'
        self.force_ax.text(0, 3.5, 'Live Forces', ha='center', va='center',
                          fontsize=9, fontweight='bold', color=theme_color)
        
        # Refresh display
        self.force_canvas.draw()

    def update_retro_indicator(self, widget, active):
        """Update retro-style status indicator"""
        if widget.is_active != active:
            widget.is_active = active
            theme = self.themes["retro"]
            color = theme['telemetry']['status_active'] if active else theme['telemetry']['status_inactive']
            widget.status_circle.setStyleSheet(f"color: {color}; font-size: 12px;")

    def update_professional_indicator(self, widget, active, text=None):
        """Update professional-style status indicator"""
        if widget.is_active != active or (text and hasattr(widget, 'status_text') and widget.status_text.text() != text):
            widget.is_active = active
            theme = self.themes["professional"]
            
            # Update indicator light
            color = theme['telemetry']['status_active'] if active else theme['telemetry']['status_inactive']
            widget.led.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-size: 14px;
                    font-weight: bold;
                    background: rgba(0, 255, 65, 0.2);
                    border-radius: 8px;
                }}
            """)
            
            # Update status text if provided
            if text and hasattr(widget, 'status_text'):
                widget.status_text.setText(text)
                text_color = theme['telemetry']['status_active'] if active else theme['telemetry']['gauge_text']
                widget.status_text.setStyleSheet(f"""
                    QLabel {{
                        color: {text_color};
                        font-size: 9px;
                        font-family: 'Courier New';
                        font-weight: bold;
                    }}
                """)

    def on_theme_changed(self, theme_name):
        """Handle theme selection change"""
        if theme_name != self.current_theme:
            self.current_theme = theme_name
            self.apply_theme(theme_name)
            
            # Save theme preference
            try:
                settings = self.load_settings()
                settings['theme'] = theme_name
                self.save_settings(settings)
            except:
                pass

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
        self.launch_x_vel = 0.0
        # Angular state for full rotation - start with launch guide angle
        launch_guide_angle_deg = self.launch_angle_input.value()
        self.launch_angle = math.radians(launch_guide_angle_deg)  # Convert to radians
        self.launch_angular_velocity = 0.0   # radians/sec
        # Parachute and apogee state
        self.chute_deployed = False
        self.chute_open_factor = 0.0  # 0..1 gradually opens when deployed
        self.apogee_marked = False
        self.apogee_pos = None
        self.apogee_flash_frames = 0
        self.launch_prev_velocity = 0.0
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

    def stop_launch_animation(self):
        """Stop the rocket launch animation and reset UI state."""
        try:
            if hasattr(self, 'launch_timer'):
                self.launch_timer.stop()
            self.is_launching = False
            self.launch_button.setText('Launch!')
            self.launch_button.setEnabled(True)
            # Optional: clear trail and reset camera smoothing to defaults
            self.position_history = []
            self.smooth_center_x = 0.0
            self.smooth_center_y = 1.5
            self.smooth_zoom = 1.0
            self.smooth_flame_intensity = 0.0
        except Exception:
            pass

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
        # Instability gain (0..1) grows as margin goes below threshold
        instability_gain = 0.0
        if not stable:
            try:
                instability_gain = min(1.0, max(0.0, (0.05 - margin) / 0.05))
            except Exception:
                instability_gain = 1.0
        color = '#2E8B57' if stable else '#E94F37'
        
        # Load thrust curve data using shared method
        times_thrust, thrusts, thrust_func, burn_time = self.load_thrust_curve_data()
        
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
            self.launch_x_vel = 0.0
            self.launch_mass = m
            self.prev_acceleration = 0.0  # For smoothing
            # Initialize angular state if missing
            launch_guide_angle_deg = self.launch_angle_input.value()
            self.launch_angle = math.radians(launch_guide_angle_deg)
            self.launch_angular_velocity = 0.0
            # Parachute/apogee defaults
            self.chute_deployed = False
            self.chute_open_factor = 0.0
            self.apogee_marked = False
            self.apogee_pos = None
            self.apogee_flash_frames = 0
            self.launch_prev_velocity = 0.0
            
        dt = 0.025  # Smaller time step for smoother physics (25ms)

        # Handle parachute deployment triggers (descent + below threshold altitude)
        if not hasattr(self, 'chute_deployed'):
            self.chute_deployed = False
            self.chute_open_factor = 0.0
        # Deploy only on descent below set altitude
        try:
            deploy_alt_threshold = max(0.0, chute_height or 0.0)
            should_deploy = (self.launch_velocity < 0) and (self.launch_altitude <= deploy_alt_threshold)
        except Exception:
            should_deploy = False
        if not self.chute_deployed and should_deploy:
            self.chute_deployed = True
        
        # Perform multiple small integration steps for smoother motion
        for step_idx in range(2):  # 2 steps of 25ms each = 50ms total
            # Sample thrust per substep for smoother burn dynamics
            t_sub = t + step_idx * dt
            current_thrust_step = float(thrust_func(t_sub)) if t_sub <= burn_time else 0.0

            # --- Angular dynamics (spin) ---
            # Dynamic pressure based on total speed
            v_total = max(0.0, (self.launch_velocity**2 + self.launch_x_vel**2) ** 0.5)
            q_dyn = 0.5 * rho * (v_total ** 2)
            # Torques: restoring when stable, divergent when unstable, plus damping and small turbulence
            k_stable = 3.0
            k_unstable = 2.0
            k_damp = 1.2
            torque = 0.0
            # Angle is measured from vertical (0 = up)
            if stable:
                torque += -k_stable * q_dyn * self.launch_angle
            else:
                torque += k_unstable * q_dyn * instability_gain * self.launch_angle
                torque += 0.4 * q_dyn * instability_gain * (random.random() - 0.5)
            # Damping always opposes angular velocity
            torque += -k_damp * self.launch_angular_velocity
            # Convert torque to angular acceleration via an arbitrary inertia constant
            I = max(0.1, m * 0.02)  # crude rotational inertia proxy
            angular_acc = torque / I
            # Integrate orientation
            self.launch_angular_velocity += angular_acc * dt
            self.launch_angle += self.launch_angular_velocity * dt
            # Keep angle within -pi..pi for numerical stability (not limiting spin, just wrapping)
            if self.launch_angle > math.pi:
                self.launch_angle -= 2 * math.pi
            elif self.launch_angle < -math.pi:
                self.launch_angle += 2 * math.pi

            # Thrust aligned with body axis
            thrust_dir_x = math.sin(self.launch_angle)
            thrust_dir_y = math.cos(self.launch_angle)
            thrust_x = current_thrust_step * thrust_dir_x
            thrust_y = current_thrust_step * thrust_dir_y

            # Effective drag area with parachute (Cd*A + Cd_chute*A_chute*open)
            drag_area_base = Cd * A
            chute_area_term = (chute_cd * chute_size) if (chute_size and chute_cd) else 0.0
            if self.chute_deployed:
                # Gradually open chute
                self.chute_open_factor = min(1.0, self.chute_open_factor + 0.12)
            drag_area_eff = drag_area_base + (self.chute_open_factor * chute_area_term)

            # Calculate vertical drag force magnitude: F_drag = 0.5 * rho * v^2 * drag_area_eff
            if self.launch_velocity != 0:
                drag_force_mag = 0.5 * rho * (self.launch_velocity ** 2) * drag_area_eff
                # Drag always opposes motion
                drag_term = math.copysign(drag_force_mag, self.launch_velocity)
            else:
                drag_term = 0.0
            
            # Net force: thrust - weight - drag(sign)
            net_force = thrust_y - drag_term - (self.launch_mass * g)
            acceleration = net_force / self.launch_mass
            
            # Add instability if rocket is unstable (stronger, includes lateral wobble)
            if not stable:
                # Vertical wobble increases slightly with time
                wobble_magnitude = (0.8 + 1.2 * instability_gain) * math.sin(t_sub * 8.0) * (1 + min(t, 10) * 0.07)
                acceleration += wobble_magnitude
                # Lateral acceleration from thrust tilt and wobble
                a_x = thrust_x / self.launch_mass
                a_x += (0.8 * instability_gain) * math.sin(t_sub * (6.0 + 1.5 * instability_gain))
                a_x += (0.4 * instability_gain) * (random.random() - 0.5)  # small noise for non-periodic motion
                # Horizontal drag opposes lateral velocity to avoid runaway drift
                if self.launch_x_vel != 0:
                    drag_x_mag = 0.5 * rho * (self.launch_x_vel ** 2) * drag_area_eff
                    drag_x_term = math.copysign(drag_x_mag, self.launch_x_vel)
                    a_x += -drag_x_term / self.launch_mass
                # Integrate x velocity and position
                self.launch_x_vel += a_x * dt
            else:
                # When stable, lateral acceleration only from thrust alignment
                a_x = thrust_x / self.launch_mass
                # Horizontal drag
                if self.launch_x_vel != 0:
                    drag_x_mag = 0.5 * rho * (self.launch_x_vel ** 2) * drag_area_eff
                    drag_x_term = math.copysign(drag_x_mag, self.launch_x_vel)
                    a_x += -drag_x_term / self.launch_mass
                self.launch_x_vel += a_x * dt
            
            # Smooth acceleration changes to avoid jerky motion
            acceleration_smoothing = 0.3
            self.prev_acceleration += (acceleration - self.prev_acceleration) * acceleration_smoothing
            
            # Update velocity and position with smoothed acceleration
            self.launch_velocity += self.prev_acceleration * dt
            self.launch_altitude += self.launch_velocity * dt
            
            # Add wind drift (smaller steps for smoother movement)
            # Combine wind drift and integrated lateral velocity
            self.launch_x_pos += (self.launch_x_vel + x_drift_per_sec) * dt
            
            # Don't go below ground
            if self.launch_altitude < 0:
                self.launch_altitude = 0
                self.launch_velocity = max(0, self.launch_velocity * -0.3)  # Bounce with energy loss
        
        # Detect apogee (sign change of vertical velocity)
        try:
            if (not self.apogee_marked) and (self.launch_prev_velocity > 0) and (self.launch_velocity <= 0) and (self.launch_altitude > 0.5):
                self.apogee_marked = True
                self.apogee_pos = (self.launch_x_pos, self.launch_altitude)
                self.apogee_flash_frames = 30
        except Exception:
            pass
        self.launch_prev_velocity = self.launch_velocity

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
        camera_smoothing = 0.60  # Lower = smoother, higher = more responsive
        zoom_smoothing = 0.8    # Much faster zoom response for a snappier feel

        # Smooth camera position
        # Follow vertically; horizontally: partial follow when unstable so drift is visible but stays in frame
        if not stable:
            # Widen camera follow for unstable rockets
            target_center_x = 0.8 * x_pos
            follow_alpha_x = 0.2
        else:
            target_center_x = x_pos
            follow_alpha_x = camera_smoothing
        self.smooth_center_x += (target_center_x - self.smooth_center_x) * follow_alpha_x
        target_center_y = max(1.5, y_pos)
        self.smooth_center_y += (target_center_y - self.smooth_center_y) * camera_smoothing

        # Smooth zoom with altitude and velocity; keep rocket big on ascent
        base_zoom = max(1.0, y_pos * 0.25 + abs(self.launch_velocity) * 0.02)
    # Remove all zoom capping: camera always zooms out as much as needed
        # Keep rocket visually large: blend between min zoom and physics zoom
        min_visual_zoom = 1.2
        if self.launch_velocity > 0:
            # On ascent, blend so rocket stays big
            visual_alpha = max(0.0, min(1.0, y_pos / 30.0))  # 0 at pad, 1 at 30m+
            target_zoom = min_visual_zoom * (1 - visual_alpha) + base_zoom * visual_alpha
        else:
            target_zoom = base_zoom
        self.smooth_zoom += (target_zoom - self.smooth_zoom) * zoom_smoothing

        # Apply smoothed values
        center_x = self.smooth_center_x
        center_y = self.smooth_center_y
        # Make x zoom much slower for readability
        x_zoom_factor = 0.35  # Lower = slower expansion, more readable
        view_width = 2 * (self.smooth_zoom * x_zoom_factor + self.smooth_zoom * (1 - x_zoom_factor))
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
        
        # Draw current rocket position (rotated polygon) and flame aligned with body
        if y_pos > 0:
            # Rocket dimensions in world units (visual only)
            L_draw = 0.6
            W_draw = 0.18
            # Body frame vertices: (x_right, y_forward)
            nose = (0.0, L_draw/2)
            left_tail = (-W_draw/2, -L_draw/2)
            right_tail = (W_draw/2, -L_draw/2)
            # Forward along body axis and right perpendicular
            u_forward = (math.sin(self.launch_angle), math.cos(self.launch_angle))
            u_right = (math.cos(self.launch_angle), -math.sin(self.launch_angle))
            def to_world(pt):
                x_r, y_f = pt
                return (x_pos + x_r * u_right[0] + y_f * u_forward[0],
                        y_pos + x_r * u_right[1] + y_f * u_forward[1])
            verts = [to_world(nose), to_world(right_tail), to_world(left_tail)]
            rocket_poly = mpatches.Polygon(verts, closed=True, facecolor=color, edgecolor='black', linewidth=2, zorder=6)
            ax.add_patch(rocket_poly)

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
                # Tail center in world coords (0, -L/2 in body frame)
                tail_world = to_world((0.0, -L_draw/2))
                # Flame direction opposite forward
                flame_dir = (-u_forward[0], -u_forward[1])
                end1 = (tail_world[0] + flame_dir[0] * actual_flame_length,
                        tail_world[1] + flame_dir[1] * actual_flame_length)
                end2 = (tail_world[0] + flame_dir[0] * actual_flame_length * 0.7,
                        tail_world[1] + flame_dir[1] * actual_flame_length * 0.7)
                ax.plot([tail_world[0], end1[0]], [tail_world[1], end1[1]],
                        color='orange', linewidth=max(1, int(8 * self.smooth_flame_intensity)), alpha=0.8)
                ax.plot([tail_world[0], end2[0]], [tail_world[1], end2[1]],
                        color='yellow', linewidth=max(1, int(4 * self.smooth_flame_intensity)), alpha=0.9)

            # Draw parachute if deployed
            if self.chute_deployed and self.chute_open_factor > 0.05:
                # Direction opposite velocity
                v_total = (self.launch_x_vel**2 + self.launch_velocity**2) ** 0.5
                if v_total < 1e-3:
                    para_dir = (0.0, 1.0)
                else:
                    para_dir = (-self.launch_x_vel / v_total, -self.launch_velocity / v_total)
                # Canopy center a bit behind rocket along para_dir
                canopy_offset = 0.9 * L_draw
                canopy_center = (x_pos + para_dir[0] * canopy_offset,
                                 y_pos + para_dir[1] * canopy_offset)
                canopy_radius = 0.35 * self.chute_open_factor
                canopy = mpatches.Circle(canopy_center, canopy_radius, facecolor='#A7C7E7', edgecolor='#3C2F1E', linewidth=2, alpha=0.85, zorder=5)
                ax.add_patch(canopy)
                # Lines (shrouds) to tail
                tail_anchor = to_world((0.0, -L_draw/2))
                ax.plot([tail_anchor[0], canopy_center[0]], [tail_anchor[1], canopy_center[1]], color='#3C2F1E', linewidth=1, alpha=0.8, zorder=5)

            # FBD arrows (thrust, drag, gravity) near rocket
            # Thrust
            max_thrust = max(thrusts) if thrusts else 1000
            t_scale = 0.4 * (current_thrust / max_thrust) if max_thrust > 0 else 0
            ax.arrow(x_pos, y_pos, u_forward[0]*t_scale, u_forward[1]*t_scale, head_width=0.06, head_length=0.08, fc='green', ec='green', alpha=0.8, zorder=7)
            # Drag opposite velocity
            if v_total > 1e-3:
                d_dir = (-self.launch_x_vel / v_total, -self.launch_velocity / v_total)
                d_scale = 0.4 * min(1.0, v_total / 50.0)
                ax.arrow(x_pos, y_pos, d_dir[0]*d_scale, d_dir[1]*d_scale, head_width=0.06, head_length=0.08, fc='red', ec='red', alpha=0.8, zorder=7)
            # Gravity
            g_len = 0.3
            ax.arrow(x_pos, y_pos, 0, -g_len, head_width=0.06, head_length=0.08, fc='blue', ec='blue', alpha=0.8, zorder=7)

        # Apogee flash marker
        if self.apogee_flash_frames and self.apogee_pos:
            fx, fy = self.apogee_pos
            flash_alpha = max(0.0, self.apogee_flash_frames / 30.0)
            ax.scatter([fx], [fy], s=180, c='#FFD447', edgecolors='#E94F37', linewidths=2, alpha=flash_alpha, zorder=8, marker='*')
            self.apogee_flash_frames = max(0, self.apogee_flash_frames - 1)
        
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
        ax.set_title(f'Rocket Launch - T+{t:.1f}s - Alt: {y_pos:.1f}m', fontsize=14, fontweight='bold')
        ax.set_xlabel('Drift (m)')
        ax.set_ylabel('Altitude (m)')
        # Theme-aware styling
        self.style_axes(ax)
        
        # Add status text
        if not stable and y_pos > 0:
            # Attach instability warning near the rocket so it's always visible
            ax.text(x_pos, y_pos + 0.5, 'UNSTABLE!', ha='center', va='center', 
                   fontsize=12, color='red', fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))
        
        if y_pos <= 0 and t > 1:
            ax.text(x_pos, 0.3, 'IMPACT!', ha='center', va='center', 
                   fontsize=14, color='red', fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='orange', alpha=0.9))
        
        self.launch_canvas.draw()
        
        # Update time
        self.launch_time += 0.05
        
        # End animation when rocket impacts ground, or after a safety max duration
        if (y_pos <= 0 and t > 1) or self.launch_time > 60:
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
        # Default to the thrust_curves directory in the project if it exists
        default_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'thrust_curves')
        if not os.path.isdir(default_dir):
            default_dir = ''
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Thrust Curve",
            default_dir,
            "Thrust Curves (*.csv *.eng *.rasp);;CSV Files (*.csv);;RASP/ENG Files (*.eng *.rasp);;All Files (*)",
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
        # No random time-based deployment by default; we deploy based on descent and height
        chute_deploy_time = None
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
         # --- Populate spreadsheet table ---
            headers = list(results[0].keys()) if results else []
            self.spreadsheet_table.setColumnCount(len(headers))
            self.spreadsheet_table.setRowCount(len(results))
            self.spreadsheet_table.setHorizontalHeaderLabels([h.capitalize() for h in headers])
            for row_idx, row in enumerate(results):
                for col_idx, key in enumerate(headers):
                    val = row[key]
                    # Format floats for readability
                    if isinstance(val, float):
                        val = f"{val:.4f}"
                    self.spreadsheet_table.setItem(row_idx, col_idx, QtWidgets.QTableWidgetItem(str(val)))
            self.spreadsheet_table.resizeColumnsToContents()
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
        # Apply theme-aware styling
        self.style_axes(ax)

        times = [r['time'] for r in results]
        # Pick series colors based on theme
        if self.current_theme == "retro":
            series_colors = ["#E94F37", "#1C77C3", "#FFD447", "#3C2F1E", "#A7C7E7", "#A259F7"]
        else:
            series_colors = ["#00D4FF", "#00FF41", "#FF6B35", "#ECF0F1", "#FFA500", "#FF69B4"]
        labels = ["Altitude", "Velocity", "Mass", "Acceleration", "Thrust", "Drag"]
        keys = ["altitude", "velocity", "mass", "acceleration", "thrust", "drag"]
        # Plot selected variable(s), but default to altitude for tooltip
        plotted = False
        tooltip_label = 'Altitude'
        tooltip_values = [r['altitude'] for r in results]
        for i, (label, key) in enumerate(zip(labels, keys)):
            if self.graph_vars[label].isChecked():
                values = [r.get(key, 0) for r in results]
                ax.plot(times, values, label=label, color=series_colors[i % len(series_colors)])
                if not plotted:
                    tooltip_label = label
                    tooltip_values = values
                plotted = True
        if not plotted:
            # Default to altitude if nothing selected
            ax.plot(times, tooltip_values, label=tooltip_label, color=series_colors[0])
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Value')
        ax.legend()
        ax.figure.tight_layout()
        self.canvas.draw()

        # === FBD Animation Overlay ===
        from matplotlib.lines import Line2D

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
        self._fbd_timer = QtCore.QTimer()
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
    # Global stylesheet removed; theming is applied per-widget via apply_theme

    # Splash screen with GIF animation
    gif_path = os.path.join(os.path.dirname(__file__), 'jarvis.gif')
    splash_movie = QtGui.QMovie(gif_path)
    
    if splash_movie.isValid():
        splash_label = QtWidgets.QLabel()
        splash_label.setMovie(splash_movie)
        splash_label.setWindowFlags(QtCore.Qt.SplashScreen | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        splash_label.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        splash_label.setAlignment(QtCore.Qt.AlignCenter)
        
        # Center the splash screen
        screen = app.primaryScreen().geometry()
        splash_label.resize(400, 300)  # Set appropriate size
        splash_label.move((screen.width() - 400) // 2, (screen.height() - 300) // 2)
        
        # Start animation and show
        splash_movie.start()
        splash_label.movie = splash_movie  # Prevent garbage collection
        splash_label.show()
        app.processEvents()
        
        # Show splash for 4 seconds, then show main window
        def show_main():
            splash_label.close()
            splash_movie.stop()
            window.show()
        
        window = RocketSimulationUI()
        QtCore.QTimer.singleShot(4000, show_main)
    else:
        print(f"Could not load splash GIF: {gif_path}")
        # Show main window immediately if GIF fails to load
        window = RocketSimulationUI()
        window.show()

    sys.exit(app.exec_())

def excepthook(type_, value, tb):
    error_text = ''.join(traceback.format_exception(type_, value, tb))
    dlg = CrashImageDialog(r'c:/blah blah blah/JARVIS/5cdd0647707b66d1d76174d4ffa47ce1.jpg', error_text)
    dlg.exec_()
    sys.exit(1)

sys.excepthook = excepthook


