import os
import re

content = open('core/ui/theme.py', encoding='utf-8').read()

# 1. Add to PALETTE_LABELS
content = content.replace(
    '"bg_selection":     "Selected row highlight",',
    '"bg_selection":     "Selected row highlight",\n    "bg_cell_selection": "Selected cell highlight",\n    "bg_cell_hover":    "Cell hover highlight",'
)

# 2. Add to PRESETS (using a regex to find "bg_selection": "...", and append our two new keys)
# We will just duplicate bg_selection for bg_cell_selection, and lighten/darken it for bg_cell_hover.
def repl(m):
    bg_sel = m.group(1)
    # We'll just make them the same as bg_selection initially, the user can customize them
    return f'{m.group(0)}\n        "bg_cell_selection": {bg_sel},\n        "bg_cell_hover":     {bg_sel},'

content = re.sub(r'("bg_selection":\s*("[^"]+")),', repl, content)

# 3. Update build_stylesheet
# To get cell hover, we need QTableWidget::item:hover
# To get selected cell, we need QTableWidget::item:selected
# We also need to add qproperty-mouseTracking to enable hover
css_replace = """    QTableWidget::item {
        border-right: 1px solid {d['border']};
        border-bottom: 1px solid {d['border']};
        padding: 2px;
    }
    QTableWidget::item:hover {
        background-color: {d.get('bg_cell_hover', d['bg_selection'])};
    }
    QTableWidget::item:selected {
        background-color: {d.get('bg_cell_selection', d['bg_selection'])};
    }"""
content = content.replace(
    """    QTableWidget::item {
        border-right: 1px solid {d['border']};
        border-bottom: 1px solid {d['border']};
        padding: 2px;
    }""",
    css_replace
)

open('core/ui/theme.py', 'w', encoding='utf-8').write(content)
