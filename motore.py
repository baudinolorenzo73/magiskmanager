# -*- coding: utf-8 -*-
"""
Motore di Magisk Manager (senza interfaccia): root, moduli, GitHub, integrità.
by Lollo ®2026
Tutte le funzioni sono "bloccanti": l'interfaccia le chiama in un thread.
"""
import os
import re
import json
import shlex
import ssl
import hashlib
import subprocess
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

VERSIONE = "1.4"
MARCHIO = "by Lollo ®2026"
MODULI_DIR = "/data/adb/modules"
CHECKER_REPO = "1nikolas/play-integrity-checker-app"
DATI = Path.home() / ".magisk_manager"

# ID dei moduli che influiscono sull'integrità (per segnalarli nel report)
MODULI_INTEGRITA = {
    "playintegrityfix": "Play Integrity Fix/Fork", "tricky_store": "Tricky Store",
    "zygisk_shamiko": "Shamiko", "zygisk-assistant": "Zygisk Assistant",
    "zygisksu": "Zygisk Next", "zygisk_lsposed": "LSPosed",
}

# repo = "proprietario/nome" su GitHub; pattern = regex del nome del file ZIP;
# ids = possibili ID del modulo in /data/adb/modules (serve a riconoscerlo).
CATALOGO_BASE = [
    {"nome": "LSPosed (fork JingMatrix)", "categoria": "Framework",
     "repo": "JingMatrix/LSPosed", "pattern": r"zygisk.*release.*\.zip$",
     "ids": ["zygisk_lsposed"],
     "desc": "Framework Xposed: permette ad altri moduli di modificare il comportamento "
             "di app e sistema senza toccare gli APK.",
     "req": "Zygisk attivo (integrato in Magisk oppure Zygisk Next).",
     "avviso": "Fork mantenuto dalla community; verifica che il progetto sia ancora attivo."},
    {"nome": "Shamiko", "categoria": "Nascondere root",
     "repo": "LSPosed/LSPosed.github.io", "pattern": r"^Shamiko.*release\.zip$",
     "ids": ["zygisk_shamiko"],
     "desc": "Nasconde root e Zygisk alle app che li rifiutano (banche, giochi) "
             "per le app nella DenyList.",
     "req": "Zygisk attivo; 'Applica DenyList' di Magisk DISATTIVATO; le app da nascondere "
            "vanno aggiunte alla DenyList (Configura DenyList).",
     "avviso": "Da solo non basta per Play Integrity."},
    {"nome": "Zygisk Next", "categoria": "Zygisk",
     "repo": "Dr-TSNG/ZygiskNext", "pattern": r"release.*\.zip$", "ids": ["zygisksu"],
     "desc": "Implementazione alternativa di Zygisk, indipendente da Magisk.",
     "req": "Zygisk integrato di Magisk DISATTIVATO (non usarli insieme).",
     "avviso": "Se non hai un motivo preciso, usa lo Zygisk integrato di Magisk."},
    {"nome": "Play Integrity Fork", "categoria": "Nascondere root",
     "repo": "osm0sis/PlayIntegrityFork", "pattern": r"\.zip$", "ids": ["playintegrityfix"],
     "desc": "Aiuta a superare il controllo Play Integrity (verdetto base/device) "
             "richiesto da alcune app.",
     "req": "Zygisk attivo (integrato o Zygisk Next).",
     "avviso": "Non garantito: Google cambia i controlli spesso. "
               "Il verdetto 'strong' richiede una keybox valida."},
    {"nome": "Tricky Store", "categoria": "Nascondere root",
     "repo": "5ec1cff/TrickyStore", "pattern": r"\.zip$", "ids": ["tricky_store"],
     "desc": "Modifica l'attestazione delle chiavi hardware per Play Integrity avanzato.",
     "req": "Uso avanzato: leggi il README del progetto prima di installare.",
     "avviso": "Serve una keybox: questa app NON ne fornisce."},
    {"nome": "Zygisk Assistant", "categoria": "Nascondere root",
     "repo": "snake-4/Zygisk-Assistant", "pattern": r"\.zip$", "ids": ["zygisk-assistant"],
     "desc": "Nasconde le tracce di root dalle app nella DenyList (alternativa a Shamiko).",
     "req": "Zygisk attivo; usa la DenyList di Magisk.",
     "avviso": "Non installarlo insieme a Shamiko."},
    {"nome": "Bindhosts", "categoria": "Rete",
     "repo": "backslashxx/bindhosts", "pattern": r"bindhosts.*\.zip$", "ids": ["bindhosts"],
     "desc": "Blocco pubblicità/tracker a livello di sistema tramite file hosts (systemless).",
     "req": "Nessuno in particolare.",
     "avviso": "Blocchi troppo aggressivi possono rompere alcune app."},
    {"nome": "NeoZygisk", "categoria": "Zygisk",
     "repo": "JingMatrix/NeoZygisk", "pattern": r"\.zip$", "ids": ["zygisksu"],
     "desc": "Implementazione di Zygisk indipendente da Magisk, mantenuta insieme a LSPosed.",
     "req": "Zygisk integrato di Magisk DISATTIVATO. Non usarlo con Zygisk Next o ReZygisk.",
     "avviso": "Tre implementazioni diverse (Zygisk Next, NeoZygisk, ReZygisk): ne serve UNA sola."},
    {"nome": "ReZygisk", "categoria": "Zygisk",
     "repo": "PerformanC/ReZygisk", "pattern": r"\.zip$", "ids": ["rezygisk"],
     "desc": "Altra implementazione di Zygisk, open source, per Magisk, KernelSU e APatch.",
     "req": "Zygisk integrato di Magisk DISATTIVATO. Non usarlo con Zygisk Next o NeoZygisk.",
     "avviso": "Ne serve UNA sola tra Zygisk Next, NeoZygisk e ReZygisk."},
    {"nome": "Tricky Addons", "categoria": "Nascondere root",
     "repo": "KOWX712/Tricky-Addons-Update-Target-List", "pattern": r"\.zip$", "ids": [],
     "desc": "Aggiunge a Tricky Store la gestione comoda dell'elenco delle app da trattare.",
     "req": "Tricky Store installato.",
     "avviso": "Controlla il README: il nome dei file di release puo cambiare."},
    {"nome": "Zygisk Detach", "categoria": "App",
     "repo": "j-hc/zygisk-detach", "pattern": r"\.zip$", "ids": [],
     "desc": "Impedisce al Play Store di aggiornare le app che scegli (utile per app modificate).",
     "req": "Zygisk attivo.",
     "avviso": "Le app scelte non si aggiornano piu dal Play Store finche non le riattivi."},
    {"nome": "Trust User Certs", "categoria": "Rete",
     "repo": "NVISOsecurity/MagiskTrustUserCerts", "pattern": r"\.zip$", "ids": [],
     "desc": "Fa considerare attendibili i certificati installati dall'utente anche alle app di sistema.",
     "req": "Nessuno in particolare.",
     "avviso": "Serve per analisi del traffico (es. proxy): non lasciare certificati sconosciuti."},
    {"nome": "MagiskFrida", "categoria": "Sviluppo",
     "repo": "ViRb3/magisk-frida", "pattern": r"\.zip$", "ids": [],
     "desc": "Avvia frida-server all'accensione: strumento di analisi per sviluppatori.",
     "req": "Uso avanzato.",
     "avviso": "Solo per sviluppo e test: non serve all'uso normale."},
]


# ───────────────────────── Cartelle e file ─────────────────────────
def imposta_cartella(percorso):
    """Cartella dati dell'app (su Android: user_data_dir)."""
    global DATI
    DATI = Path(percorso)
    DATI.mkdir(parents=True, exist_ok=True)


def cartella_download():
    d = DATI / "download"
    d.mkdir(parents=True, exist_ok=True)
    return d


def scrivi_json_atomico(percorso: Path, dati):
    """Scrive su file temporaneo e poi rinomina, per non corrompere i dati."""
    percorso.parent.mkdir(parents=True, exist_ok=True)
    tmp = percorso.with_suffix(percorso.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)
    os.replace(tmp, percorso)


def _file_catalogo():
    return DATI / "catalogo.json"


# ───────────────────────── Root e sistema ─────────────────────────
def su(comando, timeout=60):
    """Esegue un comando da root. Ritorna (codice, stdout, stderr)."""
    try:
        r = subprocess.run(["su", "-c", comando], capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return 127, "", "su non trovato"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except OSError as e:
        return 126, "", str(e)


def prop(nome):
    try:
        r = subprocess.run(["getprop", nome], capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def root_ok():
    rc, out, _ = su("id")
    return rc == 0 and "uid=0" in out


def id_sicuro(mid):
    return bool(re.fullmatch(r"[A-Za-z0-9._-]+", mid or ""))


def riavvia():
    su("reboot")


def file_esiste(percorso):
    """True se il file esiste ed è leggibile da root (anche in /sdcard)."""
    rc, _, _ = su(f"test -f {shlex.quote(percorso)}")
    return rc == 0


def info_completa():
    """Stato di Magisk e del dispositivo. dict; 'root' False se manca il root."""
    if not root_ok():
        return {"root": False}
    d = {"root": True}
    rc, o, _ = su("magisk -v")
    d["versione"] = o.strip() if rc == 0 and o.strip() else None
    rc, o, _ = su("magisk -V")
    d["codice"] = o.strip() if rc == 0 else "?"
    rc, o, _ = su("magisk --path")
    d["path"] = o.strip() if rc == 0 else "?"
    rc, o, _ = su("magisk --sqlite \"SELECT value FROM settings WHERE key='zygisk'\"")
    d["zygisk"] = "value=1" in o
    rc, _, _ = su("magisk --denylist status")
    d["denylist"] = (rc == 0)
    rc, o, _ = su("pm list packages")
    d["app"] = sorted(set(re.findall(r"package:([\w.]*magisk[\w.]*)", o, re.I)))
    d["dispositivo"] = f"{prop('ro.product.manufacturer')} {prop('ro.product.model')}".strip()
    d["android"] = f"{prop('ro.build.version.release')} (SDK {prop('ro.build.version.sdk')})"
    d["abi"] = prop("ro.product.cpu.abi")
    mods = leggi_moduli()
    d["n_moduli"] = None if mods is None else len(mods)
    return d


# ───────────────────────── Rete / GitHub ─────────────────────────
def _contesto_ssl():
    """Su Android il sistema non offre i certificati a Python: si usa certifi."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "magisk-manager-lollo"})
    return urllib.request.urlopen(req, timeout=timeout, context=_contesto_ssl())


def http_json(url):
    with http_get(url) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def github_release(repo, pattern):
    """Prima release stabile con un file che rispetta il pattern.
    Ritorna dict(tag, nome_file, url, size, note) oppure None."""
    elenco = http_json(f"https://api.github.com/repos/{repo}/releases?per_page=15")
    for solo_stabili in (True, False):
        for rel in elenco:
            if rel.get("draft") or (solo_stabili and rel.get("prerelease")):
                continue
            for a in rel.get("assets", []):
                if re.search(pattern, a["name"], re.I):
                    return {"tag": rel.get("tag_name", "?"), "nome_file": a["name"],
                            "url": a["browser_download_url"], "size": a.get("size", 0),
                            "note": (rel.get("body") or "").strip()}
    return None


def scarica(url, destinazione: Path, avanzamento=None):
    """Scarica in un file. avanzamento(fatti, totale) facoltativo. Ritorna lo SHA-256."""
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    tmp = destinazione.with_suffix(destinazione.suffix + ".part")
    h = hashlib.sha256()
    with http_get(url, 30) as r, open(tmp, "wb") as f:
        totale = int(r.headers.get("Content-Length") or 0)
        fatti = 0
        while True:
            blocco = r.read(65536)
            if not blocco:
                break
            f.write(blocco)
            h.update(blocco)
            fatti += len(blocco)
            if avanzamento:
                avanzamento(fatti, totale)
    os.replace(tmp, destinazione)
    return h.hexdigest()


def nome_file_sicuro(nome, estensione):
    nome = re.sub(r"[^\w.\-]", "_", nome or "file")
    return nome if nome.lower().endswith(estensione) else nome + estensione


def tupla_versione(s):
    return tuple(int(x) for x in re.findall(r"\d+", s or ""))[:3]


# ───────────────────────── Moduli ─────────────────────────
SCRIPT_MODULI = r'''
for d in /data/adb/modules/*/; do
  [ -d "$d" ] || continue
  echo "@@MOD $(basename "$d")"
  cat "${d}module.prop" 2>/dev/null
  echo
  for f in disable remove; do [ -e "${d}$f" ] && echo "@@FLAG $f"; done
done
echo "@@PENDING"
ls -1 /data/adb/modules_update 2>/dev/null
'''


def leggi_moduli():
    """Lista di moduli installati (dict). None se non si riesce a leggere."""
    rc, out, _ = su(SCRIPT_MODULI)
    if rc != 0 and not out:
        return None
    mods, cur, pending, sezione = [], None, set(), "mod"
    for riga in out.splitlines():
        if riga.startswith("@@MOD "):
            cur = {"id": riga[6:].strip(), "righe": [], "disabled": False, "remove": False}
            mods.append(cur)
            sezione = "mod"
        elif riga.startswith("@@FLAG ") and cur is not None:
            flag = riga[7:].strip()
            if flag == "disable":
                cur["disabled"] = True
            elif flag == "remove":
                cur["remove"] = True
        elif riga.startswith("@@PENDING"):
            sezione, cur = "pend", None
        elif sezione == "pend":
            if riga.strip():
                pending.add(riga.strip())
        elif cur is not None:
            cur["righe"].append(riga)
    for m in mods:
        p = {}
        for r in m.pop("righe"):
            if "=" in r and not r.lstrip().startswith("#"):
                k, v = r.split("=", 1)
                p[k.strip()] = v.strip()
        m["name"] = p.get("name", m["id"])
        m["version"] = p.get("version", "?")
        m["versionCode"] = p.get("versionCode", "")
        m["author"] = p.get("author", "?")
        m["description"] = p.get("description", "")
        m["updateJson"] = p.get("updateJson", "")
        m["pending"] = m["id"] in pending
    return mods


def stato_testo(m):
    """Stato del modulo come (testo, colore_hex)."""
    if m["remove"]:
        s, c = "rimozione al riavvio", "ff5555"
    elif m["disabled"]:
        s, c = "disattivato", "ffd34d"
    else:
        s, c = "attivo", "44ff77"
    if m["pending"]:
        s += " · riavvio per applicare"
    return s, c


def modifica_modulo(mid, azione):
    """azione: disabilita / abilita / rimuovi / annulla_rimozione. Ritorna (ok, errore)."""
    if not id_sicuro(mid):
        return False, "ID modulo con caratteri non ammessi"
    base = f"{MODULI_DIR}/{mid}"
    cmd = {"disabilita": f"touch {base}/disable", "abilita": f"rm -f {base}/disable",
           "rimuovi": f"touch {base}/remove", "annulla_rimozione": f"rm -f {base}/remove"}.get(azione)
    if not cmd:
        return False, "azione sconosciuta"
    rc, _, err = su(cmd)
    return rc == 0, err.strip()


# ───────────────────────── Catalogo e aggiornamenti ─────────────────────────
def catalogo_completo():
    voci = list(CATALOGO_BASE)
    try:
        with open(_file_catalogo(), encoding="utf-8") as f:
            extra = json.load(f)
        if isinstance(extra, list):
            voci += [e for e in extra if isinstance(e, dict) and e.get("repo") and e.get("nome")]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return voci


def _leggi_extra():
    try:
        with open(_file_catalogo(), encoding="utf-8") as f:
            voci = json.load(f)
        return voci if isinstance(voci, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def repo_gia_presente(repo):
    return any(v.get("repo", "").lower() == repo.lower() for v in catalogo_completo())


def cerca_github(testo="", quanti=15):
    """Cerca su GitHub repository con l'argomento 'magisk-module'.
    Ritorna una lista di dict(repo, desc, stelle, aggiornato, archiviato)."""
    q = (testo.strip() + " " if testo.strip() else "") + "topic:magisk-module"
    url = ("https://api.github.com/search/repositories?q=" + urllib.parse.quote(q)
           + f"&sort=stars&order=desc&per_page={int(quanti)}")
    try:
        dati = http_json(url)
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            raise RuntimeError("Troppe ricerche su GitHub: aspetta un minuto e riprova") from e
        raise
    return [{"repo": r["full_name"], "desc": (r.get("description") or "")[:160],
             "stelle": r.get("stargazers_count", 0),
             "aggiornato": (r.get("pushed_at") or "")[:10],
             "archiviato": bool(r.get("archived"))} for r in dati.get("items", [])]


_RE_REPO = re.compile(r"[\w.-]+/[\w.-]+")


def _repo_da_testo(s):
    """Accetta 'proprietario/nome' oppure un indirizzo github.com/proprietario/nome."""
    s = s.strip().strip(",;")
    m = re.match(r"https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/.*)?$", s)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return s if _RE_REPO.fullmatch(s) else None


def importa_catalogo(sorgente):
    """Importa voci nel catalogo personale. La sorgente puo essere:
    un elenco JSON incollato, un indirizzo web a un file JSON, il percorso di un file,
    un indirizzo github.com/proprietario/nome oppure piu 'proprietario/nome' separati da spazi.
    Ritorna (ok, messaggio)."""
    s = (sorgente or "").strip()
    if not s:
        return False, "Incolla un indirizzo, un percorso o un elenco"
    voci_in = None
    try:
        if s[0] in "[{":
            voci_in = json.loads(s)
        elif _repo_da_testo(s):
            voci_in = [s]
        elif s.lower().startswith(("http://", "https://")):
            with http_get(s, 30) as r:
                voci_in = json.loads(r.read(1048576).decode("utf-8", "replace"))
        elif Path(s).expanduser().is_file():
            with open(Path(s).expanduser(), encoding="utf-8") as f:
                voci_in = json.load(f)
        else:
            voci_in = [x for x in re.split(r"[\s,;]+", s) if x]
    except (json.JSONDecodeError, OSError, urllib.error.URLError, TimeoutError) as e:
        return False, f"Non riesco a leggere la sorgente: {str(e)[:80]}"
    if isinstance(voci_in, dict):
        voci_in = voci_in.get("moduli") or voci_in.get("modules") or [voci_in]
    if not isinstance(voci_in, list):
        return False, "Formato non riconosciuto: serve un elenco di moduli"

    extra = _leggi_extra()
    note = {"agg": 0, "dup": 0, "scarto": 0}
    for v in voci_in[:300]:
        if isinstance(v, str):
            v = {"repo": v}
        repo = _repo_da_testo(str(v.get("repo", ""))) if isinstance(v, dict) else None
        if not repo:
            note["scarto"] += 1
            continue
        if repo_gia_presente(repo) or any(e.get("repo", "").lower() == repo.lower() for e in extra):
            note["dup"] += 1
            continue
        pattern = str(v.get("pattern") or r"\.zip$")
        try:
            re.compile(pattern)
        except re.error:
            pattern = r"\.zip$"
        ids = v.get("ids") if isinstance(v.get("ids"), list) else []
        extra.append({"nome": str(v.get("nome") or repo.split("/")[1])[:60],
                      "categoria": str(v.get("categoria") or "Importato")[:30],
                      "repo": repo, "pattern": pattern, "ids": [str(i) for i in ids][:5],
                      "desc": str(v.get("desc") or "Modulo importato")[:300],
                      "req": str(v.get("req") or "Vedi il README del progetto.")[:300],
                      "avviso": str(v.get("avviso") or
                                    "Voce importata: controlla l'affidabilita della fonte.")[:300]})
        note["agg"] += 1
    if note["agg"]:
        scrivi_json_atomico(_file_catalogo(), extra)
    testo = f"Importati {note['agg']}"
    if note["dup"]:
        testo += f", gia presenti {note['dup']}"
    if note["scarto"]:
        testo += f", scartati {note['scarto']}"
    return note["agg"] > 0, testo


def aggiungi_voce_catalogo(repo, descrizione="", pattern=r"\.zip$"):
    """Aggiunge un repo GitHub al catalogo personale. Ritorna (ok, messaggio)."""
    repo = (repo or "").strip()
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        return False, "Formato non valido: usa proprietario/nome"
    try:
        re.compile(pattern)
    except re.error:
        return False, "Regex non valida"
    if repo_gia_presente(repo):
        return False, "Questo repository e gia nel catalogo"
    voci = _leggi_extra()
    voci.append({"nome": repo.split("/")[1], "categoria": "Personale", "repo": repo,
                 "pattern": pattern, "ids": [], "desc": descrizione or "Modulo personalizzato",
                 "req": "Vedi il README del progetto.",
                 "avviso": "Voce aggiunta da te: controlla l'affidabilità della fonte."})
    scrivi_json_atomico(_file_catalogo(), voci)
    return True, "Aggiunto al catalogo"


def trova_voce(m, catalogo):
    for e in catalogo:
        if m["id"] in e.get("ids", []) or e["nome"].lower() == m["name"].lower():
            return e
    return None


def controlla_modulo(m, catalogo):
    """Ritorna dict(stato, remoto, url, fonte). stato: ok / agg / nd / err."""
    try:
        if m["updateJson"]:
            j = http_json(m["updateJson"])
            remoto = str(j.get("version", "?"))
            url = j.get("zipUrl")
            try:
                agg = int(j.get("versionCode")) > int(m["versionCode"])
            except (TypeError, ValueError):
                agg = tupla_versione(remoto) > tupla_versione(m["version"])
            return {"stato": "agg" if agg else "ok", "remoto": remoto,
                    "url": url, "fonte": "updateJson"}
        voce = trova_voce(m, catalogo)
        if voce:
            rel = github_release(voce["repo"], voce["pattern"])
            if not rel:
                return {"stato": "nd", "remoto": "?", "url": None, "fonte": "GitHub"}
            tr, tl = tupla_versione(rel["tag"]), tupla_versione(m["version"])
            if not tr or not tl:
                return {"stato": "nd", "remoto": rel["tag"], "url": rel["url"], "fonte": "GitHub"}
            return {"stato": "agg" if tr > tl else "ok", "remoto": rel["tag"],
                    "url": rel["url"], "fonte": "GitHub"}
    except urllib.error.HTTPError as e:
        extra = " (limite GitHub: riprova più tardi)" if e.code == 403 else ""
        return {"stato": "err", "remoto": f"HTTP {e.code}{extra}", "url": None, "fonte": "-"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        return {"stato": "err", "remoto": str(e)[:40], "url": None, "fonte": "-"}
    return {"stato": "nd", "remoto": "-", "url": None, "fonte": "nessuna"}


# ───────────────────────── Installazione ─────────────────────────
def installa_zip(percorso: Path):
    """Installa uno ZIP con 'magisk --install-module'. Ritorna (ok, righe_output)."""
    q = shlex.quote
    rc, out, err = su(f"magisk --install-module {q(str(percorso))}", 300)
    if rc != 0:
        # secondo tentativo: copia in una cartella leggibile da root
        tmp = f"/data/local/tmp/{Path(percorso).name}"
        su(f"cp {q(str(percorso))} {q(tmp)} && chmod 644 {q(tmp)}")
        rc, out, err = su(f"magisk --install-module {q(tmp)}", 300)
        su(f"rm -f {q(tmp)}")
    return rc == 0, (out + "\n" + err).strip().splitlines()


def installa_apk(percorso: Path):
    """Installa un APK con 'pm install -r'. Ritorna (ok, righe_output)."""
    q = shlex.quote
    tmp = f"/data/local/tmp/{Path(percorso).name}"
    rc, _, err = su(f"cp {q(str(percorso))} {q(tmp)} && chmod 644 {q(tmp)}")
    if rc != 0:
        return False, [f"Copia non riuscita: {err.strip()}"]
    rc, out, err = su(f"pm install -r {q(tmp)}", 120)
    su(f"rm -f {q(tmp)}")
    return rc == 0, (out + "\n" + err).strip().splitlines()


# ───────────────────────── Integrità (Play Integrity) ─────────────────────────
def controlli_locali():
    """Indizi locali sullo stato del dispositivo. Lista di (nome, valore, esito).
    esito: True = buono, False = da controllare, None = informativo.
    NON è il verdetto di Google: quello lo dà solo l'app checker."""
    righe = []
    vb = prop("ro.boot.verifiedbootstate")
    righe.append(("Verified boot", vb or "n/d", (vb == "green") if vb else None))
    fl = prop("ro.boot.flash.locked")
    righe.append(("Bootloader bloccato", fl or "n/d", (fl == "1") if fl else None))
    vm = prop("ro.boot.vbmeta.device_state")
    righe.append(("vbmeta device state", vm or "n/d", (vm == "locked") if vm else None))
    tags = prop("ro.build.tags")
    righe.append(("Build tags", tags or "n/d", (tags == "release-keys") if tags else None))
    dbg = prop("ro.debuggable")
    righe.append(("Build debuggable", dbg or "n/d", (dbg == "0") if dbg else None))
    rc, o, _ = su("getenforce")
    se = o.strip() if rc == 0 else "n/d"
    righe.append(("SELinux", se, (se == "Enforcing") if rc == 0 else None))
    rc, o, _ = su("pm list packages")
    gms = "package:com.google.android.gms" in o
    store = "package:com.android.vending" in o
    righe.append(("Google Play Services", "presente" if gms else "assente", gms))
    righe.append(("Google Play Store", "presente" if store else "assente", store))
    return righe


def moduli_integrita(mods):
    """Nomi (con eventuale '(disattivato)') dei moduli che influiscono sull'integrità."""
    return [MODULI_INTEGRITA[m["id"]] + (" (disattivato)" if m["disabled"] else "")
            for m in (mods or []) if m["id"] in MODULI_INTEGRITA]


def trova_checker():
    """Cerca tra i pacchetti installati un'app 'integrity checker'."""
    rc, o, _ = su("pm list packages")
    for p in re.findall(r"package:(\S+)", o):
        if "integrity" in p.lower() and "check" in p.lower():
            return p
    return None


def avvia_checker():
    """Avvia l'app checker. Ritorna (ok, messaggio)."""
    pkg = trova_checker()
    if not pkg:
        return False, "App checker non trovata tra i pacchetti installati"
    rc, _, _ = su(f"monkey -p {shlex.quote(pkg)} -c android.intent.category.LAUNCHER 1")
    return (rc == 0), (f"Avviata: {pkg}" if rc == 0 else "Non riesco ad avviarla: aprila dal cassetto delle app")


# ───────────────────────── Recupero: copia dell'immagine di boot ─────────────────────────
CARTELLA_BACKUP_BOOT = "/sdcard/MagiskManager/backup-boot"


def partizioni_boot():
    """Cerca le partizioni boot e init_boot (con l'eventuale slot A/B).
    Ritorna (suffisso_slot, [(nome, dispositivo)])."""
    suffisso = prop("ro.boot.slot_suffix")
    trovate = []
    for nome in ("boot", "init_boot"):
        for cand in ([nome + suffisso, nome] if suffisso else [nome]):
            script = ("for d in /dev/block/by-name /dev/block/bootdevice/by-name "
                      "/dev/block/platform/*/by-name /dev/block/platform/*/*/by-name; do "
                      f"[ -e \"$d/{cand}\" ] && echo \"$d/{cand}\" && break; done")
            rc, out, _ = su(script)
            dev = out.strip().splitlines()[0] if rc == 0 and out.strip() else ""
            if dev:
                trovate.append((nome, dev))
                break
    return suffisso, trovate


def _spazio_libero_mb(cartella):
    rc, out, _ = su(f"df -k {shlex.quote(cartella)} | tail -n 1")
    try:
        return int(out.split()[3]) // 1024
    except (IndexError, ValueError):
        return None


def backup_boot(scrivi=lambda m: None):
    """Copia boot (e init_boot se c'e) in /sdcard/MagiskManager/backup-boot.
    Ritorna (ok, righe_riassunto). scrivi(msg) riceve l'avanzamento."""
    q = shlex.quote
    if not root_ok():
        return False, ["Root non disponibile"]
    suffisso, parti = partizioni_boot()
    if not parti:
        return False, ["Non trovo la partizione di boot su questo telefono: "
                       "non faccio nulla per non rischiare."]
    scrivi(f"Slot: {suffisso or 'nessuno (non A/B)'} - partizioni: "
           + ", ".join(n for n, _ in parti))
    cartella = CARTELLA_BACKUP_BOOT
    rc, _, err = su(f"mkdir -p {q(cartella)}")
    if rc != 0:
        return False, [f"Non riesco a creare la cartella {cartella}: {err.strip()}"]
    data = __import__("time").strftime("%Y%m%d-%H%M%S")
    riassunto, tutto_ok = [], True
    for nome, dev in parti:
        rc, out, _ = su(f"blockdev --getsize64 {q(dev)}")
        try:
            dim = int(out.strip())
        except ValueError:
            dim = 0
        libero = _spazio_libero_mb(cartella)
        if dim and libero is not None and libero < dim // 1048576 + 50:
            riassunto.append(f"{nome}: spazio insufficiente ({libero} MB liberi)")
            tutto_ok = False
            continue
        dest = f"{cartella}/{nome}{suffisso}_{data}.img"
        scrivi(f"Copio {nome} ({dim // 1048576} MB)...")
        rc, _, err = su(f"dd if={q(dev)} of={q(dest)} bs=4194304", 600)
        rc2, out2, _ = su(f"wc -c < {q(dest)}")
        try:
            copiato = int(out2.strip())
        except ValueError:
            copiato = -1
        if rc != 0 or (dim and copiato != dim):
            riassunto.append(f"{nome}: copia NON riuscita ({copiato} byte su {dim}) {err.strip()[:80]}")
            tutto_ok = False
            su(f"rm -f {q(dest)}")
            continue
        scrivi(f"Calcolo l'impronta SHA-256 di {nome}...")
        _, h, _ = su(f"sha256sum {q(dest)}", 300)
        impronta = h.split()[0] if h.split() else "?"
        su(f"echo {q(impronta + '  ' + dest.rsplit('/', 1)[1])} > {q(dest + '.sha256')}")
        riassunto.append(f"{nome}: OK, {copiato // 1048576} MB, SHA-256 {impronta[:16]}...")
    # Copia originale di fabbrica che Magisk conserva dopo la sua installazione
    rc, out, _ = su("ls -d /data/magisk_backup_* 2>/dev/null | head -n 1")
    cartella_mg = out.strip()
    if rc == 0 and cartella_mg:
        for nome, _ in parti:
            sorgente = f"{cartella_mg}/{nome}.img.gz"
            if file_esiste(sorgente):
                rc3, _, _ = su(f"cp {q(sorgente)} {q(cartella + '/originale-' + nome + '_' + data + '.img.gz')}")
                riassunto.append(f"Originale di fabbrica ({nome}) copiato da Magisk"
                                 if rc3 == 0 else f"Originale {nome}: copia non riuscita")
    return tutto_ok, riassunto


def elenco_backup_boot():
    rc, out, _ = su(f"ls -lh {shlex.quote(CARTELLA_BACKUP_BOOT)} 2>/dev/null")
    righe = [r for r in out.splitlines() if r.strip() and not r.startswith("total")]
    return rc == 0, righe
