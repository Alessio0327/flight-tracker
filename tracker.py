"""Monitor prezzi voli andata/ritorno su Google Flights.

All'avvio chiede il tipo di viaggio (ritorno dalla stessa citta' o da un'altra), le
citta' di andata e ritorno (1 o 2 per lato, risolte in aeroporti), periodo di partenza,
durata, top N e frequenza, poi ripete la ricerca ogni N minuti finche' non lo fermi
(Ctrl+C). Confronta l'andata e ritorno sullo stesso biglietto con due biglietti di sola
andata, per ogni combinazione di citta'.

Ogni giro:
  1. stima dal calendario prezzi di Google tutte le coppie (andata, ritorno) e tutte
     le sole andate (una richiesta per coppia di aeroporti, e per durata se A/R);
  2. verifica con la ricerca completa la top attuale e le stime piu' basse (ogni
     ricerca copre tutti gli aeroporti scelti insieme);
  3. per la top, apre le pagine di prenotazione e prende il venditore piu' economico
     (le agenzie spesso costano meno del prezzo in lista);
  4. scrive la top N in top.txt e notifica (macOS/Telegram) se il prezzo minimo scende.

Piu' istanze possono girare insieme, ognuna in un terminale: ogni combinazione di
parametri ha la sua cartella. Rilanciare con gli stessi parametri riprende i dati salvati.

I parametri si possono anche leggere da un file JSON (vedi ricerche/esempio.json):
all'avvio il tool chiede se rispondere alle domande o indicare il file.

Uso: .venv/bin/python tracker.py
     .venv/bin/python tracker.py --setup-telegram   (attiva notifiche Telegram)
"""

import calendar
import csv
import fcntl
import html
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path

from base64 import b64encode

from fast_flights import FlightQuery, Passengers, create_query
from fast_flights.pb.flights_pb2 import Airport
from primp import Client
from selectolax.lexbor import LexborHTMLParser

import telegram_bot
from fli.models import (
    Airport as FliAirport, FlightSearchFilters, FlightSegment, MaxStops, PassengerInfo,
    SeatType, SortBy, TripType,
)
from fli.search import SearchFlights

from luoghi import Luoghi

BASE = Path(__file__).resolve().parent
URL = "https://www.google.com/travel/flights"
# Senza questi cookie Google (da IP europeo) risponde con la pagina di consenso.
CONSENT_COOKIE = "SOCS=CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg; CONSENT=YES+"
PAUSA_SECONDI = 3
RICERCHE_MAX_PER_GIRO = 100  # a ritmo normale; dimezzato a ogni rallentamento
VERIFICA_DA_STIMA = 15  # combinazioni piu' economiche del calendario da verificare ogni giro
CALENDARIO_URL = (
    "https://www.google.com/_/FlightsFrontendUi/data/"
    "travel.frontend.flights.FlightsFrontendService/GetCalendarGraph"
)
MAX_GIORNI_CALENDARIO = 61
# Limiti di Google Flights, misurati: la ricerca completa accetta voli fino a oggi + 330
# giorni (conta l'ultimo volo, cioe' il ritorno), il calendario prezzi fino a oggi + 305.
LIMITE_RICERCA_GIORNI = 330
LIMITE_CALENDARIO_GIORNI = 305
ITINERARI_VENDITORI = 4  # itinerari (orari) di cui aprire la pagina di prenotazione, per combinazione
PAUSA_CALENDARIO = 1
GIORNI_FUORI_PERIODO = 7  # giorni prima/dopo il periodo in cui cercare date piu' economiche


# --- input utente -----------------------------------------------------------

def chiedi(domanda, converti):
    """Ripete la domanda finche' converti(risposta) non va a buon fine."""
    while True:
        try:
            return converti(input(domanda).strip())
        except ValueError as e:
            print(f"  {e}")


def scegli_luogo(luoghi, testo):
    """Un nome di citta' (o codice IATA) -> {"nome", "aeroporti"}, o None."""
    codice = testo.upper()
    if codice in luoghi.per_aeroporto and codice not in luoghi.aeroporti:
        citta, nome = luoghi.per_aeroporto[codice]
        return {"nome": nome, "aeroporti": [codice]}

    trovate = luoghi.cerca(testo)[:8]
    if not trovate:
        print(f"  nessuna citta' trovata per '{testo}'")
        return None
    citta = trovate[0]
    if len(trovate) > 1:
        for i, c in enumerate(trovate, 1):
            elenco = ", ".join(f"{a} {n}" for a, n in luoghi.aeroporti[c["code"]])
            print(f"  [{i}] {luoghi.nome_citta(c)}, {c['country_code']}  ({elenco})")
        n = chiedi(f"  Quale '{testo}'? (Invio = 1): ", indici(len(trovate), default=[1]))
        citta = trovate[n[0] - 1]

    aeroporti = luoghi.aeroporti[citta["code"]]
    if len(aeroporti) > 1:
        for i, (a, n) in enumerate(aeroporti, 1):
            print(f"  [{i}] {a} {n}")
        scelti = chiedi("  Aeroporti (Invio = tutti, oppure es. 1,2): ", indici(len(aeroporti)))
        aeroporti = [aeroporti[i - 1] for i in scelti] if scelti else aeroporti
    return {"nome": luoghi.nome_citta(citta), "aeroporti": [a for a, _ in aeroporti]}


def chiedi_citta(luoghi, ruolo, default=None):
    """Una o due citta' (con i loro aeroporti) per un ruolo, es. "partenza dell'andata".

    Con default, Invio alla prima domanda riusa quelle citta'.
    """
    suggerimento = f" (Invio = {etichetta(default)})" if default else " (Invio = 1)"
    n = chiedi(f"Quante citta' di {ruolo}? [1/2]{suggerimento}: ", scelta("", "1", "2"))
    if not n and default:
        return default
    elenco = []
    for i in range(1, int(n or "1") + 1):
        while not (c := scegli_luogo(luoghi, input(f"  Citta' di {ruolo}{f' {i}' if n == '2' else ''}: ").strip())):
            pass
        elenco.append(c)
    return elenco


def aeroporti(citta):
    return list(dict.fromkeys(a for c in citta for a in c["aeroporti"]))


def etichetta(citta):
    return " / ".join(f"{c['nome']} ({', '.join(c['aeroporti'])})" for c in citta)


def nomi(citta):
    return "/".join(c["nome"] for c in citta)


def citta_ar(p):
    """Citta' per cui ha senso l'andata e ritorno sullo stesso biglietto.

    Sono quelle di arrivo dell'andata da cui si puo' anche ripartire, se il ritorno
    arriva dove e' partita l'andata. Lista vuota = solo biglietti di sola andata.
    """
    if aeroporti(p["ritorno"]["a"]) != aeroporti(p["andata"]["da"]):
        return []
    return [c for c in p["andata"]["a"] if c in p["ritorno"]["da"]]


def indici(massimo, default=None):
    """Numeri separati da virgola tra 1 e massimo; risposta vuota -> default."""
    def conv(s):
        if not s:
            return default or []
        try:
            n = [int(x) for x in s.split(",")]
        except ValueError:
            n = [0]
        if not all(1 <= x <= massimo for x in n):
            raise ValueError(f"numeri tra 1 e {massimo}, separati da virgola")
        return n
    return conv


def mese(s):
    m = re.fullmatch(r"(\d{4})-(\d{1,2})|(\d{1,2})/(\d{4}|\d{2})", s)
    if not m:
        raise ValueError("formato: 10/2027, 10/27 oppure 2027-10")
    anno, num = (m[1], m[2]) if m[1] else (m[4], m[3])
    anno, num = int(anno), int(num)
    if anno < 100:  # anno a due cifre: 27 -> 2027
        anno += 2000
    if not 1 <= num <= 12:
        raise ValueError("mese non valido")
    return date(anno, num, 1), date(anno, num, calendar.monthrange(anno, num)[1])


def data(s):
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError("formato: 15/10/2027, 15/10/27 oppure 2027-10-15")


def intero(minimo):
    def conv(s):
        n = int(s) if s.isdigit() else None
        if n is None or n < minimo:
            raise ValueError(f"serve un numero intero >= {minimo}")
        return n
    return conv


def scali(s):
    if not s:
        return None
    return intero(0)(s)


def scelta(*valori):
    def conv(s):
        if s not in valori:
            raise ValueError(f"rispondi {' o '.join(v for v in valori if v)}")
        return s
    return conv


def chiedi_periodo():
    modo = chiedi("Periodo di partenza: [1] un mese  [2] intorno a una data: ", scelta("1", "2"))
    if modo == "1":
        inizio, fine = chiedi("Mese (es. 10/2027): ", mese)
    else:
        centro = chiedi("Data (es. 15/10/2027): ", data)
        delta = chiedi("Quanti giorni prima/dopo quella data: ", intero(0))
        inizio, fine = centro - timedelta(days=delta), centro + timedelta(days=delta)
    return max(inizio, date.today() + timedelta(days=1)), fine


def voli_in_vendita(client, org, dst, inizio, fine):
    """Date con almeno un volo di sola andata dal calendario: {data: prezzo minimo}."""
    trovate = {}
    da = inizio
    while da <= fine:
        a = min(fine, da + timedelta(days=MAX_GIORNI_CALENDARIO - 1))
        for o in org:
            for d in dst:
                for giorno, prezzo in calendario(client, o, d, da.isoformat(), a.isoformat(), None, None).items():
                    trovate[giorno] = min(prezzo, trovate.get(giorno, prezzo))
        da = a + timedelta(days=1)
    return trovate


def controlla_periodo(client, p, inizio, fine):
    """Verifica il periodo sul calendario. Ritorna "ok", "periodo" o "citta" (cosa richiedere)."""
    lim_ricerca, lim_cal = limite(LIMITE_RICERCA_GIORNI), limite(LIMITE_CALENDARIO_GIORNI)
    if fine < inizio:
        print("  Periodo gia' passato.")
        return "periodo"
    if inizio > lim_ricerca:
        print(
            f"  Google Flights cerca voli solo fino al {lim_ricerca:%d/%m/%Y}: partenze dal "
            f"{inizio:%d/%m/%Y} non sono ancora cercabili."
        )
        scelta_ = chiedi("  [1] cambia periodo  [2] monitora comunque, in attesa che entrino in vendita: ",
                         scelta("1", "2"))
        return "periodo" if scelta_ == "1" else "ok"
    if inizio > lim_cal:
        print(f"  Il calendario prezzi arriva al {lim_cal:%d/%m/%Y}: non posso verificare in anticipo, "
              "lo fara' la ricerca completa.")
        return "ok"
    fine_cal = min(fine, lim_cal)
    # Il ritorno parte dopo: si controlla un mese in piu' (la durata non e' ancora nota).
    lati = [("Andata", p["andata"], inizio, fine_cal)]
    if p["tipo"] == "diversa":
        lati.append(("Ritorno", p["ritorno"], inizio, min(fine + timedelta(days=30), lim_cal)))
    print("  Controllo i voli in vendita...")
    for nome, lato, da, a in lati:
        try:
            trovate = voli_in_vendita(client, aeroporti(lato["da"]), aeroporti(lato["a"]), da, a)
        except Exception as e:  # noqa: BLE001 - senza verifica si prosegue comunque
            print(f"  Verifica non riuscita ({e}), proseguo.")
            return "ok"
        if not trovate:
            print(f"  {nome}: nessun volo in vendita da {nomi(lato['da'])} a {nomi(lato['a'])} "
                  f"tra il {da:%d/%m/%Y} e il {a:%d/%m/%Y}.")
            scelta_ = chiedi("  Cambia [1] periodo  [2] citta': ", scelta("1", "2"))
            return "periodo" if scelta_ == "1" else "citta"
        print(f"  {nome}: voli in {len(trovate)} date su {(a - da).days + 1}, solo andata da {min(trovate.values())} EUR.")
    if fine > lim_cal:
        print(f"  Dopo il {lim_cal:%d/%m/%Y} il calendario non vede: quelle date le verifica la ricerca completa.")
    return "ok"


def _leggi_citta(valore, dove):
    if not isinstance(valore, list) or not 1 <= len(valore) <= 2:
        raise ValueError(f"{dove}: serve una lista di 1 o 2 citta'")
    out = []
    for c in valore:
        if (not isinstance(c, dict) or not isinstance(c.get("nome"), str)
                or not isinstance(c.get("aeroporti"), list) or not c["aeroporti"]):
            raise ValueError(f'{dove}: ogni citta\' e\' {{"nome": "Roma", "aeroporti": ["FCO"]}}')
        out.append({"nome": c["nome"], "aeroporti": [str(a).upper() for a in c["aeroporti"]]})
    return out


def parametri_da_file(percorso):
    """Parametri da un file JSON (formato in ricerche/esempio.json). ValueError se non valido."""
    try:
        f = json.loads(Path(percorso).expanduser().read_text())
    except OSError as e:
        raise ValueError(f"non riesco a leggere il file: {e.strerror}") from None
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON non valido (riga {e.lineno}): {e.msg}") from None
    try:
        andata = {"da": _leggi_citta(f["andata"]["da"], "andata.da"),
                  "a": _leggi_citta(f["andata"]["a"], "andata.a")}
        if f.get("ritorno"):
            ritorno = {"da": _leggi_citta(f["ritorno"]["da"], "ritorno.da"),
                       "a": _leggi_citta(f["ritorno"]["a"], "ritorno.a")}
            tipo = "diversa"
        else:
            ritorno, tipo = {"da": andata["a"], "a": andata["da"]}, "stessa"
        per = f["periodo"]
        if "mese" in per:
            inizio, fine = mese(str(per["mese"]))
        elif "data" in per:
            centro, delta = data(str(per["data"])), int(per.get("giorni_prima_dopo", 0))
            inizio, fine = centro - timedelta(days=delta), centro + timedelta(days=delta)
        else:
            inizio, fine = data(str(per["dal"])), data(str(per["al"]))
        inizio = max(inizio, date.today() + timedelta(days=1))
        p = {
            "tipo": tipo, "andata": andata, "ritorno": ritorno,
            "inizio": inizio.isoformat(), "fine": fine.isoformat(),
            "giorni_min": int(f["durata"]["min"]), "giorni_max": int(f["durata"]["max"]),
            "max_scali": None if f.get("max_scali") is None else int(f["max_scali"]),
            "top": int(f.get("top", 5)), "frequenza_minuti": int(f.get("frequenza_minuti", 30)),
        }
    except KeyError as e:
        raise ValueError(f"manca il campo {e}") from None
    except (TypeError, AttributeError):
        raise ValueError("struttura non valida: confronta il file con ricerche/esempio.json") from None
    if fine < inizio:
        raise ValueError("periodo vuoto o gia' passato")
    if not 1 <= p["giorni_min"] <= p["giorni_max"]:
        raise ValueError("durata: serve 1 <= min <= max")
    if p["top"] < 1 or p["frequenza_minuti"] < 1 or (p["max_scali"] or 0) < 0:
        raise ValueError("top e frequenza_minuti devono essere >= 1, max_scali >= 0")
    return p


def chiedi_file():
    def conv(s):
        # Un file trascinato nel Terminale arriva con spazi protetti o tra apici.
        s = s.strip().strip("'\"").replace("\\ ", " ")
        if not s:
            raise ValueError("scrivi il percorso del file")
        return parametri_da_file(s)
    p = chiedi("Percorso del file JSON: ", conv)
    scali_txt = {None: "scali qualsiasi", 0: "solo diretti", 1: "max 1 scalo"}.get(p["max_scali"], f"max {p['max_scali']} scali")
    print(f"  Andata {etichetta(p['andata']['da'])} -> {etichetta(p['andata']['a'])}\n"
          f"  Ritorno {etichetta(p['ritorno']['da'])} -> {etichetta(p['ritorno']['a'])}\n"
          f"  Partenza dal {date.fromisoformat(p['inizio']):%d/%m/%Y} al {date.fromisoformat(p['fine']):%d/%m/%Y}, "
          f"durata {p['giorni_min']}-{p['giorni_max']} giorni, {scali_txt}, top {p['top']}, "
          f"ogni {p['frequenza_minuti']} min")
    return p


def chiedi_parametri():
    if chiedi("Parametri: [1] rispondo alle domande  [2] leggo da un file JSON (Invio = 1): ",
              scelta("", "1", "2")) == "2":
        return chiedi_file()
    luoghi = Luoghi()
    client = nuovo_client()
    p = {}
    print(
        f"Date cercabili: partenza da domani, ultimo volo entro il {limite(LIMITE_RICERCA_GIORNI):%d/%m/%Y} "
        f"(limite di Google Flights, oggi + {LIMITE_RICERCA_GIORNI} giorni).\n"
    )
    while True:
        p["tipo"] = {"1": "stessa", "2": "diversa"}[chiedi(
            "Tipo di viaggio: [1] andata e ritorno sulla stessa citta'  [2] ritorno da un'altra citta': ",
            scelta("1", "2"),
        )]
        print("ANDATA")
        andata = {"da": chiedi_citta(luoghi, "partenza"), "a": chiedi_citta(luoghi, "arrivo")}
        if p["tipo"] == "stessa":
            ritorno = {"da": andata["a"], "a": andata["da"]}
        else:
            print("RITORNO")
            ritorno = {
                "da": chiedi_citta(luoghi, "partenza del ritorno", default=andata["a"]),
                "a": chiedi_citta(luoghi, "arrivo del ritorno", default=andata["da"]),
            }
        p["andata"], p["ritorno"] = andata, ritorno
        while (esito := controlla_periodo(client, p, *(periodo := chiedi_periodo()))) == "periodo":
            pass
        if esito == "ok":
            break
    inizio, fine = periodo
    p["inizio"], p["fine"] = inizio.isoformat(), fine.isoformat()
    while True:
        p["giorni_min"] = chiedi("Durata minima viaggio (giorni): ", intero(1))
        p["giorni_max"] = chiedi("Durata massima viaggio (giorni): ", intero(p["giorni_min"]))
        tot, ora = len(chiavi(p, anche_future=True)), len(chiavi(p))
        if ora == tot:
            break
        print(f"  {tot - ora} ricerche su {tot} riguardano voli dopo il "
              f"{limite(LIMITE_RICERCA_GIORNI):%d/%m/%Y}: le faccio man mano che diventano possibili.")
        if ora == 0:
            primo = min(ultima_data(k) for k in chiavi(p, anche_future=True))
            print(f"  Per ora nessuna e' cercabile: la prima lo diventa il "
                  f"{primo - timedelta(days=LIMITE_RICERCA_GIORNI):%d/%m/%Y}.")
            if chiedi("  [1] cambia durata  [2] monitora comunque: ", scelta("1", "2")) == "1":
                continue
        break
    p["max_scali"] = chiedi("Massimo scali per tratta (0 = solo diretti, Invio = qualsiasi): ", scali)
    p["top"] = chiedi("Quanti migliori risultati mostrare: ", intero(1))
    p["frequenza_minuti"] = chiedi("Frequenza aggiornamento (minuti): ", intero(1))
    return p


# --- ricerca -----------------------------------------------------------------

def limite(giorni):
    return date.today() + timedelta(days=giorni)


def _giorni(da, a):
    while da <= a:
        yield da
        da += timedelta(days=1)


def finestra_partenze(p):
    return max(date.fromisoformat(p["inizio"]), date.today() + timedelta(days=1)), date.fromisoformat(p["fine"])


def finestra_ritorni(p):
    inizio, fine = finestra_partenze(p)
    return inizio + timedelta(days=p["giorni_min"]), fine + timedelta(days=p["giorni_max"])


def periodo_allargato(p):
    """Parametri con il periodo di partenza allargato di GIORNI_FUORI_PERIODO per lato."""
    giorni = timedelta(days=GIORNI_FUORI_PERIODO)
    return {**p, "inizio": (date.fromisoformat(p["inizio"]) - giorni).isoformat(),
            "fine": (date.fromisoformat(p["fine"]) + giorni).isoformat()}


def fuori_periodo(p, x):
    return not p["inizio"] <= x["andata"] <= p["fine"]


def combinazioni(p, anche_future=False):
    """Coppie "andata|ritorno" per l'andata e ritorno sullo stesso biglietto.

    Senza anche_future: solo quelle gia' cercabili (ritorno entro il limite di Google).
    Ogni giorno il limite avanza e se ne aggiungono altre.
    """
    if not citta_ar(p):
        return []
    out = []
    for andata in _giorni(*finestra_partenze(p)):
        for durata in range(p["giorni_min"], p["giorni_max"] + 1):
            ritorno = andata + timedelta(days=durata)
            if anche_future or ritorno <= limite(LIMITE_RICERCA_GIORNI):
                out.append(f"{andata.isoformat()}|{ritorno.isoformat()}")
    return out


def sole_andate(p, anche_future=False):
    """Voli di sola andata da cercare: "out|<citta' di arrivo>|data" e "ret|<citta' di partenza>|data"."""
    out = []
    for lato, citta, finestra in (("out", p["andata"]["a"], finestra_partenze(p)),
                                  ("ret", p["ritorno"]["da"], finestra_ritorni(p))):
        for c in citta:
            for giorno in _giorni(*finestra):
                if anche_future or giorno <= limite(LIMITE_RICERCA_GIORNI):
                    out.append(f"{lato}|{c['nome']}|{giorno.isoformat()}")
    return out


def chiavi(p, anche_future=False):
    """Tutte le ricerche precise: andate e ritorni sullo stesso biglietto + sole andate."""
    return combinazioni(p, anche_future) + sole_andate(p, anche_future)


def ultima_data(k):
    return date.fromisoformat(k.split("|")[-1])


def citta_per_nome(p, lato, nome):
    elenco = p["andata"]["a"] if lato == "out" else p["ritorno"]["da"]
    return next(c for c in elenco if c["nome"] == nome)


def tratta_sola_andata(p, k):
    """(giorno, aeroporti di partenza, aeroporti di arrivo) per una chiave di sola andata."""
    lato, nome, giorno = k.split("|")
    c = citta_per_nome(p, lato, nome)
    if lato == "out":
        return giorno, aeroporti(p["andata"]["da"]), c["aeroporti"]
    return giorno, c["aeroporti"], aeroporti(p["ritorno"]["a"])


def _varint(n):
    out = b""
    while n > 0x7F:
        out += bytes([n & 0x7F | 0x80])
        n >>= 7
    return out + bytes([n])


def _campo(numero, dati):
    """Campo protobuf di tipo length-delimited."""
    return _varint(numero << 3 | 2) + _varint(len(dati)) + dati


def _tratta(giorno, da, a, max_scali):
    """FlightData con piu' aeroporti di partenza/arrivo.

    fast-flights ne accetta uno solo, ma Google tratta from/to (campi 13/14) come
    ripetuti: si aggiungono gli altri aeroporti in coda ai byte serializzati.
    """
    fd = FlightQuery(
        date=giorno, from_airport=da[0], to_airport=a[0], max_stops=max_scali
    ).pb().SerializeToString()
    for numero, codici in ((13, da[1:]), (14, a[1:])):
        for c in codici:
            fd += _campo(numero, Airport(airport=c).SerializeToString())
    return _campo(3, fd)  # Info.data


class Bloccato(Exception):
    """Google sta limitando le richieste (429, captcha o troppi errori)."""


def controlla_blocco(r):
    if r.status_code == 429:
        raise Bloccato("HTTP 429, troppe richieste")
    if "/sorry/" in str(getattr(r, "url", "")) or "unusual traffic" in r.text[:20000]:
        raise Bloccato("captcha di Google")


class Ritmo:
    """Velocita' adattiva: rallenta quando Google limita, riaccelera dopo un giro pulito.

    A ogni livello: meta' ricerche per giro, pause doppie, intervallo tra giri doppio.
    """

    LIVELLO_MAX = 3

    def __init__(self):
        self.livello = 0

    @property
    def fattore(self):
        return 2 ** self.livello

    def pausa(self):
        return PAUSA_SECONDI * self.fattore

    def pausa_calendario(self):
        return PAUSA_CALENDARIO * self.fattore

    def budget(self, frequenza_minuti):
        # Non piu' ricerche di quante ne stanno nell'intervallo (circa 3 s a ricerca + pausa).
        entro_intervallo = frequenza_minuti * 60 // (self.pausa() + 3)
        return max(2, min(RICERCHE_MAX_PER_GIRO // self.fattore, entro_intervallo))

    def intervallo_minuti(self, frequenza_minuti):
        return frequenza_minuti * self.fattore

    def descrizione(self, frequenza_minuti):
        return (
            f"livello {self.livello}/{self.LIVELLO_MAX}: max {self.budget(frequenza_minuti)} ricerche per giro, "
            f"pausa {self.pausa()} s, un giro ogni {self.intervallo_minuti(frequenza_minuti)} min"
        )


def cerca(client, org, dst, andata, ritorno, max_scali=None):
    """Volo A/R piu' economico tra tutti gli aeroporti, o None se non in vendita."""
    return _cerca(client, "round-trip", [(andata, org, dst), (ritorno, dst, org)], max_scali)


def cerca_sola_andata(client, giorno, org, dst, max_scali=None):
    """Volo di sola andata piu' economico tra tutti gli aeroporti, o None."""
    return _cerca(client, "one-way", [(giorno, org, dst)], max_scali)


def _cerca(client, viaggio, tratte, max_scali):
    base = create_query(flights=[], trip=viaggio, passengers=Passengers(adults=1))
    tfs = b64encode(base.to_bytes() + b"".join(_tratta(g, da, a, max_scali) for g, da, a in tratte)).decode()
    params = {"tfs": tfs, "hl": "it", "curr": "EUR"}
    link = f"{URL}/search?tfs={tfs}&hl=it&curr=EUR"
    r = client.get(URL, params=params)
    controlla_blocco(r)
    script = LexborHTMLParser(r.text).css_first(r"script.ds\:1")
    if script is None:
        raise RuntimeError("risposta Google inattesa (pagina senza risultati)")
    payload_str = script.text().split("data:", 1)[1].rsplit(",", 1)[0]
    if payload_str.endswith("errorHasStatus: true"):
        return None
    payload = json.loads(payload_str)

    migliore = None
    # [2] = "voli migliori", [3] = altri voli; voci senza prezzo vengono saltate.
    for sezione in (2, 3):
        righe = (payload[sezione] or [None])[0] if len(payload) > sezione else None
        for r in righe or []:
            try:
                prezzo = r[1][0][1]
                volo = r[0]
            except (IndexError, TypeError):
                continue
            if prezzo is None or (migliore and prezzo >= migliore["prezzo"]):
                continue
            migliore = {
                "prezzo": prezzo,
                "compagnie": ", ".join(volo[1]),
                "tratte": " ".join(f"{l[3]}-{l[6]}" for l in volo[2]),
                "link": link,
            }
    if migliore:
        migliore.update(indicatori_prezzo(payload))
    return migliore


def indicatori_prezzo(payload):
    """Indicatori prezzo di Google per la tratta e le date cercate.

    payload[5] = [livello, [_, attuale], [_, tipico], [_, differenza], [_, fascia min],
    [_, fascia max], ..., [storico 60 giorni: [[timestamp ms, prezzo], ...]]].
    Formato ricavato dalle risposte, non documentato: se manca, nessun giudizio.
    """
    try:
        x = payload[5]
        out = {"tipico": x[2][1], "fascia": [x[4][1], x[5][1]]}
    except (IndexError, TypeError):
        return {}
    try:
        out["min_60gg"] = min(v for _, v in x[10][0] if v)
    except (IndexError, TypeError, ValueError):
        pass
    return out


def migliore(v):
    """Prezzo piu' basso noto per una combinazione: lista Google o venditore (agenzia)."""
    candidati = [v.get("prezzo"), (v.get("venditore") or {}).get("prezzo")]
    return min((x for x in candidati if x), default=None)


def descrivi_prezzo(v):
    """Es. "656 EUR su lastminute.com (674 EUR in lista, andata 15:10, ritorno 17:55)"."""
    ven = v.get("venditore") or {}
    if ven.get("prezzo") and ven["prezzo"] < v["prezzo"]:
        return f"{ven['prezzo']} EUR su {ven['nome']} ({v['prezzo']} EUR in lista, {ven['orari']})"
    return f"{v['prezzo']} EUR"


def prezzo_venditori(cercatore, p, andata, ritorno):
    """Venditore piu' economico (compagnia o agenzia) tra le pagine di prenotazione.

    I prezzi delle agenzie (lastminute, BudgetAir, ...) compaiono solo nella pagina
    "Prenota con" di un itinerario preciso, non nella lista dei risultati.
    Usa la libreria fli (GetShoppingResults + GetBookingResults).
    """
    try:
        org = [[FliAirport[a], 0] for a in aeroporti(p["andata"]["da"])]
        dst = [[FliAirport[a], 0] for a in aeroporti(citta_ar(p))]
    except KeyError:
        return None  # aeroporto sconosciuto a fli
    stops = {None: MaxStops.ANY, 0: MaxStops.NON_STOP, 1: MaxStops.ONE_STOP_OR_FEWER}.get(
        p["max_scali"], MaxStops.TWO_OR_FEWER_STOPS if p["max_scali"] == 2 else MaxStops.ANY
    )
    filtri = FlightSearchFilters(
        trip_type=TripType.ROUND_TRIP, passenger_info=PassengerInfo(adults=1),
        flight_segments=[
            FlightSegment(departure_airport=org, arrival_airport=dst, travel_date=andata),
            FlightSegment(departure_airport=dst, arrival_airport=org, travel_date=ritorno),
        ],
        seat_type=SeatType.ECONOMY, stops=stops, sort_by=SortBy.CHEAPEST,
    )
    itinerari = cercatore.search(filtri, top_n=3, currency="EUR", language="it", country="IT") or []
    # Per l'A/R il prezzo del volo di ritorno e' il totale dell'itinerario.
    itinerari = sorted((it for it in itinerari if it[1].price), key=lambda it: it[1].price)
    meglio = None
    for andata_v, ritorno_v in itinerari[:ITINERARI_VENDITORI]:
        for o in cercatore.get_booking_options((andata_v, ritorno_v), filtri, currency="EUR", language="it", country="IT"):
            if o.price and (meglio is None or o.price < meglio["prezzo"]):
                meglio = {
                    "prezzo": round(o.price),
                    "nome": o.vendor_name,
                    "orari": f"andata {andata_v.legs[0].departure_datetime:%H:%M}, "
                             f"ritorno {ritorno_v.legs[0].departure_datetime:%H:%M}",
                }
    return meglio


def giudizio(v):
    """Etichetta del prezzo rispetto alla fascia tipica Google, o "" se non disponibile."""
    if not v.get("fascia"):
        return ""
    basso, alto = v["fascia"]
    p = migliore(v)
    if p < basso:
        etichetta = "BASSO"
    elif p > alto:
        etichetta = "ALTO"
    elif p <= basso + (alto - basso) / 3:
        etichetta = "nella media, parte bassa"
    elif p >= alto - (alto - basso) / 3:
        etichetta = "nella media, parte alta"
    else:
        etichetta = "nella media"
    diff = round((p - v["tipico"]) / v["tipico"] * 100)
    testo = f"{etichetta}: {diff:+d}% sul tipico {v['tipico']} EUR, fascia {basso}-{alto} EUR"
    if "min_60gg" in v:
        testo += f", minimo ultimi 60 gg {v['min_60gg']} EUR"
    return testo


def calendario(client, org, dst, da, a, durata, max_scali):
    """Prezzi stimati per ogni partenza tra da e a (max 61 giorni).

    Con durata: A/R di durata fissa, ritorna {"andata|ritorno": prezzo}.
    Con durata None: solo andata, ritorna {"andata": prezzo}.
    Usa GetCalendarGraph, l'API interna del grafico prezzi di Google Flights:
    una richiesta copre tutte le date. Formato ricavato dalla libreria `fli`
    (github.com/punitarani/fli), non documentato da Google.
    """
    stops = {None: 0, 0: 1, 1: 2, 2: 3}.get(max_scali, 0)

    def segmento(da_aer, a_aer, giorno, tipo):
        return [[[[da_aer, 0]]], [[[a_aer, 0]]], None, stops, None, None, giorno,
                None, None, None, None, None, None, None, tipo]

    if durata is None:
        tipo_viaggio, segmenti, durate = 2, [segmento(org, dst, da, 3)], []
    else:
        ritorno = (date.fromisoformat(da) + timedelta(days=durata)).isoformat()
        tipo_viaggio = 1
        segmenti = [segmento(org, dst, da, 3), segmento(dst, org, ritorno, 1)]
        durate = [None, [durata, durata]]
    filtri = [
        None,
        [None, None, tipo_viaggio, None, [], 1, [1, 0, 0, 0], None, None, None, None, None, None,
         segmenti, None, None, None, 1],
        [da, a],
        *durate,
    ]
    corpo = "f.req=" + urllib.parse.quote(
        json.dumps([None, json.dumps(filtri, separators=(",", ":"))], separators=(",", ":"))
    )
    r = client.post(
        CALENDARIO_URL, params={"hl": "it", "curr": "EUR"}, data=corpo,
        headers={"content-type": "application/x-www-form-urlencoded;charset=UTF-8"},
    )
    controlla_blocco(r)
    if r.status_code != 200:
        raise RuntimeError(f"calendario HTTP {r.status_code}")
    out = {}
    for riga in r.text.splitlines():
        if not riga.startswith('[["wrb.fr"'):
            continue
        for chunk in json.loads(riga):
            if chunk[0] != "wrb.fr" or not chunk[2]:
                continue
            for item in json.loads(chunk[2])[-1] or []:
                try:
                    out[item[0] if durata is None else f"{item[0]}|{item[1]}"] = item[2][0][1]
                except (IndexError, TypeError):
                    continue
    return out


def _finestre(da, a):
    a = min(a, limite(LIMITE_CALENDARIO_GIORNI))
    while da <= a:
        yield da, min(a, da + timedelta(days=MAX_GIORNI_CALENDARIO - 1))
        da += timedelta(days=MAX_GIORNI_CALENDARIO)


def scansione_calendario(client, p, ritmo):
    """Stime dal calendario per tutte le ricerche, con le stesse chiavi di chiavi(p).

    Una chiamata per coppia di aeroporti (e durata, per l'A/R), non tutti gli aeroporti
    insieme: con piu' aeroporti (es. KIX+ITM+UKB) il calendario restituisce quasi
    sempre un solo risultato.
    """
    chiamate = []  # (prefisso chiave o None per A/R, partenza, arrivo, da, a, durata)
    if citta_ar(p):
        for da, a in _finestre(*finestra_partenze(p)):
            for o in aeroporti(p["andata"]["da"]):
                for d in aeroporti(citta_ar(p)):
                    for durata in range(p["giorni_min"], p["giorni_max"] + 1):
                        chiamate.append((None, o, d, da, a, durata))
    for c in p["andata"]["a"]:
        for da, a in _finestre(*finestra_partenze(p)):
            for o in aeroporti(p["andata"]["da"]):
                for d in c["aeroporti"]:
                    chiamate.append((f"out|{c['nome']}|", o, d, da, a, None))
    for c in p["ritorno"]["da"]:
        for da, a in _finestre(*finestra_ritorni(p)):
            for o in c["aeroporti"]:
                for d in aeroporti(p["ritorno"]["a"]):
                    chiamate.append((f"ret|{c['nome']}|", o, d, da, a, None))
    print()
    stime, errori = {}, 0
    with Barra("Calendario", len(chiamate)) as barra:
        for prefisso, o, d, da, a, durata in chiamate:
            try:
                for k, prezzo in calendario(client, o, d, da.isoformat(), a.isoformat(), durata, p["max_scali"]).items():
                    k = (prefisso or "") + k
                    stime[k] = min(prezzo, stime.get(k, prezzo))
            except Bloccato:
                raise
            except Exception as e:  # noqa: BLE001 - senza calendario si usa solo la ricerca precisa
                errori += 1
                barra.scrivi(f"[errore calendario] {o}-{d}: {e}")
                if errori >= 5:
                    barra.scrivi("[stop calendario] troppi errori, continuo con la ricerca precisa")
                    break
            barra.avanza(f"{len(stime)} prezzi stimati")
            time.sleep(ritmo.pausa_calendario())
    return stime


def proposte(p, prezzi_di):
    """Viaggi completi con il loro prezzo, dal piu' economico.

    prezzi_di: {chiave: prezzo} (prezzi verificati o stime). Ogni proposta e'
    {"prezzo", "tipo": "ar"|"2b", "andata", "ritorno", "chiavi", "va", "torna"}
    (va/torna = nomi delle citta' di arrivo dell'andata e di partenza del ritorno).
    """
    out = []
    nome_ar = nomi(citta_ar(p))
    for k in combinazioni(p):
        if prezzi_di.get(k):
            andata, ritorno = k.split("|")
            out.append({"prezzo": prezzi_di[k], "tipo": "ar", "andata": andata, "ritorno": ritorno,
                        "chiavi": [k], "va": nome_ar, "torna": nome_ar})
    for x in p["andata"]["a"]:
        for y in p["ritorno"]["da"]:
            if p["tipo"] == "stessa" and x["nome"] != y["nome"]:
                continue
            for andata in _giorni(*finestra_partenze(p)):
                k_out = f"out|{x['nome']}|{andata.isoformat()}"
                if not prezzi_di.get(k_out):
                    continue
                for durata in range(p["giorni_min"], p["giorni_max"] + 1):
                    ritorno = (andata + timedelta(days=durata)).isoformat()
                    k_ret = f"ret|{y['nome']}|{ritorno}"
                    if prezzi_di.get(k_ret):
                        out.append({"prezzo": prezzi_di[k_out] + prezzi_di[k_ret], "tipo": "2b",
                                    "andata": andata.isoformat(), "ritorno": ritorno,
                                    "chiavi": [k_out, k_ret], "va": x["nome"], "torna": y["nome"]})
    return sorted(out, key=lambda x: x["prezzo"])


def notifica(titolo, testo):
    if sys.platform == "darwin":
        script = f"display notification {json.dumps(testo)} with title {json.dumps(titolo)}"
        subprocess.run(["osascript", "-e", script], check=False)


def citta_da_tratte(p, tratte):
    """Citta' di arrivo dell'andata, dall'ultimo aeroporto delle tratte (es. "FCO-ICN ICN-KIX")."""
    arrivo = tratte.split()[-1].split("-")[-1] if tratte else ""
    return next((c["nome"] for c in citta_ar(p) if arrivo in c["aeroporti"]), nomi(citta_ar(p)))


def proposte_verificate(p, prezzi):
    """Proposte con soli prezzi verificati; per l'A/R la citta' viene dalle tratte trovate."""
    out = proposte(p, {k: migliore(v) for k, v in prezzi.items() if migliore(v)})
    for x in out:
        if x["tipo"] == "ar":
            x["va"] = x["torna"] = citta_da_tratte(p, prezzi[x["chiavi"][0]].get("tratte"))
    return out


def giro(p, cartella, client, ritmo, primo=False):
    """Un giro di ricerche. Ritorna (motivo del blocco o None, messaggio Telegram o None)."""
    prezzi_path = cartella / "prezzi.json"
    try:
        prezzi = json.loads(prezzi_path.read_text())
    except FileNotFoundError:
        prezzi = {}

    tutte = chiavi(p)
    valide = set(tutte)
    prezzi = {k: v for k, v in prezzi.items() if k in valide}  # date ormai passate

    # 1. Stima veloce di tutte le ricerche dal calendario prezzi. Il calendario guarda
    #    anche qualche giorno prima e dopo il periodo: una richiesta copre fino a 61 giorni,
    #    quindi di solito non costa richieste in piu'.
    largo = periodo_allargato(p)
    bloccato = None
    try:
        stime_larghe = scansione_calendario(client, largo, ritmo)
    except Bloccato as e:
        bloccato, stime_larghe = str(e), {}
    stime = {k: v for k, v in stime_larghe.items() if k in valide}

    # 2. Ricerca precisa: le ricerche della top attuale, poi quelle dei viaggi con la
    #    stima piu' bassa, poi a rotazione tutte le altre (mai verificate prima). La
    #    rotazione serve: il calendario non vede tutte le tariffe (es. China Eastern
    #    751 EUR stimata 833), quindi una stima alta non basta per scartare una ricerca.
    budget = ritmo.budget(p["frequenza_minuti"]) if not bloccato else 0
    verificate_prima = proposte_verificate(p, prezzi)
    da_fare, motivo = [], {}

    def aggiungi(k, perche):
        if k not in motivo:
            da_fare.append(k)
            motivo[k] = perche

    for x in verificate_prima[: p["top"]]:
        for k in x["chiavi"]:
            if len(da_fare) < budget // 2:
                aggiungi(k, "top")
    for x in proposte(p, stime):
        if sum(1 for m in motivo.values() if m == "stima") >= VERIFICA_DA_STIMA:
            break
        for k in x["chiavi"]:
            aggiungi(k, "stima")
    da_fare = da_fare[:budget]
    for k in sorted((k for k in tutte if k not in motivo), key=lambda k: prezzi.get(k, {}).get("controllato", "")):
        if len(da_fare) >= budget:
            break
        aggiungi(k, "rotazione")
    # Fuori periodo: verifico solo la proposta stimata piu' economica, e solo se costa
    # meno del meglio nel periodo (1-2 ricerche in piu').
    chiavi_fuori = []
    dentro = [x["prezzo"] for x in verificate_prima[:1] + proposte(p, stime)[:1]]
    fuori = next((x for x in proposte(largo, stime_larghe) if fuori_periodo(p, x)), None)
    if budget and fuori and (not dentro or fuori["prezzo"] < min(dentro)):
        chiavi_fuori = fuori["chiavi"]
        for k in chiavi_fuori:
            aggiungi(k, "fuori periodo")
    if da_fare:
        conta = {m: sum(1 for k in da_fare if motivo[k] == m)
                 for m in ("top", "stima", "rotazione", "fuori periodo")}
        print(
            f"\nVerifica precisa: {len(da_fare)} ricerche "
            f"(top attuale {conta['top']}, stime migliori {conta['stima']}, a rotazione {conta['rotazione']}"
            + (f", fuori periodo {conta['fuori periodo']}" if conta["fuori periodo"] else "") + ")"
        )

    record_prima = verificate_prima[0]["prezzo"] if verificate_prima else None
    minimo = record_prima
    adesso = datetime.now().isoformat(timespec="seconds")
    errori = 0
    with open(cartella / "storico.csv", "a", newline="") as f, Barra("Verifica", len(da_fare)) as barra:
        storico = csv.writer(f)
        for k in da_fare:
            try:
                if k.count("|") == 1:
                    andata, ritorno = k.split("|")
                    ris = cerca(client, aeroporti(p["andata"]["da"]), aeroporti(citta_ar(p)),
                                andata, ritorno, p["max_scali"])
                else:
                    giorno, org, dst = tratta_sola_andata(largo, k)
                    ris = cerca_sola_andata(client, giorno, org, dst, p["max_scali"])
            except Bloccato as e:
                bloccato = str(e)
                break
            except Exception as e:  # noqa: BLE001 - un errore non deve fermare il giro
                errori += 1
                barra.scrivi(f"[errore] {k}: {e}")
                if errori >= 5:
                    bloccato = "5 errori di fila, probabile limitazione"
                    break
                barra.avanza()
                continue
            errori = 0
            # Il venditore resta finche' la fase 3 non lo ricontrolla.
            prezzi[k] = {**(ris or {"prezzo": None}), "controllato": adesso,
                         "venditore": prezzi.get(k, {}).get("venditore") if ris else None}
            if ris:
                a, b = k.split("|") if k.count("|") == 1 else (k.split("|")[2], k.rsplit("|", 1)[0])
                storico.writerow([adesso, a, b, ris["prezzo"], ris["compagnie"], ris["tratte"]])
                f.flush()
                meglio = proposte_verificate(p, prezzi)
                if meglio and (minimo is None or meglio[0]["prezzo"] < minimo):
                    minimo = meglio[0]["prezzo"]
                    barra.scrivi(f"★ nuovo minimo: {riassunto(meglio[0])}")
            barra.avanza(f"minimo {minimo} EUR" if minimo else "")
            # Salva subito: Ctrl+C a meta' giro non perde le ricerche fatte.
            prezzi_path.write_text(json.dumps(prezzi, indent=1, ensure_ascii=False))
            time.sleep(ritmo.pausa())

    # 3. Venditori: per gli A/R in top, prezzi di agenzie e compagnia nelle pagine di
    #    prenotazione (per la sola andata fli non restituisce i venditori).
    if not bloccato:
        candidati = [x["chiavi"][0] for x in proposte_verificate(p, prezzi)[: p["top"]] if x["tipo"] == "ar"]
        cercatore, errori = SearchFlights(), 0
        if candidati:
            print(f"\nPrezzi dei venditori (agenzie comprese) per {len(candidati)} A/R in top")
        with open(cartella / "storico.csv", "a", newline="") as f, Barra("Venditori", len(candidati)) as barra:
            storico = csv.writer(f)
            for k in candidati:
                andata, ritorno = k.split("|")
                try:
                    ven = prezzo_venditori(cercatore, p, andata, ritorno)
                except Exception as e:  # noqa: BLE001 - il prezzo della lista resta valido
                    if "429" in str(e):
                        bloccato = "HTTP 429 sulle pagine di prenotazione"
                        break
                    errori += 1
                    barra.scrivi(f"[errore venditori] {andata} -> {ritorno}: {e}")
                    if errori >= 3:
                        break
                    barra.avanza()
                    continue
                if ven:
                    prezzi[k]["venditore"] = {**ven, "controllato": adesso}
                    storico.writerow([adesso, andata, ritorno, ven["prezzo"], f"{ven['nome']} (venditore)", ven["orari"]])
                    if minimo is None or ven["prezzo"] < minimo:
                        barra.scrivi(f"★ nuovo minimo: {ven['prezzo']} EUR su {ven['nome']}  {andata} -> {ritorno}  ({ven['orari']})")
                        minimo = ven["prezzo"]
                barra.avanza(f"minimo {minimo} EUR" if minimo else "")
                prezzi_path.write_text(json.dumps(prezzi, indent=1, ensure_ascii=False))
                time.sleep(ritmo.pausa())
    if bloccato:
        print(f"[blocco] Google limita le richieste: {bloccato}. Giro interrotto.")

    tutte_proposte = proposte_verificate(p, prezzi)
    top = tutte_proposte[: p["top"]]
    tratta = nome_tratta(p)
    scali_txt = {None: "scali qualsiasi", 0: "solo diretti", 1: "max 1 scalo"}.get(
        p["max_scali"], f"max {p['max_scali']} scali"
    )
    cop = {
        "totale": len(valide),
        "stimate": len(valide & (set(stime) | set(prezzi))),
        "verificate": len(valide & set(prezzi)),
        "budget": ritmo.budget(p["frequenza_minuti"]),
        "future": len(chiavi(p, anche_future=True)) - len(valide),
        "migliori": 0,
    }
    if cop["verificate"] < cop["totale"]:
        # Le stime piu' basse del calendario vengono verificate per prime: lo dico, cosi'
        # una scansione parziale non sembra un risultato incompleto.
        for x in proposte(p, stime)[:VERIFICA_DA_STIMA]:
            if not all(k in prezzi for k in x["chiavi"]):
                break
            cop["migliori"] += 1
    copertura = testo_copertura(cop)
    righe = [
        f"Top {len(top)} {tratta}, partenza {p['inizio']} .. {p['fine']}, "
        f"{p['giorni_min']}-{p['giorni_max']} giorni, {scali_txt} (aggiornato {adesso})",
        copertura[0].upper() + copertura[1:],
        "",
    ]
    for i, x in enumerate(top, 1):
        righe.append(f"{i}. " + dettaglio(x, prezzi))
    if not top:
        righe.append("Nessun prezzo ancora: date forse non in vendita.")
    confronto = confronto_varianti(p, tutte_proposte, proposte(p, stime))
    righe += ["", *confronto]
    consiglio = suggerimento(p, largo, prezzi, chiavi_fuori, top)
    if consiglio:
        righe += ["", *consiglio]
    testo = "\n".join(righe)
    (cartella / "top.txt").write_text(testo + "\n")
    print("\n" + "=" * 80 + "\n" + testo)

    nuovo = top and (record_prima is None or top[0]["prezzo"] < record_prima)
    if nuovo:
        notifica(f"Volo {tratta}: nuovo minimo", riassunto(top[0]))
    # Al primo giro di ogni avvio la top completa arriva comunque, anche se i prezzi
    # vengono da un'esecuzione precedente.
    if nuovo or (primo and top):
        titolo = "✈️ <b>Nuovo prezzo minimo</b>" if nuovo else "🚀 <b>Tracker avviato</b>: prezzi migliori attuali"
        return bloccato, messaggio_telegram(p, top, prezzi, cop, confronto + ([""] + consiglio if consiglio else []),
                                            titolo)
    # Nessun nuovo minimo: messaggio breve, cosi' su Telegram si vede che il controllo e' stato fatto.
    e = html.escape
    titolo = ("⚠️ <b>Check interrotto</b>: Google limita le richieste" if bloccato
              else "✅ <b>Check ok</b>, nessun prezzo migliore trovato")
    stato = f"🏆 Minimo attuale: <b>{e(riassunto(top[0]))}</b>" if top else "Nessun prezzo ancora."
    return bloccato, (intestazione_telegram(p, titolo, cop) + f"\n\n{stato}"
                      + (f"\n\n{e(chr(10).join(consiglio))}" if consiglio else ""))


def testo_copertura(cop):
    """Copertura della scansione su una riga, per terminale e top.txt."""
    testo = (f"stimate {cop['stimate']}/{cop['totale']} ricerche, "
             f"verificate col prezzo completo {cop['verificate']}/{cop['totale']}"
             + (" (scansione completa)" if cop["verificate"] == cop["totale"] else " (scansione in corso)"))
    if cop["verificate"] < cop["totale"]:
        if cop["migliori"]:
            testo += f". Le {cop['migliori']} combinazioni piu' economiche secondo il calendario sono gia' verificate"
        testo += (f"; le altre {cop['totale'] - cop['verificate']} ricerche ai prossimi controlli "
                  f"(massimo {cop['budget']} per controllo, per non farsi bloccare da Google)")
    if cop["future"]:
        testo += f"; altre {cop['future']} non ancora possibili (voli oltre il {limite(LIMITE_RICERCA_GIORNI):%d/%m/%Y})"
    return testo


def intestazione_telegram(p, titolo, cop):
    """Titolo, riassunto dei parametri e copertura della scansione, in HTML per Telegram."""
    e = html.escape
    giorno = lambda s: f"{date.fromisoformat(s):%d/%m/%Y}"
    scali_txt = {None: "scali qualsiasi", 0: "solo diretti", 1: "max 1 scalo"}.get(
        p["max_scali"], f"max {p['max_scali']} scali")
    righe = [
        titolo,
        "",
        f"🛫 {e(etichetta(p['andata']['da']))} → {e(etichetta(p['andata']['a']))}",
        f"🛬 {e(etichetta(p['ritorno']['da']))} → {e(etichetta(p['ritorno']['a']))}",
        f"📅 Partenza dal {giorno(p['inizio'])} al {giorno(p['fine'])}",
        f"🧳 Durata min: {p['giorni_min']} gg - max: {p['giorni_max']} giorni · {scali_txt} · controllo ogni {p['frequenza_minuti']} min",
        "",
    ]
    if cop["verificate"] == cop["totale"]:
        righe.append(f"🔎 <b>Scansione completa</b>: {cop['verificate']}/{cop['totale']} ricerche verificate")
    else:
        righe.append(f"🔎 <b>Scansione in corso</b>: {cop['verificate']}/{cop['totale']} ricerche verificate, "
                     f"{cop['stimate']}/{cop['totale']} stimate")
        if cop["migliori"]:
            righe.append(f"✅ Le {cop['migliori']} combinazioni più economiche del calendario sono già verificate")
        righe.append(f"⏳ Le altre {cop['totale'] - cop['verificate']} ai prossimi controlli "
                     f"(max {cop['budget']} per controllo, per non farsi bloccare da Google)")
    if cop["future"]:
        righe.append(f"🔒 Altre {cop['future']} non ancora cercabili "
                     f"(voli oltre il {limite(LIMITE_RICERCA_GIORNI):%d/%m/%Y})")
    return "\n".join(righe)


def suggerimento(p, largo, prezzi, chiavi_fuori, top):
    """Righe "💡 ..." se una partenza fuori dal periodo, verificata in questo giro, costa meno della top."""
    if not chiavi_fuori:
        return []
    x = next((x for x in proposte_verificate(largo, prezzi)
              if fuori_periodo(p, x) and set(x["chiavi"]) <= set(chiavi_fuori)), None)
    if not x or (top and x["prezzo"] >= top[0]["prezzo"]):
        return []
    risparmio = f"risparmi {top[0]['prezzo'] - x['prezzo']} EUR" if top else "ci sono voli"
    giorno = date.fromisoformat(x["andata"])
    return [f"💡 Partendo il {giorno:%d/%m} (fuori dal tuo periodo) {risparmio}: {riassunto(x)}",
            *(f"   {prezzi[k]['link']}" for k in x["chiavi"])]


def nome_tratta(p):
    andata = f"{nomi(p['andata']['da'])} -> {nomi(p['andata']['a'])}"
    if p["tipo"] == "stessa":
        return andata
    return f"{andata}, ritorno {nomi(p['ritorno']['da'])} -> {nomi(p['ritorno']['a'])}"


def _gg(x):
    return (date.fromisoformat(x["ritorno"]) - date.fromisoformat(x["andata"])).days


def riassunto(x):
    """Una riga: "701 EUR 2 biglietti, andata Tokyo / ritorno da Osaka, 2027-03-08 -> 2027-03-22"."""
    tipo = f"A/R {x['va']}" if x["tipo"] == "ar" else f"2 biglietti, andata {x['va']} / ritorno da {x['torna']}"
    return f"{x['prezzo']} EUR {tipo}, {x['andata']} -> {x['ritorno']} ({_gg(x)} gg)"


def dettaglio(x, prezzi):
    """Proposta per terminale e top.txt."""
    if x["tipo"] == "ar":
        v = prezzi[x["chiavi"][0]]
        return (
            f"{descrivi_prezzo(v)}  A/R {x['va']}  {x['andata']} -> {x['ritorno']} ({_gg(x)} gg)  "
            f"{v['compagnie']}  [{v['tratte']}]  visto {v['controllato']}\n"
            + (f"   Prezzo {giudizio(v)}\n" if giudizio(v) else "")
            + f"   {v['link']}"
        )
    va, torna = (prezzi[k] for k in x["chiavi"])
    righe = [f"{x['prezzo']} EUR  2 biglietti: andata {x['va']}, ritorno da {x['torna']}  "
             f"{x['andata']} -> {x['ritorno']} ({_gg(x)} gg)"]
    for nome, v in (("Andata ", va), ("Ritorno", torna)):
        righe.append(f"   {nome} {v['prezzo']} EUR  {v['compagnie']}  [{v['tratte']}]  visto {v['controllato']}"
                     + (f"  ({giudizio(v).split(':')[0]})" if giudizio(v) else ""))
    righe.append("   ⚠ biglietti separati: se un volo cambia o salta, l'altro non e' protetto")
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
            for tipo, nome in (("ar", "A/R"), ("2b", "2 biglietti")):
                if tipo == "ar" and not (x["nome"] == y["nome"] and x in citta_ar(p)):
                    continue
                trova = lambda elenco: next((z for z in elenco if z["tipo"] == tipo and z["va"] == x["nome"]
                                             and z["torna"] == y["nome"]), None)
                v, st = trova(verificate), trova(stimate) if stimate else None
                celle.append((v["prezzo"] if v else None, f"{nome} " + (
                    f"{v['prezzo']} EUR" if v else f"~{st['prezzo']} EUR (stima)" if st else "n.d.")))
            righe.append((min((c[0] for c in celle if c[0]), default=None),
                          f"  Andata {x['nome']}, ritorno da {y['nome']}: " + " · ".join(c[1] for c in celle)))
    if len(righe) == 1 and len(righe[0][1].split(" · ")) == 1:
        return []  # una sola variante: niente da confrontare
    migliore_v = min((r[0] for r in righe if r[0]), default=None)
    return ["Confronto varianti (prezzi verificati):"] + [
        testo + ("  ← migliore" if prezzo and prezzo == migliore_v else "") for prezzo, testo in righe
    ]


def messaggio_telegram(p, top, prezzi, cop, confronto, titolo="✈️ <b>Nuovo prezzo minimo</b>"):
    """Top N in HTML per Telegram, con link cliccabili a Google Flights."""
    e = html.escape
    gm = lambda s: f"{date.fromisoformat(s):%d/%m}"
    righe = [intestazione_telegram(p, titolo, cop), "", f"🏆 <b>Top {len(top)}</b>"]
    for i, x in enumerate(top, 1):
        date_txt = f"   📆 {gm(x['andata'])} → {gm(x['ritorno'])} ({_gg(x)} gg)"
        if x["tipo"] == "ar":
            v = prezzi[x["chiavi"][0]]
            blocco = [f"{i}. <b>{x['prezzo']} EUR</b> · A/R {e(x['va'])}", date_txt]
            if x["prezzo"] < v["prezzo"]:
                blocco.append(f"   🏷 su {e(v['venditore']['nome'])} ({v['prezzo']} EUR in lista, "
                              f"{e(v['venditore']['orari'])})")
            blocco.append(f"   🛩 {e(v['compagnie'])} [{e(v['tratte'])}]")
            if giudizio(v):
                blocco.append(f"   📊 <i>{e(giudizio(v))}</i>")
            blocco.append(f"   🔗 <a href=\"{e(v['link'])}\">Apri su Google Flights</a>")
        else:
            va, torna = (prezzi[k] for k in x["chiavi"])
            blocco = [f"{i}. <b>{x['prezzo']} EUR</b> · 2 biglietti: andata {e(x['va'])}, ritorno da {e(x['torna'])}",
                      date_txt]
            for nome, v in (("Andata", va), ("Ritorno", torna)):
                blocco.append(f"   🛩 {nome} {v['prezzo']} EUR {e(v['compagnie'])} [{e(v['tratte'])}] "
                              f"<a href=\"{e(v['link'])}\">apri</a>")
            blocco.append("   ⚠️ biglietti separati: se un volo cambia o salta, l'altro non è protetto")
        righe += ["", *blocco]
    if confronto:
        testo = e("\n".join(confronto)).replace("Confronto varianti (prezzi verificati):",
                                                 "⚖️ <b>Confronto varianti</b> (prezzi verificati)")
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
            tempo = f"~{_durata(trascorso / self.fatte * (self.totale - self.fatte))} rimasti"
        else:
            tempo = "stima tempo..."
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
        print(f"\nProssimo aggiornamento alle {prossimo:%H:%M}.")
        time.sleep(secondi)
        return
    print()
    while (resto := fine - time.monotonic()) > 0:
        m, s = divmod(int(resto + 0.999), 60)
        h, m = divmod(m, 60)
        timer = f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        print(f"\rProssimo aggiornamento tra {timer} (alle {prossimo:%H:%M})  ", end="", flush=True)
        time.sleep(min(1, resto))
    print("\r" + " " * 60 + "\r", end="", flush=True)


def nuovo_client():
    return Client(impersonate="chrome_145", impersonate_os="macos", referer=True, headers={"Cookie": CONSENT_COOKIE})


def main():
    if "--setup-telegram" in sys.argv:
        telegram_bot.setup()
        return
    if not telegram_bot.configurato():
        print("(Notifiche Telegram non attive: per attivarle .venv/bin/python tracker.py --setup-telegram)\n")
    telegram_bot.ascolta_in_background()  # /start e /stop di chiunque apra il bot
    p = chiedi_parametri()
    # Per l'A/R sulla stessa citta' il nome e' quello delle versioni precedenti, cosi'
    # le istanze gia' avviate riprendono i loro dati.
    nome = (
        f"{'_'.join(aeroporti(p['andata']['da']))}-{'_'.join(aeroporti(p['andata']['a']))}"
        f"-{p['inizio']}_{p['fine']}"
        f"-{p['giorni_min']}-{p['giorni_max']}gg-scali{'X' if p['max_scali'] is None else p['max_scali']}"
        + (f"-rit_{'_'.join(aeroporti(p['ritorno']['da']))}-{'_'.join(aeroporti(p['ritorno']['a']))}"
           if p["tipo"] == "diversa" else "")
    )
    cartella = BASE / "data" / nome
    cartella.mkdir(parents=True, exist_ok=True)

    # Due istanze con gli stessi parametri si sovrascriverebbero i file.
    lock = open(cartella / ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit(f"Un'altra istanza con questi parametri e' gia' attiva ({cartella}).")
    (cartella / "parametri.json").write_text(json.dumps(p, indent=1))

    tot, future = len(chiavi(p)), len(chiavi(p, anche_future=True)) - len(chiavi(p))
    print(f"\n{tot} ricerche da monitorare ({len(combinazioni(p))} A/R, {len(sole_andate(p))} sole andate)"
          + (f", +{future} non ancora possibili" if future else "") + f". Dati in {cartella}")
    print(f"Aggiornamento ogni {p['frequenza_minuti']} min (si allunga da solo se Google limita). Ctrl+C per fermare.")

    if sys.stdout.isatty():
        # primp scrive i suoi errori di connessione direttamente sui descrittori 1 e 2 e
        # rompe la barra: li mando in un file. print() e gli errori Python restano sul terminale.
        sys.stdout.flush()
        sys.stdout = os.fdopen(os.dup(1), "w", buffering=1)
        sys.stderr = os.fdopen(os.dup(2), "w", buffering=1)
        with open(cartella / "errori_rete.log", "a") as log:
            os.dup2(log.fileno(), 1)
            os.dup2(log.fileno(), 2)

    client = nuovo_client()
    ritmo = Ritmo()
    tratta = nome_tratta(p)
    primo = True
    try:
        while True:
            t0 = time.monotonic()
            bloccato, messaggio = giro(p, cartella, client, ritmo, primo=primo)
            primo = False
            avviso = None
            if bloccato and ritmo.livello < Ritmo.LIVELLO_MAX:
                ritmo.livello += 1
                avviso = f"⚠️ <b>Rallento</b>: Google limita le richieste ({html.escape(bloccato)})."
            elif bloccato:
                avviso = f"⚠️ Google limita ancora le richieste ({html.escape(bloccato)}), resto al ritmo minimo."
            elif ritmo.livello > 0:
                ritmo.livello -= 1
                avviso = "✅ <b>Accelero</b>: Google risponde di nuovo normalmente."
            attesa = max(0, ritmo.intervallo_minuti(p["frequenza_minuti"]) * 60 - (time.monotonic() - t0))
            prossimo = f"⏱ Prossimo controllo alle {datetime.now() + timedelta(seconds=attesa):%H:%M}"
            if avviso:
                stato = ritmo.descrizione(p["frequenza_minuti"])
                print(f"\n[ritmo] {re.sub('<[^>]+>', '', avviso)} Ora {stato}.")
                telegram_bot.invia(f"{avviso}\n{html.escape(tratta)}\nOra {stato}.\n{prossimo}")
            if messaggio:
                telegram_bot.invia(f"{messaggio}\n\n{prossimo}")
            conto_alla_rovescia(attesa)
    except KeyboardInterrupt:
        print("\nFermato.")
        telegram_bot.invia(f"⏹ <b>Tracker fermato</b> da te (Ctrl+C)\n{html.escape(tratta)}")
    except Exception as e:
        telegram_bot.invia(f"❌ <b>Tracker fermato</b> per un errore\n{html.escape(tratta)}\n"
                           f"<code>{html.escape(f'{type(e).__name__}: {e}')[:500]}</code>\n"
                           "Rilancialo dal terminale.")
        raise


if __name__ == "__main__":
    main()
