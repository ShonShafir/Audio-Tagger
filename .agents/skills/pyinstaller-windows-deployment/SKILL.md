---
name: pyinstaller-windows-deployment
description: >-
  Expertise in PyInstaller for compiling secure, robust Windows executables. Use this
  skill to handle .spec files, inject version manifests (setup.iss), manage external
  binary dependencies, and avoid false-positive detections from Windows Defender.
---

# PyInstaller & Windows Deployment Expert

This skill guides the agent in cleanly compiling Python apps into standalone `.exe` files for Windows distribution.

## Core Directives

1. **One-Folder vs One-File**: Always prefer One-Folder builds (`--onedir`) wrapped with an Inno Setup installer. One-File builds (`--onefile`) extract to temp directories on every launch, which is slow and commonly triggers Windows Defender heuristics.
2. **Resource Resolution**: Use the `sys._MEIPASS` trick to reliably locate static assets (like `.ico`, `.png`, or `.json` configs) both in development and in the compiled exe.
3. **Hidden Imports**: If a library uses dynamic imports (e.g. mutagen loading specific file formats), ensure they are explicitly added to `hiddenimports=[]` in the `.spec` file.
4. **Version Info**: Always compile with a `version_info.txt` file so the `.exe` has legitimate properties (Company, Version, Description). This adds professionalism and lowers antivirus false-positives.
5. **No Console**: Ensure `--noconsole` is used for PyQt6 GUI apps so no empty black terminal window pops up in the background.
