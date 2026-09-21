"""
core/ui/widgets.py
------------------
Reusable custom Qt widgets used in the main track table.

Classes
-------
ClickableImageLabel   — 64×64 cover thumbnail.
                        • Click  → opens CoverViewDialog (full-size preview)
                        • Drag-and-drop a .png/.jpg → replaces the cover
                          in-memory and emits ``image_dropped(bytes)``
CoverViewDialog       — Modal dialog that shows the cover at up to 82 % of
                        the screen size with resolution / size info.
AudioPlayerBar        — Compact media player bar (play/pause, seek, time).
                        Powered by QMediaPlayer.  Call load(path, name) to
                        start playback.  Hidden when nothing is loaded.

Constants
---------
THUMB_SIZE            — pixel size of the in-table thumbnail (default: 64)
"""

from PyQt6.QtWidgets import (
    QLabel, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
    QWidget, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

THUMB_SIZE = 64   # pixels for the in-table cover thumbnail cell


# ─────────────────────────────────────────────────────────────────────────────
# ClickableImageLabel
# ─────────────────────────────────────────────────────────────────────────────

class ClickableImageLabel(QLabel):
    """64×64 cover thumbnail that supports click-to-enlarge and drag-and-drop.

    Emits
    -----
    image_dropped(bytes)  — raw bytes of the dropped image file, so the parent
                            can store it in the row's ``cover_data`` field.
    """

    image_dropped = pyqtSignal(bytes)

    def __init__(self, img_data: bytes = None, track_name: str = "", parent=None):
        super().__init__(parent)
        self._track_name = track_name
        self.setFixedSize(THUMB_SIZE, THUMB_SIZE)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(
            "Double-click to view full size, or drag & drop a .png/.jpg here to set cover."
        )
        self.setAcceptDrops(True)
        self.update_image(img_data)

    # ── Drag-and-drop ─────────────────────────────────────────────────────────

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
                try:
                    with open(file_path, "rb") as f:
                        data = f.read()
                    self.update_image(data)
                    self.image_dropped.emit(data)
                except Exception:
                    pass
                break   # Only process the first valid image

    # ── Image rendering ───────────────────────────────────────────────────────

    def update_image(self, img_data: bytes):
        """Render *img_data* as a scaled thumbnail, or show a '—' placeholder."""
        self._img_data = img_data
        if img_data:
            px = QPixmap()
            px.loadFromData(img_data)
            self.setPixmap(px.scaled(
                THUMB_SIZE - 4, THUMB_SIZE - 4,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            self.setText("")
            self.setStyleSheet("border: 1px solid #45475a; border-radius: 3px;")
        else:
            self.setPixmap(QPixmap())
            self.setText("—")
            self.setStyleSheet("color:#45475a; font-size:20px;")

    def mouseDoubleClickEvent(self, event):
        if self._img_data:
            dlg = CoverViewDialog(self._img_data, self._track_name, self.window())
            dlg.exec()
        else:
            event.ignore()


# ─────────────────────────────────────────────────────────────────────────────
# CoverViewDialog
# ─────────────────────────────────────────────────────────────────────────────

class CoverViewDialog(QDialog):
    """Modal full-size cover viewer.  Click the image or press Esc to close."""

    def __init__(self, img_data: bytes, title: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title or "Cover Art")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowCloseButtonHint)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        px = QPixmap()
        px.loadFromData(img_data)

        # Scale to at most 82 % of the available screen area
        screen = self.screen() or QApplication.primaryScreen()
        avail  = screen.availableGeometry()
        max_w  = int(avail.width()  * 0.82)
        max_h  = int(avail.height() * 0.82)
        scaled = px.scaled(
            max_w, max_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        lbl = QLabel()
        lbl.setPixmap(scaled)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl.setToolTip("Click to close")
        lbl.mousePressEvent = lambda _e: self.close()
        layout.addWidget(lbl)

        info = QLabel(
            f"{px.width()} \u00d7 {px.height()} px"
            f"  \u00b7  {len(img_data) // 1024} KB"
            f"  \u00b7  click to close"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color:#6c7086; font-size:11px;")
        layout.addWidget(info)
        self.adjustSize()


# ─────────────────────────────────────────────────────────────────────────────
# AudioPlayerBar
# ─────────────────────────────────────────────────────────────────────────────

class AudioPlayerBar(QWidget):
    """Compact audio player bar embedded below the track table.

    Usage
    -----
    bar.load(path, track_name)   — load and immediately play an MP3
    bar.toggle_play_pause()      — bound to Spacebar shortcut
    bar.stop()                   — stop and hide the bar

    The bar is hidden until the first track is loaded.  It self-hides again
    when the user clicks Stop.

    If PyQt6.QtMultimedia is not installed the bar silently disables itself
    (available property becomes False) so the rest of the app still works.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self._available = False
        self._current_path = ""

        try:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            self._player       = QMediaPlayer()
            self._audio_output = QAudioOutput()
            self._player.setAudioOutput(self._audio_output)
            self._audio_output.setVolume(0.0)   # Default volume 0%
            self._available = True
        except Exception:
            return   # QtMultimedia not installed — bar stays hidden forever

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedWidth(32)
        self.play_btn.setToolTip("Play / Pause  (Space)")
        self.play_btn.clicked.connect(self.toggle_play_pause)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setFixedWidth(32)
        self.stop_btn.setToolTip("Stop and close player")
        self.stop_btn.clicked.connect(self.stop)

        self.track_lbl = QLabel("—")
        self.track_lbl.setMinimumWidth(160)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderMoved.connect(self._seek)

        self.time_lbl = QLabel("0:00 / 0:00")
        self.time_lbl.setFixedWidth(90)
        self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.vol_lbl = QLabel("🔊")
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(0)
        self.vol_slider.setFixedWidth(80)
        self.vol_slider.setToolTip("Volume")
        self.vol_slider.valueChanged.connect(lambda v: self._audio_output.setVolume(v / 100.0))

        layout.addWidget(self.play_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.track_lbl)
        layout.addWidget(self.seek_slider, 1)
        layout.addWidget(self.time_lbl)
        layout.addWidget(self.vol_lbl)
        layout.addWidget(self.vol_slider)

        # Wire player signals
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.playbackStateChanged.connect(self._on_state)

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        return self._available

    def load(self, path: str, track_name: str):
        """Load *path* and start playing immediately."""
        if not self._available:
            return
        from PyQt6.QtCore import QUrl
        self._current_path = path
        self._player.setSource(QUrl.fromLocalFile(path))
        self.track_lbl.setText(track_name)
        self.setVisible(True)
        self._player.play()

    def toggle_play_pause(self):
        """Play if paused/stopped; pause if playing.  Bound to Space."""
        if not self._available:
            return
        from PyQt6.QtMultimedia import QMediaPlayer
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def stop(self):
        """Stop playback and hide the bar."""
        if not self._available:
            return
        self._player.stop()
        self.setVisible(False)

    # ── Internal slots ────────────────────────────────────────────────────────

    def _seek(self, ms: int):
        self._player.setPosition(ms)

    def _on_position(self, ms: int):
        self.seek_slider.setValue(ms)
        dur = self._player.duration()
        self.time_lbl.setText(f"{_fmt_ms(ms)} / {_fmt_ms(dur)}")

    def _on_duration(self, ms: int):
        self.seek_slider.setRange(0, ms)

    def _on_state(self, state):
        from PyQt6.QtMultimedia import QMediaPlayer
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_btn.setText("⏸" if playing else "▶")


def _fmt_ms(ms: int) -> str:
    """Format milliseconds as M:SS."""
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"
