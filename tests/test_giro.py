"""Un controllo completo (giro) con Google finto: calendario, verifica, venditori, testi.

Prezzi finti: 800 EUR per l'A/R, 650 EUR per l'A/R che parte 2 giorni prima del periodo
(per il suggerimento 💡), 400 + 450 EUR per i due biglietti di sola andata.
"""

import json

import pytest

import google_flights
import interfaccia
import ricerca
import tracker
from conftest import viaggio, tra


def prezzo(k):
    if k.count("|") == 1:
        return 650 if k.split("|")[0] == tra(58).isoformat() else 800
    return 400 if k.startswith("out|") else 450


@pytest.fixture
def google_finto(monkeypatch):
    chiamate = {"calendario": [], "ricerche": []}

    def scansione(client, p, ritmo):
        chiamate["calendario"].append((p["inizio"], p["fine"]))
        return {k: prezzo(k) for k in ricerca.chiavi(p)}

    def risultato(chiave):
        chiamate["ricerche"].append(chiave)
        return {"prezzo": prezzo(chiave), "compagnie": "Qatar Airways",
                "tratte": "FCO-DOH DOH-KIX", "link": f"https://example.com/{chiave}"}

    def cerca(client, org, dst, andata, ritorno, max_scali):
        return risultato(f"{andata}|{ritorno}")

    def cerca_sola_andata(client, giorno, org, dst, max_scali):
        lato = "out" if org == ["FCO"] else "ret"
        return risultato(f"{lato}|Osaka|{giorno}")

    monkeypatch.setattr(google_flights, "scansione_calendario", scansione)
    monkeypatch.setattr(google_flights, "cerca", cerca)
    monkeypatch.setattr(google_flights, "cerca_sola_andata", cerca_sola_andata)
    monkeypatch.setattr(google_flights, "prezzo_venditori", lambda *a: None)
    monkeypatch.setattr(tracker, "SearchFlights", lambda: None)
    monkeypatch.setattr(interfaccia, "notifica", lambda *a: None)
    monkeypatch.setattr(tracker.time, "sleep", lambda s: None)
    monkeypatch.setattr(google_flights, "posizione", lambda: {"ip": "203.0.113.7", "paese": "IT", "citta": "Milano"})
    return chiamate


def test_primo_giro_nuovo_minimo(tmp_path, google_finto, capsys):
    p = viaggio(giorni_partenza=3, durata=(14, 15))
    bloccato, messaggio, _ = tracker.giro(p, tmp_path, None, ricerca.Ritmo())
    out = capsys.readouterr().out

    assert bloccato is None
    assert messaggio.startswith("✈️ <b>Nuovo prezzo minimo</b>")
    # il calendario guarda anche 7 giorni prima e dopo il periodo
    assert google_finto["calendario"] == [(tra(53).isoformat(), tra(69).isoformat())]
    assert "★ nuovo minimo: 800 EUR A/R Osaka" in out
    assert "(scansione completa)" in out
    assert "💡 Partendo il" in out and "risparmi 150 EUR" in out
    assert "💡 Partendo il" in messaggio
    top = (tmp_path / "top.txt").read_text(encoding="utf-8")
    assert top.count("A/R Osaka") >= 5
    # le date fuori periodo non entrano nella top
    assert tra(58).isoformat() not in top.split("💡")[0]


def test_nessun_messaggio_senza_nuovo_minimo_ma_si_all_avvio(tmp_path, google_finto):
    p = viaggio(giorni_partenza=3, durata=(14, 15))
    tracker.giro(p, tmp_path, None, ricerca.Ritmo())

    _, messaggio, _ = tracker.giro(p, tmp_path, None, ricerca.Ritmo())
    assert messaggio is None

    _, messaggio, _ = tracker.giro(p, tmp_path, None, ricerca.Ritmo(), primo=True)
    assert messaggio.startswith("🚀 <b>Tracker avviato</b>")
    assert "🏆 <b>Top" in messaggio


def test_scansione_parziale_e_rotazione(tmp_path, google_finto, monkeypatch):
    monkeypatch.setattr(ricerca, "RICERCHE_MAX_PER_GIRO", 8)
    p = viaggio(giorni_partenza=5, durata=(14, 16))
    totale = len(ricerca.chiavi(p))

    _, messaggio, _ = tracker.giro(p, tmp_path, None, ricerca.Ritmo())
    assert "🔎 <b>Scansione in corso</b>" in messaggio
    assert "max 8 per controllo" in messaggio

    # Con un budget piccolo la top e le stime migliori vengono ricontrollate a ogni giro,
    # ma una parte resta alla rotazione: prima o poi ogni ricerca viene verificata.
    verificate = []
    for _ in range(totale):
        tracker.giro(p, tmp_path, None, ricerca.Ritmo())
        prezzi = json.loads((tmp_path / "prezzi.json").read_text(encoding="utf-8"))
        verificate.append(len(set(ricerca.chiavi(p)) & set(prezzi)))
        if verificate[-1] == totale:
            break
    assert verificate[-1] == totale
    assert verificate == sorted(verificate)


def test_blocco_di_google(tmp_path, google_finto, monkeypatch):
    def bloccato(*a):
        raise google_flights.Bloccato("HTTP 429, troppe richieste")

    monkeypatch.setattr(google_flights, "scansione_calendario", bloccato)
    p = viaggio(giorni_partenza=2, durata=(14, 14))
    motivo, messaggio, _ = tracker.giro(p, tmp_path, None, ricerca.Ritmo())
    assert motivo == "HTTP 429, troppe richieste"
    assert google_finto["ricerche"] == []
    assert messaggio is None  # il blocco arriva come avviso di rallentamento


def test_date_passate_tolte_dai_dati(tmp_path, google_finto):
    vecchia = f"{tra(-30).isoformat()}|{tra(-16).isoformat()}"
    (tmp_path / "prezzi.json").write_text(json.dumps({vecchia: {"prezzo": 1, "controllato": "x"}}))
    p = viaggio(giorni_partenza=2, durata=(14, 14))
    tracker.giro(p, tmp_path, None, ricerca.Ritmo())
    assert vecchia not in json.loads((tmp_path / "prezzi.json").read_text(encoding="utf-8"))


def test_posizione_nel_terminale_e_su_telegram(tmp_path, google_finto, capsys):
    p = viaggio(giorni_partenza=2, durata=(14, 14))
    _, messaggio, pos = tracker.giro(p, tmp_path, None, ricerca.Ritmo())
    out = capsys.readouterr().out
    assert "🌍 Ricerche da 🇮🇹 IT, Milano (IP 203.0.113.7)" in out
    assert "🌍 Ricerche da 🇮🇹 IT" in messaggio
    assert "203.0.113.7" not in messaggio  # l'IP resta nel terminale
    assert pos["paese"] == "IT"
    assert "IP 203.0.113.7" in (tmp_path / "top.txt").read_text(encoding="utf-8")
    righe = (tmp_path / "storico.csv").read_text(encoding="utf-8").splitlines()
    assert righe[0] == ",".join(tracker.INTESTAZIONE_STORICO)
    assert righe[1].endswith(",IT")


def test_paese_cambiato(tmp_path, google_finto, capsys):
    p = viaggio(giorni_partenza=2, durata=(14, 14))
    prima = {"ip": "198.51.100.1", "paese": "FR", "citta": "Paris"}
    _, messaggio, _ = tracker.giro(p, tmp_path, None, ricerca.Ritmo(), posizione_prima=prima)
    assert "⚠️ IP cambiato dall'ultimo controllo: prima 🇫🇷 FR (IP 198.51.100.1), ora 🇮🇹 IT" in capsys.readouterr().out
    assert "⚠️ Paese di uscita cambiato: prima 🇫🇷 FR, ora 🇮🇹 IT" in messaggio


def test_posizione_non_rilevata(tmp_path, google_finto, monkeypatch, capsys):
    monkeypatch.setattr(google_flights, "posizione", lambda: None)
    p = viaggio(giorni_partenza=2, durata=(14, 14))
    _, messaggio, pos = tracker.giro(p, tmp_path, None, ricerca.Ritmo())
    assert pos is None
    assert "Paese di uscita non rilevato" in capsys.readouterr().out
    assert "🌍" not in messaggio
