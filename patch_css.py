import os

content = open('core/ui/theme.py', encoding='utf-8').read()

old_css = """    QTableWidget::item {{
        border-right: 1px solid {d['border']};
        border-bottom: 1px solid {d['border']};
        padding: 2px;
    }}"""

new_css = """    QTableWidget::item {{
        border-right: 1px solid {d['border']};
        border-bottom: 1px solid {d['border']};
        padding: 2px;
    }}
    QTableWidget::item:hover {{
        background-color: {d.get('bg_cell_hover', d['bg_selection'])};
    }}
    QTableWidget::item:selected {{
        background-color: {d.get('bg_cell_selection', d['bg_selection'])};
        color: {d['text_primary']};
    }}"""

content = content.replace(old_css, new_css)
open('core/ui/theme.py', 'w', encoding='utf-8').write(content)
