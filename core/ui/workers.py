"""
core/ui/workers.py
------------------
Background QThread workers that keep the UI responsive during
heavy I/O operations.

Classes
-------
ScanWorker      — walks a folder, parses filenames, returns a list of row dicts
DiscogsWorker   — fetches release metadata + cover art from the Discogs API
ApplyWorker     — writes ID3 tags and renames MP3 files on disk

All three workers expose a pause / resume / stop API and emit a
``progress(int, str)`` signal so the main window can update its
progress bar and status bar.
"""

import os
import re
import glob
import traceback
import time

from PyQt6.QtCore import QThread, pyqtSignal

from core.config import DEFAULT_FIELDS
from core.transforms import apply_transform, sanitize_filename, resolve_discogs_value
from core.parser import (
    normalize_feat, strip_original_mix, extract_feat,
    extract_remixer, scan_m3u_files, scan_nfo_files,
    build_proposed_filename, title_case_smart,
)
from core.discogs import DiscogsClient
from core.tagger import load_or_create_id3, clear_user_tags, read_cover, get_file_type, apply_tags as _apply_tags_to_file


# ─────────────────────────────────────────────────────────────────────────────
# ScanWorker
# ─────────────────────────────────────────────────────────────────────────────

class ScanWorker(QThread):
    """Walk *folder*, parse every MP3 filename, and emit the resulting rows.

    Signals
    -------
    progress(int, str)  — (0-100 %, status message)
    finished(list)      — list of row dicts once done
    error(str)          — full traceback string on unexpected failure
    """

    progress = pyqtSignal(int, str)
    complete = pyqtSignal(list)    # renamed from 'finished' to avoid shadowing QThread.finished
    error    = pyqtSignal(str)


    def __init__(self, folder: str, cfg: dict,
                 existing_rows: list = None, allowed_fields: set = None, target_paths: dict = None):
        super().__init__()
        self.folder         = folder
        self.cfg            = cfg
        self.existing_rows  = existing_rows or []
        self.allowed_fields = allowed_fields
        self.target_paths   = target_paths   # None = update everything
        self.is_paused      = False
        self._is_running    = True

    def pause(self):  self.is_paused   = True
    def resume(self): self.is_paused   = False
    def stop(self):   self._is_running = False

    def run(self):
        try:
            cfg      = self.cfg
            feat_fmt = cfg.get("feat_format", "ft.")

            # ── Collect audio paths (MP3, FLAC, WAV) ────────────────────────
            EXTS = (".mp3", ".flac", ".wav")
            audio_files = []
            for root, _, files in os.walk(self.folder):
                for f in files:
                    if os.path.splitext(f)[1].lower() in EXTS:
                        audio_files.append(os.path.join(root, f))
            self.progress.emit(5, f"Found {len(audio_files)} audio files (MP3/FLAC/WAV)...")

            m3u_map = scan_m3u_files(self.folder)
            self.progress.emit(10, "Parsed .m3u files...")
            nfo_map = scan_nfo_files(self.folder)

            existing_map = {rd["path"]: rd for rd in self.existing_rows}
            results      = []
            total        = len(audio_files)

            for i, path in enumerate(audio_files):
                if not self._is_running:
                    break
                while self.is_paused:
                    time.sleep(0.5)
                    if not self._is_running:
                        return
                
                # If we're doing a targeted re-scan and this file isn't targeted,
                # just keep the existing row (if we have it).
                if self.target_paths is not None and path not in self.target_paths:
                    if path in existing_map:
                        results.append(existing_map[path])
                    continue

                fname     = os.path.basename(path).lower()
                nfo       = nfo_map.get(fname, {})
                file_type = get_file_type(path)   # "MP3" / "FLAC" / "WAV"

                # ── Catalogue number ─────────────────────────────────────────
                catno = m3u_map.get(fname) or nfo.get("catno", "")
                if not catno:
                    parent = os.path.basename(os.path.dirname(path))
                    m = re.search(r"([A-Z]{2,6}B?\d{2,4})", parent, re.IGNORECASE)
                    catno = m.group(1).upper() if m else ""

                # ── Filename → raw artist / title ────────────────────────────
                base = os.path.splitext(os.path.basename(path))[0]
                base = re.sub(r"^\d+[-_]",         "", base)
                base = re.sub(r"-[a-f0-9]{8}$",    "", base)
                base = re.sub(r"[-_][a-z0-9]{3,8}$", "", base)
                # Split on the LAST " - " (handles hyphens inside artist names)
                if " - " in base:
                    parts = base.rsplit(" - ", 1)
                else:
                    parts = base.rsplit("-", 1)
                raw_a = parts[0].replace("_", " ").strip() if len(parts) == 2 else base.replace("_", " ").strip()
                raw_t = parts[1].replace("_", " ").strip() if len(parts) == 2 else ""

                # NFO metadata overrides filename guesses
                if "artist" in nfo: raw_a = nfo["artist"]
                if "title"  in nfo: raw_t = nfo["title"]

                raw_a = normalize_feat(raw_a, feat_fmt)
                raw_t = normalize_feat(raw_t, feat_fmt)
                if cfg.get("strip_original_mix", True):
                    raw_t = strip_original_mix(raw_t)

                artist,  featured = extract_feat(raw_a, feat_fmt)
                raw_t,   remixer  = extract_remixer(raw_t)

                artist   = title_case_smart(artist)
                featured = title_case_smart(featured)
                raw_t    = title_case_smart(raw_t)
                remixer  = title_case_smart(remixer)

                fv = {
                    "file_type":  file_type,
                    "artist":     artist,
                    "featured":   featured,
                    "title":      raw_t,
                    "remixer":    remixer,
                    "catno":      catno,
                    "date":       nfo.get("date", ""),
                    "style":      "",
                    "country":    "",
                    "genre":      "",
                    "label_name": nfo.get("company", ""),
                    "album":      "",
                }

                # Apply static values and field transforms
                for field in cfg.get("fields", DEFAULT_FIELDS):
                    if field["source"] in ("static", "both") and field.get("static_value"):
                        fv[field["id"]] = field["static_value"]
                    xform = field.get("transform", "")
                    if xform and field["id"] in fv and fv[field["id"]]:
                        fv[field["id"]] = apply_transform(fv[field["id"]], xform)

                # ── Merge with existing row (respects locked and targeted columns) ──
                existing_cover = b""
                enabled        = True
                
                if self.target_paths is not None:
                    row_allowed = self.target_paths[path]
                    if self.allowed_fields is not None:
                        row_allowed = row_allowed.intersection(self.allowed_fields)
                else:
                    row_allowed = self.allowed_fields

                if path in existing_map:
                    ex = existing_map[path]
                    enabled = ex.get("enabled", True)
                    
                    if row_allowed is not None:
                        for field_id, old_val in ex.get("fields", {}).items():
                            if field_id not in row_allowed:
                                fv[field_id] = old_val
                    
                    if row_allowed is not None and "__cover__" not in row_allowed:
                        existing_cover = ex.get("cover_data", b"")
                    else:
                        existing_cover = read_cover(path)
                else:
                    # Try to load an existing embedded cover (works for all formats)
                    existing_cover = read_cover(path)

                tmpl     = cfg.get("naming_template", "({catno}) {artist} - {title}.mp3")
                proposed = build_proposed_filename(
                    tmpl,
                    fv.get("catno", "UNKNOWN"),
                    fv.get("artist", ""),
                    fv.get("featured", ""),
                    fv.get("title", ""),
                    feat_format=feat_fmt,
                    original_ext=os.path.splitext(path)[1],
                )
                results.append({
                    "path":       path,
                    "original":   os.path.basename(path),
                    "proposed":   proposed,
                    "fields":     fv,
                    "enabled":    enabled,
                    "cover_data": existing_cover,
                })
                self.progress.emit(
                    10 + int(80 * (i + 1) / total),
                    f"Parsed {i+1}/{total}: {os.path.basename(path)}",
                )

            self.progress.emit(95, "Done.")
            self.complete.emit(results)
        except Exception:
            self.error.emit(traceback.format_exc())



# ─────────────────────────────────────────────────────────────────────────────
# DiscogsWorker
# ─────────────────────────────────────────────────────────────────────────────

class DiscogsWorker(QThread):
    """Fetch Discogs release metadata + cover art for every row that has a CatNo.

    Uses a four-tier search strategy to maximise hit rate:
    1. CatNo + lead artist + clean title
    2. CatNo + lead artist
    3. CatNo + first word of lead artist
    4. CatNo alone (last resort)

    Signals
    -------
    progress(int, str)          — (0-100 %, status message)
    row_updated(int, dict, bytes) — (row index, new field values, cover bytes)
    finished()
    error(str)
    """

    progress    = pyqtSignal(int, str)
    row_updated = pyqtSignal(int, dict, bytes)
    complete    = pyqtSignal()     # renamed from 'finished' to avoid shadowing QThread.finished
    error       = pyqtSignal(str)


    def __init__(self, rows: list, cfg: dict, folder: str, allowed_fields: set = None, target_cells: dict = None):
        super().__init__()
        self.rows           = rows
        self.cfg            = cfg
        self.folder         = folder
        self.allowed_fields = allowed_fields
        self.target_cells   = target_cells
        self.is_paused      = False
        self._is_running    = True

    def pause(self):  self.is_paused   = True
    def resume(self): self.is_paused   = False
    def stop(self):   self._is_running = False

    def run(self):
        try:
            cfg      = self.cfg
            fields   = cfg.get("fields", DEFAULT_FIELDS)
            feat_fmt = cfg.get("feat_format", "ft.")
            client = DiscogsClient(
                token=cfg.get("discogs_token", ""),
                rate_limit=float(cfg.get("rate_limit", 2)),
            )
            cache_rel: dict = {}
            cache_cov: dict = {}
            total = len(self.rows)

            for i, row in enumerate(self.rows):
                if self.target_cells is not None and i not in self.target_cells:
                    continue
                
                if self.target_cells is not None:
                    row_allowed = self.target_cells[i]
                    if self.allowed_fields is not None:
                        row_allowed = row_allowed.intersection(self.allowed_fields)
                else:
                    row_allowed = self.allowed_fields

                if not self._is_running:
                    break
                while self.is_paused:
                    time.sleep(0.5)
                    if not self._is_running:
                        return

                catno = row["fields"].get("catno", "")
                if not catno or catno == "UNKNOWN":
                    self.progress.emit(
                        int(100 * (i + 1) / total),
                        f"Skipped: {os.path.basename(row['path'])}",
                    )
                    continue

                if catno not in cache_rel:
                    artist      = row["fields"].get("artist", "")
                    title       = row["fields"].get("title",  "")
                    # Keep only the lead artist (drop "A ft. B", "A and B", etc.)
                    lead_artist = re.split(
                        r"\s+(?:and|&|ft\.?|feat\.?|vs\.?|with)\s+",
                        artist, flags=re.IGNORECASE,
                    )[0].strip()
                    # Strip parenthetical qualifiers from the title
                    clean_title = re.sub(r"\s*\(.*?\)", "", title).strip()

                    def _norm(s):
                        return re.sub(r"[-\s]", "", (s or "")).upper()

                    def _best_match(candidates):
                        """Rank by: exact catno match first, then artist-word overlap."""
                        norm_exp   = _norm(catno)
                        lead_words = set(re.sub(r"[^a-z0-9 ]", "", lead_artist.lower()).split())
                        scored = []
                        for r in candidates:
                            catno_ok     = (_norm(r.get("catno", "")) == norm_exp)
                            r_title_norm = re.sub(r"[^a-z0-9 ]", "", r.get("title", "").lower())
                            artist_score = sum(1 for w in lead_words if w in r_title_norm)
                            scored.append((catno_ok, artist_score, r))
                        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
                        return scored[0][2] if scored else None

                    # Four-tier search
                    results = client.search_release(f"{catno} {lead_artist} {clean_title}".strip())
                    if not results:
                        results = client.search_release(f"{catno} {lead_artist}".strip())
                    if not results and lead_artist:
                        results = client.search_release(f"{catno} {lead_artist.split()[0]}".strip())
                    if not results:
                        results = client.search_release(catno)

                    best = _best_match(results) if results else None
                    if best:
                        rel_id = best["id"]
                        full   = client._get(f"https://api.discogs.com/releases/{rel_id}")
                        cache_rel[catno] = full
                        if self.target_cells is None or (row_allowed is not None and "__cover__" in row_allowed):
                            images = full.get("images", [])
                            if images:
                                primary = next(
                                    (img for img in images if img.get("type") == "primary"),
                                    images[0],
                                )
                                cache_cov[catno] = client.download_image(primary["uri"])
                            elif cfg.get("cover_fallback_local", True):
                                local_art = (
                                    glob.glob(os.path.join(self.folder, "*.png"))
                                    + glob.glob(os.path.join(self.folder, "*.jpg"))
                                )
                                if local_art:
                                    with open(local_art[0], "rb") as f:
                                        cache_cov[catno] = f.read()

                release = cache_rel.get(catno)
                
                # If we need the cover, ensure it's downloaded if not already in cache_cov
                needs_cover = self.target_cells is None or (row_allowed is not None and "__cover__" in row_allowed)
                if needs_cover and catno not in cache_cov and release:
                    images = release.get("images", [])
                    if images:
                        primary = next((img for img in images if img.get("type") == "primary"), images[0])
                        cache_cov[catno] = client.download_image(primary["uri"])
                    elif cfg.get("cover_fallback_local", True):
                        local_art = glob.glob(os.path.join(self.folder, "*.png")) + glob.glob(os.path.join(self.folder, "*.jpg"))
                        if local_art:
                            with open(local_art[0], "rb") as f:
                                cache_cov[catno] = f.read()

                # Fetch cover from cache if targeted or global update
                if needs_cover:
                    cover = cache_cov.get(catno, row.get("cover_data", b""))
                else:
                    cover = row.get("cover_data", b"")
                    
                if not release:
                    continue

                new_fv = dict(row["fields"])
                for field in fields:
                    if row_allowed is not None and field["id"] not in row_allowed:
                        continue
                    src = field["source"]
                    if src in ("discogs", "both") and field.get("discogs_field"):
                        val = resolve_discogs_value(release, field["discogs_field"])
                        if val:
                            xform = field.get("transform", "")
                            if xform:
                                val = apply_transform(val, xform)
                            if src == "discogs" or (src == "both" and not new_fv.get(field["id"])):
                                new_fv[field["id"]] = val

                tmpl     = cfg.get("naming_template", "({catno}) {artist} - {title}.mp3")
                proposed = build_proposed_filename(
                    tmpl,
                    new_fv.get("catno", "UNKNOWN"),
                    new_fv.get("artist", ""),
                    new_fv.get("featured", ""),
                    new_fv.get("title", ""),
                    feat_format=feat_fmt,
                    original_ext=os.path.splitext(row["path"])[1],
                )
                new_fv["__proposed__"] = sanitize_filename(proposed)
                self.row_updated.emit(i, new_fv, cover)
                self.progress.emit(
                    int(100 * (i + 1) / total),
                    f"Discogs {i+1}/{total}: {os.path.basename(row['path'])}",
                )

            self.complete.emit()
        except Exception:
            self.error.emit(traceback.format_exc())



# ─────────────────────────────────────────────────────────────────────────────
# ApplyWorker
# ─────────────────────────────────────────────────────────────────────────────

class ApplyWorker(QThread):
    """Write ID3 tags and rename MP3 files.  Runs in background to keep UI alive.

    Signals
    -------
    progress(int, str)  — (0-100 %, status message)
    finished()
    error(str)          — stops processing on first error
    """

    progress = pyqtSignal(int, str)
    complete = pyqtSignal()    # renamed from 'finished' to avoid shadowing QThread.finished
    error    = pyqtSignal(str)


    def __init__(self, rows: list, cfg: dict, covers: dict):
        super().__init__()
        self.rows   = rows
        self.cfg    = cfg
        self.covers = covers

    def run(self):
        cfg    = self.cfg
        fields = cfg.get("fields", DEFAULT_FIELDS)
        total  = len(self.rows)

        for i, row in enumerate(self.rows):
            if not row.get("enabled", True):
                continue
            path = row["path"]
            if not os.path.exists(path):
                self.error.emit(f"File not found: {path}")
                return
            try:
                fv  = row["fields"]
                cov = row.get("cover_data", b"")

                # Write tags using the format-aware dispatcher (MP3 / FLAC / WAV)
                _apply_tags_to_file(
                    path,
                    fv=fv,
                    fields=fields,
                    cover_data=cov,
                    embed_cover=cfg.get("embed_cover_art", True),
                )

                # Rename the file according to the proposed filename
                proposed = row.get("proposed", "")
                if proposed and proposed != "UNKNOWN":
                    new_path = os.path.join(os.path.dirname(path), proposed)
                    if path != new_path:
                        if os.path.exists(new_path):
                            self.error.emit(f"Target already exists: {new_path}")
                            return
                        os.rename(path, new_path)

            except Exception:
                self.error.emit(f"Error on {row['original']}:\n{traceback.format_exc()}")
                return

            self.progress.emit(int(100 * (i + 1) / total), f"Tagged {i+1}/{total}: {row['original']}")
        self.complete.emit()


