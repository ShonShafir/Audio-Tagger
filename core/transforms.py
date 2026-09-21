"""
core/transforms.py
------------------
Pure-Python utilities for transforming string values.

Public API
----------
sanitize_filename(name)                  — strip Windows-illegal chars
apply_transform(value, transform_expr)   — run a pipe-separated transform chain
resolve_discogs_value(release, path)     — pull a scalar out of a Discogs JSON blob

The transform mini-language understood by apply_transform:

  date:FORMAT     — reformat a date (tokens: dd, mm, yyyy, yy)
  s/FIND/REPL/    — regex substitute (case-sensitive)
  s/FIND/REPL/i   — regex substitute (case-insensitive)
  upper           — UPPERCASE
  lower           — lowercase
  title           — Title Case
  trim            — strip surrounding whitespace
  safe            — replace Windows-illegal filename chars with '-'

Commands are chained with '|' and execute left-to-right.
"""

import re


# ── Filename safety ───────────────────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    """Replace Windows-illegal filename characters (\\/:*?"<>|) with a hyphen."""
    return re.sub(r'[\\/:*?"<>|]', "-", name)


# ── Date reformatter ──────────────────────────────────────────────────────────

def _transform_date(value: str, fmt: str) -> str:
    """Reformat *value* into *fmt* using tokens dd / mm / yyyy / yy.

    Handles the messy Discogs date formats:
    ``"2011-12-02"``, ``"2011-12-00"``, ``"2011-12"``, ``"2011"``,
    and free-text such as ``"02 Dec 2011"``.
    """
    from datetime import datetime

    value = value.strip()
    if not value:
        return ""

    # Try ISO-style split first (yyyy-mm-dd or yyyy-mm or yyyy)
    parts = value.replace("/", "-").split("-")
    year  = parts[0] if len(parts) >= 1 else "0000"
    month = parts[1] if len(parts) >= 2 else "00"
    day   = parts[2] if len(parts) >= 3 else "00"

    # Fallback: try common full-text date formats
    if not year.isdigit():
        for date_fmt in ("%d %b %Y", "%B %d, %Y", "%Y-%m-%d"):
            try:
                dt    = datetime.strptime(value, date_fmt)
                year  = str(dt.year)
                month = f"{dt.month:02d}"
                day   = f"{dt.day:02d}"
                break
            except ValueError:
                continue

    result = fmt
    result = result.replace("yyyy", year.zfill(4))
    result = result.replace("yy",   year[-2:] if len(year) >= 2 else year)
    result = result.replace("mm",   month.zfill(2))
    result = result.replace("dd",   day.zfill(2))
    return result


# ── Transform chain executor ──────────────────────────────────────────────────

def apply_transform(value: str, transform_expr: str) -> str:
    """Apply a pipe-separated chain of transform commands to *value*.

    Returns *value* unchanged if *transform_expr* is empty or None.
    """
    if not transform_expr or not transform_expr.strip():
        return value

    for step in transform_expr.split("|"):
        step = step.strip()
        if not step:
            continue

        if step.startswith("date:"):
            value = _transform_date(value, step[5:])

        elif step.startswith("s/"):
            # sed-style: s/pattern/replacement/[i]
            parts = step[2:].split("/")
            if len(parts) >= 3:
                pattern, repl = parts[0], parts[1]
                # Unescape \& → & and \\ → \ so users can type them in the UI
                repl = repl.replace("\\&", "&").replace("\\\\", "\\")
                flags_str = parts[2] if len(parts) > 2 else ""
                flags = re.IGNORECASE if "i" in flags_str else 0
                value = re.sub(pattern, repl, value, flags=flags)

        elif step == "upper": value = value.upper()
        elif step == "lower": value = value.lower()
        elif step == "title": value = value.title()
        elif step == "trim":  value = value.strip()
        elif step == "safe":  value = sanitize_filename(value)

    return value


# ── Discogs JSON field-path resolver ──────────────────────────────────────────

def resolve_discogs_value(release: dict, field_path: str) -> str:
    """Extract a human-readable string from a Discogs release dict.

    Special shorthand paths
    -----------------------
    ``"artists"``  — joined display names (strips trailing ``(N)`` suffixes)
    ``"labels"``   — joined label names

    All other paths use dot/bracket notation understood by the Discogs API
    docs, e.g. ``"released"``, ``"styles"``, ``"country"``, ``"title"``.

    Returns an empty string on any error (missing key, wrong type, etc.).
    """
    if not field_path or not release:
        return ""

    # Shorthand: artists list → "Name1, Name2"
    if field_path == "artists":
        arts  = release.get("artists", [])
        names = [re.sub(r" \(\d+\)$", "", a.get("name", "")) for a in arts]
        return ", ".join(n for n in names if n)

    # Shorthand: labels list → "Label1, Label2"
    if field_path == "labels":
        labs  = release.get("labels", [])
        names = [re.sub(r" \(\d+\)$", "", a.get("name", "")) for a in labs]
        return ", ".join(n for n in names if n)

    # Generic dot / bracket traversal
    try:
        tokens = []
        for part in re.split(r"(\[\d+\])", field_path):
            if not part:
                continue
            if part.startswith("["):
                tokens.append(int(part[1:-1]))
            else:
                tokens.extend(s for s in part.split(".") if s)
        obj = release
        for t in tokens:
            obj = obj[t]
        if isinstance(obj, list):
            return ", ".join(str(x) for x in obj[:3])
        return str(obj)
    except Exception:
        return ""
