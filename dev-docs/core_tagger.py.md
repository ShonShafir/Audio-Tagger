# `core/tagger.py`

**Purpose**: The ID3 writing engine. It acts as an abstraction layer over the `mutagen` library, handling the physical writing of tags to MP3 files.

## Key Components

### ID3 Initialization
- **`load_or_create_id3(path)`**: Safely attempts to load existing ID3 tags from a file. If the file has no tags, it creates a pristine ID3v2.4 header.

### `write_tags(path, fv, cover_data, cfg)`
The primary function called by `ApplyWorker`. It takes a dictionary of fields (`fv`) and writes them to their designated ID3 frames based on `DEFAULT_FIELDS`.

#### Handling Standard Frames
Standard frames (`TIT2`, `TPE1`, `TALB`, `TCON`) are overwritten or added natively using the `mutagen.id3` namespace.

#### Handling Custom Frames (TXXX)
Non-standard metadata (like "Catalog Number", "Featured Artist", "Remixer") is stored using User-Defined Text Information (`TXXX`) frames. The engine ensures the description (e.g., `desc="CATALOGNUMBER"`) is properly formatted.

#### Handling Cover Art (APIC)
Embedding cover art in MP3 files is dangerous if done poorly (resulting in multiple layered covers that bloat file size). The tagging engine actively strips ALL existing `APIC` (Attached Picture) frames from the file before writing the new one, ensuring only a single, clean cover is embedded.

### Tag Clearing
- **`clear_user_tags(path, keep_fields)`**: A utility function that completely wipes ID3 tags from a file while preserving specific fields (like BPM or Key if necessary). Currently used as a pre-flight step to ensure old tags don't leak into the newly written file.
