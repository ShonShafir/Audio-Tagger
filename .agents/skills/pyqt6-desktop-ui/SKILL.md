---
name: pyqt6-desktop-ui
description: >-
  Expertise in PyQt6 for desktop application development. Use this skill when architecting
  complex UI layouts, handling multi-threading (QThread) to prevent UI freezes, applying
  advanced stylesheets (QSS), and managing cross-platform window behavior.
---

# PyQt6 Desktop UI Expert

This skill provides the agent with advanced knowledge for building flawless desktop apps with PyQt6.

## Core Directives

1. **Never Block the Main Thread**: All network requests, file I/O (like scanning folders or reading audio tags), and heavy computation MUST be delegated to a `QThread` worker.
2. **QThread Signal Mapping**: Always communicate between background workers and the UI using `pyqtSignal`. Never update a UI widget directly from inside `run()`.
3. **Responsive UI**: Ensure elements like progress bars reset smoothly, and use `sp.setRetainSizeWhenHidden(True)` where applicable so that hiding UI elements doesn't collapse layout geometry.
4. **Clean Code Separation**: Keep the `MainWindow` class strictly for window initialization and routing. Break out specific tabs (e.g. `TaggerTab`, `SettingsTab`) into separate classes or Mixins.
5. **Robust Theming**: When applying QSS themes dynamically, ensure that palettes are updated on the fly without requiring an app restart.
