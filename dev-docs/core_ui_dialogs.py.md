# `core/ui/dialogs.py`

**Purpose**: Contains all the modal popup dialogs used throughout the application.

## Key Components

### `FindReplaceDialog`
A sophisticated bulk editing tool.
- Takes the current table data and the set of user-highlighted rows.
- The user can select a target column, enter a search term, and a replacement term.
- It dynamically generates a live preview table showing exactly which cells will be affected and what their new values will look like.
- When accepted, it returns a list of specific cells to the main thread for instant updating.

### `ColumnManagerDialog`
Allows the user to reconfigure the dynamic columns of the main table.
- Supports Drag-and-Drop reordering using a custom `QListWidget`.
- Users can toggle column visibility and edit the specific ID3 mappings for custom fields.

### `DiscogsSearchDialog`
A manual override dialog. If the automated Catalog Number search fails or fetches the wrong release, the user can right-click a row and select "Search Discogs Manually".
- Allows text-based searching (e.g., Artist + Title).
- Previews the cover art and release details of the selected result.
- Returns the specific Discogs Release ID to the main thread for a targeted metadata fetch.
