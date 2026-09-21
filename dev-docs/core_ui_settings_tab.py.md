# `core/ui/settings_tab.py`

**Purpose**: The configuration interface for the application, handling all user preferences and API credentials.

## Key Components

### `SettingsTab`
A `QWidget` subclass containing `QFormLayout` elements for various settings.
- **Discogs Token**: Text field for the API token.
- **Naming Template**: Text field allowing users to configure how files are renamed (e.g., `{artist} - {title}`).
- **Rate Limit**: Spinbox for configuring the API delay in seconds.
- **Toggles**: Checkboxes for "Strip 'Original Mix'", "Embed Cover Art", etc.

### `FieldsConfigWidget`
A specialized inner widget used within the settings tab to configure the dynamic columns. It lists the `DEFAULT_FIELDS` and allows users to set static fallbacks (e.g., always set Genre to "Electronic").

### Real-time Saving
The tab implements a `save()` method that serializes the current form state into a dictionary and writes it to `config.json` via `config.save_config()`. This ensures user preferences persist between sessions.
