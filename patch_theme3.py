import re

content = open('core/ui/theme.py', encoding='utf-8').read()

# 1. PALETTE_LABELS
content = content.replace(
    '"bg_selection":     "Selected row highlight",',
    '"bg_selection":     "Selected row highlight",\n    "bg_cell_selection": "Selected cell background",\n    "bg_cell_hover":    "Cell hover background",'
)

# 2. Add to PRESETS
# We match PRESETS = { ... }
# We only want to replace bg_selection inside the presets
def repl(m):
    val = m.group(1) # The hex value
    return f'"bg_selection":    {val},\n        "bg_cell_selection": {val},\n        "bg_cell_hover":     {val},'

content = re.sub(r'"bg_selection":\s*("#[A-Fa-f0-9]+"),', repl, content)

# 3. Update build_stylesheet
css_replace = """    QTableWidget::item {
        border-right: 1px solid {d['border']};
        border-bottom: 1px solid {d['border']};
        padding: 2px;
    }
    QTableWidget::item:hover {
        background: {d.get('bg_cell_hover', d['bg_selection'])};
    }
    QTableWidget::item:selected {
        background: {d.get('bg_cell_selection', d['bg_selection'])};
        color: {d['text_primary']};
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
