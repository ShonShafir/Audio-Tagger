import sys
from PyQt6.QtWidgets import QApplication
from core.ui.workers import ScanWorker
from core.config import DEFAULT_CONFIG

app = QApplication(sys.argv)
worker = ScanWorker('D:/test', DEFAULT_CONFIG)

def on_error(err):
    print(err)
    app.quit()

def on_finished(results):
    for r in results:
        print(r['original'])
        for k, v in r['fields'].items():
            if v:
                print('  ', k, ':', v)
    app.quit()

worker.finished.connect(on_finished)
worker.error.connect(on_error)
worker.start()
app.exec()
