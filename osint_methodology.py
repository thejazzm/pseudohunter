"""
osint_methodology.py
Methodological functions for PseudoHunter:
-search timestamping
-confidence score for generated usernames
-session log
-structured dork export
-hit deduplication across tools
"""
import json
import re
from datetime import datetime

# ─── confidence score for usernames ───────────────────────────────────────────
def score_pseudo(pseudo, first, last):
    """
    Retourne un score 0-100 de vraisemblance d'usage réel,
    basé sur des patterns statistiquement courants.
    """
    p = pseudo.lower()
    f = first.lower()
    l = last.lower()
    score = 30  # base

    if p in (f"{f}.{l}", f"{f}_{l}", f"{f}{l}"):
        score += 50
    elif p in (f"{l}.{f}", f"{l}_{f}", f"{l}{f}"):
        score += 35
    elif p.startswith(f[0]) and l in p:
        score += 25
    elif f in p or l in p:
        score += 15

    if re.search(r'\d{2,4}$', p):  # suffixe numérique (ex: prenom.nom92)
        score += 5
    if len(p) <= 16:
        score += 5
    if p.startswith('_') or p.endswith('x'):
        score -= 10

    return max(0, min(100, score))


def rank_pseudos(pseudos, first, last):
    """Retourne la liste triée par score décroissant, avec le score attaché."""
    scored = [(p, score_pseudo(p, first, last)) for p in pseudos]
    return sorted(scored, key=lambda x: x[1], reverse=True)


# ─── session log ───────────────────────────────────────────────────────
class SessionJournal:
    """
    Timestamped log of a search session, kept separate from the results report.
    Enables tracking of who/what/when was searched, independently of the hits found.
    """
    def __init__(self, first, last):
        self.start_time = datetime.now()
        self.first = first
        self.last = last
        self.entries = []

    def log(self, event_type, detail):
        self.entries.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "type": event_type,   # ex: "search_start", "timeout", "hit", "error"
            "detail": detail,
        })

    def log_pseudo_result(self, tool, pseudo, status, nb_hits=0):
        """status attendu: 'ok', 'timeout', 'tool_not_found', 'error'"""
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


# ─── Structured export of dorks.───────────────────────────────────────────────
def format_dorks_for_txt(dorks):
    """Retourne un bloc texte cohérent avec le reste du rapport TXT."""
    lines = []
    for d in dorks:
        lines.append(f"  -> {d}")
    return "\n".join(lines)


# ─── Deduplication of hits between Sherlock and Maigret. ─────────────────────────
URL_PATTERN = re.compile(r'https?://[^\s)\]]+')

def extract_url(line):
    m = URL_PATTERN.search(line)
    return m.group(0).rstrip('/').lower() if m else None

def dedupe_hits(sherlock_results, maigret_results):
    """
    sherlock_results, maigret_results: dict {pseudo: [lignes]}
    Returns a merged dictionary `{pseudo: {"sherlock": [...], "maigret": [...], "merged_urls": [...]}}`
    with deduplication based on normalized URLs.
    """
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