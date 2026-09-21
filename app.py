"""
app.py — Audio Tagger entry point
----------------------------------
Run this file to launch the application:

    python app.py

All application logic lives in the core/ package:

    core/
    ├── config.py       — configuration constants, load/save
    ├── transforms.py   — string transforms (date, regex, sanitize)
    ├── parser.py       — filename parsing utilities
    ├── discogs.py      — Discogs API client
    ├── tagger.py       — ID3 tag helpers (mutagen)
    └── ui/
        ├── workers.py      — background QThread workers
        ├── widgets.py      — ClickableImageLabel, CoverViewDialog
        ├── dialogs.py      — ColumnManagerDialog, DiscogsSearchDialog
        ├── settings_tab.py — Settings panel
        ├── tagger_tab.py   — Tagger tab + table management (mixin)
        └── main_window.py  — MainWindow (composes everything)
"""

import sys
import os

# Ensure the project root is on the Python path so 'core' imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from core.ui.main_window import MainWindow

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Audio Tagger")
    
    icon_path = get_resource_path("app_icon.ico")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    win = MainWindow()
    if os.path.exists(icon_path):
        win.setWindowIcon(app_icon)
        
    win.show()
    sys.exit(app.exec())
