---
name: mutagen-id3-metadata
description: >-
  Mastery of the Mutagen Python library and the official ID3v2.3 / ID3v2.4 standards.
  Use when reading, writing, or clearing audio metadata, embedding cover art, or
  handling custom TXXX frames for perfect compatibility with DJ software and players.
---

# Mutagen & ID3 Metadata Expert

This skill ensures audio tags are written perfectly so they can be read by Rekordbox, Serato, Traktor, Windows Explorer, and standard media players.

## Core Directives

1. **ID3v2.3 Compliance**: Always save MP3 files with `v2_version=3` (`audio.save(path, v2_version=3)`). Windows Explorer and many hardware CDJs struggle with ID3v2.4.
2. **Text Encoding**: Always use `encoding=3` (UTF-8) for all text frames to prevent character mojibake for international track titles.
3. **Custom TXXX Frames**: For non-standard fields like `CATALOGNUMBER`, `REMIXER`, or `STYLE`, use `TXXX(encoding=3, desc='YOUR_FIELD', text=['value'])`. 
4. **Flawless Cover Art**: Always embed cover art as `APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=bytes)`. Never leave `mime` empty.
5. **Clean Slate**: When tagging from scratch, delete conflicting frames using `audio.delall('TIT2')` or `audio.tags.delall('TXXX')` before inserting the new ones to prevent duplicate multi-value fields.
