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
PLATFORM_IMPORTANCE = {
    "linkedin": 100, "github": 95, "twitter": 85, "x.com": 85,
    "instagram": 80, "facebook": 75, "reddit": 70, "tiktok": 65,
    "pinterest": 50, "youtube": 60, "telegram": 55, "discord": 50,
}

def guess_platform_importance(url_or_line):
    """Devine l'importance d'un site à partir de son URL/nom (0-100, 30 par défaut)."""
    text = url_or_line.lower()
    for site, weight in PLATFORM_IMPORTANCE.items():
        if site in text:
            return weight
    return 30
    
    
def build_tree_report_data(res, pseudo_scores):
    """
    Construit une structure hiérarchique triée pour le rapport HTML :
    pseudo (trié par score) -> outil -> hits (triés par importance plateforme)
    """
    tree = []
    all_pseudos = set(res.get("sherlock", {}).keys()) | set(res.get("maigret", {}).keys())

    for pseudo in sorted(all_pseudos, key=lambda p: pseudo_scores.get(p, 0), reverse=True):
        entry = {"pseudo": pseudo, "score": pseudo_scores.get(pseudo, 0), "hits": []}
        for tool_key, tool_label in [("sherlock", "Sherlock"), ("maigret", "Maigret")]:
            for line in res.get(tool_key, {}).get(pseudo, []):
                entry["hits"].append({
                    "tool": tool_label,
                    "line": line,
                    "importance": guess_platform_importance(line),
                })
        entry["hits"].sort(key=lambda h: h["importance"], reverse=True)
        if entry["hits"]:
            tree.append(entry)

    return tree

def export_html_tree(res, pseudo_scores, first, last):
    """Génère un rapport HTML en arborescence, trié par pertinence."""
    tree = build_tree_report_data(res, pseudo_scores)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = "output"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"pseudohunter_report_{first}_{last}_{ts}.html")

    def score_badge(score):
        color = "#3fb950" if score >= 70 else "#d29922" if score >= 45 else "#8b949e"
        return f'<span style="background:{color}22;color:{color};padding:2px 8px;border-radius:10px;font-size:12px;">{score}%</span>'

    def importance_bar(imp):
        color = "#f85149" if imp >= 80 else "#d29922" if imp >= 50 else "#3fb950"
        return f'<div style="background:#21262d;border-radius:4px;height:6px;width:80px;display:inline-block;"><div style="background:{color};height:100%;width:{imp}%;border-radius:4px;"></div></div>'

    nodes_html = ""
    for entry in tree:
        hits_html = ""
        for h in entry["hits"]:
            url_match = re.search(r'https?://\S+', h["line"])
            url = url_match.group(0) if url_match else h["line"]
            hits_html += f"""
            <li style="margin:6px 0;">
                <span style="color:#8b949e;font-size:11px;">[{h['tool']}]</span>
                <a href="{url}" target="_blank" style="color:#58a6ff;">{url}</a>
                {importance_bar(h['importance'])}
            </li>"""

        nodes_html += f"""
        <details style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 16px;margin-bottom:10px;" open>
            <summary style="cursor:pointer;font-weight:600;color:#c9d1d9;">
                {entry['pseudo']} {score_badge(entry['score'])}
                <span style="color:#8b949e;font-size:12px;">({len(entry['hits'])} hit(s))</span>
            </summary>
            <ul style="list-style:none;padding-left:8px;margin-top:10px;">{hits_html}</ul>
        </details>"""

    html_doc = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8">
<title>PseudoHunter Report — {first} {last}</title>
<style>
body {{ background:#0d1117; color:#c9d1d9; font-family:-apple-system,sans-serif; padding:40px 20px; }}
.container {{ max-width:800px; margin:0 auto; }}
h1 {{ font-size:24px; }} .subtitle {{ color:#8b949e; margin-bottom:24px; }}
</style></head><body>
<div class="container">
<h1>PseudoHunter — {first} {last}</h1>
<div class="subtitle">Triés par pertinence du pseudo et importance de la plateforme</div>
{nodes_html}
</div></body></html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return path