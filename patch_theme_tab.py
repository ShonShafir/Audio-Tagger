import re

content = open('core/ui/theme_tab.py', encoding='utf-8').read()

content = content.replace(
    '"bg_header", "bg_selection",',
    '"bg_header", "bg_selection", "bg_cell_selection", "bg_cell_hover",'
)

open('core/ui/theme_tab.py', 'w', encoding='utf-8').write(content)
