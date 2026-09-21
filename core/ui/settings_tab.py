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

    FCOLS = ["Visible", "Label", "Source", "Source Config", "Static Value", "Discogs Field", "ID3 Tag", "Transform"]

    def __init__(self, fields: list):
        super().__init__()
        self.fields = copy.deepcopy(fields)
        self._extra_data = {}  # { row_index: {"template_value": str, "fallback_order": list} }

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
        self.tbl.verticalHeader().setVisible(False)
        layout.addWidget(self.tbl)

        self._populate()

    def _populate(self):
        self.tbl.setRowCount(0)
        self._extra_data.clear()
        for f in self.fields:
            self._add_row(f)

    def _add_row(self, f: dict):
        r = self.tbl.rowCount()
        self.tbl.insertRow(r)
        
        self._extra_data[r] = {
            "template_value": f.get("template_value", ""),
            "fallback_order": f.get("fallback_order", ["parsed", "discogs"])
        }

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
        
        # Column 3 - source config button
        cfg_btn = QPushButton("Configure...")
        cfg_btn.clicked.connect(lambda _, row=r: self._configure_source(row))
        self.tbl.setCellWidget(r, 3, cfg_btn)

        # Columns 4-7 — text fields
        self.tbl.setItem(r, 4, QTableWidgetItem(f.get("static_value", "")))
        self.tbl.setItem(r, 5, QTableWidgetItem(f.get("discogs_field", "")))
        self.tbl.setItem(r, 6, QTableWidgetItem(f.get("id3_frame", "")))
        xf_item = QTableWidgetItem(f.get("transform", ""))
        xf_item.setToolTip(
            "e.g.  date:dd-mm-yyyy  |  s/Feat\\./ft./i  |  upper  |  trim  |  safe"
        )
        self.tbl.setItem(r, 7, xf_item)
        
        # Initial button state
        self._update_cfg_btn(r)
        combo.currentIndexChanged.connect(lambda _, row=r: self._update_cfg_btn(row))

    def _update_cfg_btn(self, row: int):
        combo = self.tbl.cellWidget(row, 2)
        btn = self.tbl.cellWidget(row, 3)
        if combo and btn:
            src = combo.currentText()
            btn.setEnabled(src in ("template", "fallback"))
            
    def _configure_source(self, row: int):
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        from core.ui.template_widgets import TemplateBuilderWidget, SourceFallbackWidget
        
        combo = self.tbl.cellWidget(row, 2)
        src = combo.currentText()
        if src not in ("template", "fallback"):
            return
            
        dlg = QDialog(self)
        dlg.setWindowTitle("Configure Source")
        dlg.resize(500, 400)
        layout = QVBoxLayout(dlg)
        
        extra = self._extra_data.get(row, {})
        
        if src == "template":
            widget = TemplateBuilderWidget(self.get_fields(), extra.get("template_value", ""))
        else:
            widget = SourceFallbackWidget(extra.get("fallback_order", ["parsed"]))
            
        layout.addWidget(widget)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        layout.addWidget(bb)
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if src == "template":
                extra["template_value"] = widget.get_template()
            else:
                extra["fallback_order"] = widget.get_fallback_order()
            self._extra_data[row] = extra

    def _add(self):
        self._add_row({
            "id": f"custom_{self.tbl.rowCount()}",
            "label": "New Field",
            "visible": True,
            "source": "static",
            "static_value": "",
            "template_value": "",
            "fallback_order": ["parsed"],
            "discogs_field": "",
            "id3_frame": "TXXX:CUSTOM",
            "editable": True,
            "transform": "",
        })

    def _remove(self):
        for r in sorted({i.row() for i in self.tbl.selectedItems()}, reverse=True):
            self.tbl.removeRow(r)
            if r in self._extra_data:
                del self._extra_data[r]

    def get_fields(self) -> list:
        """Return all rows as a list of field dicts matching DEFAULT_FIELDS format."""
        result = []
        for r in range(self.tbl.rowCount()):
            lbl_item = self.tbl.item(r, 1)
            combo    = self.tbl.cellWidget(r, 2)
            extra    = self._extra_data.get(r, {})
            result.append({
                "id":            lbl_item.data(Qt.ItemDataRole.UserRole) if lbl_item else f"custom_{r}",
                "label":         lbl_item.text().strip() if lbl_item else "",
                "visible":       self.tbl.item(r, 0).checkState() == Qt.CheckState.Checked,
                "source":        combo.currentText() if combo else "static",
                "template_value":extra.get("template_value", ""),
                "fallback_order":extra.get("fallback_order", []),
                "static_value":  self.tbl.item(r, 4).text().strip() if self.tbl.item(r, 4) else "",
                "discogs_field": self.tbl.item(r, 5).text().strip() if self.tbl.item(r, 5) else "",
                "id3_frame":     self.tbl.item(r, 6).text().strip() if self.tbl.item(r, 6) else "",
                "transform":     self.tbl.item(r, 7).text().strip() if self.tbl.item(r, 7) else "",
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

        self.tmpl_edit = QLineEdit(cfg.get("naming_template", "({catno}) {artist} - {title}.mp3"))
        tmpl_btn = QPushButton("Edit...")
        tmpl_btn.clicked.connect(self._edit_filename_template)
        tmpl_layout = QHBoxLayout()
        tmpl_layout.setContentsMargins(0,0,0,0)
        tmpl_layout.addWidget(self.tmpl_edit)
        tmpl_layout.addWidget(tmpl_btn)
        
        discogs_btn = QPushButton("Configure Discogs Fallbacks...")
        discogs_btn.clicked.connect(self._edit_discogs_fallbacks)

        self.feat_edit    = QLineEdit(cfg.get("feat_format", "ft."))
        self.strip_chk    = QCheckBox("Strip (Original Mix) from titles")
        self.strip_chk.setChecked(cfg.get("strip_original_mix", True))
        self.cover_chk    = QCheckBox("Embed cover art")
        self.cover_chk.setChecked(cfg.get("embed_cover_art", True))
        self.fallback_chk = QCheckBox("Use local Label.jpg as fallback cover")
        self.fallback_chk.setChecked(cfg.get("cover_fallback_local", True))

        form.addRow("Discogs Token:",         self.token_edit)
        form.addRow("API Rate Limit:",         self.rate_spin)
        form.addRow("Discogs Search:", discogs_btn)
        form.addRow("Filename Template:",      tmpl_layout)
        form.addRow("Featured Artist Format:", self.feat_edit)
        form.addRow("", self.strip_chk)
        form.addRow("", self.cover_chk)
        form.addRow("", self.fallback_chk)
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

    def _edit_filename_template(self):
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        from core.ui.template_widgets import TemplateBuilderWidget
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Filename Template")
        dlg.resize(500, 400)
        layout = QVBoxLayout(dlg)
        
        # Fields available for templating
        fields = self.fields_widget.get_fields()
        widget = TemplateBuilderWidget(fields, self.tmpl_edit.text())
        
        layout.addWidget(widget)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        layout.addWidget(bb)
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.tmpl_edit.setText(widget.get_template())

    def _edit_discogs_fallbacks(self):
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        from core.ui.template_widgets import DiscogsFallbackListWidget
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Discogs Search Priorities")
        dlg.resize(600, 500)
        layout = QVBoxLayout(dlg)
        
        fields = self.fields_widget.get_fields()
        current_fb = self.cfg.get("discogs_fallbacks", ["{catno} {artist} {title}", "{catno} {artist}", "{catno}"])
        widget = DiscogsFallbackListWidget(current_fb, fields)
        
        layout.addWidget(widget)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        layout.addWidget(bb)
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cfg["discogs_fallbacks"] = widget.get_fallbacks()

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


