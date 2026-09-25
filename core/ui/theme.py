"""
core/ui/theme.py
----------------
Theme engine: built-in palette definitions, stylesheet generator, and
palette resolver.

Public API
----------
PRESETS                 — dict of named preset palettes
PALETTE_LABELS          — human-readable label for each colour token
build_stylesheet(p)     — generate a complete QSS string from a palette dict
get_palette(cfg)        — resolve the active palette from the config dict
"""

# ── Palette token labels (used in the Settings UI) ────────────────────────────

PALETTE_LABELS = {
    "bg_base":          "Table / base background",
    "bg_window":        "Window background",
    "bg_surface":       "Alternate row / surface",
    "bg_input":         "Input field background",
    "bg_header":        "Header / tab background",
    "bg_selection":     "Selected row highlight",
    "bg_cell_selection": "Selected cell background",
    "bg_cell_hover":    "Cell hover background",
    "text_primary":     "Primary text",
    "text_muted":       "Muted / secondary text",
    "text_readonly":    "Read-only cell text",
    "accent":           "Accent (buttons, progress)",
    "accent_hover":     "Accent hover",
    "accent_disabled":  "Disabled button",
    "border":           "Borders & grid lines",
    "error":            "Error / warning colour",
    "accent_apply":     "Apply Button Accent",
    "accent_apply_hover": "Apply Button Hover",
}

# ── Built-in presets ──────────────────────────────────────────────────────────

PRESETS: dict[str, dict[str, str]] = {
    "Dark": {
        "bg_base":         "#181825",
        "bg_window":       "#1e1e2e",
        "bg_surface":      "#1e1e2e",
        "bg_input":        "#313244",
        "bg_header":       "#313244",
        "bg_selection":    "#45475a",
        "bg_cell_selection": "#45475a",
        "bg_cell_hover":     "#45475a",
        "text_primary":    "#cdd6f4",
        "text_muted":      "#6c7086",
        "text_readonly":   "#585b70",
        "accent":          "#89b4fa",
        "accent_hover":    "#b4befe",
        "accent_disabled": "#45475a",
        "border":          "#45475a",
        "error":           "#f38ba8",
        "accent_apply":    "#a6e3a1",
        "accent_apply_hover": "#94e2d5",
    },
    "Light": {
        "bg_base":         "#ffffff",
        "bg_window":       "#f5f5f5",
        "bg_surface":      "#ebebeb",
        "bg_input":        "#ffffff",
        "bg_header":       "#e0e0e0",
        "bg_selection":    "#d0e4ff",
        "bg_cell_selection": "#d0e4ff",
        "bg_cell_hover":     "#d0e4ff",
        "text_primary":    "#1e1e2e",
        "text_muted":      "#666677",
        "text_readonly":   "#888899",
        "accent":          "#1565c0",
        "accent_hover":    "#1976d2",
        "accent_disabled": "#bdbdbd",
        "border":          "#cccccc",
        "error":           "#c62828",
        "accent_apply":    "#2e7d32",
        "accent_apply_hover": "#4caf50",
    },
    "Dracula": {
        "bg_base":         "#282a36",
        "bg_window":       "#1e1f29",
        "bg_surface":      "#282a36",
        "bg_input":        "#44475a",
        "bg_header":       "#44475a",
        "bg_selection":    "#44475a",
        "bg_cell_selection": "#44475a",
        "bg_cell_hover":     "#44475a",
        "text_primary":    "#f8f8f2",
        "text_muted":      "#6272a4",
        "text_readonly":   "#6272a4",
        "accent":          "#bd93f9",
        "accent_hover":    "#ff79c6",
        "accent_disabled": "#44475a",
        "border":          "#6272a4",
        "error":           "#ff5555",
        "accent_apply":    "#50fa7b",
        "accent_apply_hover": "#8be9fd",
    },
    "Nord": {
        "bg_base":         "#2e3440",
        "bg_window":       "#242933",
        "bg_surface":      "#2e3440",
        "bg_input":        "#3b4252",
        "bg_header":       "#3b4252",
        "bg_selection":    "#434c5e",
        "bg_cell_selection": "#434c5e",
        "bg_cell_hover":     "#434c5e",
        "text_primary":    "#d8dee9",
        "text_muted":      "#4c566a",
        "text_readonly":   "#4c566a",
        "accent":          "#88c0d0",
        "accent_hover":    "#81a1c1",
        "accent_disabled": "#434c5e",
        "border":          "#4c566a",
        "error":           "#bf616a",
        "accent_apply":    "#a3be8c",
        "accent_apply_hover": "#8fbcbb",
    },
    "Solarized Dark": {
        "bg_base":         "#002b36",
        "bg_window":       "#001f27",
        "bg_surface":      "#002b36",
        "bg_input":        "#073642",
        "bg_header":       "#073642",
        "bg_selection":    "#073642",
        "bg_cell_selection": "#073642",
        "bg_cell_hover":     "#073642",
        "text_primary":    "#839496",
        "text_muted":      "#586e75",
        "text_readonly":   "#586e75",
        "accent":          "#268bd2",
        "accent_hover":    "#2aa198",
        "accent_disabled": "#073642",
        "border":          "#586e75",
        "error":           "#dc322f",
        "accent_apply":    "#859900",
        "accent_apply_hover": "#b58900",
    },
    "Solarized Light": {
        "bg_base":         "#fdf6e3",
        "bg_window":       "#eee8d5",
        "bg_surface":      "#fdf6e3",
        "bg_input":        "#eee8d5",
        "bg_header":       "#eee8d5",
        "bg_selection":    "#eee8d5",
        "bg_cell_selection": "#eee8d5",
        "bg_cell_hover":     "#eee8d5",
        "text_primary":    "#657b83",
        "text_muted":      "#93a1a1",
        "text_readonly":   "#93a1a1",
        "accent":          "#268bd2",
        "accent_hover":    "#2aa198",
        "accent_disabled": "#eee8d5",
        "border":          "#93a1a1",
        "error":           "#dc322f",
        "accent_apply":    "#859900",
        "accent_apply_hover": "#2aa198",
    },
    "Monokai": {
        "bg_base":         "#272822",
        "bg_window":       "#1e1f1c",
        "bg_surface":      "#272822",
        "bg_input":        "#3e3d32",
        "bg_header":       "#3e3d32",
        "bg_selection":    "#49483e",
        "bg_cell_selection": "#49483e",
        "bg_cell_hover":     "#49483e",
        "text_primary":    "#f8f8f2",
        "text_muted":      "#75715e",
        "text_readonly":   "#75715e",
        "accent":          "#66d9ef",
        "accent_hover":    "#fd971f",
        "accent_disabled": "#49483e",
        "border":          "#75715e",
        "error":           "#f92672",
        "accent_apply":    "#a6e22e",
        "accent_apply_hover": "#e6db74",
    },
}


# ── Stylesheet builder ────────────────────────────────────────────────────────

def build_stylesheet(p: dict) -> str:
    """Generate a complete Qt Style Sheet string from palette dict *p*.

    *p* must contain all 14 colour tokens defined in PALETTE_LABELS.
    Any missing key falls back to the Dark preset value.
    """
    d = dict(PRESETS["Dark"])   # safe fallback
    d.update(p)

    return f"""
    QMainWindow, QWidget {{
        background: {d['bg_window']};
        color: {d['text_primary']};
        font-size: {d.get('font_size', 13)}px;
    }}
    QTableWidget {{
        background: {d['bg_base']};
        gridline-color: {d['border']};
                alternate-background-color: {d['bg_surface']};
        color: {d['text_primary']};
    }}
    QTableWidget::item {{
        border-right: 1px solid {d['border']};
        border-bottom: 1px solid {d['border']};
        padding: 2px;
    }}
    QTableWidget::item:hover {{
        background-color: {d.get('bg_cell_hover', d['bg_selection'])};
    }}
    QTableWidget::item:selected {{
        background-color: {d.get('bg_cell_selection', d['bg_selection'])};
        color: {d['text_primary']};
    }}
    QHeaderView::section {{
        background: {d['bg_header']};
        color: {d['text_primary']};
        padding: 6px;
        border: none;
        border-right: 1px solid {d['border']};
        border-bottom: 1px solid {d['border']};
        font-weight: bold;
    }}
    QPushButton {{
        background: {d['accent']};
        color: {d['bg_base']};
        border-radius: 6px;
        padding: 6px 14px;
        font-weight: bold;
        border: none;
    }}
    QPushButton:hover {{
        background: {d['accent_hover']};
    }}
    QPushButton#btnApply {{
        background: {d.get('accent_apply', d['accent'])};
        color: #1e1e2e;
    }}
    QPushButton#btnApply:hover {{
        background: {d.get('accent_apply_hover', d['accent_hover'])};
    }}
    QPushButton:disabled {{
        background: {d['accent_disabled']};
        color: {d['text_muted']};
    }}
    QPushButton:checked {{
        background: {d['accent_hover']};
    }}
    QPushButton[pill="true"] {{
        background-color: {d['bg_input']};
        color: {d['text_muted']};
        border-radius: 12px;
        padding: 4px 14px;
        font-weight: 600;
        border: 2px solid transparent;
    }}
    QPushButton[pill="true"]:hover {{
        background-color: {d['bg_cell_hover']};
        color: {d['text_primary']};
    }}
    QPushButton[pill="true"]:checked {{
        background-color: transparent;
        color: {d['accent']};
        border: 2px solid {d['accent']};
    }}
    QPushButton[pill="true"]:checked:hover {{
        background-color: {d['bg_cell_hover']};
        color: {d['accent_hover']};
        border: 2px solid {d['accent_hover']};
    }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background: {d['bg_input']};
        border: 1px solid {d['border']};
        border-radius: 4px;
        padding: 4px 6px;
        color: {d['text_primary']};
    }}
    QComboBox QAbstractItemView {{
        background: {d['bg_input']};
        color: {d['text_primary']};
            }}
    QProgressBar {{
        background: {d['bg_input']};
        border-radius: 4px;
        text-align: center;
        height: 16px;
        color: {d['text_primary']};
    }}
    QProgressBar::chunk {{
        background: {d['accent']};
        border-radius: 4px;
    }}
    QTabWidget::pane {{
        border: 1px solid {d['border']};
    }}
    QTabBar::tab {{
        background: {d['bg_header']};
        color: {d['text_primary']};
        padding: 8px 18px;
        margin-right: 2px;
        border-radius: 4px 4px 0 0;
    }}
    QTabBar::tab:selected {{
        background: {d['bg_selection']};
    }}
    QTabBar::tab:hover {{
        background: {d['bg_selection']};
    }}
    QDialog {{
        background: {d['bg_window']};
        color: {d['text_primary']};
    }}
    QListWidget {{
        background: {d['bg_base']};
        border: 1px solid {d['border']};
        color: {d['text_primary']};
    }}
    QListWidget::item:selected {{
        background: {d['bg_selection']};
    }}
    QScrollBar:vertical {{
        background: {d['bg_surface']};
        width: 10px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: {d['border']};
        border-radius: 5px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QCheckBox {{
        color: {d['text_primary']};
    }}
    QLabel {{
        color: {d['text_primary']};
        background: transparent;
    }}
    QStatusBar {{
        background: {d['bg_header']};
        color: {d['text_muted']};
    }}
    QTextBrowser {{
        background: {d['bg_window']};
        color: {d['text_primary']};
        border: none;
    }}
    QMessageBox {{
        background: {d['bg_window']};
        color: {d['text_primary']};
    }}
    QToolTip {{
        background: {d['bg_header']};
        color: {d['text_primary']};
        border: 1px solid {d['border']};
        padding: 4px;
    }}
    """


# ── Palette resolver ──────────────────────────────────────────────────────────

def get_palette(cfg: dict) -> dict:
    """Resolve the active colour palette from *cfg*.

    Logic:
    1. Start with the named preset (default: "Dark").
    2. Overlay any custom overrides from cfg["theme"]["custom"].
    """
    theme_cfg = cfg.get("theme", {})
    preset    = theme_cfg.get("preset", "Dark")
    base      = dict(PRESETS.get(preset, PRESETS["Dark"]))
    custom    = theme_cfg.get("custom", {})
    base.update({k: v for k, v in custom.items() if k in PALETTE_LABELS})
    base["font_size"] = cfg.get("font_size", 13)
    return base
