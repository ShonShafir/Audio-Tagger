"""
core/ui/dialogs.py
------------------
Standalone modal Qt dialogs.

Classes
-------
ColumnManagerDialog   — drag-to-reorder, show/hide columns
DiscogsSearchDialog   — manual Discogs search and release picker
FindReplaceDialog     — bulk find-and-replace across any visible column
"""

import copy
import re

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QDialogButtonBox,
    QLineEdit, QPushButton, QMessageBox, QAbstractItemView, QApplication,
    QCheckBox, QComboBox, QTableWidget, QTableWidgetItem, QFormLayout,
    QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


# ─────────────────────────────────────────────────────────────────────────────
# ColumnManagerDialog
# ─────────────────────────────────────────────────────────────────────────────

class ColumnManagerDialog(QDialog):
    """Let the user show/hide columns and drag them into any order."""

    def __init__(self, fields: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Columns")
        self.setMinimumSize(380, 480)
        self.fields = copy.deepcopy(fields)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Check to show / uncheck to hide.  Drag to reorder."))

        self.lst = QListWidget()
        self.lst.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        for f in fields:
            item = QListWidgetItem(f["label"])
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsDragEnabled,
            )
            item.setCheckState(
                Qt.CheckState.Checked if f.get("visible", True) else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, f["id"])
            self.lst.addItem(item)
        layout.addWidget(self.lst)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def get_updated_fields(self) -> list:
        """Return the full fields list with updated ``visible`` flags and order."""
        fmap   = {f["id"]: f for f in self.fields}
        result = []
        for i in range(self.lst.count()):
            item = self.lst.item(i)
            fid  = item.data(Qt.ItemDataRole.UserRole)
            f    = copy.deepcopy(fmap[fid])
            f["visible"] = item.checkState() == Qt.CheckState.Checked
            result.append(f)
        return result


# ─────────────────────────────────────────────────────────────────────────────
# DiscogsSearchDialog
# ─────────────────────────────────────────────────────────────────────────────

class DiscogsSearchDialog(QDialog):
    """Search Discogs manually and pick the correct release for a track row.

    Attributes
    ----------
    selected_release : dict | None
        The raw Discogs search-result dict for the chosen release, or None
        if the user cancelled.
    """

    def __init__(self, client, catno: str, parent=None):
        super().__init__(parent)
        self.client           = client
        self.selected_release = None

        self.setWindowTitle("Fix Discogs Match")
        self.resize(600, 400)

        layout        = QVBoxLayout(self)
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit(catno)
        self.search_input.setPlaceholderText("Enter Catalog Number, Artist, or Title...")
        self.search_btn = QPushButton("Search Discogs")
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(btn_box)

        self.search_btn.clicked.connect(self.do_search)
        self.search_input.returnPressed.connect(self.do_search)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        if catno:
            self.do_search()

    def do_search(self):
        q = self.search_input.text().strip()
        if not q:
            return
        self.list_widget.clear()
        self.list_widget.addItem("Searching...")
        QApplication.processEvents()
        try:
            res  = self.client._get(
                "https://api.discogs.com/database/search",
                params={"q": q, "type": "release"},
            )
            hits = res.get("results", [])
            self.list_widget.clear()
            for hit in hits:
                c     = hit.get("catno", "N/A")
                t     = hit.get("title", "Unknown")
                y     = hit.get("year", "")
                y_str = f" ({y})" if y else ""
                item  = QListWidgetItem(f"[{c}] {t}{y_str}")
                item.setData(Qt.ItemDataRole.UserRole, hit)
                self.list_widget.addItem(item)
            if not hits:
                self.list_widget.addItem("No results found.")
        except Exception as e:
            self.list_widget.clear()
            self.list_widget.addItem(f"Error: {e}")

    def accept(self):
        item = self.list_widget.currentItem()
        if item and item.data(Qt.ItemDataRole.UserRole):
            self.selected_release = item.data(Qt.ItemDataRole.UserRole)
            super().accept()
        else:
            QMessageBox.warning(self, "No selection", "Please select a release.")


# ─────────────────────────────────────────────────────────────────────────────
# FindReplaceDialog
# ─────────────────────────────────────────────────────────────────────────────

class FindReplaceDialog(QDialog):
    """Bulk find-and-replace across any visible table column.

    Parameters
    ----------
    col_names : list[str]
        All column names the user can target (visible field labels +
        'Proposed Filename').  The first entry becomes the default.
    rows_data : list[dict]
        Each dict: ``{"col_name": str, "row_index": int, "current": str}``
        — one entry per (row, column) cell the replace will consider.
        Built by the caller so the dialog stays decoupled from the table.
    selected_rows : set[int]
        Row indices that are currently selected in the table.

    After the user clicks Apply, read ``replacements`` — a list of
    ``{"row_index": int, "col_name": str, "new_value": str}`` dicts.
    """

    def __init__(self, col_names: list, rows_data: list, selected_rows: set,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find and Replace")
        self.setMinimumSize(700, 480)
        self.rows_data     = rows_data
        self.selected_rows = selected_rows
        self.replacements  = []          # filled after Apply

        layout = QVBoxLayout(self)

        # ── Controls ─────────────────────────────────────────────────────────
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.find_input    = QLineEdit()
        self.find_input.setPlaceholderText("Text to find…")
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with… (leave blank to delete)")

        self.col_combo = QComboBox()
        self.col_combo.addItems(col_names)

        opts_row = QHBoxLayout()
        self.case_chk  = QCheckBox("Case sensitive")
        self.regex_chk = QCheckBox("Regex")
        self.sel_chk   = QCheckBox("Selected rows only")
        self.sel_chk.setChecked(bool(selected_rows))
        opts_row.addWidget(self.case_chk)
        opts_row.addWidget(self.regex_chk)
        opts_row.addWidget(self.sel_chk)
        opts_row.addStretch()

        form.addRow("Find:", self.find_input)
        form.addRow("Replace:", self.replace_input)
        form.addRow("Column:", self.col_combo)
        form.addRow("Options:", opts_row)
        layout.addLayout(form)

        # ── Preview button ────────────────────────────────────────────────────
        prev_btn = QPushButton("Preview Changes")
        prev_btn.clicked.connect(self._refresh_preview)
        layout.addWidget(prev_btn)

        # ── Preview table ─────────────────────────────────────────────────────
        self.preview = QTableWidget(0, 3)
        self.preview.setHorizontalHeaderLabels(["Row", "Before", "After"])
        self.preview.horizontalHeader().setStretchLastSection(True)
        self.preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.preview, 1)

        self.match_lbl = QLabel("Press 'Preview Changes' to see results.")
        layout.addWidget(self.match_lbl)

        # ── Buttons ───────────────────────────────────────────────────────────
        bb = QDialogButtonBox()
        self.apply_btn  = bb.addButton("Apply", QDialogButtonBox.ButtonRole.AcceptRole)
        self.cancel_btn = bb.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        self.apply_btn.clicked.connect(self._on_apply)
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(bb)

        # Auto-refresh preview when inputs change
        for w in (self.find_input, self.replace_input):
            w.textChanged.connect(self._refresh_preview)
        for w in (self.col_combo, self.case_chk, self.regex_chk, self.sel_chk):
            w.currentIndexChanged.connect(self._refresh_preview) if hasattr(w, "currentIndexChanged") else None
            w.stateChanged.connect(self._refresh_preview) if hasattr(w, "stateChanged") else None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_replacements(self) -> list:
        """Compute the list of changes for the current settings."""
        find    = self.find_input.text()
        replace = self.replace_input.text()
        col     = self.col_combo.currentText()
        flags   = 0 if self.case_chk.isChecked() else re.IGNORECASE
        sel_only = self.sel_chk.isChecked()

        if not find:
            return []

        results = []
        for cell in self.rows_data:
            if cell["col_name"] != col:
                continue
            if sel_only and cell["row_index"] not in self.selected_rows:
                continue
            current = cell["current"]
            try:
                if self.regex_chk.isChecked():
                    new_val = re.sub(find, replace, current, flags=flags)
                else:
                    if flags & re.IGNORECASE:
                        new_val = re.sub(re.escape(find), replace, current, flags=re.IGNORECASE)
                    else:
                        new_val = current.replace(find, replace)
            except re.error:
                new_val = current   # bad regex — leave unchanged
            if new_val != current:
                results.append({
                    "row_index": cell["row_index"],
                    "col_name":  col,
                    "new_value": new_val,
                    "old_value": current,
                })
        return results

    def _refresh_preview(self, *_):
        results = self._build_replacements()
        self.preview.setRowCount(len(results))
        amber = QColor("#f9e2af")
        for ri, r in enumerate(results):
            self.preview.setItem(ri, 0, QTableWidgetItem(str(r["row_index"] + 1)))
            before = QTableWidgetItem(r["old_value"])
            after  = QTableWidgetItem(r["new_value"])
            after.setBackground(amber)
            self.preview.setItem(ri, 1, before)
            self.preview.setItem(ri, 2, after)
        self.match_lbl.setText(
            f"{len(results)} cell(s) will be changed." if results
            else "No matches found."
        )

    def _on_apply(self):
        self.replacements = self._build_replacements()
        if not self.replacements:
            QMessageBox.information(self, "No matches", "Nothing to replace.")
            return
        self.accept()
