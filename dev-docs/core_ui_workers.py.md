# `core/ui/workers.py`

**Purpose**: Houses the `QThread` subclasses responsible for all heavy processing. This ensures the PyQt GUI remains perfectly responsive (60fps) during intensive tasks.

## Key Components

### `ScanWorker(QThread)`
- **Task**: Recursively scans a selected directory for `.mp3` files. Reads adjacent `.m3u` files to map Catalog Numbers to filenames. Runs the complex regex parsing suite from `parser.py`.
- **Targeting**: Accepts a `target_paths` dictionary. If provided, it will only parse and update the specific fields (columns) of the specific files (rows) requested, leaving the rest of the in-memory row data intact.
- **Signals**: Emits `finished(results_list)` when complete.

### `DiscogsWorker(QThread)`
- **Task**: Iterates over the `rows` data model. Uses `DiscogsClient` to fetch release metadata and download cover art images based on the Catalog Number.
- **Caching**: Implements a robust internal memory cache (`cache_rel` and `cache_cov`). If multiple tracks share the same Catalog Number (an EP or Album), it only queries the Discogs API once, instantly applying the cached result to subsequent rows.
- **Targeting**: Identical to `ScanWorker`, it respects a `target_cells` map to ensure manual edits in unselected columns are not overwritten by Discogs data.
- **Signals**: Emits `row_updated` after each successful fetch to allow the UI to update progressively.

### `ApplyWorker(QThread)`
- **Task**: Executes the physical file modifications. Iterates over enabled rows, calls `write_tags` in `tagger.py`, and finally renames the `.mp3` file to the generated "Proposed Filename".
- **Safety**: Contains internal exception handling to prevent a single file-lock or permission error from crashing the entire batch operation. Emits errors to be logged by the UI.
