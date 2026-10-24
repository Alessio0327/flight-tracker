"""Parametri della ricerca: domande all'avvio, controllo del periodo, file JSON.
"""

import calendar
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from google_flights import nuovo_client, voli_in_vendita
from interfaccia import testo_durata, testo_scali
from lingua import t
from luoghi import Luoghi
from ricerca import (
    GIORNI_WEEKEND_MAX, LIMITE_CALENDARIO_GIORNI, LIMITE_RICERCA_GIORNI, aeroporti, chiavi, etichetta, limite,
    nomi, ultima_data,
)
import google_flights
import lingua
import ricerca


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
        _, nome = luoghi.per_aeroporto[codice]
        return {"nome": nome, "aeroporti": [codice]}

    trovate = luoghi.cerca(testo)[:8]
    if not trovate:
        print(t("nessuna_citta", testo=testo))
        return None
    citta = trovate[0]
    if len(trovate) > 1:
        for i, c in enumerate(trovate, 1):
            elenco = ", ".join(f"{a} {n}" for a, n in luoghi.aeroporti[c["code"]])
            print(f"  [{i}] {luoghi.nome_citta(c)}, {luoghi.nome_paese(c['country_code'])}  ({elenco})")
        n = chiedi(t("quale_citta", testo=testo), indici(len(trovate), default=[1]))
        citta = trovate[n[0] - 1]

    aeroporti = luoghi.aeroporti[citta["code"]]
    if len(aeroporti) > 1:
        for i, (a, n) in enumerate(aeroporti, 1):
            print(f"  [{i}] {a} {n}")
        scelti = chiedi(t("aeroporti_domanda"), indici(len(aeroporti)))
        aeroporti = [aeroporti[i - 1] for i in scelti] if scelti else aeroporti
    return {"nome": luoghi.nome_citta(citta), "aeroporti": [a for a, _ in aeroporti]}


def chiedi_citta(luoghi, ruolo, default=None):
    """Una o due citta' (con i loro aeroporti) per un ruolo, es. "partenza dell'andata".

    Con default, Invio alla prima domanda riusa quelle citta'.
    """
    suggerimento = t("invio_uguale", valore=etichetta(default) if default else "1")
    n = chiedi(t("quante_citta", ruolo=ruolo, suggerimento=suggerimento), scelta("", "1", "2"))
    if not n and default:
        return default
    elenco = []
    for i in range(1, int(n or "1") + 1):
        domanda = t("citta_domanda", ruolo=ruolo, Ruolo=ruolo[0].upper() + ruolo[1:],
                    numero=f" {i}" if n == "2" else "")
        while True:
            c = scegli_luogo(luoghi, input(domanda).strip())
            # Le ricerche usano il nome della citta': due nomi uguali si confonderebbero.
            if c and any(x["nome"] == c["nome"] for x in elenco):
                print(t("citta_doppia", nome=c["nome"]))
            elif c:
                break
        elenco.append(c)
    return elenco


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
            raise ValueError(t("numeri_tra", massimo=massimo))
        return n
    return conv


def mese(s):
    m = re.fullmatch(r"(\d{4})-(\d{1,2})|(\d{1,2})/(\d{4}|\d{2})", s)
    if not m:
        raise ValueError(t("formato_mese"))
    anno, num = (m[1], m[2]) if m[1] else (m[4], m[3])
    anno, num = int(anno), int(num)
    if anno < 100:  # anno a due cifre: 27 -> 2027
        anno += 2000
    if not 1 <= num <= 12:
        raise ValueError(t("mese_non_valido"))
    return date(anno, num, 1), date(anno, num, calendar.monthrange(anno, num)[1])


def data(s):
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(t("formato_data"))


def intero(minimo):
    def conv(s):
        n = int(s) if s.isdigit() else None
        if n is None or n < minimo:
            raise ValueError(t("serve_intero", minimo=minimo))
        return n
    return conv


def tra(minimo, massimo):
    def conv(s):
        n = int(s) if s.isdigit() else None
        if n is None or not minimo <= n <= massimo:
            raise ValueError(t("serve_tra", minimo=minimo, massimo=massimo))
        return n
    return conv


def scali(s):
    if not s:
        return None
    return intero(0)(s)


def valuta(s):
    if not s:
        return "EUR"
    if not re.fullmatch(r"[A-Za-z]{3}", s):
        raise ValueError(t("formato_valuta"))
    return s.upper()


def scelta(*valori):
    def conv(s):
        if s not in valori:
            raise ValueError(t("rispondi", valori=t("oppure").join(v for v in valori if v)))
        return s
    return conv


def chiedi_periodo():
    modo = chiedi(t("periodo_domanda"), scelta("1", "2"))
    if modo == "1":
        inizio, fine = chiedi(t("mese_domanda"), mese)
    else:
        centro = chiedi(t("data_domanda"), data)
        delta = chiedi(t("giorni_domanda"), intero(0))
        inizio, fine = centro - timedelta(days=delta), centro + timedelta(days=delta)
    return max(inizio, ricerca.oggi() + timedelta(days=1)), fine


def controlla_periodo(client, p, inizio, fine):
    """Verifica il periodo sul calendario. Ritorna "ok", "periodo" o "citta" (cosa richiedere)."""
    lim_ricerca, lim_cal = limite(LIMITE_RICERCA_GIORNI), limite(LIMITE_CALENDARIO_GIORNI)
    if fine < inizio:
        print(t("periodo_passato"))
        return "periodo"
    if inizio > lim_ricerca:
        print(t("oltre_limite", limite=f"{lim_ricerca:%d/%m/%Y}", inizio=f"{inizio:%d/%m/%Y}"))
        scelta_ = chiedi(t("oltre_limite_scelta"), scelta("1", "2"))
        return "periodo" if scelta_ == "1" else "ok"
    if inizio > lim_cal:
        print(t("oltre_calendario", limite=f"{lim_cal:%d/%m/%Y}"))
        return "ok"
    fine_cal = min(fine, lim_cal)
    # Il ritorno parte dopo: si controlla un mese in piu' (la durata non e' ancora nota).
    lati = [(t("lato_andata"), p["andata"], inizio, fine_cal)]
    if p["tipo"] == "diversa":
        lati.append((t("lato_ritorno"), p["ritorno"], inizio, min(fine + timedelta(days=30), lim_cal)))
    print(t("controllo_vendita"))
    for nome, lato, da, a in lati:
        try:
            trovate = voli_in_vendita(client, aeroporti(lato["da"]), aeroporti(lato["a"]), da, a)
        except Exception as e:  # noqa: BLE001 - senza verifica si prosegue comunque
            print(t("verifica_fallita", errore=e))
            return "ok"
        if not trovate:
            print(t("nessun_volo", lato=nome, da=nomi(lato["da"]), a=nomi(lato["a"]),
                    inizio=f"{da:%d/%m/%Y}", fine=f"{a:%d/%m/%Y}"))
            print(t("controlla_citta", da=etichetta(lato["da"]), a=etichetta(lato["a"])))
            scelta_ = chiedi(t("cambia_scelta"), scelta("1", "2"))
            return "periodo" if scelta_ == "1" else "citta"
        print(t("voli_trovati", lato=nome, date=len(trovate), totale=(a - da).days + 1, prezzo=min(trovate.values())))
    if fine > lim_cal:
        print(t("calendario_non_vede", limite=f"{lim_cal:%d/%m/%Y}"))
    return "ok"


def _leggi_citta(valore, dove):
    if not isinstance(valore, list) or not 1 <= len(valore) <= 2:
        raise ValueError(t("lista_citta", dove=dove))
    out = []
    for c in valore:
        if (not isinstance(c, dict) or not isinstance(c.get("nome"), str)
                or not isinstance(c.get("aeroporti"), list) or not c["aeroporti"]):
            raise ValueError(t("formato_citta", dove=dove))
        out.append({"nome": c["nome"], "aeroporti": [str(a).upper() for a in c["aeroporti"]]})
    if len({c["nome"] for c in out}) < len(out):
        raise ValueError(t("citta_doppie", dove=dove))
    return out


def parametri_da_file(percorso, lingua_scelta=None):
    """Parametri da un file JSON (formato in ricerche/esempio.json). ValueError se non valido.

    Senza lingua_scelta (avvio diretto dal file) vale il campo "lingua" del file, o
    l'italiano se manca. Con lingua_scelta (lingua scelta all'avvio) vale quella, e il
    campo "lingua" del file viene aggiornato, cosi' file e tool restano coerenti.
    """
    percorso = Path(percorso).expanduser()
    try:
        f = json.loads(percorso.read_text(encoding="utf-8"))
    except OSError as e:
        raise ValueError(t("file_illeggibile", errore=e.strerror)) from None
    except json.JSONDecodeError as e:
        raise ValueError(t("json_non_valido", riga=e.lineno, errore=e.msg)) from None
    if not isinstance(f, dict):
        raise ValueError(t("struttura_non_valida"))
    if lingua_scelta is None:
        if f.get("lingua", "it") not in lingua.LINGUE:
            raise ValueError(t("lingua_non_valida"))
        lingua.imposta(f.get("lingua", "it"))
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
        inizio = max(inizio, ricerca.oggi() + timedelta(days=1))
        # Nel weekend la durata e' facoltativa (default 1-4 giorni di calendario).
        durata = f.get("durata") or ({"min": 1, "max": GIORNI_WEEKEND_MAX} if f.get("weekend") else f["durata"])
        p = {
            "tipo": tipo, "andata": andata, "ritorno": ritorno,
            "inizio": inizio.isoformat(), "fine": fine.isoformat(),
            "weekend": bool(f.get("weekend")),
            "giorni_min": int(durata["min"]), "giorni_max": int(durata["max"]),
            "max_scali": None if f.get("max_scali") is None else int(f["max_scali"]),
            "top": int(f.get("top", 5)), "frequenza_minuti": int(f.get("frequenza_minuti", 30)),
            "valuta": valuta(str(f.get("valuta") or "")),
            "lingua": lingua.LINGUA,
        }
    except KeyError as e:
        raise ValueError(t("manca_campo", campo=e)) from None
    except (TypeError, AttributeError):
        raise ValueError(t("struttura_non_valida")) from None
    except ValueError as e:
        if str(e) == t("formato_valuta"):
            raise ValueError(t("valuta_non_valida")) from None
        raise
    if fine < inizio:
        raise ValueError(t("periodo_vuoto"))
    if p["weekend"]:
        # Nel file la durata del weekend e' in giorni di calendario, come nelle domande.
        if not 1 <= p["giorni_min"] <= p["giorni_max"] <= GIORNI_WEEKEND_MAX:
            raise ValueError(t("durata_weekend_non_valida"))
        p["giorni_min"] -= 1
        p["giorni_max"] -= 1
    elif not 1 <= p["giorni_min"] <= p["giorni_max"]:
        raise ValueError(t("durata_non_valida"))
    if p["top"] < 1 or p["frequenza_minuti"] < 1 or (p["max_scali"] or 0) < 0:
        raise ValueError(t("valori_non_validi"))
    if lingua_scelta is not None and f.get("lingua") != lingua_scelta:
        f = {"lingua": lingua_scelta, **{k: v for k, v in f.items() if k != "lingua"}}
        percorso.write_text(json.dumps(f, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(t("file_lingua_aggiornata", file=percorso))
    return p


def chiedi_file():
    def conv(s):
        # Un file trascinato nel Terminale arriva con spazi protetti o tra apici.
        s = s.strip().strip("'\"").replace("\\ ", " ")
        if not s:
            raise ValueError(t("scrivi_percorso"))
        return parametri_da_file(s, lingua_scelta=lingua.LINGUA)
    p = chiedi(t("percorso_domanda"), conv)
    stampa_riassunto(p)
    return p


def stampa_riassunto(p):
    print(t("riassunto_file",
            andata_da=etichetta(p["andata"]["da"]), andata_a=etichetta(p["andata"]["a"]),
            ritorno_da=etichetta(p["ritorno"]["da"]), ritorno_a=etichetta(p["ritorno"]["a"]),
            inizio=f"{date.fromisoformat(p['inizio']):%d/%m/%Y}", fine=f"{date.fromisoformat(p['fine']):%d/%m/%Y}",
            durata=testo_durata(p), scali=testo_scali(p["max_scali"]),
            top=p["top"], frequenza=p["frequenza_minuti"], valuta=p.get("valuta", "EUR")))


def chiedi_parametri():
    if chiedi(t("modo_domanda"), scelta("", "1", "2")) == "2":
        return chiedi_file()
    # Paese dell'utente (dall'IP, o dalla lingua) per proporre prima le sue citta'.
    paese = (google_flights.posizione() or {}).get("paese") or {"it": "IT"}.get(lingua.LINGUA)
    try:
        luoghi = Luoghi(lingua.LINGUA, paese)
    except OSError as e:  # primo avvio senza internet: niente copia locale delle citta'
        raise SystemExit(t("luoghi_offline", errore=e)) from None
    client = nuovo_client()
    p = {}
    print(t("date_cercabili", limite=f"{limite(LIMITE_RICERCA_GIORNI):%d/%m/%Y}", giorni=LIMITE_RICERCA_GIORNI))
    while True:
        p["tipo"] = {"1": "stessa", "2": "diversa"}[chiedi(t("tipo_domanda"), scelta("1", "2"))]
        print(t("titolo_andata"))
        andata = {"da": chiedi_citta(luoghi, t("ruolo_partenza")), "a": chiedi_citta(luoghi, t("ruolo_arrivo"))}
        if p["tipo"] == "stessa":
            ritorno = {"da": andata["a"], "a": andata["da"]}
        else:
            print(t("titolo_ritorno"))
            ritorno = {
                "da": chiedi_citta(luoghi, t("ruolo_partenza_ritorno"), default=andata["a"]),
                "a": chiedi_citta(luoghi, t("ruolo_arrivo_ritorno"), default=andata["da"]),
            }
        p["andata"], p["ritorno"] = andata, ritorno
        if "valuta" not in p:
            # Prima del controllo del periodo, che mostra gia' dei prezzi.
            p["valuta"] = chiedi(t("valuta_domanda"), valuta)
            lingua.imposta_valuta(p["valuta"])
        while (esito := controlla_periodo(client, p, *(periodo := chiedi_periodo()))) == "periodo":
            pass
        if esito == "ok":
            break
    inizio, fine = periodo
    p["inizio"], p["fine"] = inizio.isoformat(), fine.isoformat()
    while True:
        p["weekend"] = chiedi(t("modo_durata_domanda"), scelta("", "1", "2")) == "2"
        if p["weekend"]:
            # Si chiedono giorni di calendario (ven -> dom = 3), si salvano differenze tra date.
            minimo = chiedi(t("weekend_min_domanda"), tra(1, GIORNI_WEEKEND_MAX))
            massimo = chiedi(t("weekend_max_domanda", minimo=minimo), tra(minimo, GIORNI_WEEKEND_MAX))
            p["giorni_min"], p["giorni_max"] = minimo - 1, massimo - 1
        else:
            p["giorni_min"] = chiedi(t("durata_min_domanda"), intero(1))
            p["giorni_max"] = chiedi(t("durata_max_domanda"), intero(p["giorni_min"]))
        tot, ora = len(chiavi(p, anche_future=True)), len(chiavi(p))
        if ora == tot:
            break
        print(t("ricerche_future", future=tot - ora, totale=tot, limite=f"{limite(LIMITE_RICERCA_GIORNI):%d/%m/%Y}"))
        if ora == 0:
            primo = min(ultima_data(k) for k in chiavi(p, anche_future=True))
            print(t("nessuna_cercabile", data=f"{primo - timedelta(days=LIMITE_RICERCA_GIORNI):%d/%m/%Y}"))
            if chiedi(t("cambia_durata"), scelta("1", "2")) == "1":
                continue
        break
    p["max_scali"] = chiedi(t("scali_domanda"), scali)
    p["top"] = chiedi(t("top_domanda"), intero(1))
    p["frequenza_minuti"] = chiedi(t("frequenza_domanda"), intero(1))
    p["lingua"] = lingua.LINGUA
    return p


def chiedi_lingua():
    lingua.imposta({"": "it", "1": "it", "2": "en"}[chiedi(t("lingua_domanda"), scelta("", "1", "2"))])
