import sys
from PyQt6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem
from PyQt6.QtGui import QColor

app = QApplication(sys.argv)
tbl = QTableWidget(2, 2)
tbl.setAlternatingRowColors(True)
tbl.setStyleSheet("""
QTableWidget{background:#181825;gridline-color:#313244;
             selection-background-color:#45475a;alternate-background-color:#1e1e2e}
""")
for r in range(2):
    for c in range(2):
        item = QTableWidgetItem(f"Row {r} Col {c}")
        if r == 0:
            item.setBackground(QColor("#f9e2af"))
            item.setForeground(QColor("#000000"))
        tbl.setItem(r, c, item)

tbl.show()
sys.exit(app.exec())
