import re

with open('core/ui/tagger_tab.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'^[ \t]*#[ \t]*Double-click a row.*?$\n^[ \t]*self\.table\.cellDoubleClicked\.connect\(self\._on_cell_double_clicked\).*?$\n', '', content, flags=re.MULTILINE)

# Just in case the comment was different:
content = re.sub(r'^[ \t]*self\.table\.cellDoubleClicked\.connect\(self\._on_cell_double_clicked\).*?$\n', '', content, flags=re.MULTILINE)

# Also completely remove the method definition
content = re.sub(r'^[ \t]*def _on_cell_double_clicked\(self, row: int, col: int\):.*?(?=^[ \t]*def |^[ \t]*# ==)', '', content, flags=re.MULTILINE | re.DOTALL)

with open('core/ui/tagger_tab.py', 'w', encoding='utf-8') as f:
    f.write(content)
