"""
osint_methodology.py
Fonctions méthodologiques pour PseudoHunter :
- horodatage par recherche
- score de confiance des pseudos générés
- journal de session
- export des dorks structuré
- déduplication des hits entre outils
- profils de cible sauvegardés
- état de reprise pour scans interrompus
"""
import json
import re
import os
from datetime import datetime

def score_pseudo(pseudo, first, last):
    p = pseudo.lower()
    f = first.lower()
    l = last.lower()
    score = 30

    if p in (f"{f}.{l}", f"{f}_{l}", f"{f}{l}"):
        score += 50
    elif p in (f"{l}.{f}", f"{l}_{f}", f"{l}{f}"):
        score += 35
    elif p.startswith(f[0]) and l in p:
        score += 25
    elif f in p or l in p:
        score += 15

    if re.search(r'\d{2,4}$', p):
        score += 5
    if len(p) <= 16:
        score += 5
    if p.startswith('_') or p.endswith('x'):
        score -= 10

    return max(0, min(100, score))


def rank_pseudos(pseudos, first, last):
    scored = [(p, score_pseudo(p, first, last)) for p in pseudos]
    return sorted(scored, key=lambda x: x[1], reverse=True)


class SessionJournal:
    def __init__(self, first, last):
        self.start_time = datetime.now()
        self.first = first
        self.last = last
        self.entries = []

    def log(self, event_type, detail):
        self.entries.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "type": event_type,
            "detail": detail,
        })

    def log_pseudo_result(self, tool, pseudo, status, nb_hits=0):
        self.log("pseudo_result", {
            "tool": tool, "pseudo": pseudo, "status": status, "hits": nb_hits
        })

    def save(self, filepath):
        data = {
            "session_start": self.start_time.isoformat(timespec="seconds"),
            "session_end": datetime.now().isoformat(timespec="seconds"),
            "target": {"first": self.first, "last": self.last},
            "entries": self.entries,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        return filepath


def format_dorks_for_txt(dorks):
    lines = []
    for d in dorks:
        lines.append(f"  -> {d}")
    return "\n".join(lines)


URL_PATTERN = re.compile(r'https?://[^\s)\]]+')

def extract_url(line):
    m = URL_PATTERN.search(line)
    return m.group(0).rstrip('/').lower() if m else None

def dedupe_hits(sherlock_results, maigret_results):
    merged = {}
    all_pseudos = set(sherlock_results.keys()) | set(maigret_results.keys())

    for p in all_pseudos:
        s_lines = sherlock_results.get(p, [])
        m_lines = maigret_results.get(p, [])

        seen_urls = set()
        merged_urls = []
        for line in s_lines + m_lines:
            url = extract_url(line)
            key = url if url else line.strip().lower()
            if key not in seen_urls:
                seen_urls.add(key)
                merged_urls.append(line)

        merged[p] = {
            "sherlock": s_lines,
            "maigret": m_lines,
            "merged_unique": merged_urls,
        }
    return merged

PROFILES_DIR = "profiles"

def _profile_path(first, last):
    os.makedirs(PROFILES_DIR, exist_ok=True)
    safe_name = re.sub(r'[^a-z0-9]', '_', f"{first}_{last}".lower())
    return os.path.join(PROFILES_DIR, f"{safe_name}.json")

def save_profile(first, last, email, phone):
    path = _profile_path(first, last)
    data = {
        "first": first,
        "last": last,
        "email": email or "",
        "phone": phone or "",
        "last_used": datetime.now().isoformat(timespec="seconds"),
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path

def list_profiles():
    if not os.path.isdir(PROFILES_DIR):
        return []
    profiles = []
    for fname in sorted(os.listdir(PROFILES_DIR)):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(PROFILES_DIR, fname)) as f:
                    profiles.append(json.load(f))
            except (json.JSONDecodeError, OSError):
                continue
    profiles.sort(key=lambda p: p.get("last_used", ""), reverse=True)
    return profiles


# ─── État de reprise pour scans interrompus ───────────────────────────────────
RESUME_DIR = "resume"

class ResumeState:
    """
    Garde une trace, pendant le scan, des pseudos déjà traités par outil.
    Persisté sur disque à chaque résultat, pour permettre une reprise
    après une interruption (Ctrl+C) sans tout relancer depuis zéro.
    """
    def __init__(self, first, last):
        os.makedirs(RESUME_DIR, exist_ok=True)
        safe_name = re.sub(r'[^a-z0-9]', '_', f"{first}_{last}".lower())
        self.path = os.path.join(RESUME_DIR, f"{safe_name}_resume.json")
        self.data = {
            "sherlock": {}, "maigret": {},
            "done_sherlock": [], "done_maigret": [],
        }
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except (json.JSONDecodeError, OSError):
                pass

    def has_pending(self):
        return os.path.exists(self.path) and (
            self.data.get("done_sherlock") or self.data.get("done_maigret")
        )

    def mark_done(self, tool, pseudo, hits):
        done_key = f"done_{tool}"
        if pseudo not in self.data[done_key]:
            self.data[done_key].append(pseudo)
        if hits:
            self.data[tool][pseudo] = hits
        self._save()

    def remaining(self, tool, pseudos):
        done = set(self.data.get(f"done_{tool}", []))
        return [p for p in pseudos if p not in done]

    def get_results(self, tool):
        return self.data.get(tool, {})

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def clear(self):
        if os.path.exists(self.path):
            os.remove(self.path)
        self.data = {
            "sherlock": {}, "maigret": {},
            "done_sherlock": [], "done_maigret": [],
        }