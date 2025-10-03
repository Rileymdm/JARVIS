"""
JARVIS Rocket Simulation - Theme System
======================================

This module handles all theming functionality for the JARVIS rocket simulation UI.
Extracted from main.py for better code organization and maintainability.

Features:
- Theme definitions (Retro and Professional)
- Theme application and styling
- Plot styling utilities
- Theme preference management
"""

import os
import json
from PyQt5 import QtCore


class ThemeManager:
    """Manages themes for the JARVIS Rocket Simulation UI"""
    
    def __init__(self, ui_instance=None):
        """
        Initialize the theme manager
        
        Args:
            ui_instance: Reference to the main UI instance for applying themes
        """
        self.ui = ui_instance
        self.current_theme = "retro"  # Default theme
        self.themes = self._setup_themes()
        self.user_settings_file = None
        
        if ui_instance and hasattr(ui_instance, 'user_settings_file'):
            self.user_settings_file = ui_instance.user_settings_file
    
    def _setup_themes(self):
        """Define all available themes for the application"""
        return {
            "retro": {
                "name": "JARVIS Retro",
                "description": "Classic 8BitDo retro gaming aesthetic with modern sleek enhancements",
                "colors": {
                    "primary_bg": "#F8F5E3",
                    "secondary_bg": "#FDF6E3", 
                    "accent": "#BCA16A",
                    "accent_light": "#D4C389",
                    "accent_dark": "#A08D5A",
                    "primary_text": "#3C2F1E",
                    "secondary_text": "#5A4A35",
                    "button_bg": "#E94F37",
                    "button_hover": "#FF6B35",
                    "button_active": "#D63E2A",
                    "button_text": "#F8F5E3",
                    "card_bg": "#FFFFFF",
                    "card_shadow": "rgba(60, 47, 30, 0.1)",
                    "success": "#2E8B57",
                    "success_light": "#3CB371",
                    "warning": "#FF6347",
                    "warning_light": "#FF7F50",
                    "info": "#4169E1",
                    "info_light": "#6495ED",
                    "border_subtle": "#E8E0CC",
                    "hover_overlay": "rgba(233, 79, 55, 0.1)"
                },
                "gradients": {
                    "primary": "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #FDF6E3, stop: 1 #F8F5E3)",
                    "button": "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #FF6B35, stop: 1 #E94F37)",
                    "card": "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #FFFFFF, stop: 1 #FDFDFD)",
                    "accent": "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #D4C389, stop: 1 #BCA16A)"
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
                "description": "Mission control center dark theme with sleek modern enhancements",
                "colors": {
                    "primary_bg": "#2C3E50",
                    "secondary_bg": "#34495E",
                    "tertiary_bg": "#3D566E",
                    "accent": "#00D4FF",
                    "accent_light": "#33DDFF",
                    "accent_dark": "#00B8E6",
                    "primary_text": "#ECF0F1",
                    "secondary_text": "#BDC3C7",
                    "muted_text": "#95A5A6",
                    "button_bg": "#E94F37",
                    "button_hover": "#FF6B35",
                    "button_active": "#D63E2A",
                    "button_text": "#FFFFFF",
                    "card_bg": "#394A5F",
                    "card_shadow": "rgba(0, 0, 0, 0.3)",
                    "success": "#00FF41",
                    "success_dark": "#00CC34",
                    "warning": "#FF6B35",
                    "warning_dark": "#E55A2B",
                    "info": "#0099FF",
                    "info_dark": "#0077CC",
                    "border_subtle": "#4A5F7A",
                    "hover_overlay": "rgba(0, 212, 255, 0.1)",
                    "glass_bg": "rgba(52, 73, 94, 0.8)",
                    "glass_border": "rgba(0, 212, 255, 0.3)"
                },
                "gradients": {
                    "primary": "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #34495E, stop: 1 #2C3E50)",
                    "button": "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #FF6B35, stop: 1 #E94F37)",
                    "card": "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3D566E, stop: 1 #394A5F)",
                    "accent": "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #33DDFF, stop: 1 #00D4FF)",
                    "glass": "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 rgba(61, 86, 110, 0.9), stop: 1 rgba(52, 73, 94, 0.8))"
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
    
    def get_enhanced_progress_bar_style(self, theme_name=None):
        """Get enhanced progress bar styling with modern design"""
        theme = self.get_theme(theme_name)
        theme_name = theme_name or self.current_theme
        
        if theme_name == "retro":
            return f"""
                QProgressBar {{
                    background: {theme['colors']['card_bg']};
                    border: 2px solid {theme['colors']['accent']};
                    border-radius: 12px;
                    height: 28px;
                    color: {theme['colors']['primary_text']};
                    font-weight: bold;
                    font-size: 14px;
                    text-align: center;
                    padding: 2px;
                }}
                QProgressBar::chunk {{
                    background: {theme['gradients']['button']};
                    border-radius: 8px;
                    margin: 2px;
                }}
            """
        else:
            return f"""
                QProgressBar {{
                    background: {theme['colors']['card_bg']};
                    border: 1px solid {theme['colors']['border_subtle']};
                    border-radius: 10px;
                    height: 24px;
                    color: {theme['colors']['primary_text']};
                    font-weight: bold;
                    font-size: 13px;
                    text-align: center;
                    padding: 2px;
                }}
                QProgressBar::chunk {{
                    background: {theme['gradients']['accent']};
                    border-radius: 8px;
                    margin: 1px;
                }}
            """