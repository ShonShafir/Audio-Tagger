# `app.py`

**Purpose**: The main entry point of the Audio Tagger application. It initializes the PyQt6 application, sets up the main window, and applies the global dark theme.

## Key Components

### `resource_path(relative_path)`
A critical helper function used for compiling the app with PyInstaller. When PyInstaller bundles the app into a single executable, it unpacks assets (like `app_icon.ico`) into a temporary folder at runtime (`sys._MEIPASS`). This function ensures that the application can always locate its graphical assets whether running from source or as a compiled `.exe`.

### `AudioTaggerMainWindow(QMainWindow, TaggerTabMixin)`
The primary window of the application.
- **Multiple Inheritance**: It inherits from `QMainWindow` (the standard PyQt main window) and `TaggerTabMixin` (which injects all the logic and UI for the main tagging grid).
- **Tab Layout**: It initializes a `QTabWidget` with two main tabs:
  1. The **Tagger Tab** (built via `self._tagger_tab()` from the mixin).
  2. The **Settings Tab** (an instance of `SettingsTab`).
- **Global State**: Holds the active `rows` (metadata list) and `cfg` (user configuration dict).

### Application Initialization (`if __name__ == "__main__":`)
Bootstraps the `QApplication`, forces the window geometry to a comfortable size (`1400x800`), applies the Catppuccin-inspired dark mode stylesheet, and executes the event loop.
