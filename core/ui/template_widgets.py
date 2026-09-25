from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QAbstractItemView, QMenu, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QAction

class TokenListWidget(QListWidget):
    def mimeData(self, items):
        mime = QMimeData()
        if items:
            mime.setText(items[0].data(Qt.ItemDataRole.UserRole))
        return mime

class ReorderListWidget(QListWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

class TemplateBuilderWidget(QWidget):
    """
    A widget to build a string template by dragging tokens from a list into a QLineEdit.
    """
    def __init__(self, fields: list, current_template: str = ""):
        super().__init__()
        self.fields = fields
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Editor
        self.editor = QLineEdit(current_template)
        self.editor.setPlaceholderText("Type text and drop tokens here (e.g. {artist} - {title})")
        layout.addWidget(QLabel("Template String:"))
        layout.addWidget(self.editor)
        
        # Tokens
        layout.addWidget(QLabel("Available Tokens (Drag into the text box):"))
        self.token_list = TokenListWidget()
        self.token_list.setDragEnabled(True)
        self.token_list.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.token_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # We don't want internal moves
        self.token_list.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        
        # Populate tokens
        
        
        for f in fields:
            label = f.get("label", f.get("id"))
            fid = f.get("id")
            self._add_token(label, f"{{{fid}}}")
            
            
        layout.addWidget(self.token_list)
        
    def _add_token(self, label: str, token: str):
        item = QListWidgetItem(f"{label} \u2192 {token}")
        item.setData(Qt.ItemDataRole.UserRole, token)
        self.token_list.addItem(item)
        
    def get_template(self) -> str:
        return self.editor.text()


class SourceFallbackWidget(QWidget):
    """
    A drag-and-drop list to reorder fallback sources.
    Available sources: parsed, static, discogs.
    """
    def __init__(self, current_order: list):
        super().__init__()
        self.available_sources = ["discogs", "parsed", "static"]
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.list_widget = ReorderListWidget()
        
        # Populate
        added = set()
        for src in current_order:
            if src in self.available_sources:
                self.list_widget.addItem(QListWidgetItem(src))
                added.add(src)
                
        # Add remaining available sources to the bottom (unchecked or disabled? No, they can just order all 4)
        for src in self.available_sources:
            if src not in added:
                self.list_widget.addItem(QListWidgetItem(src))
                
        layout.addWidget(self.list_widget)
        
    def get_fallback_order(self) -> list:
        order = []
        for i in range(self.list_widget.count()):
            order.append(self.list_widget.item(i).text())
        return order


class DiscogsFallbackListWidget(QWidget):
    """
    Manages the list of Discogs search queries (tiers).
    """
    def __init__(self, fallbacks: list, fields: list):
        super().__init__()
        self.fields = fields
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter: List of tiers on top, Template builder on bottom
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top panel
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        self.list_widget = ReorderListWidget()
        for fb in fallbacks:
            self.list_widget.addItem(QListWidgetItem(fb))
            
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Tier")
        self.btn_rem = QPushButton("Remove Tier")
        self.btn_up = QPushButton("Up")
        self.btn_down = QPushButton("Down")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_rem)
        btn_layout.addWidget(self.btn_up)
        btn_layout.addWidget(self.btn_down)
        
        top_layout.addWidget(QLabel("Discogs Search Priorities (Top to Bottom):"))
        top_layout.addWidget(self.list_widget)
        top_layout.addLayout(btn_layout)
        
        # Bottom panel
        self.builder = TemplateBuilderWidget(fields, "")
        self.builder.editor.textChanged.connect(self._on_editor_changed)
        
        splitter.addWidget(top_widget)
        splitter.addWidget(self.builder)
        
        layout.addWidget(splitter)
        
        # Signals
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        self.btn_add.clicked.connect(self._add_tier)
        self.btn_rem.clicked.connect(self._rem_tier)
        self.btn_up.clicked.connect(self._move_up)
        self.btn_down.clicked.connect(self._move_down)
        
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            
    def _on_row_changed(self, row: int):
        if row >= 0:
            item = self.list_widget.item(row)
            self.builder.editor.blockSignals(True)
            self.builder.editor.setText(item.text())
            self.builder.editor.blockSignals(False)
        else:
            self.builder.editor.blockSignals(True)
            self.builder.editor.setText("")
            self.builder.editor.blockSignals(False)
            
    def _on_editor_changed(self, text: str):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.item(row).setText(text)
            
    def _add_tier(self):
        self.list_widget.addItem(QListWidgetItem("{catno}"))
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)
        
    def _rem_tier(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)
            
    def _move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row - 1, item)
            self.list_widget.setCurrentRow(row - 1)
            
    def _move_down(self):
        row = self.list_widget.currentRow()
        if row >= 0 and row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row + 1, item)
            self.list_widget.setCurrentRow(row + 1)
            
    def get_fallbacks(self) -> list:
        fallbacks = []
        for i in range(self.list_widget.count()):
            fallbacks.append(self.list_widget.item(i).text())
        return fallbacks
