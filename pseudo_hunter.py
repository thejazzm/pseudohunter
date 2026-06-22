#!/usr/bin/env python3
import sys, subprocess, re, time, threading, json, os, shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from osint_methodology import (
    rank_pseudos, SessionJournal, format_dorks_for_txt, dedupe_hits,
    save_profile, list_profiles, ResumeState
)

_active_processes = []
_active_processes_lock = threading.Lock()

def _register_process(proc):
    with _active_processes_lock:
        _active_processes.append(proc)

def _unregister_process(proc):
    with _active_processes_lock:
        if proc in _active_processes:
            _active_processes.remove(proc)

def kill_all_active_processes():
    with _active_processes_lock:
        for proc in _active_processes:
            try:
                proc.kill()
            except Exception:
                pass
        _active_processes.clear()

# ─── Colors ──────────────────────────────────────────────────────────────────
R="\033[0m";BD="\033[1m";DM="\033[2m";IT="\033[3m"
PU="\033[35m";TE="\033[36m";GR="\033[32m";YE="\033[33m"
GY="\033[90m";RD="\033[31m";CY="\033[96m";BL="\033[34m";MG="\033[95m"

BANNER=f"""{PU}{BD}
██████╗ ███████╗███████╗██╗   ██╗██████╗  ██████╗
██╔══██╗██╔════╝██╔════╝██║   ██║██╔══██╗██╔═══██╗
██████╔╝███████╗█████╗  ██║   ██║██║  ██║██║   ██║
██╔═══╝ ╚════██║██╔══╝  ██║   ██║██║  ██║██║   ██║
██║     ███████║███████╗╚██████╔╝██████╔╝╚██████╔╝
╚═╝     ╚══════╝╚══════╝ ╚═════╝ ╚═════╝  ╚═════╝{R}
{TE}        ██╗  ██╗██╗   ██╗███╗   ██╗████████╗███████╗██████╗ {R}
{TE}        ██║  ██║██║   ██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗{R}
{TE}        ███████║██║   ██║██╔██╗ ██║   ██║   █████╗  ██████╔╝{R}
{TE}        ██╔══██║██║   ██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗{R}
{TE}        ██║  ██║╚██████╔╝██║ ╚████║   ██║   ███████╗██║  ██║{R}
{TE}        ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝{R}
{GY}                       OSINT username hunter — by thejazzman{R}
"""

SEP = f"  {GY}{'─'*62}{R}"

def sv(t): return re.sub(r'[aeiouAEIOU]','',t)

def ask(q, opts):
    print(f"\n  {BD}{YE}{q}{R}")
    for k,v in opts.items(): print(f"  {TE}[{k}]{R} {v}")
    print(f"  {GY}> {R}",end="")
    while True:
        r=input().strip().lower()
        if r in opts: return r
        print(f"  {RD}Invalid choice:{R} ",end="")

def inp(label, optional=False):
    tag = f"{GY}(optional, Enter to skip){R}" if optional else ""
    print(f"  {BD}{TE}{label}{R} {tag}: ",end="")
    return input().strip()

def section(title, color=GR):
    print(f"\n{SEP}")
    print(f"  {BD}{color}{title}{R}\n")

def gen_pseudos(first, last):
    p=first.lower();n=last.lower();pv=sv(p);nv=sv(n)
    p2=p[:2];n2=n[:2];p3=p[:3];n3=n[:3]
    ps=set()
    ps.update([
        f"{p}.{n}",f"{n}.{p}",f"{p}{n}",f"{n}{p}",
        f"{p}_{n}",f"{n}_{p}",f"{p}-{n}",f"{n}-{p}",
        f"{p[0]}.{n}",f"{p[0]}{n}",f"{p[0]}_{n}",f"{p[0]}-{n}",
        f"{p}.{n[0]}",f"{p}{n[0]}",f"{p}_{n[0]}",
        f"{p[0]}{n[0]}",f"{p[0]}.{n[0]}",f"{p[0]}_{n[0]}",
        f"{nv}.{p}",f"{p}.{nv}",f"{nv}{p}",f"{p}{nv}",
        f"{nv}_{p}",f"{p}_{nv}",f"{nv}-{p}",f"{p}-{nv}",
        f"{pv}.{n}",f"{n}.{pv}",f"{pv}{n}",f"{pv}_{n}",
        f"{pv}.{nv}",f"{nv}.{pv}",f"{nv}{pv}",f"{pv}{nv}",
        f"{p3}.{n}",f"{p3}{n}",f"{p3}_{n}",
        f"{n3}.{p}",f"{n3}{p}",
        f"{p3}.{n3}",f"{p3}{n3}",
        f"{p[0]}{nv}",f"{nv}{p[0]}",
        f"{n[0]}{pv}",f"{pv}{n[0]}",
        f"{p2}.{n}",f"{p2}{n}",
        f"{n2}.{p}",f"{n2}{p}",
        f"{p.capitalize()}{n}",f"{p}{n.capitalize()}",
        f"{p}.{n3}",f"{p3}.{n3}",
        f"{nv}.{p3}",f"{p3}.{nv}",
        f"{p3}-{n}",f"{n}-{p3}",
        f"{p2}-{n}",f"{n2}-{p}",
        f"{p}{n[:3]}",f"{n}{p[:3]}",
        f"{pv}{nv}x",f"_{p}.{n}",
        f"{p}{n[0]}{n[-1]}",f"{p[0]}{p[-1]}{n}",
    ])
    return sorted({x for x in ps if len(re.sub(r'[.\-_]','',x))>=5})

def gen_dorks(first, last, email=None, phone=None):
    name=f'"{first} {last}"'
    dorks=[
        f'{name} site:linkedin.com',
        f'{name} site:twitter.com OR site:x.com',
        f'{name} site:facebook.com',
        f'{name} site:instagram.com',
        f'{name} filetype:pdf',
        f'{name} email',
        f'{name} phone OR tel OR contact',
        f'"{first}.{last}" OR "{last}.{first}"',
        f'"{first[0]}{last}" site:github.com',
        f'{name} -site:linkedin.com -site:facebook.com',
    ]
    if email: dorks.append(f'"{email}"')
    if phone: dorks.append(f'"{phone}"')
    return dorks

# ─── Estimation & profils de concurrence ──────────────────────────────────────
SHERLOCK_TIME_PER_PSEUDO = 25
MAIGRET_TIME_PER_PSEUDO  = 140

def get_concurrency_profile(nb):
    if nb <= 5:
        return {"workers": 3, "sherlock_timeout": 300, "maigret_timeout": 420}
    elif nb <= 15:
        return {"workers": 3, "sherlock_timeout": 300, "maigret_timeout": 420}
    elif nb <= 20:
        return {"workers": 2, "sherlock_timeout": 300, "maigret_timeout": 480}
    else:
        return {"workers": 2, "sherlock_timeout": 360, "maigret_timeout": 540}

def estimate_seconds(nb, use_s, use_m, workers):
    if nb <= 0:
        return 0
    batches = -(-nb // workers)
    total = 0
    if use_s: total = max(total, batches * SHERLOCK_TIME_PER_PSEUDO)
    if use_m: total = max(total, batches * MAIGRET_TIME_PER_PSEUDO)
    return total

def fmt_duration(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h: return f"{h}h{m:02d}min"
    if m: return f"{m}min{s:02d}s"
    return f"{s}s"

class Tracker:
    def __init__(self, tasks):
        self.lock=threading.Lock()
        self.tasks={t:{"done":0,"total":n,"hits":0} for t,n in tasks.items()}
        self.active="";self._stop=False
        self._t=threading.Thread(target=self._loop,daemon=True)
    def start(self): self._t.start()
    def stop(self): self._stop=True;self._t.join();print()
    def update(self,tool,pseudo,hit):
        with self.lock:
            if tool in self.tasks:
                self.tasks[tool]["done"]+=1
                if hit: self.tasks[tool]["hits"]+=1
            self.active=pseudo
    def _bar(self,d,t,c):
        if t==0: return f"{GY}[off]{R}"
        pct=d/t;f=int(pct*18);b="█"*f+"░"*(18-f)
        return f"{c}[{b}]{R}{BD}{int(pct*100):3d}%{R}{DM}({d}/{t}){R}"
    def _loop(self):
        sp=["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"];i=0
        while not self._stop:
            with self.lock:
                parts=[]
                total_hits=0
                for name,data in self.tasks.items():
                    parts.append(f"{name} {self._bar(data['done'],data['total'],TE if name=='Sherlock' else PU if name=='Maigret' else BL)}")
                    total_hits+=data["hits"]
                ac=self.active
            s=sp[i%len(sp)];i+=1
            line="  ".join(parts)
            print(f"\r  {TE}{s}{R} {line}  {GR}hits:{total_hits}{R}  {GY}{ac[:22]:<22}{R}",end="",flush=True)
            time.sleep(0.08)

def run_sherlock(p,t,timeout=300,journal=None):
    proc = None
    try:
        proc = subprocess.Popen(["sherlock",p,"--timeout","8","--print-found"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        _register_process(proc)
        stdout, stderr = proc.communicate(timeout=timeout)
        l=[x.strip() for x in stdout.splitlines() if "[+]" in x or "http" in x]
        status = "ok" if proc.returncode == 0 or l else "error"
        if journal: journal.log_pseudo_result("sherlock", p, status, len(l))
        t.update("Sherlock",p,bool(l));return p,l
    except FileNotFoundError:
        if journal: journal.log_pseudo_result("sherlock", p, "tool_not_found")
        t.update("Sherlock",p,False);return p,[]
    except subprocess.TimeoutExpired:
        if proc: proc.kill()
        if journal: journal.log_pseudo_result("sherlock", p, "timeout")
        t.update("Sherlock",p,False);return p,[]
    finally:
        if proc: _unregister_process(proc)

def run_maigret(p,t,timeout=420,journal=None):
    proc = None
    try:
        proc = subprocess.Popen(["maigret",p,"--no-color"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        _register_process(proc)
        stdout, stderr = proc.communicate(timeout=timeout)
        l=[x.strip() for x in stdout.splitlines() if "[+]" in x or "http" in x or "Found" in x]
        status = "ok" if proc.returncode == 0 or l else "error"
        if journal: journal.log_pseudo_result("maigret", p, status, len(l))
        t.update("Maigret",p,bool(l));return p,l
    except FileNotFoundError:
        if journal: journal.log_pseudo_result("maigret", p, "tool_not_found")
        t.update("Maigret",p,False);return p,[]
    except subprocess.TimeoutExpired:
        if proc: proc.kill()
        if journal: journal.log_pseudo_result("maigret", p, "timeout")
        t.update("Maigret",p,False);return p,[]
    finally:
        if proc: _unregister_process(proc)

def run_holehe(email,t):
    try:
        r=subprocess.run(["holehe",email,"--only-used"],capture_output=True,text=True,timeout=120)
        l=[x.strip() for x in r.stdout.splitlines() if "[+]" in x or "http" in x]
        t.update("Holehe",email,bool(l));return email,l
    except FileNotFoundError: t.update("Holehe",email,False);return email,[]
    except subprocess.TimeoutExpired: t.update("Holehe",email,False);return email,[]

def run_phoneinfoga(phone,t):
    try:
        r=subprocess.run(["phoneinfoga","scan","-n",phone],capture_output=True,text=True,timeout=120)
        l=[x.strip() for x in r.stdout.splitlines() if x.strip() and "Error" not in x and "---" not in x]
        t.update("Phone",phone,bool(l));return phone,l
    except FileNotFoundError: t.update("Phone",phone,False);return phone,[]
    except subprocess.TimeoutExpired: t.update("Phone",phone,False);return phone,[]

# ─── Export ──────────────────────────────────────────────────────────────────
def export_results(data, first, last):
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    name=f"pseudohunter_{first}_{last}_{ts}"
    with open(f"{name}.json","w") as f: json.dump(data,f,indent=2)
    with open(f"{name}.txt","w") as f:
        f.write(f"PseudoHunter — {first} {last} — {datetime.now()}\n")
        f.write("="*60+"\n\n")
        for section,results in data.items():
            f.write(f"\n[ {section} ]\n")
            if isinstance(results,list):
                for r in results: f.write(f"  {r}\n")
            elif isinstance(results,dict):
                for k,v in results.items():
                    f.write(f"  {k}:\n")
                    for x in v: f.write(f"    + {x}\n")
    return name

def check_dependencies(need_sherlock=False, need_maigret=False, need_holehe=False, need_phoneinfoga=False):
    checks = {
        "sherlock": need_sherlock,
        "maigret": need_maigret,
        "holehe": need_holehe,
        "phoneinfoga": need_phoneinfoga,
    }
    missing = [tool for tool, needed in checks.items() if needed and shutil.which(tool) is None]
    return (len(missing) == 0, missing)

def score_color(score):
    if score >= 70: return GR
    if score >= 45: return YE
    return GY

def main():
    print(BANNER)

    # ── Load existing profile or enter new target
    existing_profiles = list_profiles()
    first = last = None
    email = phone = ""

    if existing_profiles:
        print(f"\n  {BD}{YE}Saved profiles found:{R}")
        for idx, prof in enumerate(existing_profiles, 1):
            print(f"  {TE}[{idx}]{R} {prof['first']} {prof['last']}  {GY}(last used: {prof.get('last_used','?')}){R}")
        print(f"  {TE}[n]{R} New target")
        print(f"  {GY}> {R}", end="")
        choice = input().strip().lower()
        if choice.isdigit() and 1 <= int(choice) <= len(existing_profiles):
            prof = existing_profiles[int(choice)-1]
            first, last = prof["first"], prof["last"]
            email, phone = prof.get("email","") or "", prof.get("phone","") or ""
            print(f"\n  {GR}Loaded profile: {first} {last}{R}")

    if not first or not last:
        first = inp("First name")
        last  = inp("Last name")
        if not first or not last:
            print(f"\n  {YE}First and last name required.{R}\n"); sys.exit(1)
        email = inp("Email address", optional=True)
        phone = inp("Phone number (e.g. +33612345678)", optional=True)

    # ── Pseudo generation + confidence ranking
    all_pseudos = gen_pseudos(first, last)
    ranked = rank_pseudos(all_pseudos, first, last)
    all_pseudos = [p for p, score in ranked]
    pseudo_scores = {p: score for p, score in ranked}

    print(f"\n  {GY}{len(all_pseudos)} variants available (>=5 chars){R}\n")

    items_all = list(enumerate(all_pseudos, 1))
    for i in range(0, len(items_all), 3):
        row = items_all[i:i+3]
        line = ""
        for idx, p in row:
            sc = pseudo_scores.get(p, 0)
            c = score_color(sc)
            line += f"  {GY}{idx:02d}.{R} {p:<22}{c}{sc:3d}%{R}  "
        print(line)

    print(f"\n  {BD}{YE}Selection mode:{R}")
    print(f"  {TE}[a]{R} Auto — take the first N (fastest)")
    print(f"  {TE}[m]{R} Manual — pick specific numbers from the list above")
    print(f"  {GY}> {R}", end="")
    sel_mode = input().strip().lower()

    pseudos = []
    if sel_mode == "m":
        print(f"  {BD}{TE}Enter numbers separated by commas{R} {DM}(e.g. 2,7,15){R}: ", end="")
        raw = input().strip()
        try:
            chosen_idx = sorted({int(x.strip()) for x in raw.split(",") if x.strip().isdigit()})
            pseudos = [all_pseudos[i-1] for i in chosen_idx if 1 <= i <= len(all_pseudos)]
        except (ValueError, IndexError):
            pseudos = []
        if not pseudos:
            print(f"\n  {RD}Invalid selection. Falling back to auto mode.{R}")
            sel_mode = "a"

    if sel_mode != "m":
        print(f"  {BD}{YE}How many variants to search?{R} {DM}(Enter = all){R}: ", end="")
        nb_in = input().strip()
        nb = len(all_pseudos) if not nb_in.isdigit() else max(1, min(int(nb_in), len(all_pseudos)))
        pseudos = all_pseudos[:nb]

    print(f"\n  {GR}{len(pseudos)} pseudo(s) selected.{R}")

    # ── Estimation before mode choice
    profile = get_concurrency_profile(len(pseudos))
    est_sherlock = estimate_seconds(len(pseudos), True, False, profile["workers"])
    est_maigret  = estimate_seconds(len(pseudos), False, True, profile["workers"])
    est_both     = estimate_seconds(len(pseudos), True, True, profile["workers"])

    print(f"\n  {BD}{YE}Estimated time for {len(pseudos)} pseudo(s){R} "
          f"{DM}({profile['workers']} workers parallel){R}:")
    print(f"    {TE}Sherlock only{R}        : ~{fmt_duration(est_sherlock)}")
    print(f"    {PU}Maigret only{R}         : ~{fmt_duration(est_maigret)}")
    print(f"    {BD}Sherlock + Maigret{R}   : ~{fmt_duration(est_both)}")

    # ── Tool selection
    mode = ask("Select search mode:", {
        "1": "Sherlock only",
        "2": "Maigret only",
        "3": "Sherlock + Maigret",
        "4": "Full scan (Sherlock + Maigret + Holehe + PhoneInfoga)",
        "5": "Generate variants only (no search)",
    })

    use_s = mode in ("1","3","4")
    use_m = mode in ("2","3","4")
    use_h = mode == "4" and bool(email)
    use_p = mode == "4" and bool(phone)

    # ── Vérification des dépendances avant tout lancement
    deps_ok, missing = check_dependencies(use_s, use_m, use_h, use_p)
    if not deps_ok:
        print(f"\n  {RD}{BD}Missing required tool(s):{R} {', '.join(missing)}")
        print(f"  {YE}Install them before running this mode, or choose a different mode.{R}\n")
        sys.exit(1)

    # ── Resume check
    resume = ResumeState(first, last)
    if resume.has_pending():
        print(f"\n  {YE}A previous interrupted scan was found for {first} {last}.{R}")
        rchoice = ask("Resume previous scan?", {"y":"Yes, continue where it left off","n":"No, start fresh (discard previous progress)"})
        if rchoice != "y":
            resume.clear()

    todo_s = resume.remaining("sherlock", pseudos) if use_s else []
    todo_m = resume.remaining("maigret", pseudos) if use_m else []

    skipped_s = len(pseudos) - len(todo_s) if use_s else 0
    skipped_m = len(pseudos) - len(todo_m) if use_m else 0
    if skipped_s or skipped_m:
        print(f"\n  {GR}Resuming:{R} skipping {skipped_s} already-done Sherlock and {skipped_m} already-done Maigret lookups.")

    remaining_count = max(
        len(todo_s) if use_s else 0,
        len(todo_m) if use_m else 0,
        len(pseudos) if not (use_s or use_m) else 0
    )
    est_seconds = estimate_seconds(remaining_count, use_s, use_m, profile["workers"])
    if est_seconds > 600:
        conf = ask("This scan will take a while. Continue?", {"y":"Yes, launch it","n":"No, go back and reduce pseudo count"})
        if conf == "n":
            print(f"\n  {YE}Cancelled. Re-run the script with fewer variants.{R}\n")
            sys.exit(0)

    # ── Display variants summary
    print(f"\n  {BD}{PU}Target{R}   : {BD}{first} {last}{R}")
    if email: print(f"  {BD}{PU}Email{R}    : {email}")
    if phone: print(f"  {BD}{PU}Phone{R}    : {phone}")
    print(f"  {BD}{TE}Variants{R} : {len(pseudos)} selected\n")
    print(SEP)
    items=list(enumerate(pseudos,1))
    for i in range(0,len(items),3):
        row=items[i:i+3];line=""
        for idx,p in row: line+=f"  {GY}{idx:02d}.{R} {p:<24}"
        print(line)
    print(SEP)

    if mode == "5":
        print(f"\n  {GR}Variants generated. No search launched.{R}\n"); sys.exit(0)

    # ── Google Dorks
    section("Google Dorks — copy & search manually", YE)
    for d in gen_dorks(first, last, email, phone):
        print(f"  {YE}→{R} {d}")

    # ── Launch search
    print(f"\n  {BD}{YE}Launching search...{R}\n")
    tasks={}
    if use_s: tasks["Sherlock"]=len(todo_s)
    if use_m: tasks["Maigret"]=len(todo_m)
    if use_h: tasks["Holehe"]=1
    if use_p: tasks["Phone"]=1

    tracker=Tracker(tasks); tracker.start()

    journal = SessionJournal(first, last)
    journal.log("search_start", {"mode": mode, "nb_pseudos": len(pseudos)})

    futures_map = {}
    fh=None;fp=None
    ex_sherlock = ThreadPoolExecutor(max_workers=profile["workers"]) if use_s and todo_s else None
    ex_maigret  = ThreadPoolExecutor(max_workers=max(1, profile["workers"]-1)) if use_m and todo_m else None
    ex_misc     = ThreadPoolExecutor(max_workers=2) if (use_h or use_p) else None

    try:
        if ex_sherlock:
            for p in todo_s:
                fut = ex_sherlock.submit(run_sherlock,p,tracker,profile["sherlock_timeout"],journal)
                futures_map[fut] = ("sherlock", p)
        if ex_maigret:
            for p in todo_m:
                fut = ex_maigret.submit(run_maigret,p,tracker,profile["maigret_timeout"],journal)
                futures_map[fut] = ("maigret", p)
        if use_h: fh=ex_misc.submit(run_holehe,email,tracker)
        if use_p: fp=ex_misc.submit(run_phoneinfoga,phone,tracker)

        for fut in as_completed(futures_map):
            tool, p = futures_map[fut]
            _, hits = fut.result()
            resume.mark_done(tool, p, hits)
        if fh: fh.result()
        if fp: fp.result()
    except KeyboardInterrupt:
        tracker.stop()
        print(f"\n  {YE}Stopping running scans (progress saved — you can resume later)...{R}")
        raise
    finally:
        if ex_sherlock: ex_sherlock.shutdown(wait=True)
        if ex_maigret:  ex_maigret.shutdown(wait=True)
        if ex_misc:     ex_misc.shutdown(wait=True)

    tracker.stop()

    # ── Collect results
    res={"target":{"first":first,"last":last,"email":email,"phone":phone},
         "dorks":gen_dorks(first,last,email,phone),
         "sherlock": resume.get_results("sherlock") if use_s else {},
         "maigret": resume.get_results("maigret") if use_m else {},
         "holehe":[], "phoneinfoga":[]}

    if use_h and fh:
        _,l=fh.result()
        res["holehe"]=l

    if use_p and fp:
        _,l=fp.result()
        res["phoneinfoga"]=l

    # ── Scan fully completed -> clear resume state
    resume.clear()

    # ── Cross-tool deduplication
    merged = dedupe_hits(res.get("sherlock", {}), res.get("maigret", {}))
    res["merged"] = merged

    # ── Display results
    if use_s:
        section("Sherlock Results", GR)
        if res["sherlock"]:
            for p,ls in res["sherlock"].items():
                sc = pseudo_scores.get(p, 0); c = score_color(sc)
                print(f"  {BD}{TE}{p}{R}  {c}({sc}% confidence){R}")
                for l in ls: print(f"    {GR}[+]{R} {l.split(': ')[-1] if ': ' in l else l}")
                print()
        else: print(f"  {GY}No results from Sherlock.{R}\n")

    if use_m:
        section("Maigret Results", PU)
        if res["maigret"]:
            for p,ls in res["maigret"].items():
                sc = pseudo_scores.get(p, 0); c = score_color(sc)
                print(f"  {BD}{PU}{p}{R}  {c}({sc}% confidence){R}")
                for l in ls: print(f"    {CY}[+]{R} {l}")
                print()
        else: print(f"  {GY}No results from Maigret.{R}\n")

    if use_s and use_m and res.get("merged"):
        any_merged = any(data["merged_unique"] for data in res["merged"].values())
        if any_merged:
            section("Cross-tool Deduplicated Hits", YE)
            for p, data in res["merged"].items():
                if data["merged_unique"]:
                    sc = pseudo_scores.get(p, 0); c = score_color(sc)
                    print(f"  {BD}{YE}{p}{R}  {c}({sc}% confidence){R}")
                    for l in data["merged_unique"]: print(f"    {GR}[+]{R} {l}")
                    print()

    if use_h:
        section("Holehe Results — Email accounts", BL)
        if res["holehe"]:
            for l in res["holehe"]: print(f"  {BL}[+]{R} {l}")
        else: print(f"  {GY}No accounts found for this email.{R}\n")

    if use_p:
        section("PhoneInfoga Results", MG)
        if res["phoneinfoga"]:
            for l in res["phoneinfoga"]: print(f"  {MG}[+]{R} {l}")
        else: print(f"  {GY}No results for this number.{R}\n")

    # ── Export
    print(SEP)
    exp = ask("Export results?", {"y":"Yes — save JSON + TXT report","n":"No"})
    if exp == "y":
        fname = export_results(res, first, last)
        print(f"\n  {GR}Saved:{R} {fname}.json / {fname}.txt\n")

    journal_path = journal.save(f"pseudohunter_journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    print(f"  {GR}Journal saved:{R} {journal_path}\n")

    # ── Save profile
    print(SEP)
    save_choice = ask("Save this target as a profile for later?", {"y":"Yes","n":"No"})
    if save_choice == "y":
        ppath = save_profile(first, last, email, phone)
        print(f"\n  {GR}Profile saved:{R} {ppath}\n")

    # ── Summary
    total = len(res["sherlock"])+len(res["maigret"])+(1 if res["holehe"] else 0)+(1 if res["phoneinfoga"] else 0)
    print(SEP)
    print(f"  {BD}Done.{R} {GR}{total} source(s) with results.{R}\n")

def safe_main():
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {YE}Interrupted by user (Ctrl+C). Killing active scans...{R}")
        kill_all_active_processes()
        sys.exit(130)

if __name__=="__main__": safe_main()
