"""Accesso a Google Flights: ricerca completa, calendario prezzi, venditori, IP di uscita.

Usa API interne e non documentate (fast-flights, fli e chiamate dirette): se Google
cambia formato, e' qui che va corretto.
"""

import json
import time
import urllib.parse
import urllib.request
from base64 import b64encode
from datetime import date, timedelta

from fast_flights import FlightQuery, Passengers, create_query
from fast_flights.pb.flights_pb2 import Airport
from primp import Client
from selectolax.lexbor import LexborHTMLParser
from fli.models import (
    Airport as FliAirport, FlightSearchFilters, FlightSegment, MaxStops, PassengerInfo, SeatType,
    SortBy, TripType,
)

from interfaccia import Barra
from lingua import t
from ricerca import LIMITE_CALENDARIO_GIORNI, aeroporti, citta_ar, finestra_partenze, finestra_ritorni, limite
import lingua


URL = "https://www.google.com/travel/flights"
# Senza questi cookie Google (da IP europeo) risponde con la pagina di consenso.
CONSENT_COOKIE = "SOCS=CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg; CONSENT=YES+"
CALENDARIO_URL = (
    "https://www.google.com/_/FlightsFrontendUi/data/"
    "travel.frontend.flights.FlightsFrontendService/GetCalendarGraph"
)
MAX_GIORNI_CALENDARIO = 61
ITINERARI_VENDITORI = 4  # itinerari (orari) di cui aprire la pagina di prenotazione, per combinazione
# Servizi per IP pubblico e paese di uscita (Google adatta i prezzi al paese da cui cerchi).
GEOLOCALIZZAZIONE = ("https://ipinfo.io/json", "https://api.country.is")


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


class FormatoCambiato(RuntimeError):
    """La risposta di Google non ha piu' la struttura attesa: va aggiornato il tool."""


def controlla_blocco(r):
    if r.status_code == 429:
        raise Bloccato(t("http_429"))
    if "/sorry/" in str(getattr(r, "url", "")) or "unusual traffic" in r.text[:20000]:
        raise Bloccato(t("captcha"))


def cerca(client, org, dst, andata, ritorno, max_scali=None):
    """Volo A/R piu' economico tra tutti gli aeroporti, o None se non in vendita."""
    return _cerca(client, "round-trip", [(andata, org, dst), (ritorno, dst, org)], max_scali)


def cerca_sola_andata(client, giorno, org, dst, max_scali=None):
    """Volo di sola andata piu' economico tra tutti gli aeroporti, o None."""
    return _cerca(client, "one-way", [(giorno, org, dst)], max_scali)


def _cerca(client, viaggio, tratte, max_scali):
    base = create_query(flights=[], trip=viaggio, passengers=Passengers(adults=1))
    tfs = b64encode(base.to_bytes() + b"".join(_tratta(g, da, a, max_scali) for g, da, a in tratte)).decode()
    params = {"tfs": tfs, "hl": "it", "curr": lingua.VALUTA}
    link = f"{URL}/search?tfs={tfs}&hl={lingua.LINGUA}&curr={lingua.VALUTA}"
    r = client.get(URL, params=params)
    controlla_blocco(r)
    script = LexborHTMLParser(r.text).css_first(r"script.ds\:1")
    if script is None or "data:" not in script.text():
        raise FormatoCambiato(t("risposta_inattesa"))
    payload_str = script.text().split("data:", 1)[1].rsplit(",", 1)[0]
    if payload_str.endswith("errorHasStatus: true"):
        return None
    try:
        payload = json.loads(payload_str)
    except ValueError:
        raise FormatoCambiato(t("risposta_inattesa")) from None
    if not isinstance(payload, list):
        raise FormatoCambiato(t("risposta_inattesa"))

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
    itinerari = cercatore.search(filtri, top_n=ITINERARI_VENDITORI, currency=lingua.VALUTA, language="it",
                                 country="IT") or []
    # Per l'A/R il prezzo del volo di ritorno e' il totale dell'itinerario.
    itinerari = sorted((it for it in itinerari if it[1].price), key=lambda it: it[1].price)
    meglio = None
    for andata_v, ritorno_v in itinerari[:ITINERARI_VENDITORI]:
        for o in cercatore.get_booking_options((andata_v, ritorno_v), filtri, currency=lingua.VALUTA, language="it", country="IT"):
            if o.price and (meglio is None or o.price < meglio["prezzo"]):
                meglio = {
                    "prezzo": round(o.price),
                    "nome": o.vendor_name,
                    "ora_andata": f"{andata_v.legs[0].departure_datetime:%H:%M}",
                    "ora_ritorno": f"{ritorno_v.legs[0].departure_datetime:%H:%M}",
                }
    return meglio


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
        CALENDARIO_URL, params={"hl": "it", "curr": lingua.VALUTA}, data=corpo,
        headers={"content-type": "application/x-www-form-urlencoded;charset=UTF-8"},
    )
    controlla_blocco(r)
    if r.status_code != 200:
        raise RuntimeError(t("calendario_http", codice=r.status_code))
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
    with Barra(t("barra_calendario"), len(chiamate)) as barra:
        for prefisso, o, d, da, a, durata in chiamate:
            try:
                for k, prezzo in calendario(client, o, d, da.isoformat(), a.isoformat(), durata, p["max_scali"]).items():
                    k = (prefisso or "") + k
                    stime[k] = min(prezzo, stime.get(k, prezzo))
            except Bloccato:
                raise
            except Exception as e:  # noqa: BLE001 - senza calendario si usa solo la ricerca precisa
                errori += 1
                barra.scrivi(t("errore_calendario", tratta=f"{o}-{d}", errore=e))
                if errori >= 5:
                    barra.scrivi(t("stop_calendario"))
                    break
            barra.avanza(t("prezzi_stimati", n=len(stime)))
            time.sleep(ritmo.pausa_calendario())
    return stime


def posizione():
    """IP pubblico e paese da cui escono le richieste (es. VPN), o None se non rilevabile.

    Google Flights adatta risultati e prezzi al paese dell'IP: con una VPN in Francia
    i prezzi possono essere diversi da quelli visti dall'Italia.
    """
    for url in GEOLOCALIZZAZIONE:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                d = json.loads(r.read())
            if d.get("ip") and d.get("country"):
                return {"ip": d["ip"], "paese": d["country"].upper(), "citta": d.get("city") or ""}
        except (OSError, ValueError):
            continue
    return None


def nuovo_client():
    return Client(impersonate="chrome_145", impersonate_os="macos", referer=True, headers={"Cookie": CONSENT_COOKIE})
