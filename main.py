# -*- coding: utf-8 -*-
"""
Magisk Manager (APK, Kivy)  —  by Lollo ®2026
Controlla Magisk e i moduli, cerca aggiornamenti, installa moduli da un catalogo
e verifica l'integrità del dispositivo (Play Integrity). Richiede root (Magisk).
La logica è in motore.py; qui c'è solo l'interfaccia.
"""
import threading
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import escape_markup as esc

import motore as mt

# Stile "fosforo verde retrò"
VERDE = (0.27, 1.0, 0.47, 1)
BIANCO = (1, 1, 1, 1)
GIALLO = (1.0, 0.83, 0.3, 1)
BG = (0.02, 0.05, 0.03, 1)
CARD = (0.06, 0.11, 0.07, 1)
BTN = (0.08, 0.35, 0.16, 1)
BTN_GRIGIO = (0.2, 0.25, 0.22, 1)
BTN_ROSSO = (0.55, 0.15, 0.12, 1)
BTN_NAV = (0.04, 0.12, 0.07, 1)
BTN_NAV_ATTIVO = (0.1, 0.45, 0.22, 1)


# ───────────────────────── Widget di base ─────────────────────────
class Testo(Label):
    """Etichetta con markup, a capo automatico e altezza che segue il testo."""

    def __init__(self, testo="", colore=VERDE, halign="left", dimensione=15, **kw):
        super().__init__(text=testo, markup=True, color=colore, halign=halign,
                         valign="top", font_size=sp(dimensione), size_hint_y=None, **kw)
        self.bind(width=self._adatta, texture_size=self._adatta)
        self._adatta()

    def _adatta(self, *_):
        self.text_size = (self.width, None)
        self.height = self.texture_size[1] + dp(4)


class Scheda(BoxLayout):
    """Riquadro con sfondo scuro, alto quanto il contenuto."""

    def __init__(self, **kw):
        super().__init__(orientation="vertical", size_hint_y=None,
                         padding=dp(10), spacing=dp(6), **kw)
        with self.canvas.before:
            Color(*CARD)
            self._sfondo = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._agg, size=self._agg, minimum_height=self.setter("height"))

    def _agg(self, *_):
        self._sfondo.pos = self.pos
        self._sfondo.size = self.size


def bottone(testo, azione, colore=BTN, altezza=48):
    b = Button(text=testo, size_hint_y=None, height=dp(altezza), background_normal="",
               background_color=colore, color=BIANCO, font_size=sp(15))
    b.bind(on_release=lambda *_: azione())
    return b


def riga_bottoni(*bottoni):
    r = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
    for b in bottoni:
        r.add_widget(b)
    return r


def campo(suggerimento):
    return TextInput(hint_text=suggerimento, multiline=False, size_hint_y=None,
                     height=dp(44), write_tab=False, font_size=sp(15),
                     background_color=(0.1, 0.16, 0.11, 1), foreground_color=BIANCO,
                     hint_text_color=(0.5, 0.6, 0.52, 1), cursor_color=VERDE)


def in_background(lavoro, finito):
    """Esegue lavoro() in un thread; finito(risultato_o_eccezione) gira nel thread grafico."""
    def corpo():
        try:
            ris = lavoro()
        except Exception as e:  # noqa: BLE001 - l'errore va mostrato, non perso
            ris = e
        Clock.schedule_once(lambda dt: finito(ris))
    threading.Thread(target=corpo, daemon=True).start()


class Pagina(ScrollView):
    """Pagina scorrevole. carica() mostra 'Attendere', lavora in background e disegna."""

    def __init__(self):
        super().__init__(do_scroll_x=False)
        self.lista = BoxLayout(orientation="vertical", size_hint_y=None,
                               padding=dp(10), spacing=dp(10))
        self.lista.bind(minimum_height=self.lista.setter("height"))
        self.add_widget(self.lista)
        self.token = 0

    def svuota(self):
        self.lista.clear_widgets()

    def aggiungi(self, w):
        self.lista.add_widget(w)

    def carica(self, lavoro, disegna):
        self.svuota()
        self.aggiungi(Testo("Attendere..."))
        self.token += 1
        mio = self.token

        def fine(ris):
            if mio != self.token:  # nel frattempo la pagina è stata ricaricata
                return
            self.svuota()
            if isinstance(ris, Exception):
                self.aggiungi(Testo(f"[color=ff5555]Errore: {esc(str(ris))}[/color]"))
                return
            disegna(ris)
        in_background(lavoro, fine)


def conferma(titolo, testo, si, etichetta_si="Si"):
    sv = ScrollView()
    sv.add_widget(Testo(testo, colore=BIANCO))
    riga = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
    box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
    box.add_widget(sv)
    box.add_widget(riga)
    p = Popup(title=titolo, content=box, size_hint=(0.92, 0.6))
    riga.add_widget(bottone("Annulla", p.dismiss, BTN_GRIGIO))
    riga.add_widget(bottone(etichetta_si, lambda: (p.dismiss(), si()), BTN))
    p.open()


class Operazione:
    """Finestra con il registro di un'operazione lunga (thread-safe)."""

    def __init__(self, titolo):
        self.log = Testo("", colore=BIANCO)
        self.riga = Testo("", colore=GIALLO)
        dentro = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        dentro.bind(minimum_height=dentro.setter("height"))
        dentro.add_widget(self.log)
        dentro.add_widget(self.riga)
        sv = ScrollView()
        sv.add_widget(dentro)
        self.chiudi = bottone("Chiudi", lambda: self.popup.dismiss(), BTN_GRIGIO)
        self.chiudi.disabled = True
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        box.add_widget(sv)
        box.add_widget(self.chiudi)
        self.popup = Popup(title=titolo, content=box, size_hint=(0.95, 0.8), auto_dismiss=False)
        self.popup.open()

    def scrivi(self, msg):
        Clock.schedule_once(lambda dt: setattr(
            self.log, "text", (self.log.text + "\n" if self.log.text else "") + esc(msg)))

    def stato(self, msg):
        Clock.schedule_once(lambda dt: setattr(self.riga, "text", esc(msg)))

    def fine(self):
        Clock.schedule_once(lambda dt: setattr(self.chiudi, "disabled", False))


def flusso_download(titolo, url, nome_file, tipo, dopo=None):
    """Scarica un file e lo installa. tipo: 'zip' (modulo Magisk) oppure 'apk'."""
    op = Operazione(titolo)
    nome = mt.nome_file_sicuro(nome_file, ".zip" if tipo == "zip" else ".apk")

    def lavoro():
        dest = mt.cartella_download() / nome
        op.scrivi(f"Scarico {nome}")

        def prog(fatti, totale):
            op.stato(f"{fatti / 1048576:.1f} / {totale / 1048576:.1f} MB" if totale
                     else f"{fatti / 1048576:.1f} MB")
        sha = mt.scarica(url, dest, prog)
        op.stato("")
        op.scrivi(f"SHA-256: {sha}")
        op.scrivi("Installo...")
        ok, righe = mt.installa_zip(dest) if tipo == "zip" else mt.installa_apk(dest)
        for r in righe[-12:]:
            op.scrivi(r)
        if ok and tipo == "zip":
            op.scrivi("FATTO. Riavvia il dispositivo per attivare il modulo.")
            op.scrivi("Se il telefono non parte (bootloop): modalita provvisoria o "
                      "disabilita i moduli da recovery.")
        elif ok:
            op.scrivi("FATTO. App installata.")
            if dopo:
                dopo(op)
        else:
            op.scrivi("NON RIUSCITA. Puoi installare a mano il file: " + str(dest))
        return ok

    def finito(ris):
        if isinstance(ris, Exception):
            op.scrivi(f"Errore: {ris}")
        op.fine()
    in_background(lavoro, finito)


def flusso_zip_locale(percorso):
    op = Operazione("Installa da ZIP")

    def lavoro():
        if not mt.file_esiste(percorso):
            op.scrivi("File non trovato (o non leggibile da root).")
            return False
        op.scrivi("Installo...")
        ok, righe = mt.installa_zip(Path(percorso))
        for r in righe[-12:]:
            op.scrivi(r)
        op.scrivi("FATTO. Riavvia per attivare il modulo." if ok else "NON RIUSCITA.")
        return ok

    def finito(ris):
        if isinstance(ris, Exception):
            op.scrivi(f"Errore: {ris}")
        op.fine()
    in_background(lavoro, finito)


# ───────────────────────── App ─────────────────────────
class MagiskApp(App):
    title = "Magisk Manager"

    SCHEDE = [("stato", "Stato"), ("moduli", "Moduli"), ("aggiorna", "Aggiorna"),
              ("installa", "Installa"), ("integrita", "Integrita")]

    def build(self):
        mt.imposta_cartella(self.user_data_dir)
        Window.clearcolor = BG
        Window.softinput_mode = "below_target"
        radice = BoxLayout(orientation="vertical")
        radice.add_widget(Testo(
            f"[b]MAGISK MANAGER[/b]  v{mt.VERSIONE}\n[size=12sp]{mt.MARCHIO}[/size]",
            halign="center", dimensione=18))
        self.barra = Testo("", colore=GIALLO)
        radice.add_widget(self.barra)
        self.area = BoxLayout()
        radice.add_widget(self.area)
        nav = BoxLayout(size_hint_y=None, height=dp(56))
        self.pagine, self.nav = {}, {}
        for chiave, etichetta in self.SCHEDE:
            b = Button(text=etichetta, background_normal="", background_color=BTN_NAV,
                       color=VERDE, font_size=sp(13))
            b.bind(on_release=lambda *_, k=chiave: self.mostra(k))
            nav.add_widget(b)
            self.nav[chiave] = b
        radice.add_widget(nav)
        self.mostra("stato")
        return radice

    # --- navigazione ---
    def mostra(self, chiave):
        self.area.clear_widgets()
        pag = self.pagine.setdefault(chiave, Pagina())
        self.area.add_widget(pag)
        self.messaggio("")
        for k, b in self.nav.items():
            b.background_color = BTN_NAV_ATTIVO if k == chiave else BTN_NAV
        getattr(self, "carica_" + chiave)()

    def messaggio(self, testo):
        self.barra.text = esc(testo)

    def _esito(self, ris, ok_msg):
        """Mostra l'esito di un'azione (ok, errore) o un'eccezione."""
        if isinstance(ris, Exception):
            self.messaggio(f"Errore: {ris}")
        elif ris[0]:
            self.messaggio(ok_msg)
        else:
            self.messaggio(f"Non riuscito: {ris[1]}")

    # --- Stato ---
    def carica_stato(self):
        self.pagine["stato"].carica(mt.info_completa, self.disegna_stato)

    def disegna_stato(self, d):
        pag = self.pagine["stato"]
        if not d["root"]:
            s = Scheda()
            s.add_widget(Testo(
                "[color=ff5555]Root non disponibile.[/color]\nApri Magisk, vai in Superuser e "
                "consenti l'accesso a Magisk Manager, poi tocca Riprova."))
            s.add_widget(bottone("Riprova", self.carica_stato))
            pag.aggiungi(s)
            return

        def r(k, v):
            return f"[b]{k}[/b]  {esc(str(v))}"
        s = Scheda()
        s.add_widget(Testo("\n".join([
            r("Magisk", f"{d['versione'] or 'non rilevato'} (codice {d['codice']})"),
            r("Percorso", d["path"]),
            r("Zygisk", "attivo" if d["zygisk"] else "disattivo"),
            r("DenyList", "applicata" if d["denylist"] else "non applicata"),
            r("App Magisk", ", ".join(d["app"]) or "non trovata"),
            r("Dispositivo", d["dispositivo"]),
            r("Android", d["android"]),
            r("Architettura", d["abi"]),
            r("Moduli installati", "?" if d["n_moduli"] is None else d["n_moduli"]),
        ])))
        pag.aggiungi(s)
        pag.aggiungi(Testo("L'aggiornamento di Magisk stesso si fa dall'app Magisk.",
                           colore=(0.6, 0.75, 0.65, 1), dimensione=13))
        pag.aggiungi(bottone("Aggiorna", self.carica_stato))

    # --- Moduli ---
    def carica_moduli(self):
        self.pagine["moduli"].carica(self._leggi_moduli_o_errore, self.disegna_moduli)

    @staticmethod
    def _leggi_moduli_o_errore():
        if not mt.root_ok():
            raise RuntimeError("root non disponibile (consenti Magisk Manager in Superuser)")
        mods = mt.leggi_moduli()
        if mods is None:
            raise RuntimeError("lettura dei moduli non riuscita")
        return mods

    def disegna_moduli(self, mods):
        pag = self.pagine["moduli"]
        if not mods:
            pag.aggiungi(Testo("Nessun modulo installato."))
        for m in mods:
            testo_stato, colore = mt.stato_testo(m)
            s = Scheda()
            s.add_widget(Testo(
                f"[b]{esc(m['name'])}[/b]  {esc(m['version'])}\n"
                f"[color={colore}]{testo_stato}[/color]\n"
                f"[size=13sp]{esc(m['description'] or '-')}[/size]"))
            az1 = "abilita" if m["disabled"] else "disabilita"
            az2 = "annulla_rimozione" if m["remove"] else "rimuovi"
            s.add_widget(riga_bottoni(
                bottone("Abilita" if m["disabled"] else "Disabilita",
                        lambda i=m["id"], a=az1: self.azione_modulo(i, a), BTN_GRIGIO),
                bottone("Annulla rimozione" if m["remove"] else "Rimuovi",
                        lambda i=m["id"], a=az2: self.azione_modulo(i, a), BTN_ROSSO)))
            pag.aggiungi(s)
        pag.aggiungi(Testo("Le modifiche hanno effetto al riavvio.",
                           colore=(0.6, 0.75, 0.65, 1), dimensione=13))
        pag.aggiungi(bottone("Riavvia il dispositivo", self.chiedi_riavvio, BTN_ROSSO))

    def azione_modulo(self, mid, azione):
        def finito(ris):
            self._esito(ris, "Fatto. Riavvia per applicare.")
            self.carica_moduli()
        in_background(lambda: mt.modifica_modulo(mid, azione), finito)

    def chiedi_riavvio(self):
        conferma("Riavvio", "Riavviare il dispositivo adesso?",
                 lambda: in_background(mt.riavvia, lambda _: None), "Riavvia")

    # --- Aggiornamenti ---
    def carica_aggiorna(self):
        pag = self.pagine["aggiorna"]
        pag.token += 1
        pag.svuota()
        s = Scheda()
        s.add_widget(Testo(
            "Controlla online se i moduli installati hanno una versione piu recente "
            "(updateJson del modulo oppure GitHub per quelli del catalogo).\n"
            "Per GitHub il confronto e indicativo."))
        s.add_widget(bottone("Controlla ora", self.controlla_tutti))
        pag.aggiungi(s)

    def controlla_tutti(self):
        self.pagine["aggiorna"].carica(self._check_tutti, self.disegna_aggiornamenti)

    @staticmethod
    def _check_tutti():
        mods = MagiskApp._leggi_moduli_o_errore()
        cat = mt.catalogo_completo()
        return [(m, mt.controlla_modulo(m, cat)) for m in mods]

    def disegna_aggiornamenti(self, coppie):
        pag = self.pagine["aggiorna"]
        if not coppie:
            pag.aggiungi(Testo("Nessun modulo da controllare."))
        esiti = {"ok": ("aggiornato", "44ff77"), "agg": ("AGGIORNAMENTO DISPONIBILE", "ffd34d"),
                 "nd": ("da verificare a mano", "9aa89d"), "err": ("errore", "ff5555")}
        for m, r in coppie:
            etichetta, colore = esiti[r["stato"]]
            s = Scheda()
            s.add_widget(Testo(
                f"[b]{esc(m['name'])}[/b]\nInstallata: {esc(m['version'])}   "
                f"Disponibile: {esc(r['remoto'])}  ({esc(r['fonte'])})\n"
                f"[color={colore}]{etichetta}[/color]"))
            if r["stato"] == "agg" and r["url"]:
                s.add_widget(bottone(
                    "Aggiorna", lambda mm=m, rr=r: self.chiedi_aggiornamento(mm, rr)))
            pag.aggiungi(s)
        pag.aggiungi(bottone("Ricontrolla", self.controlla_tutti, BTN_GRIGIO))

    def chiedi_aggiornamento(self, m, r):
        conferma("Aggiorna modulo",
                 f"Scarico e installo {m['name']} {r['remoto']}?\nFonte: {r['fonte']}",
                 lambda: flusso_download(f"Aggiorna {m['name']}", r["url"],
                                         r["url"].rsplit("/", 1)[-1] or m["id"], "zip"))

    # --- Installa ---
    def carica_installa(self):
        self.pagine["installa"].carica(mt.leggi_moduli, self.disegna_installa)

    def disegna_installa(self, mods):
        pag = self.pagine["installa"]
        presenti = {m["id"] for m in (mods or [])}
        nomi = {m["name"].lower() for m in (mods or [])}
        for v in mt.catalogo_completo():
            installato = bool(set(v.get("ids", [])) & presenti) or v["nome"].lower() in nomi
            s = Scheda()
            s.add_widget(Testo(
                f"[b]{esc(v['nome'])}[/b]  [size=12sp]{esc(v.get('categoria', '-'))}"
                f"{'  - GIA INSTALLATO' if installato else ''}[/size]\n"
                f"{esc(v.get('desc', '-'))}\n"
                f"[color=9aa89d]Requisiti:[/color] {esc(v.get('req', '-'))}\n"
                f"[color=ffd34d]Attenzione:[/color] {esc(v.get('avviso', '-'))}",
                dimensione=14))
            s.add_widget(bottone("Cerca e installa", lambda vv=v: self.avvia_voce(vv)))
            pag.aggiungi(s)

        z = Scheda()
        z.add_widget(Testo("[b]Installa da file ZIP[/b]\nScrivi il percorso del file."))
        self.campo_zip = campo("/sdcard/Download/modulo.zip")
        z.add_widget(self.campo_zip)
        z.add_widget(bottone("Installa ZIP", self.installa_zip_locale))
        pag.aggiungi(z)

        a = Scheda()
        a.add_widget(Testo("[b]Aggiungi un repo GitHub al catalogo[/b]"))
        self.campo_repo = campo("proprietario/nome")
        self.campo_desc = campo("Cosa fa (breve)")
        a.add_widget(self.campo_repo)
        a.add_widget(self.campo_desc)
        a.add_widget(bottone("Aggiungi", self.aggiungi_repo, BTN_GRIGIO))
        pag.aggiungi(a)

    def avvia_voce(self, v):
        self.messaggio(f"Cerco {v['nome']} su GitHub...")

        def finito(rel):
            self.messaggio("")
            if isinstance(rel, Exception):
                self.messaggio(f"Errore di rete/GitHub: {rel}")
            elif not rel:
                self.messaggio("Nessun file corrispondente nelle release: il progetto potrebbe "
                               "aver cambiato i nomi dei file.")
            else:
                mb = rel["size"] / 1048576
                note = rel["note"][:400] + ("..." if len(rel["note"]) > 400 else "")
                conferma(v["nome"],
                         f"Versione: {rel['tag']}\nFile: {rel['nome_file']} ({mb:.1f} MB)\n\n"
                         f"{note}\n\nScarico e installo?",
                         lambda: flusso_download(f"Installa {v['nome']}", rel["url"],
                                                 rel["nome_file"], "zip"))
        in_background(lambda: mt.github_release(v["repo"], v["pattern"]), finito)

    def installa_zip_locale(self):
        percorso = self.campo_zip.text.strip()
        if not percorso.lower().endswith(".zip"):
            self.messaggio("Scrivi il percorso completo di un file .zip")
            return
        conferma("Installa ZIP", f"Installo questo file?\n{percorso}",
                 lambda: flusso_zip_locale(percorso))

    def aggiungi_repo(self):
        ok, msg = mt.aggiungi_voce_catalogo(self.campo_repo.text, self.campo_desc.text.strip())
        self.messaggio(msg)
        if ok:
            self.carica_installa()

    # --- Integrità (SafetyNet / Play Integrity) ---
    def carica_integrita(self):
        self.pagine["integrita"].carica(self._dati_integrita, self.disegna_integrita)

    @staticmethod
    def _dati_integrita():
        if not mt.root_ok():
            return {"root": False}
        return {"root": True, "controlli": mt.controlli_locali(),
                "moduli": mt.moduli_integrita(mt.leggi_moduli()),
                "checker": mt.trova_checker()}

    def disegna_integrita(self, d):
        pag = self.pagine["integrita"]
        if not d["root"]:
            pag.aggiungi(Testo("[color=ff5555]Root non disponibile.[/color]"))
            pag.aggiungi(bottone("Riprova", self.carica_integrita))
            return
        righe = []
        for nome, val, ok in d["controlli"]:
            if ok is None:
                esito = "[color=9aa89d]info[/color]"
            elif ok:
                esito = "[color=44ff77]OK[/color]"
            else:
                esito = "[color=ffd34d]da vedere[/color]"
            righe.append(f"[b]{esc(nome)}[/b]  {esc(val)}  {esito}")
        s = Scheda()
        s.add_widget(Testo("\n".join(righe)))
        s.add_widget(Testo("[b]Moduli che influiscono:[/b] " +
                           (esc(", ".join(d["moduli"])) if d["moduli"] else "nessuno")))
        pag.aggiungi(s)
        n = Scheda()
        n.add_widget(Testo(
            "[color=ffd34d]Importante[/color]\n"
            "- SafetyNet e stato dismesso da Google: oggi vale solo Play Integrity.\n"
            "- Il verdetto vero (Basic / Device / Strong) lo firma Google e si ottiene solo da "
            "un'app con Play Services: questa app NON puo calcolarlo.\n"
            "- I controlli sopra sono solo indizi: bootloader sbloccato o build non ufficiale "
            "di solito impediscono i verdetti Device/Strong.", dimensione=14))
        pag.aggiungi(n)
        c = Scheda()
        c.add_widget(Testo("[b]App checker:[/b] " +
                           (esc(d["checker"]) if d["checker"] else "non installata")))
        c.add_widget(bottone("Scarica e installa Play Integrity Checker",
                             self.scarica_checker))
        c.add_widget(bottone("Avvia app checker", self.avvia_checker, BTN_GRIGIO))
        pag.aggiungi(c)
        pag.aggiungi(bottone("Ricontrolla", self.carica_integrita, BTN_GRIGIO))

    def scarica_checker(self):
        self.messaggio("Cerco l'APK su GitHub...")

        def finito(rel):
            self.messaggio("")
            if isinstance(rel, Exception):
                self.messaggio(f"Errore di rete/GitHub: {rel}")
            elif not rel:
                self.messaggio("Nessun APK nelle release: cerca 'Play Integrity API Checker' "
                               "sul Play Store.")
            else:
                conferma("Play Integrity Checker",
                         f"Versione: {rel['tag']}\nFile: {rel['nome_file']} "
                         f"({rel['size'] / 1048576:.1f} MB)\nFonte: github.com/{mt.CHECKER_REPO}"
                         "\n\nScarico e installo?",
                         lambda: flusso_download("Play Integrity Checker", rel["url"],
                                                 rel["nome_file"], "apk", self._avvia_dopo))
        in_background(lambda: mt.github_release(mt.CHECKER_REPO, r"\.apk$"), finito)

    @staticmethod
    def _avvia_dopo(op):
        ok, msg = mt.avvia_checker()
        op.scrivi(msg)

    def avvia_checker(self):
        in_background(mt.avvia_checker, lambda ris: self._esito(ris, ris[1] if not isinstance(
            ris, Exception) else ""))


if __name__ == "__main__":
    MagiskApp().run()
