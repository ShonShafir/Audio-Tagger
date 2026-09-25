import re

with open('core/ui/tagger_tab.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove the double click connection (and its comment)
content = re.sub(r'^[ \t]*#[ \t]*Double-click a row.*?$\n^[ \t]*self\.table\.cellDoubleClicked\.connect\(self\._on_cell_double_clicked\).*?$\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^[ \t]*self\.table\.cellDoubleClicked\.connect\(self\._on_cell_double_clicked\).*?$\n', '', content, flags=re.MULTILINE)

# 2. Rename `def _on_cell_double_clicked(self, row: int, col: int):` to `def _play_row_audio(self, row: int):`
content = re.sub(
    r'def _on_cell_double_clicked\(self, row: int, col: int\):',
    r'def _play_row_audio(self, row: int):',
    content
)

# 3. Update the context menu call
content = content.replace(
    'self._on_cell_double_clicked(row, 0)',
    'self._play_row_audio(row)'
)

with open('core/ui/tagger_tab.py', 'w', encoding='utf-8') as f:
    f.write(content)
