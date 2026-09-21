# `core/ui/widgets.py`

**Purpose**: A library of custom Qt widgets utilized throughout the application to provide specialized functionality.

## Key Components

### `ClickableImageLabel`
A subclass of `QLabel` designed to hold cover art thumbnails in the grid.
- Overrides mouse events to allow drag-and-drop. Users can drag an image file directly from their OS into this label to instantly update a track's cover art.
- Overrides `mouseDoubleClickEvent` to open an enlarged pop-out view of the cover art.
- Overrides `mousePressEvent` to explicitly pass click events back to the parent `QTableWidget` to ensure native cell selection continues to function perfectly even when clicking the image.

### `AudioPlayerBar`
A floating or docked media player component using `QMediaPlayer` and `QAudioOutput`.
- Features Play/Pause controls, a timeline slider, and a volume slider.
- When a user double-clicks a row in the grid, the MP3 path is passed to this widget, and playback begins immediately.

### `DragDropTableWidget`
A subclass of `QTableWidget` used strictly within the `ColumnManagerDialog`.
- Implements `dropEvent` logic to allow users to visually reorder list items via drag-and-drop.
