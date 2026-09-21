# Audio Tagger

A powerful, specialized audio tagging and file renaming application built with PyQt6. Designed specifically for electronic music (like UK Hardcore), this tool automates the tedious process of parsing complex filenames, fetching highly accurate metadata from Discogs, and writing pristine ID3 tags.

## Features

- **Smart Filename Parsing**: Intelligently extracts Artist, Featured Artist, Title, Remixer, and Catalog Numbers from complex filenames. Automatically normalizes "Feat." and strips unwanted text like "(Original Mix)".
- **M3U Playlist Integration**: Automatically scans `.m3u` files in your directories to assign Catalog Numbers to unidentifiable tracks.
- **Discogs API Integration**: Fetches precise release metadata (Release Date, Style, Genre, Label, Album) and high-quality Cover Art using Catalog Numbers.
- **Spreadsheet-Style UI**: A fast, grid-based editor that lets you review and tweak metadata before applying changes.
- **Targeted Operations**: Select specific cells to selectively re-parse filenames or fetch Discogs data without overwriting your manual edits in other columns.
- **Bulk Find & Replace**: Easily fix recurring typos or rename specific artists across hundreds of tracks at once.
- **Duplicate Detection**: Instantly spots duplicate proposed filenames and highlights them in amber to prevent file overwrite collisions.
- **Audio Preview**: Double-click any track to preview it directly inside the app using the built-in audio player.
- **Fully Customizable**: Manage which columns are visible, configure the file renaming template, and define default static values for tags (like Genre or Country).

## Installation

### Windows
Download the latest `AudioTagger_Setup.exe` from the Releases page and run the installer.

### From Source
Ensure you have Python 3.9+ installed.

```bash
# Clone the repository
git clone https://github.com/yourusername/audio-tagger.git
cd audio-tagger

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

## Quick Start

1. **Configure Discogs**: Go to the **Settings** tab and enter your personal Discogs API Token (requires a free Discogs account).
2. **Select Folder**: Go to the **Tagger** tab, click **Select Folder**, and choose a folder containing your `.mp3` files.
3. **Re-scan**: The app will automatically parse the filenames and populate the grid.
4. **Fetch Discogs**: Click **Fetch Discogs** to pull release dates, styles, labels, and cover art for the identified Catalog Numbers.
5. **Apply**: Click **Apply Tags and Rename** to write the ID3 tags and safely rename your files according to your template.

## Documentation

For developers looking to contribute, modify, or understand the architecture of the application, please refer to the [Developer Documentation (DEV_DOCS.md)](DEV_DOCS.md).

## License

This project is licensed under the MIT License.
