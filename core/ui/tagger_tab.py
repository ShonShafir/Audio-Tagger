"""
core/ui/tagger_tab.py
---------------------
Mixin class that provides all Tagger-tab functionality to MainWindow.

Why a mixin?
------------
MainWindow inherits from both QMainWindow and TaggerTabMixin.  This lets
us keep the table-management code in its own file without needing a
separate QWidget wrapper (which would complicate the signal wiring).

Responsibilities
----------------
• Build the Tagger tab widget (_tagger_tab)
• Manage table columns (_build_cols, _balance_columns, _on_section_resized)
• Populate and read the table (_fill_table, _append_row, _read_rows, _update_row)
• Duplicate detection (_check_duplicates)
• Handle user actions (run_scan, run_discogs, apply_action, manage_columns,
  select_folder, _toggle_pause)
• Bulk Find & Replace (find_replace_action)
• Audio preview (double-click row plays the MP3, Space pauses/resumes)
• Context menu for manual Discogs fix (_table_context_menu, _fix_discogs_match)
"""

import os
import copy
from collections import Counter

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QAbstractItemView, QMessageBox, QMenu, QDialog, QApplication,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from core.config import DEFAULT_FIELDS, FIXED_COLS
from core.transforms import sanitize_filename, apply_transform, resolve_discogs_value
from core.parser import build_proposed_filename
from core.discogs import DiscogsClient
from core.ui.workers import ScanWorker, DiscogsWorker, ApplyWorker
from core.ui.widgets import ClickableImageLabel, AudioPlayerBar, THUMB_SIZE
from core.ui.dialogs import ColumnManagerDialog, DiscogsSearchDialog, FindReplaceDialog


class TaggerTabMixin:
    """Mixin that adds the complete Tagger tab to whichever QMainWindow uses it.

    The host class must provide:
        self.cfg          — current config dict
        self.rows         — current list of row dicts
        self.covers       — {catno: cover_bytes} cache
        self.folder       — currently selected folder path
        self._workers     — list of active QThread workers
        self.sb           — QStatusBar
        self.settings_tab — SettingsTab instance
        self._vis_fields  — list of currently visible field dicts
        self._col_map     — {column_label: column_index}
    """

    # ── Tab builder ───────────────────────────────────────────────────────────

    def _tagger_tab(self) -> QWidget:
        """Build and return the Tagger tab widget."""
        w      = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        # ── Top toolbar ──────────────────────────────────────────────────────
        top = QHBoxLayout()

        self.folder_btn = QPushButton("Select Folder")
        self.folder_btn.clicked.connect(self.select_folder)

        self.folder_lbl = QLabel("No folder selected")
        self.folder_lbl.setStyleSheet("color:#6c7086;")

        self.scan_btn = QPushButton("↺ Re-scan")
        self.scan_btn.setEnabled(False)   # enabled after first auto-scan
        self.scan_btn.setToolTip("Re-parse filenames from scratch  (Ctrl+R)")
        self.scan_btn.clicked.connect(self.run_scan)

        self.discogs_btn = QPushButton("Fetch Discogs")
        self.discogs_btn.setEnabled(False)
        self.discogs_btn.setToolTip("Look up each track on Discogs (Right-click to configure) (Ctrl+D)")
        self.discogs_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.discogs_btn.customContextMenuRequested.connect(self._show_discogs_menu)
        self.discogs_btn.clicked.connect(self.run_discogs)
        
        self.transform_btn = QPushButton("Transform")
        self.transform_btn.setEnabled(False)
        self.transform_btn.setToolTip("Apply text transforms to selected cells (Ctrl+T)")
        self.transform_btn.clicked.connect(self.run_transforms)

        self.col_btn = QPushButton("Columns")
        self.col_btn.setEnabled(False)
        self.col_btn.clicked.connect(self.manage_columns)

        self.find_replace_btn = QPushButton("Find & Replace")
        self.find_replace_btn.setEnabled(False)
        self.find_replace_btn.setToolTip("Bulk find-and-replace in any column  (Ctrl+H)")
        self.find_replace_btn.clicked.connect(self.find_replace_action)

        self.apply_btn = QPushButton("Apply Tags and Rename")
        self.apply_btn.setObjectName("btnApply")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setToolTip("Write ID3 tags and rename files  (Ctrl+S)")
        self.apply_btn.clicked.connect(self.apply_action)

        top.addWidget(self.folder_btn)
        top.addWidget(self.folder_lbl, 1)
        top.addWidget(self.scan_btn)
        top.addWidget(self.discogs_btn)
        top.addWidget(self.transform_btn)
        top.addWidget(self.col_btn)
        top.addWidget(self.find_replace_btn)
        top.addWidget(self.apply_btn)
        layout.addLayout(top)

        # ── Pill Toggles for Columns ──
        self.pill_layout = QHBoxLayout()
        self.pill_layout.setSpacing(10)
        self.pill_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(self.pill_layout)

        # ── Track table ──────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.viewport().installEventFilter(self)
        self.table.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.table.setMouseTracking(True)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.horizontalScrollBar().setSingleStep(30)
        self.table.verticalScrollBar().setSingleStep(30)
        self.table.verticalHeader().setDefaultSectionSize(THUMB_SIZE + 4)
        self.table.verticalHeader().setToolTip("Click a row number to select the entire row")
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self.table.itemSelectionChanged.connect(self._update_cover_selection_styles)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._table_context_menu)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        # ── Audio player bar (hidden until first track is loaded) ─────────────
        self.player_bar = AudioPlayerBar()
        layout.addWidget(self.player_bar)

        self._audio_files = []

        # ── Bottom bar: progress + pause ─────────────────────────────────────
        bot = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setValue(0)
        sp = self.progress.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.progress.setSizePolicy(sp)
        self.progress.hide()
        bot.addWidget(self.progress)

        self.pause_btn = QPushButton("\u23f8 Pause")   # ⏸
        self.pause_btn.setEnabled(False)
        self.pause_btn.setCheckable(True)
        self.pause_btn.clicked.connect(self._toggle_pause)
        sp = self.pause_btn.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.pause_btn.setSizePolicy(sp)
        self.pause_btn.hide()
        bot.addWidget(self.pause_btn)

        layout.addLayout(bot)
        return w

    # ── Column management ─────────────────────────────────────────────────────

    def _build_cols(self):
        """(Re)build the table columns from the current cfg fields."""
        fields          = self.cfg.get("fields", DEFAULT_FIELDS)
        self._vis_fields = [f for f in fields if f.get("visible", True)]
        all_cols         = FIXED_COLS + [f["label"] for f in self._vis_fields]
        self._col_map    = {c: i for i, c in enumerate(all_cols)}
        self.table.setColumnCount(len(all_cols))

        # Set header items (with checkbox state for non-fixed cols)
        for i, c in enumerate(all_cols):
            item = QTableWidgetItem(c)
            if c not in FIXED_COLS:
                item.setCheckState(Qt.CheckState.Checked)
            self.table.setHorizontalHeaderItem(i, item)

        hdr = self.table.horizontalHeader()
        hdr.setSectionsMovable(True)

        # Fixed-width columns: auto-size to content
        # Interactive columns: set explicit initial widths to allow horizontal scroll
        for col_name, idx in self._col_map.items():
            if col_name in ("Check", "Cover"):
                hdr.setSectionResizeMode(idx, QHeaderView.ResizeMode.ResizeToContents)
            else:
                if col_name in ("Original File", "Proposed Filename"):
                    self.table.setColumnWidth(idx, 300)
                else:
                    self.table.setColumnWidth(idx, 150)
                hdr.setSectionResizeMode(idx, QHeaderView.ResizeMode.Interactive)
                
        self._build_pill_toggles()

        # Connect header signals only once
        if not hasattr(self, "_hdr_connected"):
            hdr.sectionClicked.connect(self._header_clicked)
            hdr.sectionResized.connect(self._on_section_resized)
            self._hdr_connected = True

    def _build_pill_toggles(self):
        while self.pill_layout.count():
            item = self.pill_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        lbl = QLabel("Columns:")
        lbl.setStyleSheet("color:#a6adc8; font-weight:bold; margin-right:5px;")
        self.pill_layout.addWidget(lbl)
        
        for field in self.cfg.get("fields", DEFAULT_FIELDS):
            btn = QPushButton(field["label"])
            btn.setCheckable(True)
            btn.setChecked(field.get("visible", True))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #313244;
                    color: #a6adc8;
                    border-radius: 12px;
                    padding: 4px 14px;
                    font-weight: 600;
                    border: 2px solid transparent;
                }
                QPushButton:hover {
                    background-color: #45475a;
                    color: #cdd6f4;
                }
                QPushButton:checked {
                    background-color: rgba(137, 180, 250, 0.15);
                    color: #89b4fa;
                    border: 2px solid rgba(137, 180, 250, 0.4);
                }
                QPushButton:checked:hover {
                    background-color: rgba(137, 180, 250, 0.25);
                }
            """)
            btn.toggled.connect(lambda checked, f=field: self._toggle_col_visibility(f, checked))
            self.pill_layout.addWidget(btn)
        self.pill_layout.addStretch()

    def _toggle_col_visibility(self, field, visible):
        field["visible"] = visible
        from core.config import save_config
        save_config(self.cfg)
        self.settings_tab.fields_widget.fields = copy.deepcopy(self.cfg["fields"])
        self.settings_tab.fields_widget._populate()
        
        # Save current rows state, then refill (deferred to prevent deleting sender during event)
        rows = self._read_rows()
        self.rows = rows
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._fill_table(rows))

    def _on_section_resized(self, logicalIndex: int, oldSize: int, newSize: int):
        """Disabled to allow free horizontal scrolling."""
        pass

    def _header_clicked(self, logicalIndex: int):
        """Toggle the lock-checkbox in non-fixed column headers."""
        item = self.table.horizontalHeaderItem(logicalIndex)
        if item and item.text() not in FIXED_COLS:
            new_state = (
                Qt.CheckState.Unchecked
                if item.checkState() == Qt.CheckState.Checked
                else Qt.CheckState.Checked
            )
            item.setCheckState(new_state)

    def get_allowed_fields(self) -> set:
        """Return the set of field ids whose header checkbox is ticked."""
        allowed = set()
        for i in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                label = item.text()
                for f in self._vis_fields:
                    if f["label"] == label:
                        allowed.add(f["id"])
        # The Cover column is always "allowed" because it lacks a lock checkbox
        allowed.add("__cover__")
        return allowed

    # ── Table population ──────────────────────────────────────────────────────


    def _on_item_changed(self, item):
        if not hasattr(self, 'rows') or not self.rows:
            return
        row = item.row()
        col = item.column()
        if row >= len(self.rows):
            return
            
        field_id = None
        for f in getattr(self, '_vis_fields', []):
            if self._col_map.get(f["label"]) == col:
                field_id = f["id"]
                break
                
        if not field_id:
            # If they manually edited the Proposed Filename column, we should still run the duplicate check
            if self._col_map.get("Proposed Filename") == col:
                self._check_duplicates()
            return
            
        self.rows[row]["fields"][field_id] = item.text()
        
        from core.parser import build_proposed_filename
        import os
        cfg = self.settings_tab.get_cfg()
        tmpl = cfg.get("naming_template", "({catno}) {artist} - {title}.mp3")
        fv = self.rows[row]["fields"]
        
        path = self.rows[row].get("path", "")
        ext = os.path.splitext(path)[1].lower() if path else ""
        
        proposed = build_proposed_filename(
            tmpl,
            fv.get("catno", "UNKNOWN"),
            fv.get("artist", ""),
            fv.get("featured", ""),
            fv.get("title", ""),
            feat_format=cfg.get("feat_format", "ft."),
            original_ext=ext
        )
        
        prop_col = self._col_map.get("Proposed Filename")
        if prop_col is not None:
            prop_item = self.table.item(row, prop_col)
            if prop_item and prop_item.text() != proposed:
                self.table.blockSignals(True)
                prop_item.setText(proposed)
                self.table.blockSignals(False)
        self._check_duplicates()

    def _update_cover_selection_styles(self):
        """Add a blue highlight border to selected cover cells, since setCellWidget obscures it."""
        cover_col = self._col_map.get("Cover")
        if cover_col is None:
            return
        
        for r in range(self.table.rowCount()):
            item = self.table.item(r, cover_col)
            container = self.table.cellWidget(r, cover_col)
            if item and container:
                if item.isSelected():
                    container.setStyleSheet("background-color: #313244; border: 2px solid #89b4fa; border-radius: 4px;")
                else:
                    container.setStyleSheet("background-color: transparent; border: none;")

    def _fill_table(self, rows: list):
        """Clear the table, rebuild columns, and repopulate from *rows*."""
        self._build_cols()
        self.table.setRowCount(0)
        for rd in rows:
            self._append_row(rd)
        QApplication.processEvents()
        self._balance_columns()
        self._check_duplicates()

    def _balance_columns(self):
        """Disabled to allow free horizontal scrolling."""
        pass

    def _append_row(self, rd: dict):
        """Append one row dict to the QTableWidget."""
        ri = self.table.rowCount()
        self.table.insertRow(ri)

        # Col 0 — enabled checkbox
        chk = QTableWidgetItem()
        chk.setCheckState(
            Qt.CheckState.Checked if rd.get("enabled", True) else Qt.CheckState.Unchecked
        )
        chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        self.table.setItem(ri, 0, chk)

        # Col 1 — cover thumbnail (drag-and-drop supported)
        cover_col  = self._col_map["Cover"]
        dummy_cover_item = QTableWidgetItem()
        dummy_cover_item.setFlags(dummy_cover_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(ri, cover_col, dummy_cover_item)
        
        track_name = os.path.splitext(rd["original"])[0]
        thumb      = ClickableImageLabel(rd.get("cover_data"), track_name)
        thumb.image_dropped.connect(lambda data, r=ri: self._update_row_cover(r, data))
        container        = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(2, 2, 2, 2)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(thumb)
        self.table.setCellWidget(ri, cover_col, container)

        # Col 2 — original filename (read-only, dimmed)
        orig_col = self._col_map["Original File"]
        orig     = QTableWidgetItem(rd["original"])
        orig.setFlags(orig.flags() & ~Qt.ItemFlag.ItemIsEditable)
        orig.setForeground(QColor("#585b70"))
        self.table.setItem(ri, orig_col, orig)

        # Col 3 — proposed filename (editable)
        prop_col = self._col_map["Proposed Filename"]
        self.table.setItem(ri, prop_col, QTableWidgetItem(rd.get("proposed", "")))

        # Dynamic field columns
        fv = rd.get("fields", {})
        for field in self._vis_fields:
            col = self._col_map.get(field["label"])
            if col is None:
                continue
            val  = str(fv.get(field["id"], ""))
            item = QTableWidgetItem(val)
            if not field.get("editable", True):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if field["id"] == "catno" and not val:
                item.setForeground(QColor("#f38ba8"))   # red hint for missing catno
            self.table.setItem(ri, col, item)

    def _update_row_cover(self, idx: int, data: bytes):
        """Store drag-dropped cover bytes into the row data model."""
        if idx < len(self.rows):
            self.rows[idx]["cover_data"] = data

    def _update_row(self, idx: int, new_fv: dict, cover: bytes):
        """Update a single row after a Discogs fetch, refreshing the UI."""
        if idx >= len(self.rows):
            return
        self.rows[idx]["fields"].update(new_fv)

        if cover:
            catno = new_fv.get("catno", self.rows[idx]["fields"].get("catno", ""))
            if catno:
                self.covers[catno] = cover
            self.rows[idx]["cover_data"] = cover
            container = self.table.cellWidget(idx, self._col_map["Cover"])
            if container:
                thumb = container.findChild(ClickableImageLabel)
                if thumb:
                    thumb.update_image(cover)

        proposed = new_fv.pop("__proposed__", "")
        if proposed:
            self.rows[idx]["proposed"] = proposed
            item = self.table.item(idx, self._col_map["Proposed Filename"])
            if item:
                item.setText(proposed)

        fv = self.rows[idx]["fields"]
        for field in self._vis_fields:
            col  = self._col_map.get(field["label"])
            item = self.table.item(idx, col) if col is not None else None
            if item:
                item.setText(str(fv.get(field["id"], "")))

        # Re-run duplicate check after each Discogs row update
        self._check_duplicates()

    def _read_rows(self) -> list:
        """Read the current state of every table cell back into row dicts."""
        result   = []
        prop_col = self._col_map.get("Proposed Filename", 3)
        for i, rd in enumerate(self.rows):
            if i >= self.table.rowCount():
                break
            new = copy.deepcopy(rd)

            chk = self.table.item(i, 0)
            new["enabled"] = chk.checkState() == Qt.CheckState.Checked if chk else True

            prop = self.table.item(i, prop_col)
            new["proposed"] = prop.text() if prop else rd.get("proposed", "")

            fv = new.get("fields", {})
            for field in self._vis_fields:
                col  = self._col_map.get(field["label"])
                item = self.table.item(i, col) if col is not None else None
                if item:
                    fv[field["id"]] = item.text()
            new["fields"] = fv
            result.append(new)
        return result

    # ── Duplicate detection ───────────────────────────────────────────────────

    def _check_duplicates(self):
        """Highlight rows amber where the Proposed Filename is shared by multiple rows."""
        prop_col = self._col_map.get("Proposed Filename")
        if prop_col is None:
            return

        # Count occurrences of each proposed filename
        prop_counts: Counter = Counter()
        for ri in range(self.table.rowCount()):
            it = self.table.item(ri, prop_col)
            v = it.text().strip() if it else ""
            if v and v != "UNKNOWN":
                prop_counts[v] += 1

        amber = QColor("#f9e2af")
        from PyQt6.QtGui import QBrush
        empty_brush = QBrush()
        
        dup_rows = 0
        self.table.blockSignals(True)
        for ri in range(self.table.rowCount()):
            it = self.table.item(ri, prop_col)
            v = it.text().strip() if it else ""
            is_dup = (v and v != "UNKNOWN" and prop_counts[v] > 1)

            if is_dup:
                dup_rows += 1

            prop_item = self.table.item(ri, prop_col)
            if prop_item:
                if is_dup:
                    prop_item.setForeground(QColor("#f38ba8")) # Red text for duplicates
                else:
                    # Restore default text color (CatNo has its own logic but that's a different column)
                    prop_item.setForeground(QColor("#cdd6f4"))
        self.table.blockSignals(False)

        if dup_rows:
            self.sb.showMessage(
                f"⚠ {dup_rows} rows with duplicate Proposed Filenames — review before applying."
            )
        else:
            if "duplicate" in self.sb.currentMessage():
                self.sb.showMessage("Duplicates resolved.")

    # ── Find & Replace ────────────────────────────────────────────────────────

    def find_replace_action(self):
        """Open the Find & Replace dialog and apply changes to the table."""
        if not self.rows:
            return

        # Build the list of column names the dialog can target
        prop_label = "Proposed Filename"
        col_names  = [prop_label] + [f["label"] for f in self._vis_fields
                                      if f.get("editable", True)]

        # Build per-cell data for all rows
        prop_col  = self._col_map.get(prop_label)
        rows_data = []
        for ri in range(self.table.rowCount()):
            # Proposed Filename column
            if prop_col is not None:
                it = self.table.item(ri, prop_col)
                if it:
                    rows_data.append({
                        "row_index": ri,
                        "col_name":  prop_label,
                        "current":   it.text(),
                    })
            # All visible editable field columns
            for field in self._vis_fields:
                if not field.get("editable", True):
                    continue
                col = self._col_map.get(field["label"])
                if col is None:
                    continue
                it = self.table.item(ri, col)
                if it:
                    rows_data.append({
                        "row_index": ri,
                        "col_name":  field["label"],
                        "current":   it.text(),
                    })

        # Which rows are currently selected?
        selected_rows = {idx.row() for idx in self.table.selectedIndexes()}

        dlg = FindReplaceDialog(col_names, rows_data, selected_rows, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        # Apply replacements back to the table
        prop_col = self._col_map.get("Proposed Filename")
        field_col_map = {f["label"]: self._col_map.get(f["label"])
                         for f in self._vis_fields}

        for r in dlg.replacements:
            ri  = r["row_index"]
            col = (prop_col if r["col_name"] == "Proposed Filename"
                   else field_col_map.get(r["col_name"]))
            if col is None:
                continue
            it = self.table.item(ri, col)
            if it:
                it.setText(r["new_value"])

        changed = len(dlg.replacements)
        self.sb.showMessage(f"Find & Replace: {changed} cell(s) updated.")
        self._check_duplicates()

    # ── Audio preview ─────────────────────────────────────────────────────────

    def _play_row_audio(self, row: int):
        """Double-clicking any cell plays that row's MP3 in the player bar.

        For editable cells Qt will also open the cell editor — that's intentional
        so the user can still edit by double-clicking.  The audio simply starts
        playing in the background.
        """
        if not self.player_bar.available:
            return
        if row >= len(self.rows):
            return
        rd   = self.rows[row]
        path = rd.get("path", "")
        if not path or not os.path.isfile(path):
            return
        name = os.path.splitext(rd.get("original", os.path.basename(path)))[0]
        self.player_bar.load(path, name)

    def _show_discogs_menu(self, pos):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        action = menu.addAction("Configure Fallbacks / Priorities...")
        if menu.exec(self.discogs_btn.mapToGlobal(pos)) == action:
            self.settings_tab._edit_discogs_fallbacks()

    # ── Context menu ──────────────────────────────────────────────────────────

    def _table_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row  = item.row()
        menu = QMenu(self)
        fix_action = menu.addAction("Fix Discogs Match...")
        play_action = menu.addAction("▶ Preview Audio")
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == fix_action:
            self._fix_discogs_match(row)
        elif action == play_action:
            self._play_row_audio(row)

    def _fix_discogs_match(self, row: int):
        """Open a manual Discogs search dialog and update the row."""
        if not hasattr(self, "discogs_client"):
            from core.config import load_config
            cfg = load_config()
            self.discogs_client = DiscogsClient(
                cfg.get("discogs_token", ""),
                cfg.get("rate_limit", 2.5),
            )
        rd    = self.rows[row]
        catno = rd["fields"].get("catno", "")
        dlg   = DiscogsSearchDialog(self.discogs_client, catno, self)

        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_release:
            rel_id = dlg.selected_release["id"]
            self.sb.showMessage(f"Fetching full release data for {rel_id}...")
            QApplication.processEvents()
            try:
                from core.config import load_config
                full   = self.discogs_client._get(
                    f"https://api.discogs.com/releases/{rel_id}"
                )
                images   = full.get("images", [])
                cov_data = b""
                if images:
                    primary  = next(
                        (img for img in images if img.get("type") == "primary"),
                        images[0],
                    )
                    cov_data = self.discogs_client.download_image(primary["uri"])

                cfg    = load_config()
                fields = cfg.get("fields", DEFAULT_FIELDS)
                new_fv = {}
                for field in fields:
                    if field["source"] in ("discogs", "both"):
                        val = resolve_discogs_value(full, field["discogs_field"])
                        if field.get("transform"):
                            val = apply_transform(val, field["transform"])
                        if val:
                            new_fv[field["id"]] = val

                tmpl     = cfg.get("naming_template", "({catno}) {artist} - {title}.mp3")
                feat_fmt = cfg.get("feat_format", "ft.")
                cat_v  = new_fv.get("catno",    rd["fields"].get("catno", "UNKNOWN"))
                art_v  = new_fv.get("artist",   rd["fields"].get("artist",  ""))
                feat_v = new_fv.get("featured", rd["fields"].get("featured", ""))
                tit_v  = new_fv.get("title",    rd["fields"].get("title",   ""))
                new_fv["__proposed__"] = sanitize_filename(
                    build_proposed_filename(tmpl, cat_v, art_v, feat_v, tit_v,
                                            feat_format=feat_fmt,
                                            original_ext=os.path.splitext(rd["path"])[1])
                )
                self._update_row(row, new_fv, cov_data)
                self.sb.showMessage(f"Updated row {row+1} from Discogs.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to fetch release:\n{e}")

    # ── Folder selection ──────────────────────────────────────────────────────

    def select_folder(self):
        f = QFileDialog.getExistingDirectory(self, "Select Music Folder")
        if f:
            self.folder = f
            self.folder_lbl.setText(f)
            self.folder_lbl.setStyleSheet("color:#a6e3a1;")
            self.sb.showMessage(f"Folder selected: {f} — scanning…")
            self.run_scan()   # auto-scan immediately


    # ── Pause / resume ────────────────────────────────────────────────────────

    def _toggle_pause(self):
        is_paused = self.pause_btn.isChecked()
        self.pause_btn.setText("\u25b6 Resume" if is_paused else "\u23f8 Pause")
        for w in self._workers:
            if hasattr(w, "pause") and hasattr(w, "resume"):
                if is_paused:
                    w.pause()
                else:
                    w.resume()

    # ── Scan workflow ─────────────────────────────────────────────────────────


    def run_transforms(self):
        self.cfg = self.settings_tab.get_cfg()
        fields = self.cfg.get("fields", [])
        
        selected_items = self.table.selectedItems()
        target_cells_by_row = {}
        
        col_to_field = {}
        for field in fields:
            label = field.get("label")
            if label in self._col_map:
                col_to_field[self._col_map[label]] = field.get("id")

        if selected_items:
            for item in selected_items:
                r = item.row()
                c = item.column()
                fid = col_to_field.get(c)
                if fid:
                    target_cells_by_row.setdefault(r, set()).add(fid)
        else:
            allowed = self.get_allowed_fields()
            for r in range(len(self.rows)):
                target_cells_by_row[r] = allowed
                
        from core.transforms import apply_transform
        
        for r, fids in target_cells_by_row.items():
            if r >= len(self.rows): continue
            row_data = self.rows[r]
            for field in fields:
                if field["id"] not in fids:
                    continue
                xform = field.get("transform", "")
                if xform:
                    old_val = row_data["fields"].get(field["id"], "")
                    if old_val:
                        new_val = apply_transform(old_val, xform)
                        if new_val != old_val:
                            label = field.get("label")
                            if label in self._col_map:
                                c = self._col_map[label]
                                item = self.table.item(r, c)
                                if item:
                                    # This triggers itemChanged, which updates row_data["fields"] and recalculates proposed filename automatically!
                                    item.setText(new_val)
                            
        self.sb.showMessage("Transforms applied.")
        self.progress.show()
        self.progress.setValue(100)
        QTimer.singleShot(2500, lambda: (self.progress.setValue(0), self.progress.hide()))

    def run_scan(self, force_full=False):
        # Stop any running workers (e.g. an in-progress Discogs fetch) before starting fresh
        for w in self._workers:
            if hasattr(w, "stop"):
                w.stop()

        # Clear the Discogs cover cache so Re-scan starts completely clean.
        # Any cover that was already embedded in a file on disk will be re-loaded
        # by ScanWorker from the file itself (via mutagen).  Discogs-only covers
        # that were fetched into memory but never written to disk are discarded.
        self.covers = {}

        self.cfg = self.settings_tab.get_cfg()
        self.discogs_btn.setEnabled(False)
        self.transform_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setChecked(False)
        self.pause_btn.setText("\u23f8 Pause")
        self.pause_btn.show()
        self.progress.show()
        self.progress.setValue(0)

        selected_items = self.table.selectedItems()
        target_paths = None
        
        if selected_items and not force_full:
            # Map column index to field ID (identical to Discogs fetch)
            col_to_field = {}
            for field in self.cfg.get("fields", []):
                label = field.get("label")
                if label in self._col_map:
                    col_to_field[self._col_map[label]] = field.get("id")
            if "Cover" in self._col_map:
                col_to_field[self._col_map["Cover"]] = "__cover__"

            target_cells_by_row = {}
            for item in selected_items:
                r = item.row()
                c = item.column()
                fid = col_to_field.get(c)
                if fid:
                    target_cells_by_row.setdefault(r, set()).add(fid)
            
            target_paths = {}
            for r, fids in target_cells_by_row.items():
                if r < len(self.rows):
                    target_paths[self.rows[r]["path"]] = fids
            
        # Always pass existing rows and allowed fields so Re-scan respects locked columns
        existing = self.rows

        w = ScanWorker(
            self.folder, 
            self.cfg, 
            existing_rows=existing, 
            allowed_fields=self.get_allowed_fields(),
            target_paths=target_paths
        )
        w.progress.connect(lambda p, m: (self.progress.setValue(p), self.sb.showMessage(m)))
        w.complete.connect(self._scan_done)
        w.error.connect(lambda e: (
            QMessageBox.critical(self, "Scan Error", e),
            self.pause_btn.setEnabled(False),
        ))
        self._workers.append(w)
        w.start()



    def _scan_done(self, rows: list):
        self.pause_btn.hide()
        self.rows = rows
        self._fill_table(rows)
        self.scan_btn.setEnabled(True)   # always keep Re-scan available after first parse
        self.discogs_btn.setEnabled(True)
        self.transform_btn.setEnabled(True)
        self.apply_btn.setEnabled(True)
        self.col_btn.setEnabled(True)
        self.find_replace_btn.setEnabled(True)
        self.progress.setValue(100)
        QTimer.singleShot(2500, lambda: (self.progress.setValue(0), self.progress.hide()))
        self.sb.showMessage(
            f"Parsed {len(rows)} tracks. Edit any cell, then Apply — or Fetch Discogs first."
        )


    # ── Discogs fetch workflow ────────────────────────────────────────────────

    def run_discogs(self):
        self.cfg  = self.settings_tab.get_cfg()
        self.rows = self._read_rows()
        self.discogs_btn.setEnabled(False)
        self.transform_btn.setEnabled(False)
        # NOTE: scan_btn intentionally NOT disabled here — user can always Re-scan
        self.pause_btn.setEnabled(True)
        self.pause_btn.setChecked(False)
        self.pause_btn.setText("\u23f8 Pause")
        self.pause_btn.show()
        self.progress.show()
        self.progress.setValue(0)

        selected_items = self.table.selectedItems()
        target_cells = None
        if selected_items:
            # Map column index to field ID
            col_to_field = {}
            for field in self.cfg.get("fields", []):
                label = field.get("label")
                if label in self._col_map:
                    col_to_field[self._col_map[label]] = field.get("id")
            if "Cover" in self._col_map:
                col_to_field[self._col_map["Cover"]] = "__cover__"

            target_cells = {}
            for item in selected_items:
                r = item.row()
                c = item.column()
                # If they selected a specific field column, add it to target_cells
                if c in col_to_field:
                    if r not in target_cells:
                        target_cells[r] = set()
                    target_cells[r].add(col_to_field[c])
            # Also ensure any row that had a selection is at least in target_cells
            for item in selected_items:
                r = item.row()
                if r not in target_cells:
                    target_cells[r] = set()

        allowed = self.get_allowed_fields()
        w = DiscogsWorker(self.rows, self.cfg, self.folder, allowed, target_cells=target_cells)
        w.progress.connect(lambda p, m: (self.progress.setValue(p), self.sb.showMessage(m)))
        w.row_updated.connect(self._update_row)
        w.complete.connect(self._discogs_done)
        w.error.connect(lambda e: (
            QMessageBox.critical(self, "Discogs Error", e),
            self.discogs_btn.setEnabled(True),
            self.transform_btn.setEnabled(True),
            self.pause_btn.setEnabled(False),
        ))
        self._workers.append(w)
        w.start()


    def _discogs_done(self):
        self.pause_btn.hide()
        self.discogs_btn.setEnabled(True)
        self.transform_btn.setEnabled(True)
        self.progress.setValue(100)
        QTimer.singleShot(2500, lambda: (self.progress.setValue(0), self.progress.hide()))
        self.sb.showMessage(f"Discogs done. {len(self.covers)} covers downloaded.")


    # ── Column visibility manager ─────────────────────────────────────────────

    def manage_columns(self):
        self.cfg = self.settings_tab.get_cfg()
        dlg = ColumnManagerDialog(self.cfg.get("fields", DEFAULT_FIELDS), self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            from core.config import save_config
            self.cfg["fields"] = dlg.get_updated_fields()
            self.settings_tab.fields_widget.fields = copy.deepcopy(self.cfg["fields"])
            self.settings_tab.fields_widget._populate()
            save_config(self.cfg)
            rows       = self._read_rows()
            self.rows  = rows
            self._fill_table(rows)
            self.sb.showMessage("Columns updated.")

    # ── Apply tags & rename workflow ──────────────────────────────────────────

    def apply_action(self):
        rows    = self._read_rows()
        enabled = [r for r in rows if r.get("enabled", True)]
        if not enabled:
            QMessageBox.warning(self, "Nothing to do", "No rows are checked.")
            return
        reply = QMessageBox.question(
            self, "Confirm",
            f"Apply tags and rename {len(enabled)} files?\n\nThis cannot be undone.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.cfg = self.settings_tab.get_cfg()
        self.apply_btn.setEnabled(False)
        self.progress.show()
        self.progress.setValue(0)

        w = ApplyWorker(enabled, self.cfg, self.covers)
        w.progress.connect(lambda p, m: (self.progress.setValue(p), self.sb.showMessage(m)))
        def _on_apply_complete():
            self.apply_btn.setEnabled(True)
            self.progress.setValue(100)
            QTimer.singleShot(2500, lambda: (self.progress.setValue(0), self.progress.hide()))
            QMessageBox.information(self, "Done", "All selected tracks tagged and renamed successfully!")
            self.run_scan(force_full=True)
            
        w.complete.connect(_on_apply_complete)
        w.error.connect(lambda e: (
            QMessageBox.critical(self, "Apply Error", e),
            self.apply_btn.setEnabled(True),
        ))
        self._workers.append(w)
        w.start()
