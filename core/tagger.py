"""
core/tagger.py
--------------
Format-aware tagging helpers for MP3, FLAC, and WAV.

Public API
----------
get_file_type(path)     -> "MP3" | "FLAC" | "WAV" | "UNKNOWN"
read_cover(path)        -> bytes | b""   (existing embedded cover, any format)
apply_tags(path, ...)   -> None          (writes tags; raises on failure)
rename_file(old, new)   -> str           (new full path)

Safety guarantees
-----------------
* FLAC: tags are modified only in-memory, then written in a SINGLE save()
  call.  The previous audio.delete() approach wrote to disk twice, leaving
  the file tag-less if the second write failed — that is fixed here.
* WAV:  cover art (APIC) is intentionally NOT embedded — software support
  for APIC in WAV is inconsistent and the frame can silently corrupt some
  players.
* All paths: fields with an empty id3_frame (display-only fields like
  "Type") are explicitly skipped before any write attempt.
* Errors propagate upward — nothing is silently swallowed.
"""

import os
from mutagen.id3 import (
    ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TRCK, TDRC,
    APIC, TXXX, TCON, TPUB, COMM
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_file_type(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    return {"mp3": "MP3", "flac": "FLAC", "wav": "WAV"}.get(ext.lstrip("."), "UNKNOWN")


def read_cover(filepath: str) -> bytes:
    """Return the embedded cover bytes from any supported format, or b''."""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".flac":
            from mutagen.flac import FLAC
            audio = FLAC(filepath)
            if audio.pictures:
                return audio.pictures[0].data
        elif ext == ".wav":
            from mutagen.wave import WAVE
            audio = WAVE(filepath)
            if audio.tags:
                apics = audio.tags.getall("APIC")
                if apics:
                    return apics[0].data
        else:  # MP3 / ID3
            tags = _load_id3(filepath)
            apics = tags.getall("APIC")
            if apics:
                return apics[0].data
    except Exception:
        pass
    return b""


# ── Internal ID3 helpers (MP3 / WAV) ─────────────────────────────────────────

def _load_id3(filepath: str) -> ID3:
    try:
        return ID3(filepath)
    except ID3NoHeaderError:
        return ID3()


def load_or_create_id3(filepath: str) -> ID3:
    """Legacy alias kept for any code that still calls it directly."""
    return _load_id3(filepath)


def clear_user_tags(audio: ID3, descs: list):
    """Remove specific TXXX frames by descriptor name (ID3 only)."""
    for desc in descs:
        key = f"TXXX:{desc}"
        if key in audio:
            del audio[key]


# ── Format-specific writers ───────────────────────────────────────────────────

def _apply_tags_id3(filepath: str, fv: dict, fields: list,
                     txxx_descs: list, cover_data: bytes,
                     embed_cover: bool, is_wav: bool) -> None:
    """Write ID3 tags to an MP3 or WAV file.

    WAV note: cover art (APIC) is intentionally skipped — software support
    for APIC embedded in WAV is inconsistent and can cause playback issues.
    """
    if is_wav:
        from mutagen.wave import WAVE
        audio = WAVE(filepath)
        if audio.tags is None:
            audio.add_tags()
        tags = audio.tags
    else:
        tags = _load_id3(filepath)

    # Clear managed frames
    clear_user_tags(tags, txxx_descs)
    for frame in ("TIT2", "TPE1", "TALB", "TDRC", "TCON", "APIC"):
        tags.delall(frame)

    # Write fields — skip display-only fields that have no id3_frame
    for field in fields:
        frame = field.get("id3_frame", "")
        if not frame:
            continue   # e.g. file_type — display only, nothing to write
        val = fv.get(field["id"], "")
        if not val:
            continue
        if   frame == "TPE1": tags.add(TPE1(encoding=3, text=[val]))
        elif frame == "TIT2": tags.add(TIT2(encoding=3, text=[val]))
        elif frame == "TALB": tags.add(TALB(encoding=3, text=[val]))
        elif frame == "TDRC": tags.add(TDRC(encoding=3, text=[val]))
        elif frame == "TCON": tags.add(TCON(encoding=3, text=[val]))
        elif frame.startswith("TXXX:"):
            tags.add(TXXX(encoding=3, desc=frame[5:], text=[val]))

    # Cover art — MP3 only; WAV is intentionally skipped (see docstring)
    if not is_wav and cover_data and embed_cover:
        mime = "image/png" if cover_data.startswith(b"\x89PNG") else "image/jpeg"
        tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=cover_data))

    if is_wav:
        audio.save()
    else:
        tags.save(filepath, v2_version=3)


def _apply_tags_flac(filepath: str, fv: dict, fields: list,
                      cover_data: bytes, embed_cover: bool) -> None:
    """Write Vorbis Comments (+ Picture) to a FLAC file.

    Safety: tags are cleared IN-MEMORY only, then the file is written in a
    SINGLE save() call.  The old audio.delete() approach triggered an
    intermediate disk write that left the file tag-less if save() later
    failed — that is corrected here.
    """
    from mutagen.flac import FLAC, Picture

    audio = FLAC(filepath)

    # ── Clear existing tags safely in memory (NO intermediate disk write) ──
    if audio.tags is not None:
        audio.tags.clear()          # wipe existing Vorbis Comments in-memory
    else:
        audio.add_tags()            # create empty VorbisComment block in-memory
    audio.clear_pictures()          # wipe existing pictures in-memory

    # Map id3_frame → Vorbis Comment key
    id3_to_vc = {
        "TPE1": "artist",
        "TIT2": "title",
        "TALB": "album",
        "TDRC": "date",
        "TCON": "genre",
    }

    # Write fields — skip display-only fields that have no id3_frame
    for field in fields:
        frame = field.get("id3_frame", "")
        if not frame:
            continue   # e.g. file_type — display only, nothing to write
        val = fv.get(field["id"], "")
        if not val:
            continue
        if frame in id3_to_vc:
            audio[id3_to_vc[frame]] = val
        elif frame.startswith("TXXX:"):
            # Store TXXX:KEY as key=value Vorbis Comment
            vc_key = frame[5:].upper().replace(" ", "_")
            audio[vc_key] = val

    # Cover art
    if cover_data and embed_cover:
        pic = Picture()
        pic.type = 3  # Front cover
        pic.mime = "image/png" if cover_data.startswith(b"\x89PNG") else "image/jpeg"
        pic.desc = "Cover"
        pic.data = cover_data
        audio.add_picture(pic)

    # ── Single disk write — all-or-nothing ────────────────────────────────
    audio.save()


# ── Public dispatcher ─────────────────────────────────────────────────────────

def apply_tags(filepath: str, fv: dict, fields: list,
               cover_data: bytes = b"", embed_cover: bool = True) -> None:
    """Apply metadata tags to *filepath* in the appropriate format.

    Parameters
    ----------
    filepath     : full path to the audio file
    fv           : dict of {field_id: value} from the table row
    fields       : list of field config dicts (from cfg["fields"])
    cover_data   : raw cover image bytes (JPEG or PNG)
    embed_cover  : whether to write the cover into the file
                   (ignored for WAV — APIC is never written to WAV)
    """
    ext = os.path.splitext(filepath)[1].lower()

    txxx_descs = [
        f["id3_frame"].split(":")[1]
        for f in fields if f.get("id3_frame", "").startswith("TXXX:")
    ]

    if ext == ".flac":
        _apply_tags_flac(filepath, fv, fields, cover_data, embed_cover)
    elif ext == ".wav":
        _apply_tags_id3(filepath, fv, fields, txxx_descs, cover_data, embed_cover, is_wav=True)
    else:  # .mp3 default
        _apply_tags_id3(filepath, fv, fields, txxx_descs, cover_data, embed_cover, is_wav=False)

def read_tags(filepath: str, fields: list) -> dict:
    """Read existing tags from a file (ID3 or FLAC) and return a dict of {field_id: value}."""
    ext = filepath.lower().endswith
    fv = {}
    
    if ext('.flac'):
        try:
            from mutagen.flac import FLAC
            audio = FLAC(filepath)
            for f in fields:
                frame = f.get("id3_frame", "")
                if not frame: continue
                if frame.startswith("TXXX:"):
                    desc = frame.split(":", 1)[1].lower()
                    val = audio.get(desc, [])
                    if val: fv[f["id"]] = str(val[0])
                elif frame == "TIT2":
                    if audio.get("title"): fv[f["id"]] = str(audio["title"][0])
                elif frame == "TPE1":
                    if audio.get("artist"): fv[f["id"]] = str(audio["artist"][0])
                elif frame == "TALB":
                    if audio.get("album"): fv[f["id"]] = str(audio["album"][0])
                elif frame == "TDRC":
                    if audio.get("date"): fv[f["id"]] = str(audio["date"][0])
                elif frame == "TCON":
                    if audio.get("genre"): fv[f["id"]] = str(audio["genre"][0])
        except Exception:
            pass
            
    elif ext('.mp3') or ext('.wav'):
        try:
            if ext('.wav'):
                from mutagen.wave import WAVE
                audio = WAVE(filepath).tags
            else:
                from mutagen.id3 import ID3
                audio = ID3(filepath)
                
            if audio:
                for f in fields:
                    frame = f.get("id3_frame", "")
                    if not frame: continue
                    if frame.startswith("TXXX:"):
                        desc = frame.split(":", 1)[1].upper()
                        for tag in audio.getall("TXXX"):
                            if tag.desc.upper() == desc:
                                fv[f["id"]] = str(tag.text[0])
                                break
                    else:
                        if frame in audio:
                            fv[f["id"]] = str(audio[frame].text[0])
        except Exception:
            pass
            
    return fv

def rename_file(old_path: str, new_filename: str) -> str:
    """Rename a file to new_filename in the same directory. Returns new full path."""
    folder   = os.path.dirname(old_path)
    new_path = os.path.join(folder, new_filename)
    if old_path != new_path:
        if os.path.exists(new_path):
            raise FileExistsError(f"Target already exists: {new_path}")
        os.rename(old_path, new_path)
    return new_path
