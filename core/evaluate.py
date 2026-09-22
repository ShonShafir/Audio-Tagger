import copy
import re
from core.transforms import resolve_discogs_value

def build_template_context(row: dict) -> dict:
    """Builds a dict of all available tokens for templates."""
    ctx = {}
    
    # Original parsed values
    if "fields_orig" in row:
        for k, v in row["fields_orig"].items():
            ctx[f"{k}_orig"] = v or ""
            # Fallback if current fields isn't populated yet
            if "fields" not in row or k not in row["fields"]:
                ctx[k] = v or ""
                
    # Current values (overrides if present)
    if "fields" in row:
        for k, v in row["fields"].items():
            ctx[k] = v or ""
            
    ctx["filename_current"] = row.get("proposed", "")
    ctx["filename_orig"] = row.get("original", "")
    
    return ctx

def evaluate_template(template_str: str, ctx: dict) -> str:
    """Safely evaluates a format string with missing keys."""
    if not template_str:
        return ""
    def repl(m):
        key = m.group(1).lower()
        return str(ctx.get(key, ""))
    return re.sub(r'\{([a-zA-Z0-9_]+)\}', repl, template_str).strip()

def get_field_value(field_cfg: dict, row: dict, discogs_data: dict = None, allow_discogs: bool = True) -> str:
    """
    Evaluates a single field based on its source (parsed, static, discogs, template, fallback).
    If allow_discogs is False, we skip discogs lookups (useful during initial scan).
    """
    fid = field_cfg["id"]
    source = field_cfg.get("source", "parsed")
    
    def get_from_source(src):
        if src == "parsed":
            return row.get("fields_orig", {}).get(fid, "")
        elif src == "static":
            return field_cfg.get("static_value", "")
        elif src == "discogs":
            if not allow_discogs:
                return ""
            if discogs_data:
                return resolve_discogs_value(discogs_data, field_cfg.get("discogs_field", ""))
            return ""
        elif src == "template":
            tmpl = field_cfg.get("template_value", "")
            ctx = build_template_context(row)
            return evaluate_template(tmpl, ctx)
        return ""
        
    if source == "fallback":
        order = field_cfg.get("fallback_order", ["parsed"])
        for src in order:
            val = get_from_source(src)
            if val:
                return val
        return ""
    else:
        return get_from_source(source)
