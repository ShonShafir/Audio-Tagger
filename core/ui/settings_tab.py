"""
core/ui/settings_tab.py
-----------------------
Settings panel shown in the "Settings" tab of the main window.

Classes
-------
FieldsSettingsWidget  — Editable table: add/remove/edit every field's source,
                        static value, Discogs path, ID3 frame, and transform.
SettingsTab           — Outer widget with "General" and "Fields" sub-tabs plus
                        Apply / Save buttons.
"""

import copy

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QLabel, QLineEdit, QCheckBox, QPushButton,
    QDoubleSpinBox, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.config import DEFAULT_FIELDS, FIELD_SOURCES, save_config
from core.ui.theme_tab import ThemeSettingsWidget



# ─────────────────────────────────────────────────────────────────────────────
# FieldsSettingsWidget
# ─────────────────────────────────────────────────────────────────────────────

class FieldsSettingsWidget(QWidget):
    """Editable table that lets the user configure every metadata field."""

    FCOLS = ["Visible", "Label", "Source", "Static Value", "Discogs Field", "ID3 Tag", "Transform"]

    def __init__(self, fields: list):
        super().__init__()
        self.fields = copy.deepcopy(fields)

        layout = QVBoxLayout(self)

        # Toolbar: Add / Remove
        bar = QHBoxLayout()
        add_btn = QPushButton("+ Add Field")
        add_btn.clicked.connect(self._add)
        del_btn = QPushButton("x Remove Selected")
        del_btn.clicked.connect(self._remove)
        bar.addWidget(add_btn)
        bar.addWidget(del_btn)
        bar.addStretch()
        layout.addLayout(bar)

        # Field table
        self.tbl = QTableWidget()
        self.tbl.setColumnCount(len(self.FCOLS))
        self.tbl.setHorizontalHeaderLabels(self.FCOLS)
        hdr = self.tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)   # Static Value — stretch
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)   # Transform    — stretch
        self.tbl.verticalHeader().setVisible(False)
        layout.addWidget(self.tbl)

        self._populate()

    def _populate(self):
        self.tbl.setRowCount(0)
        for f in self.fields:
            self._add_row(f)

    def _add_row(self, f: dict):
        r = self.tbl.rowCount()
        self.tbl.insertRow(r)

        # Column 0 — visible checkbox
        chk = QTableWidgetItem()
        chk.setCheckState(Qt.CheckState.Checked if f.get("visible", True) else Qt.CheckState.Unchecked)
        chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        self.tbl.setItem(r, 0, chk)

        # Column 1 — label (stores field id as UserRole data)
        lbl = QTableWidgetItem(f.get("label", ""))
        lbl.setData(Qt.ItemDataRole.UserRole, f.get("id", f"custom_{r}"))
        self.tbl.setItem(r, 1, lbl)

        # Column 2 — source dropdown
        combo = QComboBox()
        combo.addItems(FIELD_SOURCES)
        src = f.get("source", "static")
        combo.setCurrentIndex(FIELD_SOURCES.index(src) if src in FIELD_SOURCES else 1)
        self.tbl.setCellWidget(r, 2, combo)

        # Columns 3-6 — text fields
        self.tbl.setItem(r, 3, QTableWidgetItem(f.get("static_value", "")))
        self.tbl.setItem(r, 4, QTableWidgetItem(f.get("discogs_field", "")))
        self.tbl.setItem(r, 5, QTableWidgetItem(f.get("id3_frame", "")))
        xf_item = QTableWidgetItem(f.get("transform", ""))
        xf_item.setToolTip(
            "e.g.  date:dd-mm-yyyy  |  s/Feat\\./ft./i  |  upper  |  trim  |  safe"
        )
        self.tbl.setItem(r, 6, xf_item)

    def _add(self):
        self._add_row({
            "id": f"custom_{self.tbl.rowCount()}",
            "label": "New Field",
            "visible": True,
            "source": "static",
            "static_value": "",
            "discogs_field": "",
            "id3_frame": "TXXX:CUSTOM",
            "editable": True,
            "transform": "",
        })

    def _remove(self):
        for r in sorted({i.row() for i in self.tbl.selectedItems()}, reverse=True):
            self.tbl.removeRow(r)

    def get_fields(self) -> list:
        """Return all rows as a list of field dicts matching DEFAULT_FIELDS format."""
        result = []
        for r in range(self.tbl.rowCount()):
            lbl_item = self.tbl.item(r, 1)
            combo    = self.tbl.cellWidget(r, 2)
            result.append({
                "id":            lbl_item.data(Qt.ItemDataRole.UserRole) if lbl_item else f"custom_{r}",
                "label":         lbl_item.text().strip() if lbl_item else "",
                "visible":       self.tbl.item(r, 0).checkState() == Qt.CheckState.Checked,
                "source":        combo.currentText() if combo else "static",
                "static_value":  self.tbl.item(r, 3).text().strip() if self.tbl.item(r, 3) else "",
                "discogs_field": self.tbl.item(r, 4).text().strip() if self.tbl.item(r, 4) else "",
                "id3_frame":     self.tbl.item(r, 5).text().strip() if self.tbl.item(r, 5) else "",
                "transform":     self.tbl.item(r, 6).text().strip() if self.tbl.item(r, 6) else "",
                "editable": True,
            })
        return result


# ─────────────────────────────────────────────────────────────────────────────
# SettingsTab
# ─────────────────────────────────────────────────────────────────────────────

class SettingsTab(QWidget):
    """Settings tab: General options + Fields table + Theme panel + Apply/Save buttons."""

    settings_applied = pyqtSignal(dict)
    theme_preview    = pyqtSignal(dict)   # live preview signal (no save needed)

    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        outer    = QVBoxLayout(self)
        subtabs  = QTabWidget()
        outer.addWidget(subtabs)

        # ── General sub-tab ──────────────────────────────────────────────────
        gen  = QWidget()
        form = QFormLayout(gen)
        form.setVerticalSpacing(10)

        self.token_edit = QLineEdit(cfg.get("discogs_token", ""))
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("Optional — increases rate limit from 25 to 60 req/min")

        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(1.0, 10.0)
        self.rate_spin.setSingleStep(0.5)
        self.rate_spin.setValue(float(cfg.get("rate_limit", 2.5)))
        self.rate_spin.setSuffix(" sec")

        self.tmpl_edit    = QLineEdit(cfg.get("naming_template", "({catno}) {artist} - {title}.mp3"))
        self.feat_edit    = QLineEdit(cfg.get("feat_format", "ft."))
        self.strip_chk    = QCheckBox("Strip (Original Mix) from titles")
        self.strip_chk.setChecked(cfg.get("strip_original_mix", True))
        self.cover_chk    = QCheckBox("Embed cover art")
        self.cover_chk.setChecked(cfg.get("embed_cover_art", True))
        self.fallback_chk = QCheckBox("Use local Label.jpg as fallback cover")
        self.fallback_chk.setChecked(cfg.get("cover_fallback_local", True))

        form.addRow("Discogs Token:",         self.token_edit)
        form.addRow("API Rate Limit:",         self.rate_spin)
        form.addRow("Filename Template:",      self.tmpl_edit)
        form.addRow("Featured Artist Format:", self.feat_edit)
        form.addRow("", self.strip_chk)
        form.addRow("", self.cover_chk)
        form.addRow("", self.fallback_chk)
        form.addRow("", QLabel("Template variables: {catno}  {artist}  {title}"))
        subtabs.addTab(gen, "General")

        # ── Fields and Columns sub-tab ───────────────────────────────────────
        self.fields_widget = FieldsSettingsWidget(cfg.get("fields", DEFAULT_FIELDS))
        subtabs.addTab(self.fields_widget, "Fields and Columns")

        # ── Theme sub-tab ─────────────────────────────────────────────────────
        self.theme_widget = ThemeSettingsWidget(cfg.get("theme", {"preset": "Dark", "custom": {}}))
        # Any colour change → live preview in the main window (no save required)
        self.theme_widget.theme_changed.connect(
            lambda t: self.theme_preview.emit({**self.get_cfg(), "theme": t})
        )
        subtabs.addTab(self.theme_widget, "Theme")

        # ── Bottom buttons ───────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        apply_btn  = QPushButton("Apply for this Session")
        apply_btn.setFixedHeight(36)
        apply_btn.clicked.connect(lambda: self.save(permanent=False))
        save_btn   = QPushButton("Save Permanently")
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(lambda: self.save(permanent=True))
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(save_btn)
        outer.addLayout(btn_layout)

    def save(self, permanent: bool = True):
        self.get_cfg()
        if permanent:
            save_config(self.cfg)
            QMessageBox.information(self, "Saved", "Settings saved permanently.")
        else:
            QMessageBox.information(self, "Applied", "Settings applied for this session.")
        self.settings_applied.emit(self.cfg)

    def get_cfg(self) -> dict:
        """Sync widget state into self.cfg and return it."""
        self.cfg.update({
            "discogs_token":        self.token_edit.text().strip(),
            "rate_limit":           self.rate_spin.value(),
            "naming_template":      self.tmpl_edit.text().strip(),
            "feat_format":          self.feat_edit.text().strip(),
            "strip_original_mix":   self.strip_chk.isChecked(),
            "embed_cover_art":      self.cover_chk.isChecked(),
            "cover_fallback_local": self.fallback_chk.isChecked(),
            "fields":               self.fields_widget.get_fields(),
            "theme":                self.theme_widget.get_theme(),
        })
        return self.cfg


