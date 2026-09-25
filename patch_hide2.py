import os
content = open('core/ui/tagger_tab.py', encoding='utf-8').read()

content = content.replace(
    'self.pause_btn.setText("\\u23f8 Pause")\n        self.progress.setValue(0)',
    'self.pause_btn.setText("\\u23f8 Pause")\n        self.progress.show()\n        self.progress.setValue(0)'
)

open('core/ui/tagger_tab.py', 'w', encoding='utf-8').write(content)
