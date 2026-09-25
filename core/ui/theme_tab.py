"""
core/ui/theme_tab.py
--------------------
Theme settings widget shown as the "Theme" sub-tab inside Settings.

Classes
-------
ColourRow        — One labelled row: [label | swatch button | hex input]
ThemeSettingsWidget — Full theme panel with preset picker + 14 colour rows

The widget emits ``theme_changed(dict)`` whenever any colour changes so the
main window can repaint the app immediately (live preview).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QGridLayout, QScrollArea, QSizePolicy,
    QColorDialog, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from core.ui.theme import PRESETS, PALETTE_LABELS


# ─────────────────────────────────────────────────────────────────────────────
# ColourRow — a single colour token editor
# ─────────────────────────────────────────────────────────────────────────────

class ColourRow(QWidget):
    """One editable colour row: [label | swatch | hex input]."""

    colour_changed = pyqtSignal(str, str)   # (token_key, hex_value)

    def __init__(self, key: str, label: str, colour: str, parent=None):
        super().__init__(parent)
        self.key = key
        layout   = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        lbl = QLabel(label)
        lbl.setFixedWidth(220)
        lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(lbl)

        # Coloured swatch button — click to open colour picker
        self.swatch = QPushButton()
        self.swatch.setFixedSize(36, 26)
        self.swatch.setToolTip("Click to pick a colour")
        self.swatch.clicked.connect(self._pick_colour)
        layout.addWidget(self.swatch)

        # Hex input (editable)
        self.hex_edit = QLineEdit()
        self.hex_edit.setFixedWidth(90)
        self.hex_edit.setMaxLength(7)
        self.hex_edit.setPlaceholderText("#rrggbb")
        self.hex_edit.editingFinished.connect(self._hex_edited)
        layout.addWidget(self.hex_edit)

        layout.addStretch()
        self.set_colour(colour)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _pick_colour(self):
        current = QColor(self.hex_edit.text())
        picked  = QColorDialog.getColor(current, self, f"Pick colour: {PALETTE_LABELS.get(self.key, self.key)}")
        if picked.isValid():
            self.set_colour(picked.name())
            self.colour_changed.emit(self.key, picked.name())

    def _hex_edited(self):
        raw = self.hex_edit.text().strip()
        if not raw.startswith("#"):
            raw = "#" + raw
        colour = QColor(raw)
        if colour.isValid():
            self.set_colour(colour.name())
            self.colour_changed.emit(self.key, colour.name())
        else:
            # Revert to last known good value shown in swatch
            self.hex_edit.setText(self._current)

    def set_colour(self, hex_colour: str):
        """Update swatch and hex field to *hex_colour*."""
        self._current = hex_colour
        self.hex_edit.setText(hex_colour)
        # Compute a contrasting text colour for the swatch label
        c = QColor(hex_colour)
        brightness = (c.red() * 299 + c.green() * 587 + c.blue() * 114) // 1000
        fg = "#000000" if brightness > 128 else "#ffffff"
        self.swatch.setStyleSheet(
            f"background:{hex_colour}; color:{fg}; border:1px solid #888; border-radius:3px;"
        )

    def get_colour(self) -> str:
        return self._current


# ─────────────────────────────────────────────────────────────────────────────
# ThemeSettingsWidget
# ─────────────────────────────────────────────────────────────────────────────

class ThemeSettingsWidget(QWidget):
    """Full theme editor: preset selector + 14 colour rows.

    Signals
    -------
    theme_changed(dict)  — fired on any colour change with the full theme cfg
                           dict {"preset": str, "custom": dict}.
                           The main window connects this for live preview.
    """

    theme_changed = pyqtSignal(dict)

    # Order in which colour rows are displayed
    _GROUPS = [
        ("Backgrounds & Panels", [
            "bg_window", "bg_base", "bg_surface", "bg_input", "bg_header"
        ]),
        ("Grid Highlights", [
            "bg_selection", "bg_cell_selection", "bg_cell_hover"
        ]),
        ("Text & Typography", [
            "text_primary", "text_muted", "text_readonly"
        ]),
        ("Accents & Status", [
            "accent", "accent_hover", "accent_disabled", "border", "error", "accent_apply", "accent_apply_hover"
        ])
    ]

    def __init__(self, theme_cfg: dict):
        super().__init__()
        self._rows: dict[str, ColourRow] = {}
        self._updating = False   # guard against feedback loops

        outer = QVBoxLayout(self)
        outer.setSpacing(10)

        # ── Preset selector bar ───────────────────────────────────────────────
        preset_bar = QHBoxLayout()
        preset_bar.addWidget(QLabel("Preset:"))

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(PRESETS.keys()) + ["Custom"])
        self.preset_combo.setFixedWidth(120)
        self.preset_combo.currentTextChanged.connect(self._preset_changed)
        preset_bar.addWidget(self.preset_combo)

        reset_btn = QPushButton("Reset to Preset")
        reset_btn.setFixedHeight(28)
        reset_btn.clicked.connect(self._reset_to_preset)
        preset_bar.addWidget(reset_btn)
        preset_bar.addStretch()
        outer.addLayout(preset_bar)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        outer.addWidget(line)

        # ── Colour rows (scrollable) ──────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        grid  = QVBoxLayout(inner)
        grid.setSpacing(2)
        grid.setContentsMargins(4, 4, 4, 4)

        for group_name, keys in self._GROUPS:
            header = QLabel(group_name)
            font = header.font()
            font.setBold(True)
            font.setPointSize(font.pointSize() + 1)
            header.setFont(font)
            header.setStyleSheet("color: palette(highlight); margin-top: 12px; margin-bottom: 4px;")
            grid.addWidget(header)
            
            for key in keys:
                label = PALETTE_LABELS.get(key, key)
                row   = ColourRow(key, label, "#000000")
                row.colour_changed.connect(self._colour_changed)
                self._rows[key] = row
                grid.addWidget(row)
                
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("color: palette(mid); opacity: 0.5;")
            grid.addWidget(line)

        grid.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # Populate with initial values (no signal spam during init)
        self._load_theme(theme_cfg)

    # ── Loading helpers ───────────────────────────────────────────────────────

    def _load_theme(self, theme_cfg: dict):
        """Fill all rows from a theme config dict, silently."""
        self._updating = True
        preset  = theme_cfg.get("preset", "Dark")
        custom  = theme_cfg.get("custom", {})
        base    = dict(PRESETS.get(preset, PRESETS["Dark"]))
        palette = {**base, **custom}

        # Set combo without triggering _preset_changed
        index = self.preset_combo.findText(preset)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
        elif custom:
            self.preset_combo.setCurrentText("Custom")

        for key, row in self._rows.items():
            row.set_colour(palette.get(key, base.get(key, "#000000")))

        self._updating = False

    # ── Event handlers ────────────────────────────────────────────────────────

    def _preset_changed(self, preset_name: str):
        if self._updating or preset_name == "Custom":
            return
        if preset_name in PRESETS:
            self._updating = True
            palette = PRESETS[preset_name]
            for key, row in self._rows.items():
                row.set_colour(palette.get(key, "#000000"))
            self._updating = False
            self.theme_changed.emit({"preset": preset_name, "custom": {}})

    def _colour_changed(self, key: str, hex_value: str):
        if self._updating:
            return
        # Any manual change → switch label to "Custom"
        self._updating = True
        self.preset_combo.setCurrentText("Custom")
        self._updating = False
        self.theme_changed.emit(self.get_theme())

    def _reset_to_preset(self):
        current = self.preset_combo.currentText()
        if current in PRESETS:
            self._preset_changed(current)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_theme(self) -> dict:
        """Return the theme cfg dict: ``{"preset": str, "custom": dict}``."""
        preset = self.preset_combo.currentText()
        if preset in PRESETS:
            base   = PRESETS[preset]
            # Only store tokens that differ from the preset as custom overrides
            custom = {
                k: row.get_colour()
                for k, row in self._rows.items()
                if row.get_colour().lower() != base.get(k, "").lower()
            }
        else:
            # Full custom — store everything
            custom = {k: row.get_colour() for k, row in self._rows.items()}
            preset = "Custom"
        return {"preset": preset, "custom": custom}

    def set_theme(self, theme_cfg: dict):
        """Reload the widget with a new theme config (used after external changes)."""
        self._load_theme(theme_cfg)
