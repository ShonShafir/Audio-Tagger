# `core/config.py`

**Purpose**: Manages the application's configuration state, including default fallback values, JSON serialization, and column definitions.

## Key Components

### `FIXED_COLS`
A list of column headers that are permanently anchored to the main grid and cannot be hidden or disabled by the user:
- `"Check"`: The enable/disable row checkbox.
- `"Cover"`: The album art thumbnail.
- `"Original File"`: The read-only source filename.
- `"Proposed Filename"`: The generated destination filename.

These columns have their resize mode set to `ResizeToContents` in the UI to prevent them from breaking the grid layout.

### `DEFAULT_FIELDS`
A highly structured list of dictionaries defining the metadata fields. Each dictionary dictates:
- How the column is labeled (`label`).
- Its internal ID (`id`).
- Whether it defaults to visible (`visible`).
- Where its data originates (`source`: parsed, discogs, static).
- Which Discogs API field it maps to (`discogs_field`).
- Which ID3 frame it writes to (`id3_frame`).

### `load_config()` & `save_config(cfg)`
Handles reading and writing the user's settings to a local `config.json` file in the application directory. It ensures that if the config file is missing or corrupted, the application degrades gracefully by returning a deep copy of `DEFAULT_CONFIG`.
