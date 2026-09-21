import os
import re


def normalize_feat(text: str, feat_format: str = "ft.") -> str:
    """Replace all variants of 'feat' with the canonical format."""
    pattern = r'(?i)\b(feat(?:uring)?\.?|ft\.?)\s+'
    return re.sub(pattern, feat_format + ' ', text)

def strip_original_mix(title: str) -> str:
    return re.sub(r'\s*\(original mix\)', '', title, flags=re.IGNORECASE).strip()

def extract_feat(artist: str, feat_format: str = "ft."):
    """Split 'Artist ft. Featured' into (artist, featured)."""
    pattern = re.compile(r'\s+' + re.escape(feat_format) + r'\s+', re.IGNORECASE)
    parts = pattern.split(artist, maxsplit=1)
    if len(parts) == 2:
        feat = parts[1].strip()
        feat = feat.split('-')[0].strip()
        return parts[0].strip(), feat
    return artist.strip(), ''

def extract_remixer(title: str):
    """Return (clean_title, remixer_name) from 'Title - (Remixer Remix)' or 'Title (Remixer Remix)'."""
    m = re.search(r'-\s*\((.+?)\s+remix\)', title, re.IGNORECASE)
    if m:
        clean_title = title[:m.start()] + title[m.end():]
        return clean_title.strip(), m.group(1).strip()
        
    m = re.search(r'\((.+?)\s+remix\)', title, re.IGNORECASE)
    if m:
        clean_title = title[:m.start()] + title[m.end():]
        return clean_title.strip(), m.group(1).strip()
        
    return title, ''

def parse_catno_from_folder(folder_name: str):
    """Extract BH001, BHB001, ARR002 style CatNos from a folder name."""
    m = re.search(r'([A-Z]{2,6}B?\d{2,4})', folder_name, re.IGNORECASE)
    return m.group(1).upper() if m else ''

def scan_m3u_files(root_dir: str):
    """Walk a directory, parse all .m3u files and return {mp3_filename: catno}."""
    import os
    mapping = {}
    for dirpath, dirnames, files in os.walk(root_dir):
        folder = os.path.basename(dirpath)
        catno = parse_catno_from_folder(folder)
        if not catno:
            continue
        for f in files:
            if f.lower().endswith('.m3u'):
                try:
                    with open(os.path.join(dirpath, f), 'r', encoding='utf-8', errors='ignore') as fh:
                        for line in fh:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                mapping[line.lower()] = catno
                except Exception:
                    pass
    return mapping

def scan_nfo_files(root_dir: str):
    """Walk a directory, parse all .nfo files and return {dirpath: metadata_dict}."""
    import os, re
    nfos = {}
    for dirpath, dirnames, files in os.walk(root_dir):
        for f in files:
            if f.lower().endswith('.nfo'):
                try:
                    meta = {}
                    with open(os.path.join(dirpath, f), 'r', encoding='utf-8', errors='ignore') as fh:
                        content = fh.read()
                        m_cat = re.search(r'Catalog\.Number\.*:\s*([A-Z0-9_-]+)', content, re.IGNORECASE)
                        if m_cat: meta['catno'] = m_cat.group(1).upper()
                        m_date = re.search(r'(?:Storedate|ReleaseDate|Release Date|Streetdate)\.*:\s*([A-Za-z0-9-]+)', content, re.IGNORECASE)
                        if m_date: meta['date'] = m_date.group(1)
                        m_label = re.search(r'(?:Company|Label)\.*:\s*(.+?)\r?\n', content, re.IGNORECASE)
                        if m_label: meta['label'] = m_label.group(1).strip()
                        m_artist = re.search(r'\n\s*Artist\.*:\s*(.+?)\r?\n', content, re.IGNORECASE)
                        if m_artist: meta['artist'] = m_artist.group(1).strip()
                    if meta:
                        nfos[dirpath] = meta
                except Exception:
                    pass
    return nfos

def build_proposed_filename(template: str, catno: str, artist: str, feat: str, title: str,
                            feat_format: str = "ft.", original_ext: str = "") -> str:
    """Build a proposed filename from the template.

    ``original_ext`` (e.g. ".flac", ".wav", ".mp3") is always used as the
    final extension regardless of whatever extension the template contains.
    This prevents FLAC/WAV files from being renamed to .mp3.
    """
    full_artist = f"{artist} {feat_format} {feat}" if feat else artist
    name = template
    name = name.replace('{catno}', catno)
    name = name.replace('{artist}', full_artist)
    name = name.replace('{title}', title)
    # Sanitize special characters
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Always enforce the actual file extension — the template may say .mp3
    # but FLAC/WAV files must keep their correct extension.
    if original_ext:
        base, _ = os.path.splitext(name)
        name = base + original_ext
    return name

def title_case_smart(text: str) -> str:
    """Title case but keep vs, ft. lowercase and preserve ALL-CAPS acronyms (UK, UFO, EP...)."""
    words = text.split()
    small_words = ('vs', 'ft.', '&', 'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on')
    result = []
    for i, w in enumerate(words):
        lw = w.lower()
        if w.isupper() and len(w) > 1:
            # All-caps word — preserve as acronym
            result.append(w)
        elif i > 0 and lw in small_words:
            result.append(lw)
        else:
            result.append(w.capitalize())
    return ' '.join(result)
