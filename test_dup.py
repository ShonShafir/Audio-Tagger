import sys, time
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer

from app import MainWindow

app = QApplication(sys.argv)
win = MainWindow()
win.show()

def test_script():
    try:
        rows = [
            {"path": "c:/track1.mp3", "original": "track1.mp3", "proposed": "Artist - Title 1.mp3", "fields": {"catno": "CAT01", "artist": "Artist", "title": "Title 1"}},
            {"path": "c:/track2.mp3", "original": "track2.mp3", "proposed": "Artist - Title 2.mp3", "fields": {"catno": "CAT01", "artist": "Artist", "title": "Title 2"}}
        ]
        win.cfg["naming_template"] = "({catno}) {artist} - {title}.mp3"
        win._fill_table(rows)
        win.rows = rows
        
        # force re-eval of both
        win.table.item(0, win._col_map["Title"]).setText("Title X")
        win.table.item(1, win._col_map["Title"]).setText("Title X")
        
        prop_col = win._col_map["Proposed Filename"]
        for r in range(win.table.rowCount()):
            print("Row", r, "Proposed:", win.table.item(r, prop_col).text())
            
        win._check_duplicates()
        
        bg = win.table.item(0, prop_col).background().color().name()
        print("Background color of row 0:", bg)
        bg2 = win.table.item(1, prop_col).background().color().name()
        print("Background color of row 1:", bg2)
    except Exception as e:
        print("ERROR:", e)
    finally:
        QApplication.quit()

QTimer.singleShot(1000, test_script)
sys.exit(app.exec())
