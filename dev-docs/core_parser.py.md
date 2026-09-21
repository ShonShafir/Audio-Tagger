# `core/parser.py`

**Purpose**: The algorithmic heart of the application. This file contains a suite of Regular Expressions (Regex) and string manipulation functions designed to dissect dirty, complex electronic music filenames into clean metadata.

## Key Components

### Filename Cleaning
- **`normalize_feat(text, feat_fmt)`**: Standardizes various spellings of "featuring" (`feat`, `ft`, `ft.`, `featuring`) into a single user-defined format (e.g., `ft.`).
- **`strip_original_mix(text)`**: Removes redundant string bloat often found in DJ pools, specifically targeting `(Original Mix)` or `[Original Mix]`.
- **`title_case_smart(text)`**: Converts strings to Title Case, while explicitly ignoring uppercase abbreviations like "DJ" or "MC", and converting "and" to "&".

### Metadata Extraction
- **`extract_feat(artist_str, feat_fmt)`**: Splits a main artist string on the feature format. Returns a tuple of `(Main Artist, Featured Artist)`. Crucially truncates any trailing junk (like hyphens) from the featured artist.
- **`extract_remixer(title_str)`**: Uses Regex to find strings inside parenthesis or brackets containing the word "remix" or "mix", extracting the remixer's name and cleanly removing it from the main title string.

### Directory & M3U Scanning
- **`scan_m3u_files(folder)`**: Searches the target directory for `.m3u` playlists. Since many UK Hardcore releases distribute metadata via M3U files, this function extracts the `EXTINF` blocks to build a map of `filename -> Catalog Number`.

### Filename Generation
- **`build_proposed_filename(...)`**: Takes the user's template (e.g., `({catno}) {artist} - {title}.mp3`) and injects the parsed metadata into it. It sanitizes illegal Windows filesystem characters (`<>:"/\|?*`) before returning the final string.
