"""Cosa vede l'utente: testi della top, giudizio sul prezzo, messaggi Telegram,
barra di avanzamento e conto alla rovescia.
"""

import html
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import date, datetime, timedelta

from lingua import t
from ricerca import (
    LIMITE_RICERCA_GIORNI, citta_ar, etichetta, fuori_periodo, limite, migliore, nomi,
    proposte_verificate,
)
import lingua


# Colore delle risposte dell'utente: verde (ANSI a 256 colori), solo sul terminale.
# NO_COLOR (https://no-color.org) lo disattiva.
COLORE_RISPOSTE = "\033[38;5;77m"
RESET = "\033[0m"


def leggi(domanda):
    """input() con la risposta dell'utente colorata, se l'output e' un terminale."""
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return input(domanda)
    try:
        return input(domanda + COLORE_RISPOSTE)
    finally:
        # anche con Ctrl+C o fine input: il resto del terminale non deve restare colorato
        print(RESET, end="", flush=True)


def testo_scali(n):
    if n is None:
        return t("scali_qualsiasi")
    return t("scali_0") if n == 0 else t("scali_1") if n == 1 else t("scali_n", n=n)


def descrivi_prezzo(v):
    """Es. "656 EUR su lastminute.com (674 EUR in lista, andata 15:10, ritorno 17:55)"."""
    ven = v.get("venditore") or {}
    if ven.get("prezzo") and ven["prezzo"] < v["prezzo"]:
        return t("prezzo_venditore", prezzo=ven["prezzo"], nome=ven["nome"], lista=v["prezzo"], orari=orari(ven))
    return soldi(v["prezzo"])


def soldi(prezzo):
    return f"{prezzo} {lingua.VALUTA}"


def orari(ven):
    """Orari dei voli del venditore. I dati salvati prima del supporto alle lingue hanno
    solo il testo gia' pronto in "orari"."""
    if "ora_andata" in ven:
        return t("orari", andata=ven["ora_andata"], ritorno=ven["ora_ritorno"])
    return ven.get("orari", "")


def giudizio(v):
    """Etichetta del prezzo rispetto alla fascia tipica Google, o "" se non disponibile."""
    if not v.get("fascia"):
        return ""
    basso, alto = v["fascia"]
    p = migliore(v)
    if p < basso:
        etichetta = t("giudizio_basso")
    elif p > alto:
        etichetta = t("giudizio_alto")
    elif p <= basso + (alto - basso) / 3:
        etichetta = t("giudizio_media_bassa")
    elif p >= alto - (alto - basso) / 3:
        etichetta = t("giudizio_media_alta")
    else:
        etichetta = t("giudizio_media")
    diff = round((p - v["tipico"]) / v["tipico"] * 100)
    testo = t("giudizio", etichetta=etichetta, diff=diff, tipico=v["tipico"], basso=basso, alto=alto)
    if "min_60gg" in v:
        testo += t("minimo_60", prezzo=v["min_60gg"])
    return testo


def bandiera(paese):
    """Emoji della bandiera da un codice paese di 2 lettere (es. "FR" -> 🇫🇷)."""
    paese = paese.upper()
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in paese) if len(paese) == 2 and paese.isascii() and paese.isalpha() else ""


def testo_posizione(pos):
    if not pos:
        return t("posizione_ignota")
    return t("posizione", bandiera=bandiera(pos["paese"]), paese=pos["paese"],
             citta=f", {pos['citta']}" if pos["citta"] else "", ip=pos["ip"])


def breve_posizione(pos):
    return f"{bandiera(pos['paese'])} {pos['paese']} (IP {pos['ip']})"


def notifica(titolo, testo):
    if sys.platform == "darwin":
        # ensure_ascii=False: AppleScript non capisce gli escape \uXXXX (accenti, frecce).
        script = (f"display notification {json.dumps(testo, ensure_ascii=False)} "
                  f"with title {json.dumps(titolo, ensure_ascii=False)}")
        subprocess.run(["osascript", "-e", script], check=False)


def testo_obiettivo(p, top):
    """Riga del prezzo obiettivo ("" se non impostato): quanto manca, o raggiunto."""
    obiettivo = p.get("avvisa_sotto")
    if not obiettivo:
        return ""
    if not top:
        return t("obiettivo_riga_senza_prezzo", obiettivo=obiettivo)
    prezzo = top[0]["prezzo"]
    if prezzo <= obiettivo:
        return t("obiettivo_riga_raggiunto", obiettivo=obiettivo, prezzo=prezzo)
    return t("obiettivo_riga", obiettivo=obiettivo, prezzo=prezzo, mancano=prezzo - obiettivo)


def testo_copertura(cop):
    """Copertura della scansione su una riga, per terminale e top.txt."""
    testo = (t("copertura", stimate=cop["stimate"], verificate=cop["verificate"], totale=cop["totale"])
             + t("scansione_completa" if cop["verificate"] == cop["totale"] else "scansione_in_corso"))
    if cop["verificate"] < cop["totale"]:
        if cop["migliori"]:
            testo += t("copertura_migliori", n=cop["migliori"])
        testo += t("copertura_altre", n=cop["totale"] - cop["verificate"], budget=cop["budget"])
    if cop["future"]:
        testo += t("copertura_future", n=cop["future"], limite=f"{limite(LIMITE_RICERCA_GIORNI):%d/%m/%Y}")
    return testo


def intestazione_telegram(p, titolo, cop, top=None):
    """Titolo, riassunto dei parametri e copertura della scansione, in HTML per Telegram."""
    e = html.escape
    giorno = lambda s: f"{date.fromisoformat(s):%d/%m/%Y}"
    righe = [
        titolo,
        "",
        f"🛫 {e(etichetta(p['andata']['da']))} → {e(etichetta(p['andata']['a']))}",
        f"🛬 {e(etichetta(p['ritorno']['da']))} → {e(etichetta(p['ritorno']['a']))}",
        t("tg_partenza", inizio=giorno(p["inizio"]), fine=giorno(p["fine"])),
        t("tg_durata_weekend" if p.get("weekend") else "tg_durata",
          min=p["giorni_min"] + (1 if p.get("weekend") else 0), max=p["giorni_max"] + (1 if p.get("weekend") else 0),
          scali=testo_scali(p["max_scali"]), frequenza=p["frequenza_minuti"]),
    ]
    # Solo il paese: l'IP non va mandato a tutti gli iscritti del bot.
    if cop.get("paese_prima"):
        righe.append(t("tg_posizione_cambiata", prima=f"{bandiera(cop['paese_prima'])} {cop['paese_prima']}",
                       ora=f"{bandiera(cop['paese'])} {cop['paese']}"))
    elif cop.get("paese"):
        righe.append(t("tg_posizione", bandiera=bandiera(cop["paese"]), paese=cop["paese"]))
    if testo_obiettivo(p, top):
        righe.append(testo_obiettivo(p, top))
    righe.append("")
    if cop["verificate"] == cop["totale"]:
        righe.append(t("tg_completa", verificate=cop["verificate"], totale=cop["totale"]))
    else:
        righe.append(t("tg_in_corso", verificate=cop["verificate"], stimate=cop["stimate"], totale=cop["totale"]))
        if cop["migliori"]:
            righe.append(t("tg_migliori", n=cop["migliori"]))
        righe.append(t("tg_altre", n=cop["totale"] - cop["verificate"], budget=cop["budget"]))
    if cop["future"]:
        righe.append(t("tg_future", n=cop["future"], limite=f"{limite(LIMITE_RICERCA_GIORNI):%d/%m/%Y}"))
    return "\n".join(righe)


def suggerimento(p, largo, prezzi, chiavi_fuori, top):
    """Righe "💡 ..." se una partenza fuori dal periodo, verificata in questo giro, costa meno della top."""
    if not chiavi_fuori:
        return []
    x = next((x for x in proposte_verificate(largo, prezzi)
              if fuori_periodo(p, x) and set(x["chiavi"]) <= set(chiavi_fuori)), None)
    if not x or (top and x["prezzo"] >= top[0]["prezzo"]):
        return []
    risparmio = t("risparmi", n=top[0]["prezzo"] - x["prezzo"]) if top else t("ci_sono_voli")
    giorno = date.fromisoformat(x["andata"])
    return [t("suggerimento", giorno=f"{giorno:%d/%m}", risparmio=risparmio, testo=riassunto(x)),
            *(f"   {prezzi[k]['link']}" for k in x["chiavi"])]


def nome_tratta(p):
    andata = f"{nomi(p['andata']['da'])} -> {nomi(p['andata']['a'])}"
    if p["tipo"] == "stessa":
        return andata
    return t("tratta_ritorno", andata=andata, da=nomi(p["ritorno"]["da"]), a=nomi(p["ritorno"]["a"]))


def testo_durata(p):
    """Durata del viaggio nei testi. In modalita' weekend in giorni di calendario."""
    if p.get("weekend"):
        return t("durata_weekend", min=p["giorni_min"] + 1, max=p["giorni_max"] + 1)
    return t("durata_libera", min=p["giorni_min"], max=p["giorni_max"])


def durata_viaggio(x):
    """"(12 gg)", oppure in modalita' weekend "(3 gg, ven → dom)" con i giorni di calendario."""
    if not x.get("weekend"):
        return t("durata_gg", n=_gg(x))
    giorni = t("giorni_settimana").split()
    andata, ritorno = date.fromisoformat(x["andata"]), date.fromisoformat(x["ritorno"])
    return t("durata_gg_weekend", n=_gg(x) + 1, da=giorni[andata.weekday()], a=giorni[ritorno.weekday()])


def _gg(x):
    return (date.fromisoformat(x["ritorno"]) - date.fromisoformat(x["andata"])).days


def riassunto(x):
    """Una riga: "701 EUR 2 biglietti, andata Tokyo / ritorno da Osaka, 2027-03-08 -> 2027-03-22"."""
    tipo = f"{t('ar')} {x['va']}" if x["tipo"] == "ar" else t("riassunto_2b", va=x["va"], torna=x["torna"])
    return f"{soldi(x['prezzo'])} {tipo}, {x['andata']} -> {x['ritorno']} {durata_viaggio(x)}"


def dettaglio(x, prezzi):
    """Proposta per terminale e top.txt."""
    if x["tipo"] == "ar":
        v = prezzi[x["chiavi"][0]]
        return (
            f"{descrivi_prezzo(v)}  {t('ar')} {x['va']}  {x['andata']} -> {x['ritorno']} {durata_viaggio(x)}  "
            f"{v['compagnie']}  [{v['tratte']}]  {t('visto', quando=v['controllato'])}\n"
            + (t("prezzo_giudizio", giudizio=giudizio(v)) + "\n" if giudizio(v) else "")
            + f"   {v['link']}"
        )
    va, torna = (prezzi[k] for k in x["chiavi"])
    righe = [t("dettaglio_2b", prezzo=x["prezzo"], va=x["va"], torna=x["torna"])
             + f"  {x['andata']} -> {x['ritorno']} {durata_viaggio(x)}"]
    larghezza = max(len(t("lato_andata")), len(t("lato_ritorno")))
    for nome, v in ((t("lato_andata"), va), (t("lato_ritorno"), torna)):
        righe.append(f"   {nome:<{larghezza}} {soldi(v['prezzo'])}  {v['compagnie']}  [{v['tratte']}]  "
                     f"{t('visto', quando=v['controllato'])}"
                     + (f"  ({giudizio(v).split(':')[0]})" if giudizio(v) else ""))
    righe.append(f"   ⚠ {t('biglietti_separati')}")
    righe += [f"   {va['link']}", f"   {torna['link']}"]
    return "\n".join(righe)


def confronto_varianti(p, verificate, stimate):
    """Miglior prezzo per ogni combinazione di citta' (arrivo andata, partenza ritorno)."""
    righe = []
    for x in p["andata"]["a"]:
        for y in p["ritorno"]["da"]:
            if p["tipo"] == "stessa" and x["nome"] != y["nome"]:
                continue
            celle = []
            for tipo, nome in (("ar", t("ar")), ("2b", t("due_biglietti"))):
                if tipo == "ar" and not (x["nome"] == y["nome"] and x in citta_ar(p)):
                    continue
                trova = lambda elenco: next((z for z in elenco if z["tipo"] == tipo and z["va"] == x["nome"]
                                             and z["torna"] == y["nome"]), None)
                v, st = trova(verificate), trova(stimate) if stimate else None
                celle.append((v["prezzo"] if v else None, f"{nome} " + (
                    soldi(v["prezzo"]) if v else t("stima", prezzo=st["prezzo"]) if st else t("non_disponibile"))))
            righe.append((min((c[0] for c in celle if c[0]), default=None),
                          t("confronto_riga", va=x["nome"], torna=y["nome"]) + " · ".join(c[1] for c in celle)))
    if len(righe) == 1 and len(righe[0][1].split(" · ")) == 1:
        return []  # una sola variante: niente da confrontare
    migliore_v = min((r[0] for r in righe if r[0]), default=None)
    return [t("confronto_titolo")] + [
        testo + (t("migliore") if prezzo and prezzo == migliore_v else "") for prezzo, testo in righe
    ]


def messaggio_telegram(p, top, prezzi, cop, confronto, titolo=None):
    """Top N in HTML per Telegram, con link cliccabili a Google Flights."""
    e = html.escape
    gm = lambda s: f"{date.fromisoformat(s):%d/%m}"
    righe = [intestazione_telegram(p, titolo or t("tg_nuovo_minimo"), cop, top), "", f"🏆 <b>Top {len(top)}</b>"]
    for i, x in enumerate(top, 1):
        date_txt = f"   📆 {gm(x['andata'])} → {gm(x['ritorno'])} {durata_viaggio(x)}"
        if x["tipo"] == "ar":
            v = prezzi[x["chiavi"][0]]
            blocco = [f"{i}. <b>{soldi(x['prezzo'])}</b> · {t('ar')} {e(x['va'])}", date_txt]
            if x["prezzo"] < v["prezzo"]:
                blocco.append(t("tg_venditore", nome=e(v["venditore"]["nome"]), lista=v["prezzo"],
                                orari=e(orari(v["venditore"]))))
            blocco.append(f"   🛩 {e(v['compagnie'])} [{e(v['tratte'])}]")
            if giudizio(v):
                blocco.append(f"   📊 <i>{e(giudizio(v))}</i>")
            blocco.append(f"   🔗 <a href=\"{e(v['link'])}\">{t('tg_apri_google')}</a>")
        else:
            va, torna = (prezzi[k] for k in x["chiavi"])
            blocco = [f"{i}. <b>{soldi(x['prezzo'])}</b> · " + t("riassunto_2b", va=e(x["va"]), torna=e(x["torna"])),
                      date_txt]
            for nome, v in ((t("lato_andata"), va), (t("lato_ritorno"), torna)):
                blocco.append(f"   🛩 {nome} {soldi(v['prezzo'])} {e(v['compagnie'])} [{e(v['tratte'])}] "
                              f"<a href=\"{e(v['link'])}\">{t('tg_apri')}</a>")
            blocco.append(f"   ⚠️ {t('biglietti_separati')}")
        righe += ["", *blocco]
    if confronto:
        testo = e("\n".join(confronto)).replace(e(t("confronto_titolo")), t("tg_confronto"))
        righe += ["", testo]
    return "\n".join(righe)


class Barra:
    """Barra di avanzamento su una riga: fatte/totali, %, tempo stimato e una rotellina
    che gira anche durante una richiesta lenta (cosi' si vede che sta lavorando).
    Niente se l'output va su file."""

    ROTELLA = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, titolo, totale):
        self.titolo, self.totale, self.fatte, self.info = titolo, totale, 0, ""
        self.attiva = sys.stdout.isatty() and totale > 0
        self.inizio = time.monotonic()
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def __enter__(self):
        if self.attiva:
            self._thread = threading.Thread(target=self._gira, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, *exc):
        if self.attiva:
            self._stop.set()
            self._thread.join()
            with self._lock:
                self._disegna(finale=True)
                print()
        return False

    def avanza(self, info=None):
        with self._lock:
            self.fatte += 1
            if info is not None:
                self.info = info

    def scrivi(self, testo):
        """Stampa una riga permanente sopra la barra."""
        with self._lock:
            if self.attiva:
                print("\r\033[K", end="")
            print(testo)

    def _gira(self):
        i = 0
        while not self._stop.wait(0.15):
            with self._lock:
                self._disegna(self.ROTELLA[i % len(self.ROTELLA)])
            i += 1

    def _disegna(self, rotella="✓", finale=False):
        trascorso = time.monotonic() - self.inizio
        if finale:
            tempo = f"in {_durata(trascorso)}"
        elif self.fatte:
            tempo = t("barra_rimasti", tempo=_durata(trascorso / self.fatte * (self.totale - self.fatte)))
        else:
            tempo = t("barra_stima")
        info = f" · {self.info}" if self.info else ""
        prima = f"{rotella} {self.titolo:<10} ["
        dopo = f"] {self.fatte}/{self.totale} {100 * self.fatte // self.totale:3d}% · {tempo}{info}"
        # Mai piu' larga del terminale: se va a capo, \r torna solo all'ultima riga
        # e la barra si ripete invece di aggiornarsi. Si accorcia prima la barra.
        colonne = shutil.get_terminal_size().columns - 1
        larghezza = max(5, min(24, colonne - len(prima) - len(dopo)))
        pieni = larghezza * self.fatte // self.totale
        riga = prima + "█" * pieni + "░" * (larghezza - pieni) + dopo
        print(f"\r\033[K{riga[:colonne]}", end="", flush=True)


def _durata(secondi):
    m, s = divmod(int(secondi), 60)
    return f"{m} min {s:02d} s" if m else f"{s} s"


def conto_alla_rovescia(secondi):
    """Aspetta mostrando il tempo mancante su una riga che si aggiorna."""
    fine = time.monotonic() + secondi
    prossimo = datetime.now() + timedelta(seconds=secondi)
    if not sys.stdout.isatty():  # output su file: niente timer, solo l'orario
        print(t("prossimo_alle", ora=f"{prossimo:%H:%M}"))
        time.sleep(secondi)
        return
    print()
    while (resto := fine - time.monotonic()) > 0:
        m, s = divmod(int(resto + 0.999), 60)
        h, m = divmod(m, 60)
        timer = f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        print(t("prossimo_tra", timer=timer, ora=f"{prossimo:%H:%M}"), end="", flush=True)
        time.sleep(min(1, resto))
    print("\r\033[K", end="", flush=True)
