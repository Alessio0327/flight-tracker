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

Lingua italiana o inglese (lingua.py), scelta all'avvio o con il campo "lingua" del file JSON.
I parametri si possono anche leggere da un file JSON (vedi ricerche/esempio.json):
all'avvio il tool chiede se rispondere alle domande o indicare il file.

Moduli:
  tracker.py      avvio e ciclo dei controlli (giro)
  parametri.py    domande all'avvio, controllo del periodo, file JSON
  ricerca.py      date, combinazioni, limiti di Google, proposte, ritmo
  google_flights.py       richieste a Google Flights e IP di uscita
  interfaccia.py  testi della top, messaggi Telegram, barra di avanzamento
  lingua.py       testi in italiano e inglese
  telegram_bot.py iscrizioni e invio Telegram
  luoghi.py       citta' e aeroporti

Uso: .venv/bin/python tracker.py
     .venv/bin/python tracker.py ricerche/esempio.json   (avvio diretto, senza domande)
     .venv/bin/python tracker.py --setup-telegram   (attiva notifiche Telegram)
"""

import csv
import fcntl
import html
import json
import logging
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from fli.search import SearchFlights

from google_flights import Bloccato, nuovo_client
from interfaccia import (
    Barra, breve_posizione, confronto_varianti, conto_alla_rovescia, dettaglio, messaggio_telegram,
    nome_tratta, orari, riassunto, suggerimento, testo_copertura, testo_posizione, testo_scali,
)
from lingua import t
from parametri import chiedi_lingua, chiedi_parametri, parametri_da_file, stampa_riassunto
from ricerca import (
    Ritmo, VERIFICA_DA_STIMA, aeroporti, chiavi, citta_ar, combinazioni, fuori_periodo,
    periodo_allargato, proposte, proposte_verificate, sole_andate, tratta_sola_andata,
)
import google_flights
import interfaccia
import lingua
import telegram_bot


BASE = Path(__file__).resolve().parent


def giro(p, cartella, client, ritmo, primo=False, posizione_prima=None):
    """Un giro di ricerche. Ritorna (motivo del blocco o None, messaggio Telegram o None, posizione).

    Il messaggio c'e' solo con un nuovo prezzo minimo o al primo giro dopo l'avvio.
    """
    prezzi_path = cartella / "prezzi.json"
    try:
        prezzi = json.loads(prezzi_path.read_text())
    except FileNotFoundError:
        prezzi = {}

    tutte = chiavi(p)
    valide = set(tutte)
    prezzi = {k: v for k, v in prezzi.items() if k in valide}  # date ormai passate

    # Da dove escono le richieste: Google adatta i prezzi al paese dell'IP.
    pos = google_flights.posizione()
    print("\n" + testo_posizione(pos))
    cambiata = bool(pos and posizione_prima and pos["paese"] != posizione_prima["paese"])
    if pos and posizione_prima and pos["ip"] != posizione_prima["ip"]:
        print(t("posizione_cambiata", prima=breve_posizione(posizione_prima), ora=breve_posizione(pos)))

    # 1. Stima veloce di tutte le ricerche dal calendario prezzi. Il calendario guarda
    #    anche qualche giorno prima e dopo il periodo: una richiesta copre fino a 61 giorni,
    #    quindi di solito non costa richieste in piu'.
    largo = periodo_allargato(p)
    bloccato = None
    try:
        stime_larghe = google_flights.scansione_calendario(client, largo, ritmo)
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
    # Almeno un quarto del budget resta alla rotazione: con un budget piccolo (Google che
    # limita) top e stime lo userebbero tutto e alcune ricerche non verrebbero mai fatte.
    max_stime = min(VERIFICA_DA_STIMA, budget - len(da_fare) - budget // 4)
    for x in proposte(p, stime):
        if sum(1 for m in motivo.values() if m == "stima") >= max_stime:
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
        print(t("verifica_precisa", n=len(da_fare), top=conta["top"], stima=conta["stima"],
                rotazione=conta["rotazione"],
                fuori=t("fuori_periodo_conta", n=conta["fuori periodo"]) if conta["fuori periodo"] else ""))

    record_prima = verificate_prima[0]["prezzo"] if verificate_prima else None
    minimo = record_prima
    adesso = datetime.now().isoformat(timespec="seconds")
    errori = 0
    with open(cartella / "storico.csv", "a", newline="") as f, Barra(t("barra_verifica"), len(da_fare)) as barra:
        storico = csv.writer(f)
        for k in da_fare:
            try:
                if k.count("|") == 1:
                    andata, ritorno = k.split("|")
                    ris = google_flights.cerca(client, aeroporti(p["andata"]["da"]), aeroporti(citta_ar(p)),
                                andata, ritorno, p["max_scali"])
                else:
                    giorno, org, dst = tratta_sola_andata(largo, k)
                    ris = google_flights.cerca_sola_andata(client, giorno, org, dst, p["max_scali"])
            except Bloccato as e:
                bloccato = str(e)
                break
            except Exception as e:  # noqa: BLE001 - un errore non deve fermare il giro
                errori += 1
                barra.scrivi(t("errore_ricerca", chiave=k, errore=e))
                if errori >= 5:
                    bloccato = t("cinque_errori")
                    break
                barra.avanza()
                continue
            errori = 0
            # Il venditore resta finche' la fase 3 non lo ricontrolla.
            prezzi[k] = {**(ris or {"prezzo": None}), "controllato": adesso,
                         "venditore": prezzi.get(k, {}).get("venditore") if ris else None}
            if ris:
                a, b = k.split("|") if k.count("|") == 1 else (k.split("|")[2], k.rsplit("|", 1)[0])
                storico.writerow([adesso, a, b, ris["prezzo"], ris["compagnie"], ris["tratte"],
                                  pos["paese"] if pos else ""])
                f.flush()
                meglio = proposte_verificate(p, prezzi)
                if meglio and (minimo is None or meglio[0]["prezzo"] < minimo):
                    minimo = meglio[0]["prezzo"]
                    barra.scrivi(t("nuovo_minimo", testo=riassunto(meglio[0])))
            barra.avanza(t("minimo_barra", prezzo=minimo) if minimo else "")
            # Salva subito: Ctrl+C a meta' giro non perde le ricerche fatte.
            prezzi_path.write_text(json.dumps(prezzi, indent=1, ensure_ascii=False))
            time.sleep(ritmo.pausa())

    # 3. Venditori: per gli A/R in top, prezzi di agenzie e compagnia nelle pagine di
    #    prenotazione (per la sola andata fli non restituisce i venditori).
    if not bloccato:
        candidati = [x["chiavi"][0] for x in proposte_verificate(p, prezzi)[: p["top"]] if x["tipo"] == "ar"]
        cercatore, errori = SearchFlights(), 0
        if candidati:
            print(t("venditori_titolo", n=len(candidati)))
        with open(cartella / "storico.csv", "a", newline="") as f, Barra(t("barra_venditori"), len(candidati)) as barra:
            storico = csv.writer(f)
            for k in candidati:
                andata, ritorno = k.split("|")
                try:
                    ven = google_flights.prezzo_venditori(cercatore, p, andata, ritorno)
                except Exception as e:  # noqa: BLE001 - il prezzo della lista resta valido
                    if "429" in str(e):
                        bloccato = t("http_429_prenotazione")
                        break
                    errori += 1
                    barra.scrivi(t("errore_venditori", andata=andata, ritorno=ritorno, errore=e))
                    if errori >= 3:
                        break
                    barra.avanza()
                    continue
                if ven:
                    prezzi[k]["venditore"] = {**ven, "controllato": adesso}
                    storico.writerow([adesso, andata, ritorno, ven["prezzo"], t("venditore_storico", nome=ven["nome"]),
                                      orari(ven), pos["paese"] if pos else ""])
                    if minimo is None or ven["prezzo"] < minimo:
                        barra.scrivi(t("nuovo_minimo_venditore", prezzo=ven["prezzo"], nome=ven["nome"],
                                       andata=andata, ritorno=ritorno, orari=orari(ven)))
                        minimo = ven["prezzo"]
                barra.avanza(t("minimo_barra", prezzo=minimo) if minimo else "")
                prezzi_path.write_text(json.dumps(prezzi, indent=1, ensure_ascii=False))
                time.sleep(ritmo.pausa())
    if bloccato:
        print(t("blocco", motivo=bloccato))

    tutte_proposte = proposte_verificate(p, prezzi)
    top = tutte_proposte[: p["top"]]
    tratta = nome_tratta(p)
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
    if pos:
        cop["paese"] = pos["paese"]
        if cambiata:
            cop["paese_prima"] = posizione_prima["paese"]
    righe = [
        t("top_titolo", n=len(top), tratta=tratta, inizio=p["inizio"], fine=p["fine"], min=p["giorni_min"],
          max=p["giorni_max"], scali=testo_scali(p["max_scali"]), adesso=adesso),
        copertura[0].upper() + copertura[1:],
        testo_posizione(pos),
        "",
    ]
    for i, x in enumerate(top, 1):
        righe.append(f"{i}. " + dettaglio(x, prezzi))
    if not top:
        righe.append(t("nessun_prezzo_top"))
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
        interfaccia.notifica(t("notifica_titolo", tratta=tratta), riassunto(top[0]))
    # Al primo giro di ogni avvio la top completa arriva comunque, anche se i prezzi
    # vengono da un'esecuzione precedente.
    if nuovo or (primo and top):
        titolo = t("tg_nuovo_minimo") if nuovo else t("tg_avviato")
        return bloccato, messaggio_telegram(p, top, prezzi, cop, confronto + ([""] + consiglio if consiglio else []),
                                            titolo), pos
    # Nessun nuovo minimo: niente messaggio. Un blocco di Google arriva comunque come
    # avviso di rallentamento (main).
    return bloccato, None, pos


def log_rete(file):
    """Manda in un file i messaggi interni della libreria di rete.

    primp (le richieste a Google) passa i suoi avvisi al logging di Python, ad es.
    "h2 connection driver error: ... excessive load generating behavior" quando Google
    chiude una connessione HTTP/2 (il client ne apre un'altra). Senza un handler Python
    li stamperebbe sul terminale, in mezzo alla barra di avanzamento.
    """
    file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=file, level=logging.WARNING, force=True,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")


def main():
    log_rete(BASE / "data" / "errori_rete.log")  # fino a quando la cartella della ricerca non e' nota
    file_parametri = [a for a in sys.argv[1:] if not a.startswith("--")]
    if file_parametri:
        # Avvio diretto: nessuna domanda, lingua e parametri dal file.
        try:
            p = parametri_da_file(file_parametri[0])
        except ValueError as e:
            sys.exit(f"{file_parametri[0]}: {e}")
        stampa_riassunto(p)
    else:
        chiedi_lingua()
    if "--setup-telegram" in sys.argv:
        telegram_bot.setup()
        return
    if not telegram_bot.configurato():
        print(t("telegram_non_attivo"))
    telegram_bot.ascolta_in_background()  # /start e /stop di chiunque apra il bot
    if not file_parametri:
        p = chiedi_parametri()
    lingua.imposta_valuta(p.get("valuta", "EUR"))
    # Per l'A/R sulla stessa citta' il nome e' quello delle versioni precedenti, cosi'
    # le istanze gia' avviate riprendono i loro dati.
    nome = (
        f"{'_'.join(aeroporti(p['andata']['da']))}-{'_'.join(aeroporti(p['andata']['a']))}"
        f"-{p['inizio']}_{p['fine']}"
        f"-{p['giorni_min']}-{p['giorni_max']}gg-scali{'X' if p['max_scali'] is None else p['max_scali']}"
        + (f"-rit_{'_'.join(aeroporti(p['ritorno']['da']))}-{'_'.join(aeroporti(p['ritorno']['a']))}"
           if p["tipo"] == "diversa" else "")
        # In EUR il nome resta quello delle versioni precedenti; un'altra valuta ha i suoi dati.
        + (f"-{p['valuta']}" if p.get("valuta", "EUR") != "EUR" else "")
    )
    cartella = BASE / "data" / nome
    cartella.mkdir(parents=True, exist_ok=True)

    # Due istanze con gli stessi parametri si sovrascriverebbero i file.
    lock = open(cartella / ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit(t("altra_istanza", cartella=cartella))
    (cartella / "parametri.json").write_text(json.dumps(p, indent=1))

    tot, future = len(chiavi(p)), len(chiavi(p, anche_future=True)) - len(chiavi(p))
    print(t("da_monitorare", totale=tot, ar=len(combinazioni(p)), sole=len(sole_andate(p)),
            future=t("future_breve", n=future) if future else "", cartella=cartella))
    print(t("aggiornamento_ogni", minuti=p["frequenza_minuti"]))

    log_rete(cartella / "errori_rete.log")

    client = nuovo_client()
    ritmo = Ritmo()
    tratta = nome_tratta(p)
    primo, pos = True, None
    try:
        while True:
            t0 = time.monotonic()
            bloccato, messaggio, nuova = giro(p, cartella, client, ritmo, primo=primo, posizione_prima=pos)
            pos = nuova or pos  # se una volta non si rileva, si confronta con l'ultima nota
            primo = False
            avviso = None
            if bloccato and ritmo.livello < Ritmo.LIVELLO_MAX:
                ritmo.livello += 1
                avviso = t("tg_rallento", motivo=html.escape(bloccato))
            elif bloccato:
                avviso = t("tg_ancora_limita", motivo=html.escape(bloccato))
            elif ritmo.livello > 0:
                ritmo.livello -= 1
                avviso = t("tg_accelero")
            attesa = max(0, ritmo.intervallo_minuti(p["frequenza_minuti"]) * 60 - (time.monotonic() - t0))
            prossimo = t("tg_prossimo", ora=f"{datetime.now() + timedelta(seconds=attesa):%H:%M}")
            if avviso:
                stato = ritmo.descrizione(p["frequenza_minuti"])
                print(t("ritmo_terminale", avviso=re.sub("<[^>]+>", "", avviso), stato=stato))
                telegram_bot.invia(f"{avviso}\n{html.escape(tratta)}\n{t('ritmo_ora', stato=stato)}\n{prossimo}")
            if messaggio:
                telegram_bot.invia(f"{messaggio}\n\n{prossimo}")
            conto_alla_rovescia(attesa)
    except KeyboardInterrupt:
        print(t("fermato"))
        telegram_bot.invia(t("tg_fermato_utente", tratta=html.escape(tratta)))
    except Exception as e:
        errore = html.escape(f"{type(e).__name__}: {e}")[:500]
        telegram_bot.invia(t("tg_fermato_errore", tratta=html.escape(tratta), errore=errore))
        raise




if __name__ == "__main__":
    main()
