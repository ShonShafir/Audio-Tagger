"""
core/config.py
--------------
Application-wide constants, default field definitions, and
configuration persistence (load / save JSON).

Adding a new field to the app?  Add one dict to DEFAULT_FIELDS here —
everything else (UI columns, Discogs fetching, ID3 writing) picks it up
automatically.
"""

import os
import json
import copy

import sys

def _get_config_dir(app_name="AudioTagger") -> str:
    """Return the correct cross-platform app data directory."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:  # Linux and others
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return os.path.join(base, app_name)

CONFIG_DIR = _get_config_dir()
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

# Old path next to app.py (for backward compatibility if run from source)
_LEGACY_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config.json",
)

# Sources a field value can come from
FIELD_SOURCES = ["parsed", "static", "discogs", "template", "fallback"]

# Columns that are always present and cannot be hidden by the user
FIXED_COLS = ["Check", "Cover", "Original File", "Proposed Filename"]


# ── Default field definitions ─────────────────────────────────────────────────
# Each dict describes one metadata field.  Keys:
#   id            — internal identifier used throughout the code
#   label         — column header shown in the UI
#   visible       — shown in table by default?
#   source        — where the value comes from (see FIELD_SOURCES)
#   static_value  — value used when source is "static" or "both"
#   template_value— value used when source is "template"
#   fallback_order— list of sources when source is "fallback"
#   discogs_field — dot-path into the Discogs release JSON
#   id3_frame     — ID3 frame name (TPE1, TIT2, TXXX:XXX, …)
#   editable      — can the user edit the cell directly?
#   transform     — pipe-separated transform expression (see core/transforms.py)

DEFAULT_FIELDS = [
    {
        "id": "file_type", "label": "Type", "visible": True,
        "source": "parsed", "static_value": "", "template_value": "", "fallback_order": ["parsed"],
        "discogs_field": "", "id3_frame": "",
        "editable": False, "transform": "",
    },
    {
        "id": "artist", "label": "Artist", "visible": True,
        "source": "parsed", "static_value": "", "template_value": "", "fallback_order": ["parsed", "discogs"],
        "discogs_field": "artists", "id3_frame": "TPE1",
        "editable": True, "transform": r"s/\band\b/\&/i",
    },
    {
        "id": "featured", "label": "Featured Artist", "visible": True,
        "source": "parsed", "static_value": "", "template_value": "", "fallback_order": ["parsed", "discogs"],
        "discogs_field": "", "id3_frame": "TXXX:FEATURED ARTIST",
        "editable": True, "transform": "",
    },
    {
        "id": "title", "label": "Title", "visible": True,
        "source": "parsed", "static_value": "", "template_value": "", "fallback_order": ["parsed", "discogs"],
        "discogs_field": "", "id3_frame": "TIT2",
        "editable": True, "transform": "",
    },
    {
        "id": "remixer", "label": "Remixer", "visible": True,
        "source": "parsed", "static_value": "", "template_value": "", "fallback_order": ["parsed", "discogs"],
        "discogs_field": "", "id3_frame": "TXXX:REMIXER",
        "editable": True, "transform": "",
    },
    {
        "id": "catno", "label": "CatNo", "visible": True,
        "source": "parsed", "static_value": "", "template_value": "", "fallback_order": ["parsed"],
        "discogs_field": "", "id3_frame": "TXXX:CATALOGNUMBER",
        "editable": True, "transform": "",
    },
    {
        "id": "date", "label": "Date", "visible": True,
        "source": "discogs", "static_value": "", "template_value": "", "fallback_order": ["discogs", "parsed"],
        "discogs_field": "released", "id3_frame": "TXXX:DATE",
        "editable": True, "transform": "date:dd-mm-yyyy",
    },
    {
        "id": "style", "label": "Style", "visible": True,
        "source": "static", "static_value": "UK Hardcore", "template_value": "", "fallback_order": ["static"],
        "discogs_field": "styles", "id3_frame": "TXXX:STYLE",
        "editable": True, "transform": "",
    },
    {
        "id": "country", "label": "Country", "visible": True,
        "source": "static", "static_value": "UK", "template_value": "", "fallback_order": ["static"],
        "discogs_field": "country", "id3_frame": "TXXX:COUNTRY",
        "editable": True, "transform": "",
    },
    {
        "id": "genre", "label": "Genre", "visible": False,
        "source": "discogs", "static_value": "", "template_value": "", "fallback_order": ["discogs"],
        "discogs_field": "genres", "id3_frame": "TCON",
        "editable": True, "transform": "",
    },
    {
        "id": "label_name", "label": "Label", "visible": False,
        "source": "discogs", "static_value": "", "template_value": "", "fallback_order": ["discogs"],
        "discogs_field": "labels", "id3_frame": "TXXX:LABEL",
        "editable": True, "transform": "",
    },
    {
        "id": "album", "label": "Album", "visible": False,
        "source": "discogs", "static_value": "", "template_value": "", "fallback_order": ["discogs"],
        "discogs_field": "title", "id3_frame": "TALB",
        "editable": True, "transform": "",
    },
]

DEFAULT_CONFIG = {
    "discogs_token": "", "rate_limit": 2.5,
    "discogs_fallbacks": [
        "{catno} {artist} {title}",
        "{catno} {artist}",
        "{catno}"
    ],
    "naming_template": "({catno}) {artist} - {title}.mp3",
    "feat_format": "ft.", "strip_original_mix": True,
    "embed_cover_art": True, "cover_fallback_local": True,
    "fields": DEFAULT_FIELDS,
    "theme": {"preset": "Dark", "custom": {}},
}


# ── Persistence ───────────────────────────────────────────────────────────────

def load_config() -> dict:
    """Load config from disk, merging with DEFAULT_CONFIG for missing keys."""
    # Migrate legacy config to AppData if it exists and new one doesn't
    if os.path.exists(_LEGACY_CONFIG_PATH) and not os.path.exists(CONFIG_PATH):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            import shutil
            shutil.copy2(_LEGACY_CONFIG_PATH, CONFIG_PATH)
        except Exception:
            pass

    path_to_load = CONFIG_PATH if os.path.exists(CONFIG_PATH) else _LEGACY_CONFIG_PATH

    if os.path.exists(path_to_load):
        try:
            with open(path_to_load, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = copy.deepcopy(DEFAULT_CONFIG)
            cfg.update({k: v for k, v in data.items() if k != "fields"})
            if "fields" in data:
                cfg["fields"] = data["fields"]
            return cfg
        except Exception:
            pass
            
    return copy.deepcopy(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    """Persist *cfg* to disk as formatted JSON."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

