import os
content = open('core/ui/theme_tab.py', encoding='utf-8').read()

# Replace _ROW_ORDER with _GROUPS
content = content.replace(
    '''    _ROW_ORDER = [
        "bg_window", "bg_base", "bg_surface", "bg_input",
        "bg_header", "bg_selection", "bg_cell_selection", "bg_cell_hover",
        "text_primary", "text_muted", "text_readonly",
        "accent", "accent_hover", "accent_disabled",
        "border", "error",
    ]''',
    '''    _GROUPS = [
        ("Backgrounds & Panels", [
            "bg_window", "bg_base", "bg_surface", "bg_input", "bg_header"
        ]),
        ("Grid Highlights", [
            "bg_selection", "bg_cell_selection", "bg_cell_hover"
        ]),
        ("Text & Typography", [
            "text_primary", "text_muted", "text_readonly"
        ]),
        ("Accents & Status", [
            "accent", "accent_hover", "accent_disabled", "border", "error"
        ])
    ]'''
)

# Modify the for-loop generating the rows
old_loop = '''        for key in self._ROW_ORDER:
            label = PALETTE_LABELS.get(key, key)
            row   = ColourRow(key, label, "#000000")
            row.colour_changed.connect(self._colour_changed)
            self._rows[key] = row
            grid.addWidget(row)'''

new_loop = '''        from PyQt6.QtWidgets import QFrame
        for group_name, keys in self._GROUPS:
            header = QLabel(group_name)
            font = header.font()
            font.setBold(True)
            font.setPointSize(font.pointSize() + 1)
            header.setFont(font)
            header.setStyleSheet("color: palette(highlight); margin-top: 12px; margin-bottom: 4px;")
            grid.addWidget(header)
            
            for key in keys:
                label = PALETTE_LABELS.get(key, key)
                row   = ColourRow(key, label, "#000000")
                row.colour_changed.connect(self._colour_changed)
                self._rows[key] = row
                grid.addWidget(row)
                
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("color: palette(mid); opacity: 0.5;")
            grid.addWidget(line)'''

content = content.replace(old_loop, new_loop)

open('core/ui/theme_tab.py', 'w', encoding='utf-8').write(content)
