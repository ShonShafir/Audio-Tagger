"""
core/ui/main_window.py
----------------------
Application main window.

MainWindow composes all UI panels together and wires up the top-level
signals.  It inherits from:

  QMainWindow     — Qt window infrastructure
  TaggerTabMixin  — Tagger tab + all table / worker logic (tagger_tab.py)

This file is intentionally kept thin.  For any tagger-tab behaviour, look
in core/ui/tagger_tab.py.  For settings behaviour, look in
core/ui/settings_tab.py.
"""

import os

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QTextBrowser, QStatusBar, QApplication,
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QShortcut, QKeySequence

from core.config import load_config, save_config
from core.ui.theme import get_palette, build_stylesheet
from core.ui.settings_tab import SettingsTab
from core.ui.tagger_tab import TaggerTabMixin



class MainWindow(QMainWindow, TaggerTabMixin):
    """Top-level application window.

    State attributes
    ----------------
    cfg          — active configuration dict
    rows         — list of track row dicts (source of truth for the table)
    covers       — {catno: bytes} cache of downloaded cover art
    folder       — path to the currently selected folder
    _workers     — list of QThread workers (kept alive until they finish)
    _vis_fields  — visible field defs (built by TaggerTabMixin._build_cols)
    _col_map     — {column_label: column_index} (built by TaggerTabMixin._build_cols)
    """

    def __init__(self):
        super().__init__()
        self.cfg         = load_config()
        self.rows        = []
        self.covers      = {}
        self.folder      = ""
        self._workers    = []
        self._vis_fields = []
        self._col_map    = {}

        self.setWindowTitle("Audio Tagger")
        self.setMinimumSize(1350, 750)
        self.setAcceptDrops(True)          # enable folder drag-and-drop
        QApplication.instance().installEventFilter(self)
        self._apply_theme(self.cfg)
        self._build_ui()

    # ── Appearance ────────────────────────────────────────────────────────────

    def _apply_theme(self, cfg: dict):
        """Apply the QSS stylesheet derived from the current theme palette."""
        palette = get_palette(cfg)
        self.setStyleSheet(build_stylesheet(palette))



    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        """Assemble the three main tabs and status bar."""
        tabs = QTabWidget()

        # Tagger tab — built by TaggerTabMixin
        tabs.addTab(self._tagger_tab(), "Tagger")

        # Settings tab
        self.settings_tab = SettingsTab(self.cfg)
        self.settings_tab.settings_applied.connect(self._apply_settings)
        # Live theme preview: repaint immediately on any colour change
        self.settings_tab.theme_preview.connect(self._apply_theme)
        tabs.addTab(self.settings_tab, "Settings")

        # Help tab
        tabs.addTab(self._help_tab(), "Help")

        self.setCentralWidget(tabs)

        self.sb = QStatusBar()
        self.setStatusBar(self.sb)
        self.sb.showMessage("Ready — select a folder to begin.")

        self._setup_shortcuts()

    # ── Keyboard shortcuts ────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        """Register global keyboard shortcuts."""
        def _sc(keys, slot):
            s = QShortcut(QKeySequence(keys), self)
            s.activated.connect(slot)
            return s

        _sc("Ctrl+R", self.scan_btn.click)
        _sc("Ctrl+D", self.discogs_btn.click)
        _sc("Ctrl+S", self.apply_btn.click)
        _sc("Ctrl+H", self.find_replace_btn.click)
        _sc("Space",  self._space_pressed)
        
        _sc("Ctrl+=", self._zoom_in)
        _sc("Ctrl++", self._zoom_in)
        _sc("Ctrl+-", self._zoom_out)

    def _zoom_in(self):
        sz = self.cfg.get("font_size", 13)
        if sz < 40:
            self.cfg["font_size"] = sz + 1
            self._apply_theme(self.cfg)
            save_config(self.cfg)
            self.sb.showMessage(f"Zoomed in (Font size: {sz + 1}px)", 2000)

    def _zoom_out(self):
        sz = self.cfg.get("font_size", 13)
        if sz > 8:
            self.cfg["font_size"] = sz - 1
            self._apply_theme(self.cfg)
            save_config(self.cfg)
            self.sb.showMessage(f"Zoomed out (Font size: {sz - 1}px)", 2000)

    def _space_pressed(self):
        """Space → play/pause the audio preview if the player is visible."""
        if self.player_bar.isVisible():
            self.player_bar.toggle_play_pause()

    def eventFilter(self, obj, event):
        """Globally intercept Ctrl + Mouse Wheel for zooming across all widgets,
        and table cell clicks for clearing selection."""
        if event.type() == QEvent.Type.Wheel:
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                if delta > 0:
                    self._zoom_in()
                elif delta < 0:
                    self._zoom_out()
                return True
                
        # If the user clicks an already-selected cell in the table, clear the selection
        if hasattr(self, 'table') and obj == self.table.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.NoModifier:
                item = self.table.itemAt(event.pos())
                if item and item.isSelected():
                    self.table.clearSelection()
                    return True
                    
        return super().eventFilter(obj, event)

    # ── Drag-and-drop (folder) ────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        """Accept drag events that contain at least one folder URL."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if os.path.isdir(url.toLocalFile()):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        """Drop a folder onto the window to select it and start scanning."""
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self.folder = path
                self.folder_lbl.setText(path)
                self.folder_lbl.setStyleSheet("color:#a6e3a1;")
                self.sb.showMessage(f"Folder dropped: {path} — scanning…")
                self.run_scan(force_full=True)
                break


    # ── Settings propagation ──────────────────────────────────────────────────

    def _apply_settings(self, cfg: dict):
        """Called when the user clicks Apply or Save in the Settings tab."""
        self.cfg = cfg
        self._apply_theme(cfg)
        self.sb.showMessage("Settings saved. (Click Re-scan if you want them to apply to loaded files)")

    # ── Help tab ──────────────────────────────────────────────────────────────

    def _help_tab(self) -> QWidget:
        """Return the static HTML help page widget."""
        w      = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(15, 15, 15, 15)

        tb = QTextBrowser()
        tb.setOpenExternalLinks(True)
        tb.setStyleSheet(
            "background:#1e1e2e; color:#cdd6f4; border: none; font-size: 14px; line-height: 1.5;"
        )
        tb.setHtml(self._help_html())
        layout.addWidget(tb)
        return w

    @staticmethod
    def _help_html() -> str:
        """Return the full HTML content for the Help tab."""
        return """
        <h2 style='color:#89b4fa;'>Audio Tagger &mdash; Help &amp; Documentation</h2>
        <p>This software allows you to parse MP3 filenames automatically, retrieve metadata
        and high-res cover art from Discogs, and save clean ID3 tags.</p>

        <h3 style='color:#f38ba8;'>Basic Workflow</h3>
        <ol>
            <li><b>Select Folder:</b> Pick the directory containing your MP3s.</li>
            <li><b>Scan and Parse:</b> The app reads filenames and .m3u files to extract
                Catalog Numbers, Artists, Titles, etc.</li>
            <li><b>Fetch Discogs (Optional):</b> The app looks up each CatNo on Discogs,
                fetching the release date, record label, cover art, and more.</li>
            <li><b>Review &amp; Edit:</b> Double-click any cell to adjust values manually.</li>
            <li><b>Apply Tags &amp; Rename:</b> Embeds covers, writes ID3 tags, and renames
                the files.</li>
        </ol>

        <h3 style='color:#f38ba8;'>Field Sources Explained</h3>
        <ul>
            <li><b>parsed</b> &mdash; Extracted from the filename or .m3u.
                Discogs will <b>never</b> overwrite a <i>parsed</i> field.</li>
            <li><b>static</b> &mdash; A fixed value you type in (e.g. Country = <i>UK</i>).
                Discogs will <b>never</b> overwrite a <i>static</i> field.</li>
            <li><b>discogs</b> &mdash; Pulled from Discogs when you click Fetch Discogs.</li>
            <li><b>both</b> &mdash; Starts with your Static Value; Discogs overwrites it
                if it finds data.</li>
        </ul>

        <h3 style='color:#f38ba8;'>Discogs Token (Optional)</h3>
        <p>A Discogs Personal Access Token boosts the API rate limit from 25 to
        60 requests per minute.  Add it in <b>Settings &gt; General</b>.</p>

        <hr style='border-color:#45475a;'>

        <h2 style='color:#89b4fa;'>Transform Language</h2>
        <p>The <b>Transform</b> column in <b>Settings &gt; Fields and Columns</b> lets you
        automatically reformat values.  Chain commands with <code>|</code>.</p>

        <h3 style='color:#a6e3a1;'>Available Commands</h3>
        <table border='1' cellpadding='6' cellspacing='0'
               style='border-color:#45475a; border-collapse:collapse; width:100%;'>
            <tr style='background:#313244;'>
                <th align='left' style='color:#cdd6f4;'>Command</th>
                <th align='left' style='color:#cdd6f4;'>What it does</th>
                <th align='left' style='color:#cdd6f4;'>Example</th>
            </tr>
            <tr><td><code>date:FORMAT</code></td>
                <td>Reformats a date. Tokens: <code>dd</code>, <code>mm</code>,
                    <code>yyyy</code>, <code>yy</code>.</td>
                <td><code>date:dd-mm-yyyy</code><br>
                    2011-12-02 &rarr; 02-12-2011</td></tr>
            <tr><td><code>s/FIND/REPLACE/</code></td>
                <td>Regex find-and-replace (case-sensitive).</td>
                <td><code>s/Feat\\./ft./</code></td></tr>
            <tr><td><code>s/FIND/REPLACE/i</code></td>
                <td>Same, case-insensitive.</td>
                <td><code>s/featuring/ft./i</code></td></tr>
            <tr><td><code>upper</code></td><td>UPPERCASE.</td>
                <td>uk &rarr; UK</td></tr>
            <tr><td><code>lower</code></td><td>lowercase.</td>
                <td>UK &rarr; uk</td></tr>
            <tr><td><code>title</code></td><td>Title Case.</td>
                <td>uk hardcore &rarr; Uk Hardcore</td></tr>
            <tr><td><code>trim</code></td><td>Strip surrounding whitespace.</td>
                <td>&nbsp;text&nbsp; &rarr; text</td></tr>
            <tr><td><code>safe</code></td>
                <td>Replace Windows-illegal filename chars with '-'.</td>
                <td>Title: Remix &rarr; Title- Remix</td></tr>
        </table>

        <h3 style='color:#a6e3a1;'>Chaining with |</h3>
        <ul>
            <li><code>date:dd-mm-yyyy | trim</code></li>
            <li><code>s/Feat\\./ft./i | trim | title</code></li>
        </ul>

        <h3 style='color:#a6e3a1;'>Filename Safety</h3>
        <p>Proposed filenames are <b>always</b> automatically sanitized.
        Windows-illegal characters are replaced with <code>-</code>.</p>

        <hr style='border-color:#45475a;'>

        <h2 style='color:#89b4fa;'>Keyboard Shortcuts</h2>
        <table border='1' cellpadding='6' cellspacing='0'
               style='border-color:#45475a; border-collapse:collapse; width:100%;'>
            <tr style='background:#313244;'>
                <th align='left' style='color:#cdd6f4;'>Shortcut</th>
                <th align='left' style='color:#cdd6f4;'>Action</th>
            </tr>
            <tr><td><kbd>Ctrl</kbd> + <kbd>R</kbd></td><td>Scan / Re-scan Directory</td></tr>
            <tr><td><kbd>Ctrl</kbd> + <kbd>D</kbd></td><td>Fetch Discogs Data</td></tr>
            <tr><td><kbd>Ctrl</kbd> + <kbd>S</kbd></td><td>Apply Tags &amp; Rename Files</td></tr>
            <tr><td><kbd>Ctrl</kbd> + <kbd>H</kbd></td><td>Find &amp; Replace (in Table)</td></tr>
            <tr><td><kbd>Space</kbd></td><td>Play/Pause Audio Preview</td></tr>
            <tr><td><kbd>Ctrl</kbd> + <kbd>+</kbd> <i>or</i> <kbd>=</kbd></td><td>Zoom In (Increase Font Size)</td></tr>
            <tr><td><kbd>Ctrl</kbd> + <kbd>-</kbd></td><td>Zoom Out (Decrease Font Size)</td></tr>
        </table>
        
        <br>
        <h2 style='color:#89b4fa;'>Mouse Interactions</h2>
        <table border='1' cellpadding='6' cellspacing='0'
               style='border-color:#45475a; border-collapse:collapse; width:100%;'>
            <tr style='background:#313244;'>
                <th align='left' style='color:#cdd6f4;'>Interaction</th>
                <th align='left' style='color:#cdd6f4;'>Action</th>
            </tr>
            <tr><td><b>Click row number (left edge)</b></td><td>Select entire row</td></tr>
            <tr><td><b>Click already-selected cell</b></td><td>Clear all selection</td></tr>
            <tr><td><kbd>Ctrl</kbd> + <b>Mouse Wheel</b></td><td>Zoom UI In/Out</td></tr>
            <tr><td><b>Double-click Cover Image</b></td><td>View enlarged cover</td></tr>
            <tr><td><b>Double-click Text Cell</b></td><td>Edit cell text</td></tr>
        </table>
        <br><br>
        """
