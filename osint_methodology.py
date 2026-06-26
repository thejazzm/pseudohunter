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

LEAKCHECK_PUBLIC_URL = "https://leakcheck.io/api/public"

def check_leakcheck(email):
    """
    Queries LeakCheck's free public API to check if an email appears in
    known data breaches. No API key required, rate-limited (~5 req/min).

    Returns a dict: {"found": int, "sources": list[dict]} or
    {"found": 0, "sources": []} on no match / error.
    """
    import requests
    try:
        r = requests.get(LEAKCHECK_PUBLIC_URL, params={"check": email}, timeout=10)
        data = r.json()
        if data.get("success") and data.get("found", 0) > 0:
            return {
                "found": data.get("found", 0),
                "sources": data.get("sources", []),
            }
        return {"found": 0, "sources": []}
    except (requests.RequestException, ValueError):
        return {"found": 0, "sources": []}

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
    """Generates a polished, self-contained HTML report, sorted by pseudo
    confidence and platform importance, with search/filter and collapse controls."""
    tree = build_tree_report_data(res, pseudo_scores)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = "output"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"pseudohunter_report_{first}_{last}_{ts}.html")

    total_hits = sum(len(e["hits"]) for e in tree)
    total_pseudos = len(tree)
    high_conf = sum(1 for e in tree if e["score"] >= 70)
    high_importance_hits = sum(1 for e in tree for h in e["hits"] if h["importance"] >= 80)

    def score_class(score):
        if score >= 70: return "high"
        if score >= 45: return "medium"
        return "low"

    def importance_class(imp):
        if imp >= 80: return "high"
        if imp >= 50: return "medium"
        return "low"

    nodes_html = ""
    for entry in tree:
        sc = entry["score"]
        sc_class = score_class(sc)
        hits_html = ""
        for h in entry["hits"]:
            url_match = re.search(r'https?://\S+', h["line"])
            url = url_match.group(0) if url_match else h["line"]
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
            domain = domain_match.group(1) if domain_match else h["tool"]
            imp_class = importance_class(h["importance"])
            hits_html += f"""
            <li class="hit" data-domain="{domain.lower()}">
                <span class="tool-tag">{h['tool']}</span>
                <a href="{url}" target="_blank" rel="noopener">{domain}</a>
                <div class="importance-bar"><div class="importance-fill {imp_class}" style="width:{h['importance']}%"></div></div>
            </li>"""

        nodes_html += f"""
        <details class="pseudo-card" open data-pseudo="{entry['pseudo'].lower()}">
            <summary>
                <span class="chevron">&#9656;</span>
                <span class="pseudo-name">{entry['pseudo']}</span>
                <span class="score-badge {sc_class}">{sc}% confidence</span>
                <span class="hit-count">{len(entry['hits'])} hit(s)</span>
            </summary>
            <ul class="hits-list">{hits_html}</ul>
        </details>"""

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PseudoHunter Report — {first} {last}</title>
<style>
:root {{
    --bg: #0a0612; --card: #14101f; --border: #2a2240;
    --text: #d6d2e6; --muted: #8e86a8; --accent: #a78bfa;
    --accent2: #c4b5fd; --green: #4ade80; --yellow: #d29922; --red: #f87171;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ background: var(--bg); }}
body {{
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    padding: 48px 20px 80px;
    min-height: 100vh;
    position: relative;
    overflow-x: hidden;
}}
.glow-layer {{
    position: fixed;
    top: 0; left: 0; width: 100%; height: 100%;
    pointer-events: none;
    z-index: 0;
    background: radial-gradient(600px circle at var(--mx, 50%) var(--my, 30%),
        rgba(167, 139, 250, 0.10), transparent 70%);
    transition: background 0.05s linear;
}}
.container {{ position: relative; z-index: 1; }}
.container {{ max-width: 880px; margin: 0 auto; }}

header {{ margin-bottom: 36px; }}
header .badge {{
    display: inline-block; font-size: 11px; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--accent);
    background: rgba(88,166,255,0.1); padding: 4px 10px;
    border-radius: 20px; margin-bottom: 12px; font-weight: 600;
}}
h1 {{ font-size: 30px; font-weight: 700; letter-spacing: -0.02em; }}
.subtitle {{ color: var(--muted); margin-top: 6px; font-size: 14px; }}

.summary {{
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px;
    margin: 28px 0 36px;
}}
.summary-card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 18px 16px;
    transition: transform 0.15s, border-color 0.15s;
}}
.summary-card:hover {{ transform: translateY(-2px); border-color: var(--accent); }}
.summary-card .value {{ font-size: 26px; font-weight: 700; color: var(--accent); }}
.summary-card .label {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}

.toolbar {{
    display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;
}}
.search-box {{
    flex: 1; min-width: 200px; background: var(--card); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 14px; color: var(--text); font-size: 14px;
    outline: none; transition: border-color 0.15s;
}}
.search-box:focus {{ border-color: var(--accent); }}
.search-box::placeholder {{ color: var(--muted); }}
.btn {{
    background: var(--card); border: 1px solid var(--border); color: var(--text);
    border-radius: 8px; padding: 10px 16px; font-size: 13px; cursor: pointer;
    transition: border-color 0.15s, background 0.15s; font-weight: 500;
}}
.btn:hover {{ border-color: var(--accent); background: #1c2128; }}

.pseudo-card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; margin-bottom: 12px; overflow: hidden;
    transition: border-color 0.15s;
}}
.pseudo-card[open] {{ border-color: #3d444d; }}
.pseudo-card summary {{
    list-style: none; cursor: pointer; padding: 16px 20px;
    display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}}
.pseudo-card summary::-webkit-details-marker {{ display: none; }}
.chevron {{
    color: var(--muted); font-size: 12px; transition: transform 0.15s; display: inline-block;
}}
.pseudo-card[open] .chevron {{ transform: rotate(90deg); }}
.pseudo-name {{ font-weight: 600; font-size: 15px; font-family: ui-monospace, monospace; }}
.score-badge {{
    font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px;
    margin-left: auto;
}}
.score-badge.high {{ background: rgba(63,185,80,0.15); color: var(--green); }}
.score-badge.medium {{ background: rgba(210,153,34,0.15); color: var(--yellow); }}
.score-badge.low {{ background: rgba(139,148,158,0.15); color: var(--muted); }}
.hit-count {{ color: var(--muted); font-size: 12px; }}

.hits-list {{ list-style: none; padding: 0 20px 16px; }}
.hit {{
    display: flex; align-items: center; gap: 12px; padding: 9px 0;
    border-top: 1px solid var(--border); font-size: 13px;
}}
.hit:first-child {{ border-top: none; }}
.tool-tag {{
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    color: var(--muted); background: #21262d; padding: 2px 7px;
    border-radius: 4px; min-width: 56px; text-align: center; flex-shrink: 0;
}}
.hit a {{ color: var(--accent); text-decoration: none; word-break: break-all; flex: 1; }}
.hit a:hover {{ text-decoration: underline; }}
.importance-bar {{
    background: #21262d; border-radius: 4px; height: 6px; width: 70px;
    overflow: hidden; flex-shrink: 0;
}}
.importance-fill {{ height: 100%; border-radius: 4px; }}
.importance-fill.high {{ background: var(--red); }}
.importance-fill.medium {{ background: var(--yellow); }}
.importance-fill.low {{ background: var(--green); }}

.empty-state {{ text-align: center; color: var(--muted); padding: 60px 20px; display: none; }}

footer {{
    color: var(--muted); font-size: 12px; margin-top: 48px;
    text-align: center; border-top: 1px solid var(--border); padding-top: 24px;
}}

@media (max-width: 640px) {{
    .summary {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>
<body>
<div class="container">
    <header>
        <div class="badge">OSINT Report</div>
        <h1>{first} {last}</h1>
        <div class="subtitle">Generated by PseudoHunter &middot; {datetime.now().strftime('%Y-%m-%d %H:%M')} &middot; Sorted by pseudo confidence &amp; platform importance</div>
    </header>

    <div class="summary">
        <div class="summary-card">
            <div class="value">{total_pseudos}</div>
            <div class="label">Variants with hits</div>
        </div>
        <div class="summary-card">
            <div class="value">{total_hits}</div>
            <div class="label">Total hits found</div>
        </div>
        <div class="summary-card">
            <div class="value">{high_conf}</div>
            <div class="label">High-confidence variants</div>
        </div>
        <div class="summary-card">
            <div class="value">{high_importance_hits}</div>
            <div class="label">High-importance hits</div>
        </div>
    </div>

    <div class="toolbar">
        <input type="text" class="search-box" id="searchBox" placeholder="Filter by pseudo or domain...">
        <button class="btn" id="expandAll">Expand all</button>
        <button class="btn" id="collapseAll">Collapse all</button>
    </div>

    <div id="treeContainer">
        {nodes_html if nodes_html else ''}
    </div>
    <div class="empty-state" id="emptyState">No results match your filter.</div>

    <footer>
        PseudoHunter &middot; Public OSINT data only &middot; {total_hits} hit(s) across {total_pseudos} variant(s)
    </footer>
</div>

<script>
const searchBox = document.getElementById('searchBox');
const cards = Array.from(document.querySelectorAll('.pseudo-card'));
const emptyState = document.getElementById('emptyState');

searchBox.addEventListener('input', () => {{
    const q = searchBox.value.toLowerCase().trim();
    let visibleCount = 0;
    cards.forEach(card => {{
        const pseudo = card.dataset.pseudo;
        const hits = Array.from(card.querySelectorAll('.hit'));
        let cardMatches = pseudo.includes(q);
        let anyHitMatches = false;
        hits.forEach(hit => {{
            const domain = hit.dataset.domain;
            const match = q === '' || domain.includes(q) || pseudo.includes(q);
            hit.style.display = match ? 'flex' : 'none';
            if (match) anyHitMatches = true;
        }});
        const show = q === '' || cardMatches || anyHitMatches;
        card.style.display = show ? '' : 'none';
        if (show) visibleCount++;
    }});
    emptyState.style.display = visibleCount === 0 ? 'block' : 'none';
}});

document.getElementById('expandAll').addEventListener('click', () => {{
    cards.forEach(c => c.open = true);
}});
document.getElementById('collapseAll').addEventListener('click', () => {{
    cards.forEach(c => c.open = false);
}});
</script>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return path