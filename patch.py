import os
content = open('core/ui/tagger_tab.py', encoding='utf-8').read()

new_func = """
    def run_transforms(self):
        self.cfg = self.settings_tab.get_cfg()
        fields = self.cfg.get("fields", [])
        
        selected_items = self.table.selectedItems()
        target_cells_by_row = {}
        
        col_to_field = {}
        for field in fields:
            label = field.get("label")
            if label in self._col_map:
                col_to_field[self._col_map[label]] = field.get("id")

        if selected_items:
            for item in selected_items:
                r = item.row()
                c = item.column()
                fid = col_to_field.get(c)
                if fid:
                    target_cells_by_row.setdefault(r, set()).add(fid)
        else:
            allowed = self.get_allowed_fields()
            for r in range(len(self.rows)):
                target_cells_by_row[r] = allowed
                
        from core.transforms import apply_transform
        
        for r, fids in target_cells_by_row.items():
            if r >= len(self.rows): continue
            row_data = self.rows[r]
            for field in fields:
                if field["id"] not in fids:
                    continue
                xform = field.get("transform", "")
                if xform:
                    old_val = row_data["fields"].get(field["id"], "")
                    if old_val:
                        new_val = apply_transform(old_val, xform)
                        if new_val != old_val:
                            label = field.get("label")
                            if label in self._col_map:
                                c = self._col_map[label]
                                item = self.table.item(r, c)
                                if item:
                                    # This triggers itemChanged, which updates row_data["fields"] and recalculates proposed filename automatically!
                                    item.setText(new_val)
                            
        self.sb.showMessage("Transforms applied.")
"""

content = content.replace('    def run_scan(self):', new_func + '\n    def run_scan(self):')
open('core/ui/tagger_tab.py', 'w', encoding='utf-8').write(content)
