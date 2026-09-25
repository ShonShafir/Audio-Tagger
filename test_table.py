import sys
from PyQt6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem
from core.ui.theme import get_palette, build_stylesheet

app = QApplication(sys.argv)
t = QTableWidget(5, 5)
for r in range(5):
    for c in range(5):
        t.setItem(r, c, QTableWidgetItem(f"Cell {r}-{c}"))

t.setMouseTracking(True)
t.viewport().setAttribute(sys.modules['PyQt6.QtCore'].Qt.WidgetAttribute.WA_Hover)
t.setAlternatingRowColors(True)
# t.setSelectionBehavior(t.SelectionBehavior.SelectItems) # Default is SelectItems

d = get_palette({})
t.setStyleSheet(build_stylesheet(d))
t.show()
sys.exit(app.exec())
