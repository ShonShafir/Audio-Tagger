# `core/ui/tagger_tab.py`

**Purpose**: The absolute core of the application's user interface. It acts as the controller bridging the `QTableWidget` (the grid) with the background workers.

## Key Components

### `TaggerTabMixin`
A massive mixin class injected into `app.py`. It handles:
- **UI Layout**: Building the top toolbar and the massive `QTableWidget`.
- **Pill Toggles**: Generates "Pill" styled checkable buttons above the table for instant column hiding/showing.
- **Event Handling**: Connecting buttons to their respective worker launch methods (`run_scan`, `run_discogs`, `apply_action`).

### `_build_cols()` & `_fill_table()`
Dynamically generates the columns based on the user's `config.json`.
- `FIXED_COLS` are set to `ResizeToContents`.
- Dynamic columns (and filenames) are set to `Interactive` with explicit widths to allow horizontal scrolling.
- `_fill_table()` iterates over the `self.rows` data model, converting strings and binary image data into `QTableWidgetItem` and custom `cellWidgets`.

### Cell Targeting & Extraction
The application features a powerful cell-targeting system.
- Before launching a Re-scan or Discogs fetch, the tab calls `self.table.selectedIndexes()`.
- If specific cells are highlighted, it builds a precise map of exactly which row and column intersections are allowed to be modified.
- The background workers receive this map and ensure they only overwrite the targeted data, preserving all other manual edits in memory.

### Context Menus & Interaction
- Double-clicking a cell plays the MP3 file in the `AudioPlayerBar`.
- Single-clicking clears existing selections and highlights the target cell.
- Right-clicking triggers a `QMenu` allowing manual Discogs searching or quick clear actions.

### Duplicate Highlight (`_check_duplicates`)
Iterates over the "Proposed Filename" column. If two rows share the exact same output filename, they are highlighted in red/amber to warn the user of an impending file overwrite.
