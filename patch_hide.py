import os

content = open('core/ui/tagger_tab.py', encoding='utf-8').read()

# Replace QTimer lambda:
content = content.replace(
    'QTimer.singleShot(2500, lambda: self.progress.setValue(0))',
    'QTimer.singleShot(2500, lambda: (self.progress.setValue(0), self.progress.hide()))'
)

# And now add self.progress.show() to the 4 run functions
content = content.replace(
    'self.pause_btn.setText("⏸ Pause")\n        self.progress.setValue(0)',
    'self.pause_btn.setText("⏸ Pause")\n        self.progress.show()\n        self.progress.setValue(0)'
)

content = content.replace(
    'self.apply_btn.setEnabled(False)\n        self.progress.setValue(0)',
    'self.apply_btn.setEnabled(False)\n        self.progress.show()\n        self.progress.setValue(0)'
)

# For run_transforms, we need to show it right before we set it to 100 since it happens instantly
content = content.replace(
    'self.sb.showMessage("Transforms applied.")\n        self.progress.setValue(100)',
    'self.sb.showMessage("Transforms applied.")\n        self.progress.show()\n        self.progress.setValue(100)'
)

open('core/ui/tagger_tab.py', 'w', encoding='utf-8').write(content)
