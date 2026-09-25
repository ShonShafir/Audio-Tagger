import os

content = open('core/ui/tagger_tab.py', encoding='utf-8').read()

# 1. scan_done
content = content.replace(
    'self.progress.setValue(100)\n        self.sb.showMessage(\n            f"Parsed {len(rows)} tracks',
    'self.progress.setValue(100)\n        QTimer.singleShot(2500, lambda: self.progress.setValue(0))\n        self.sb.showMessage(\n            f"Parsed {len(rows)} tracks'
)

# 2. discogs_done
content = content.replace(
    'self.progress.setValue(100)\n        self.sb.showMessage(f"Discogs done. {len(self.covers)} covers downloaded.")',
    'self.progress.setValue(100)\n        QTimer.singleShot(2500, lambda: self.progress.setValue(0))\n        self.sb.showMessage(f"Discogs done. {len(self.covers)} covers downloaded.")'
)

# 3. run_transforms
content = content.replace(
    'self.sb.showMessage("Transforms applied.")',
    'self.sb.showMessage("Transforms applied.")\n        self.progress.setValue(100)\n        QTimer.singleShot(2500, lambda: self.progress.setValue(0))'
)

# 4. apply worker
content = content.replace(
    'self.progress.setValue(100),\n            QMessageBox.information',
    'self.progress.setValue(100),\n            QTimer.singleShot(2500, lambda: self.progress.setValue(0)),\n            QMessageBox.information'
)

open('core/ui/tagger_tab.py', 'w', encoding='utf-8').write(content)
