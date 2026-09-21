# Developer Documentation

Welcome to the Developer Documentation for Audio Tagger. This document outlines the project structure, architectural decisions, and data flow to help human developers and AI agents navigate, maintain, and extend the codebase.

## Project Architecture

The application follows a modular monolith architecture, separating the User Interface (PyQt6) from the core business logic (Parsing, API Clients, ID3 Tagging).

### Directory Structure

```text
audio-tagger/
├── app.py                  # Application entry point and Main Window setup
├── requirements.txt        # Python dependencies (PyQt6, mutagen, requests)
├── setup.iss               # Inno Setup script for building the Windows installer
├── app_icon.ico            # Application icon
├── README.md               # User-facing documentation
├── DEV_DOCS.md             # This file
└── core/                   # Core business logic and UI components
    ├── __init__.py
    ├── config.py           # Default configuration constants and column definitions
    ├── discogs.py          # DiscogsClient: API rate limiting, caching, and network requests
    ├── parser.py           # Filename and M3U parsing logic (Regex heavily utilized here)
    ├── tagger.py           # Mutagen ID3 manipulation (reading, writing, deleting frames)
    └── ui/                 # UI Sub-package
        ├── __init__.py
        ├── tagger_tab.py   # The primary spreadsheet grid view and layout
        ├── settings_tab.py # Configuration management view
        ├── dialogs.py      # Modal dialogs (Find & Replace, Column Manager, Discogs Manual Search)
        ├── widgets.py      # Reusable custom Qt widgets (AudioPlayerBar, ClickableImageLabel)
        └── workers.py      # QThread background workers (ScanWorker, DiscogsWorker, ApplyWorker)
```

## Core Components Deep Dive

### 1. Data Model & State (`tagger_tab.py`)
The primary source of truth for the application's state lives in the `TaggerTabMixin` class inside `tagger_tab.py`. 
- **`self.rows` (List[dict])**: An in-memory list of dictionaries representing the metadata for each file. 
- **Targeted Operations**: The UI allows users to highlight specific cells. When triggering actions like "Re-scan" or "Fetch Discogs", the application dynamically targets only the highlighted fields by extracting the selected indexes and passing a targeted dictionary to the background workers.

### 2. Threading Model (`workers.py`)
To prevent the PyQt GUI from freezing during heavy I/O operations (network requests, ID3 writes), all heavy lifting is offloaded to `QThread` workers:
- **`ScanWorker`**: Parses filenames and M3U files on disk. Emits results back to the main thread.
- **`DiscogsWorker`**: Iterates through rows, querying the Discogs API via `DiscogsClient`. Handles image downloading.
- **`ApplyWorker`**: Executes the physical ID3 tag writing and file renaming.

*Note: Workers emit signals (`progress`, `row_updated`, `finished`, `error`) which the main thread connects to UI updates.*

### 3. ID3 Tagging Engine (`tagger.py`)
Uses the `mutagen` library to manipulate ID3v2.4 tags.
- Uses standard frames for basic metadata (`TIT2` for Title, `TPE1` for Artist, `TALB` for Album, `TCON` for Genre).
- Uses User-Defined Text Information frames (`TXXX`) for custom fields (`TXXX:FEATURED ARTIST`, `TXXX:REMIXER`, `TXXX:CATALOGNUMBER`).
- Cover art is embedded using the `APIC` frame. The engine ensures existing `APIC` frames are wiped before appending new ones to prevent duplicate embedded covers.
- **Defensive Programming Disabled**: The tagging engine is designed to fail loudly. Exceptions during file writing are caught by the `ApplyWorker` and surfaced in the UI error log, preventing silent corruption.

### 4. Filename Parsing (`parser.py`)
Relies on a suite of specialized Regex functions designed to clean up electronic music filenames.
- Strips leading numbers, bitrates, and ID tags (e.g., `01-`, `_320kbps`).
- Splits Artist and Title on ` - `.
- Extracts Featured Artists (`ft.`, `feat.`) into a dedicated variable, ensuring they are removed from the main Artist string.
- Automatically searches parent directory names for Catalog Numbers (e.g., `BBD013`) if M3U files are missing.

## Development Workflow & Rules

For future agents and developers contributing to this codebase, please adhere to these strict rules established during the project's inception:

1. **No Silent Failures**: Avoid broad `try/except: pass` blocks. Catch specific exceptions, log them, and surface them to the user.
2. **Data Safety**: Never use `shutil.rmtree` or aggressive recursive deletions on the user's music directories.
3. **UI Responsiveness**: Any operation that takes longer than 100ms (API calls, bulk file system operations) MUST be executed in a `QThread` inside `workers.py`.
4. **Targeted Cell Execution**: Always respect table selections. If a user highlights specific cells, background operations must only overwrite those specific fields in memory, leaving the rest untouched.
5. **Executable Compilation**: The project is compiled using PyInstaller (`--noupx` to avoid antivirus false positives) and packaged using Inno Setup (`setup.iss`). Use `sys._MEIPASS` for resolving static asset paths (like `app_icon.ico`) when running as a compiled executable.

## Building the Executable (Windows)

To completely avoid Windows Defender false positives that plague PyInstaller, this project is packaged using an official, standalone Portable Python environment.

To compile the application into a standalone Windows installer:

```powershell
# 1. Download and build the Portable Python environment
mkdir PortableAudioTagger
cd PortableAudioTagger
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" -OutFile "python-embed.zip"
Expand-Archive -Path "python-embed.zip" -DestinationPath "."
rm "python-embed.zip"

# 2. Enable site-packages and install dependencies
(Get-Content "python311._pth") -replace "#import site", "import site" | Set-Content "python311._pth"
Copy-Item "..\get-pip.py" -Destination "."
.\python.exe get-pip.py
.\python.exe -m pip install PyQt6 mutagen requests

# 3. Copy source files into the portable environment
Copy-Item "..\app.py" -Destination "."
Copy-Item "..\app_icon.ico" -Destination "."
Copy-Item -Path "..\core" -Destination "core" -Recurse

# 4. Create the execution shortcut script
Set-Content -Path "Run Audio Tagger.vbs" -Value "CreateObject(`"WScript.Shell`").Run `"pythonw.exe app.py`", 0, False"
cd ..

# 5. Create the Installer (requires Inno Setup CLI)
ISCC.exe setup.iss
```

The resulting installer will be output to the `Output/` directory.
