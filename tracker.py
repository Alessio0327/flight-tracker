"""Monitor prezzi voli andata/ritorno su Google Flights.

All'avvio chiede citta' di partenza e destinazione (risolte in aeroporti),
periodo di partenza, durata, top N e frequenza, poi
ripete la ricerca ogni N minuti finche' non lo fermi (Ctrl+C).

Ogni giro:
  1. stima il prezzo di tutte le coppie (data andata, data ritorno) dal calendario
     prezzi di Google (una richiesta per durata e coppia di aeroporti);
  2. verifica con la ricerca completa la top attuale e le stime piu' basse (ogni
     ricerca copre tutti gli aeroporti scelti insieme);
  3. salva prezzi e storico nella cartella dell'istanza (data/<parametri>/);
  3. per la top, apre le pagine di prenotazione e prende il venditore piu' economico
     (le agenzie spesso costano meno del prezzo in lista);
  4. scrive la top N in top.txt e notifica (macOS/Telegram) se il prezzo minimo scende.

Piu' istanze possono girare insieme, ognuna in un terminale: ogni combinazione di
parametri ha la sua cartella. Rilanciare con gli stessi parametri riprende i dati salvati.

Uso: .venv/bin/python tracker.py
     .venv/bin/python tracker.py --setup-telegram   (attiva notifiche Telegram)
"""

import calendar
import csv
import fcntl
import html
import json
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
ITINERARI_VENDITORI = 4  # itinerari (orari) di cui aprire la pagina di prenotazione, per combinazione
PAUSA_CALENDARIO = 1


# --- input utente -----------------------------------------------------------

def chiedi(domanda, converti):
    """Ripete la domanda finche' converti(risposta) non va a buon fine."""
    while True:
        try:
            return converti(input(domanda).strip())
        except ValueError as e:
            print(f"  {e}")


def scegli_luogo(luoghi, testo):
    """Un nome di citta' (o codice IATA) -> (etichetta, [aeroporti]), o None."""
    codice = testo.upper()
    if codice in luoghi.per_aeroporto and codice not in luoghi.aeroporti:
        citta, nome = luoghi.per_aeroporto[codice]
        return f"{nome} ({codice})", [codice]

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
    codici = [a for a, _ in aeroporti]
    return f"{luoghi.nome_citta(citta)} ({', '.join(codici)})", codici


def chiedi_luoghi(luoghi, domanda):
    """Una o piu' citta' separate da virgola -> {etichetta, aeroporti}."""
    while True:
        parti = [x.strip() for x in input(domanda).split(",") if x.strip()]
        risolti = [scegli_luogo(luoghi, x) for x in parti]
        if risolti and all(risolti):
            aeroporti = list(dict.fromkeys(a for _, lista in risolti for a in lista))
            return {"etichetta": " + ".join(e for e, _ in risolti), "aeroporti": aeroporti}
        if not parti:
            print("  scrivi almeno una citta'")


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
            raise ValueError(f"rispondi {' o '.join(valori)}")
        return s
    return conv


def chiedi_parametri():
    luoghi = Luoghi()
    p = {}
    p["origine"] = chiedi_luoghi(luoghi, "Citta' di partenza (es. Roma): ")
    p["destinazione"] = chiedi_luoghi(luoghi, "Citta' di destinazione (piu' di una separate da virgola, es. Tokyo, Osaka): ")
    modo = chiedi("Periodo di partenza: [1] un mese  [2] intorno a una data: ", scelta("1", "2"))
    if modo == "1":
        inizio, fine = chiedi("Mese (es. 10/2027): ", mese)
    else:
        centro = chiedi("Data (es. 15/10/2027): ", data)
        delta = chiedi("Quanti giorni prima/dopo quella data: ", intero(0))
        inizio, fine = centro - timedelta(days=delta), centro + timedelta(days=delta)
    p["inizio"], p["fine"] = inizio.isoformat(), fine.isoformat()
    p["giorni_min"] = chiedi("Durata minima viaggio (giorni): ", intero(1))
    p["giorni_max"] = chiedi("Durata massima viaggio (giorni): ", intero(p["giorni_min"]))
    p["max_scali"] = chiedi("Massimo scali per tratta (0 = solo diretti, Invio = qualsiasi): ", scali)
    p["top"] = chiedi("Quanti migliori risultati mostrare: ", intero(1))
    p["frequenza_minuti"] = chiedi("Frequenza aggiornamento (minuti): ", intero(1))
    return p


# --- ricerca -----------------------------------------------------------------

def combinazioni(p):
    """Tutte le coppie "andata|ritorno" che rispettano i parametri."""
    inizio, fine = date.fromisoformat(p["inizio"]), date.fromisoformat(p["fine"])
    andata = max(inizio, date.today() + timedelta(days=1))
    out = []
    while andata <= fine:
        for durata in range(p["giorni_min"], p["giorni_max"] + 1):
            out.append(f"{andata.isoformat()}|{(andata + timedelta(days=durata)).isoformat()}")
        andata += timedelta(days=1)
    return out


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
    base = create_query(flights=[], trip="round-trip", passengers=Passengers(adults=1))
    tfs = b64encode(base.to_bytes() + _tratta(andata, org, dst, max_scali) + _tratta(ritorno, dst, org, max_scali)).decode()
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
        org = [[FliAirport[a], 0] for a in p["origine"]["aeroporti"]]
        dst = [[FliAirport[a], 0] for a in p["destinazione"]["aeroporti"]]
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
    """Prezzi stimati A/R per ogni partenza tra da e a (max 61 giorni), durata fissa.

    Usa GetCalendarGraph, l'API interna del grafico prezzi di Google Flights:
    una richiesta copre tutte le date. Formato ricavato dalla libreria `fli`
    (github.com/punitarani/fli), non documentato da Google.
    Ritorna {"andata|ritorno": prezzo}.
    """
    stops = {None: 0, 0: 1, 1: 2, 2: 3}.get(max_scali, 0)

    def segmento(da_aer, a_aer, giorno, tipo):
        return [[[[da_aer, 0]]], [[[a_aer, 0]]], None, stops, None, None, giorno,
                None, None, None, None, None, None, None, tipo]

    ritorno = (date.fromisoformat(da) + timedelta(days=durata)).isoformat()
    filtri = [
        None,
        [None, None, 1, None, [], 1, [1, 0, 0, 0], None, None, None, None, None, None,
         [segmento(org, dst, da, 3), segmento(dst, org, ritorno, 1)], None, None, None, 1],
        [da, a],
        None,
        [durata, durata],
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
                    out[f"{item[0]}|{item[1]}"] = item[2][0][1]
                except (IndexError, TypeError):
                    continue
    return out


def scansione_calendario(client, p, ritmo):
    """Stime per tutte le combinazioni: una chiamata per coppia di aeroporti e durata.

    Una chiamata per coppia, non tutti gli aeroporti insieme: con piu' aeroporti
    (es. KIX+ITM+UKB) il calendario restituisce quasi sempre un solo risultato.
    """
    inizio = max(date.fromisoformat(p["inizio"]), date.today() + timedelta(days=1))
    fine = date.fromisoformat(p["fine"])
    finestre = []
    while inizio <= fine:
        finestre.append((inizio, min(fine, inizio + timedelta(days=MAX_GIORNI_CALENDARIO - 1))))
        inizio += timedelta(days=MAX_GIORNI_CALENDARIO)
    chiamate = [
        (o, d, da, a, durata)
        for o in p["origine"]["aeroporti"]
        for d in p["destinazione"]["aeroporti"]
        for da, a in finestre
        for durata in range(p["giorni_min"], p["giorni_max"] + 1)
    ]
    print()
    stime, errori = {}, 0
    with Barra("Calendario", len(chiamate)) as barra:
        for o, d, da, a, durata in chiamate:
            try:
                for k, prezzo in calendario(client, o, d, da.isoformat(), a.isoformat(), durata, p["max_scali"]).items():
                    stime[k] = min(prezzo, stime.get(k, prezzo))
            except Bloccato:
                raise
            except Exception as e:  # noqa: BLE001 - senza calendario si usa solo la ricerca precisa
                errori += 1
                barra.scrivi(f"[errore calendario] {o}-{d} {durata} gg: {e}")
                if errori >= 5:
                    barra.scrivi("[stop calendario] troppi errori, continuo con la ricerca precisa")
                    break
            barra.avanza(f"{len(stime)} date stimate" + (f", da {min(stime.values())} EUR" if stime else ""))
            time.sleep(ritmo.pausa_calendario())
    return stime


def notifica(titolo, testo):
    if sys.platform == "darwin":
        script = f"display notification {json.dumps(testo)} with title {json.dumps(titolo)}"
        subprocess.run(["osascript", "-e", script], check=False)


def giro(p, cartella, client, ritmo):
    """Un giro di ricerche. Ritorna (motivo del blocco o None, messaggio Telegram o None)."""
    prezzi_path = cartella / "prezzi.json"
    try:
        prezzi = json.loads(prezzi_path.read_text())
    except FileNotFoundError:
        prezzi = {}

    tutte = combinazioni(p)
    valide = set(tutte)
    prezzi = {k: v for k, v in prezzi.items() if k in valide}  # date ormai passate

    # 1. Stima veloce di tutte le combinazioni dal calendario prezzi.
    bloccato = None
    try:
        stime = {k: v for k, v in scansione_calendario(client, p, ritmo).items() if k in valide}
    except Bloccato as e:
        bloccato, stime = str(e), {}

    # 2. Ricerca precisa: top attuale, poi le stime piu' basse, poi a rotazione tutte
    #    le altre (mai verificate prima). La rotazione serve: il calendario non vede
    #    tutte le tariffe (es. China Eastern 751 EUR stimata 833), quindi una stima
    #    alta non basta per scartare una combinazione.
    budget = ritmo.budget(p["frequenza_minuti"]) if not bloccato else 0
    note = sorted((k for k in prezzi if migliore(prezzi[k])), key=lambda k: migliore(prezzi[k]))
    da_fare = note[: min(p["top"], budget // 2)]
    da_fare += [k for k in sorted(stime, key=stime.get) if k not in da_fare][:VERIFICA_DA_STIMA]
    da_fare = da_fare[:budget]
    rotazione = sorted(
        (k for k in tutte if k not in da_fare),
        key=lambda k: prezzi.get(k, {}).get("controllato", ""),
    )
    da_fare += rotazione[: budget - len(da_fare)]
    motivo = {k: "top" if k in note[: p["top"]] else "stima" if k in stime and k not in rotazione else "rotazione"
              for k in da_fare}
    if da_fare:
        conta = {m: sum(1 for k in da_fare if motivo[k] == m) for m in ("top", "stima", "rotazione")}
        print(
            f"\nVerifica precisa: {len(da_fare)} combinazioni "
            f"(top attuale {conta['top']}, stime migliori {conta['stima']}, a rotazione {conta['rotazione']})"
        )

    record_prima = migliore(prezzi[note[0]]) if note else None
    adesso = datetime.now().isoformat(timespec="seconds")
    errori = 0
    with open(cartella / "storico.csv", "a", newline="") as f, Barra("Verifica", len(da_fare)) as barra:
        storico = csv.writer(f)
        for k in da_fare:
            andata, ritorno = k.split("|")
            minimo = min((migliore(v) for v in prezzi.values() if migliore(v)), default=None)
            try:
                ris = cerca(
                    client, p["origine"]["aeroporti"], p["destinazione"]["aeroporti"],
                    andata, ritorno, p["max_scali"],
                )
            except Bloccato as e:
                bloccato = str(e)
                break
            except Exception as e:  # noqa: BLE001 - un errore non deve fermare il giro
                errori += 1
                barra.scrivi(f"[errore] {andata} -> {ritorno}: {e}")
                if errori >= 5:
                    bloccato = "5 errori di fila, probabile limitazione"
                    break
                barra.avanza()
                continue
            errori = 0
            if ris and (minimo is None or ris["prezzo"] < minimo):
                barra.scrivi(
                    f"★ nuovo minimo: {ris['prezzo']} EUR  {andata} -> {ritorno}  "
                    f"{ris['compagnie']} [{ris['tratte']}]"
                )
            if ris:
                minimo = ris["prezzo"] if minimo is None else min(minimo, ris["prezzo"])
            barra.avanza(f"minimo {minimo} EUR" if minimo else "")
            # Il venditore resta finche' la fase 3 non lo ricontrolla.
            prezzi[k] = {**(ris or {"prezzo": None}), "controllato": adesso,
                         "venditore": prezzi.get(k, {}).get("venditore") if ris else None}
            if ris:
                storico.writerow([adesso, andata, ritorno, ris["prezzo"], ris["compagnie"], ris["tratte"]])
                f.flush()
            # Salva subito: Ctrl+C a meta' giro non perde le ricerche fatte.
            prezzi_path.write_text(json.dumps(prezzi, indent=1, ensure_ascii=False))
            time.sleep(ritmo.pausa())
    # 3. Venditori: per la top, prezzi di agenzie e compagnia nelle pagine di prenotazione.
    if not bloccato:
        candidati = sorted((k for k in prezzi if migliore(prezzi[k])), key=lambda k: migliore(prezzi[k]))[: p["top"]]
        minimo = migliore(prezzi[candidati[0]]) if candidati else None
        cercatore, errori = SearchFlights(), 0
        print(f"\nPrezzi dei venditori (agenzie comprese) per la top {len(candidati)}")
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

    top = sorted((k for k in prezzi if migliore(prezzi[k])), key=lambda k: migliore(prezzi[k]))[: p["top"]]
    tratta = f"{p['origine']['etichetta']} -> {p['destinazione']['etichetta']}"
    scali_txt = {None: "scali qualsiasi", 0: "solo diretti", 1: "max 1 scalo"}.get(
        p["max_scali"], f"max {p['max_scali']} scali"
    )
    stimate = len(valide & (set(stime) | set(prezzi)))
    verificate = len(valide & set(prezzi))
    copertura = (
        f"stimate {stimate}/{len(valide)} combinazioni, "
        f"verificate col prezzo completo {verificate}/{len(valide)}"
        + (" (scansione completa)" if verificate == len(valide) else " (scansione in corso)")
    )
    righe = [
        f"Top {len(top)} {tratta}, partenza {p['inizio']} .. {p['fine']}, "
        f"{p['giorni_min']}-{p['giorni_max']} giorni, {scali_txt} (aggiornato {adesso})",
        copertura[0].upper() + copertura[1:],
        "",
    ]
    for i, k in enumerate(top, 1):
        v = prezzi[k]
        andata, ritorno = k.split("|")
        giorni = (date.fromisoformat(ritorno) - date.fromisoformat(andata)).days
        righe.append(
            f"{i}. {descrivi_prezzo(v)}  {andata} -> {ritorno} ({giorni} gg)  "
            f"{v['compagnie']}  [{v['tratte']}]  visto {v['controllato']}\n"
            + (f"   Prezzo {giudizio(v)}\n" if giudizio(v) else "")
            + f"   {v['link']}"
        )
    if not top:
        righe.append("Nessun prezzo ancora: date forse non in vendita.")
    testo = "\n".join(righe)
    (cartella / "top.txt").write_text(testo + "\n")
    print("\n" + "=" * 80 + "\n" + testo)

    if top and (record_prima is None or migliore(prezzi[top[0]]) < record_prima):
        andata, ritorno = top[0].split("|")
        etichetta = giudizio(prezzi[top[0]]).split(":")[0]
        notifica(
            f"Volo {tratta}: nuovo minimo",
            f"{migliore(prezzi[top[0]])} EUR {andata} -> {ritorno}" + (f" ({etichetta})" if etichetta else ""),
        )
        return bloccato, messaggio_telegram(tratta, top, prezzi, copertura)
    return bloccato, None


def messaggio_telegram(tratta, top, prezzi, copertura):
    """Top N in HTML per Telegram, con link cliccabili a Google Flights."""
    e = html.escape
    righe = [f"✈️ <b>Nuovo prezzo minimo</b>\n{e(tratta)}\n<i>{e(copertura)}</i>\n"]
    for i, k in enumerate(top, 1):
        v = prezzi[k]
        andata, ritorno = k.split("|")
        giorni = (date.fromisoformat(ritorno) - date.fromisoformat(andata)).days
        righe.append(
            f"{i}. <b>{migliore(v)} EUR</b>  {andata} → {ritorno} ({giorni} gg)\n"
            + (f"   su {e(v['venditore']['nome'])} ({v['prezzo']} EUR in lista, {e(v['venditore']['orari'])})\n"
               if migliore(v) < v["prezzo"] else "")
            + f"   {e(v['compagnie'])} [{e(v['tratte'])}]"
            + (f"\n   <i>{e(giudizio(v))}</i>" if giudizio(v) else "")
            + f"\n   <a href=\"{e(v['link'])}\">Apri su Google Flights</a>"
        )
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


def main():
    if "--setup-telegram" in sys.argv:
        telegram_bot.setup()
        return
    if not telegram_bot.configurato():
        print("(Notifiche Telegram non attive: per attivarle .venv/bin/python tracker.py --setup-telegram)\n")
    p = chiedi_parametri()
    nome = (
        f"{'_'.join(p['origine']['aeroporti'])}-{'_'.join(p['destinazione']['aeroporti'])}"
        f"-{p['inizio']}_{p['fine']}"
        f"-{p['giorni_min']}-{p['giorni_max']}gg-scali{'X' if p['max_scali'] is None else p['max_scali']}"
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

    tot = len(combinazioni(p))
    print(f"\n{tot} combinazioni da monitorare. Dati in {cartella}")
    print(f"Aggiornamento ogni {p['frequenza_minuti']} min (si allunga da solo se Google limita). Ctrl+C per fermare.")

    client = Client(
        impersonate="chrome_145",
        impersonate_os="macos",
        referer=True,
        headers={"Cookie": CONSENT_COOKIE},
    )
    ritmo = Ritmo()
    tratta = f"{p['origine']['etichetta']} -> {p['destinazione']['etichetta']}"
    try:
        while True:
            t0 = time.monotonic()
            bloccato, messaggio = giro(p, cartella, client, ritmo)
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


if __name__ == "__main__":
    main()
