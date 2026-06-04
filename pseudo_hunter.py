import sys,subprocess,re,time,threading
from concurrent.futures import ThreadPoolExecutor,as_completed
RESET="\033[0m";BOLD="\033[1m";PURPLE="\033[35m";TEAL="\033[36m";GREEN="\033[32m";YELLOW="\033[33m";GRAY="\033[90m";RED="\033[31m";CYAN="\033[96m";DIM="\033[2m"
BANNER=f"""{PURPLE}{BOLD}
██████╗ ███████╗███████╗██╗   ██╗██████╗  ██████╗
██╔══██╗██╔════╝██╔════╝██║   ██║██╔══██╗██╔═══██╗
██████╔╝███████╗█████╗  ██║   ██║██║  ██║██║   ██║
██╔═══╝ ╚════██║██╔══╝  ██║   ██║██║  ██║██║   ██║
██║     ███████║███████╗╚██████╔╝██████╔╝╚██████╔╝
╚═╝     ╚══════╝╚══════╝ ╚═════╝ ╚═════╝  ╚═════╝
{RESET}{TEAL}        ██╗  ██╗██╗   ██╗███╗   ██╗████████╗███████╗██████╗ {RESET}
{TEAL}        ██║  ██║██║   ██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗{RESET}
{TEAL}        ███████║██║   ██║██╔██╗ ██║   ██║   █████╗  ██████╔╝{RESET}
{TEAL}        ██╔══██║██║   ██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗{RESET}
{TEAL}        ██║  ██║╚██████╔╝██║ ╚████║   ██║   ███████╗██║  ██║{RESET}
{TEAL}        ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝{RESET}
{GRAY}         Generate and search common usernames  — by thejazzman ft. Claude{RESET}
"""
def sv(t): return re.sub(r'[aeiouAEIOU]','',t)
def generer_pseudos(prenom,nom):
    p=prenom.lower();n=nom.lower();pv=sv(p);nv=sv(n);p2=p[:2];n2=n[:2];p3=p[:3];n3=n[:3]
    ps=set()
    ps.update([f"{p}.{n}",f"{n}.{p}",f"{p}{n}",f"{n}{p}",f"{p}_{n}",f"{n}_{p}",f"{p}-{n}",f"{n}-{p}",f"{p[0]}.{n}",f"{p[0]}{n}",f"{p[0]}_{n}",f"{p[0]}-{n}",f"{p}.{n[0]}",f"{p}{n[0]}",f"{p}_{n[0]}",f"{p[0]}{n[0]}",f"{p[0]}.{n[0]}",f"{p[0]}_{n[0]}",f"{nv}.{p}",f"{p}.{nv}",f"{nv}{p}",f"{p}{nv}",f"{nv}_{p}",f"{p}_{nv}",f"{nv}-{p}",f"{p}-{nv}",f"{pv}.{n}",f"{n}.{pv}",f"{pv}{n}",f"{pv}_{n}",f"{pv}.{nv}",f"{nv}.{pv}",f"{nv}{pv}",f"{pv}{nv}",f"{p3}.{n}",f"{p3}{n}",f"{p3}_{n}",f"{n3}.{p}",f"{n3}{p}",f"{p3}.{n3}",f"{p3}{n3}",f"{p[0]}{nv}",f"{nv}{p[0]}",f"{n[0]}{pv}",f"{pv}{n[0]}",f"{p2}.{n}",f"{p2}{n}",f"{n2}.{p}",f"{n2}{p}",f"{p.capitalize()}{n}",f"{p}{n.capitalize()}",f"{p}.{n3}",f"{p3}.{n3}",f"{nv}.{p3}",f"{p3}.{nv}",f"{p3}-{n}",f"{n}-{p3}",f"{p3}-{nv}",f"{nv}-{p3}",f"{p2}-{n}",f"{n2}-{p}",f"{p}{n[:3]}",f"{n}{p[:3]}"])
    return sorted({x for x in ps if len(re.sub(r'[.\-_]','',x))>=5})
class Tracker:
    def __init__(self,ts,tm):
        self.lock=threading.Lock();self.sd=0;self.md=0;self.ts=ts;self.tm=tm;self.hs=0;self.hm=0;self.active="";self._stop=False;self._t=threading.Thread(target=self._loop,daemon=True)
    def start(self): self._t.start()
    def stop(self): self._stop=True;self._t.join();print()
    def us(self,p,h):
        with self.lock: self.sd+=1;self.active=p;self.hs+=int(h)
    def um(self,p,h):
        with self.lock: self.md+=1;self.active=p;self.hm+=int(h)
    def _bar(self,d,t,c):
        if t==0: return f"{GRAY}[désactivé]{RESET}"
        pct=d/t;f=int(pct*22);b="█"*f+"░"*(22-f)
        return f"{c}[{b}]{RESET} {BOLD}{int(pct*100):3d}%{RESET} {DIM}({d}/{t}){RESET}"
    def _loop(self):
        sp=["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"];i=0
        while not self._stop:
            with self.lock: sd=self.sd;md=self.md;hs=self.hs;hm=self.hm;ac=self.active
            s=sp[i%len(sp)];i+=1;bs=self._bar(sd,self.ts,TEAL);bm=self._bar(md,self.tm,PURPLE)
            hits=f"{GREEN}hits:{hs+hm}{RESET}";curr=f"{GRAY}{ac[:26]:<26}{RESET}"
            print(f"\r  {TEAL}{s}{RESET} Sherlock {bs}  Maigret {bm}  {hits}  {curr}",end="",flush=True)
            time.sleep(0.1)
def run_sherlock(p,t):
    try:
        r=subprocess.run(["sherlock",p,"--timeout","8","--print-found"],capture_output=True,text=True,timeout=30)
        l=[x.strip() for x in r.stdout.splitlines() if "[+]" in x];t.us(p,bool(l));return p,l
    except FileNotFoundError: t.us(p,False);return p,["ERREUR: sherlock non trouvé"]
    except subprocess.TimeoutExpired: t.us(p,False);return p,[]
def run_maigret(p,t):
    try:
        r=subprocess.run(["maigret",p,"--no-color","-a"],capture_output=True,text=True,timeout=60)
        l=[x.strip() for x in r.stdout.splitlines() if "[+]" in x or "Found" in x];t.um(p,bool(l));return p,l
    except FileNotFoundError: t.um(p,False);return p,["ERREUR: maigret non trouvé"]
    except subprocess.TimeoutExpired: t.um(p,False);return p,[]
def ask(question,options):
    print(f"\n  {BOLD}{YELLOW}{question}{RESET}")
    for k,v in options.items(): print(f"  {TEAL}[{k}]{RESET} {v}")
    print(f"  {GRAY}> {RESET}",end="")
    while True:
        rep=input().strip().lower()
        if rep in options: return rep
        print(f"  {RED}Choix invalide :{RESET} ",end="")
def main():
    print(BANNER)
    print(f"  {BOLD}{TEAL}Entrez le prénom :{RESET} ",end="");prenom=input().strip()
    print(f"  {BOLD}{TEAL}Entrez le nom    :{RESET} ",end="");nom=input().strip()
    if not prenom or not nom: print(f"\n  {YELLOW}Prénom et nom requis.{RESET}\n");sys.exit(1)
    tous=generer_pseudos(prenom,nom)
    print(f"\n  {GRAY}{len(tous)} pseudos disponibles (>=5 caractères){RESET}")
    print(f"\n  {BOLD}{YELLOW}Combien de pseudos voulez-vous utiliser ?{RESET}")
    print(f"  {DIM}(entre 1 et {len(tous)}, ou Entrée pour tous){RESET}")
    print(f"  {GRAY}> {RESET}",end="")
    rep_nb=input().strip()
    nb=len(tous) if rep_nb=="" else max(1,min(int(rep_nb),len(tous))) if rep_nb.isdigit() else len(tous)
    pseudos=tous[:nb]
    print(f"\n  {BOLD}{PURPLE}Cible{RESET}   : {BOLD}{prenom} {nom}{RESET}")
    print(f"  {BOLD}{TEAL}Pseudos{RESET} : {len(pseudos)} variantes\n")
    print(f"  {GRAY}{'─'*60}{RESET}")
    items=list(enumerate(pseudos,1))
    for i in range(0,len(items),3):
        row=items[i:i+3];line=""
        for idx,p in row: line+=f"  {GRAY}{idx:02d}.{RESET} {p:<24}"
        print(line)
    print(f"  {GRAY}{'─'*60}{RESET}")
    mode=ask("Quel mode de recherche ?",{"1":"Sherlock uniquement","2":"Maigret uniquement","3":"Sherlock + Maigret (complet)","4":"Génération seulement (pas de recherche)"})
    use_s=mode in("1","3");use_m=mode in("2","3")
    if mode=="4": print(f"\n  {GREEN}Liste générée. Aucune recherche lancée.{RESET}\n");sys.exit(0)
    print(f"\n  {BOLD}{YELLOW}Lancement en cours...{RESET}\n")
    tracker=Tracker(len(pseudos) if use_s else 0,len(pseudos) if use_m else 0);tracker.start()
    fs={};fm={}
    with ThreadPoolExecutor(max_workers=8) as ex:
        if use_s: fs={ex.submit(run_sherlock,p,tracker):p for p in pseudos}
        if use_m: fm={ex.submit(run_maigret,p,tracker):p for p in pseudos}
        for f in as_completed({**fs,**fm}): pass
    tracker.stop()
    res_s={p:f.result()[1] for f,p in fs.items() if f.result()[1] and "ERREUR" not in f.result()[1][0]}
    res_m={p:f.result()[1] for f,p in fm.items() if f.result()[1] and "ERREUR" not in f.result()[1][0]}
    print(f"\n  {GRAY}{'─'*60}{RESET}")
    if use_s:
        print(f"  {BOLD}{GREEN}Résultats Sherlock{RESET}\n")
        if res_s:
            for p,ls in res_s.items():
                print(f"  {BOLD}{TEAL}{p}{RESET}")
                for l in ls: print(f"    {GREEN}[+]{RESET} {l.split(': ')[-1] if ': ' in l else l}")
                print()
        else: print(f"  {GRAY}Aucun résultat Sherlock.{RESET}\n")
        print(f"  {GRAY}{'─'*60}{RESET}")
    if use_m:
        print(f"  {BOLD}{PURPLE}Résultats Maigret{RESET}\n")
        if res_m:
            for p,ls in res_m.items():
                print(f"  {BOLD}{PURPLE}{p}{RESET}")
                for l in ls: print(f"    {CYAN}[+]{RESET} {l}")
                print()
        else: print(f"  {GRAY}Aucun résultat Maigret.{RESET}\n")
        print(f"  {GRAY}{'─'*60}{RESET}")
    total=len(res_s)+len(res_m)
    print(f"  {BOLD}Terminé.{RESET} {GREEN}{total} pseudo(s) avec résultats.{RESET}\n")
if __name__=="__main__": main()
