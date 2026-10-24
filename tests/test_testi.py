"""Testi per terminale e Telegram, giudizio sul prezzo, velocita' adattiva."""

import google_flights
import interfaccia
import ricerca
import pytest

import tracker
from conftest import OSAKA, ROMA, viaggio, tra


def cop(**modifiche):
    c = {"totale": 266, "stimate": 266, "verificate": 100, "budget": 100, "future": 0, "migliori": 15}
    c.update(modifiche)
    return c


def test_copertura_scansione_in_corso():
    testo = interfaccia.testo_copertura(cop())
    assert "verificate col prezzo completo 100/266 (scansione in corso)" in testo
    assert "Le 15 combinazioni piu' economiche" in testo
    assert "le altre 166 ricerche" in testo and "massimo 100 per controllo" in testo


def test_copertura_completa_senza_note():
    testo = interfaccia.testo_copertura(cop(verificate=266))
    assert testo.endswith("(scansione completa)")


def test_copertura_ricerche_future():
    testo = interfaccia.testo_copertura(cop(verificate=266, future=12))
    assert "altre 12 non ancora possibili" in testo
    assert tra(ricerca.LIMITE_RICERCA_GIORNI).strftime("%d/%m/%Y") in testo


def test_intestazione_telegram():
    p = viaggio(durata=(14, 21), max_scali=1, frequenza=60)
    testo = interfaccia.intestazione_telegram(p, "✈️ <b>Titolo</b>", cop())
    assert testo.startswith("✈️ <b>Titolo</b>")
    assert "🛫 Roma (FCO) → Osaka (KIX, ITM)" in testo
    assert f"📅 Partenza dal {tra(60):%d/%m/%Y} al {tra(62):%d/%m/%Y}" in testo
    assert "Durata min: 14 gg - max: 21 giorni · max 1 scalo · controllo ogni 60 min" in testo
    assert "✅ Le 15 combinazioni più economiche" in testo
    assert "⏳ Le altre 166" in testo


def test_intestazione_scansione_completa_e_scali():
    p = viaggio(max_scali=None)
    testo = interfaccia.intestazione_telegram(p, "t", cop(verificate=266))
    assert "Scansione completa</b>: 266/266" in testo
    assert "⏳" not in testo
    assert "scali qualsiasi" in testo
    assert "max 2 scali" in interfaccia.intestazione_telegram(viaggio(max_scali=2), "t", cop())


def test_html_protetto_nei_nomi():
    citta = {"nome": "A&B <x>", "aeroporti": ["AAA"]}
    p = viaggio(arrivi=(citta,))
    testo = interfaccia.intestazione_telegram(p, "t", cop())
    assert "A&amp;B &lt;x&gt;" in testo and "<x>" not in testo


def proposta_ar(p, prezzo_lista=674, venditore=656):
    k = ricerca.combinazioni(p)[0]
    prezzi = {k: {
        "prezzo": prezzo_lista, "compagnie": "Qatar Airways", "tratte": "FCO-DOH DOH-KIX",
        "link": "https://example.com/?a=1&b=2", "controllato": "x",
        "venditore": {"prezzo": venditore, "nome": "lastminute.com", "ora_andata": "08:55", "ora_ritorno": "17:55"},
        "fascia": [870, 1400], "tipico": 986, "min_60gg": 674,
    }}
    return ricerca.proposte_verificate(p, prezzi), prezzi


def test_messaggio_telegram_top():
    p = viaggio(giorni_partenza=1, durata=(14, 14))
    top, prezzi = proposta_ar(p)
    testo = interfaccia.messaggio_telegram(p, top, prezzi, cop(), ["Confronto varianti (prezzi verificati):", "  riga"])
    assert "✈️ <b>Nuovo prezzo minimo</b>" in testo
    assert "1. <b>656 EUR</b> · A/R Osaka" in testo
    assert f"📆 {tra(60):%d/%m} → {tra(74):%d/%m} (14 gg)" in testo
    assert "🏷 su lastminute.com (674 EUR in lista" in testo
    assert "📊 <i>BASSO" in testo
    assert 'href="https://example.com/?a=1&amp;b=2"' in testo
    assert "⚖️ <b>Confronto varianti</b>" in testo


def test_messaggio_telegram_titolo_avvio_e_senza_venditore():
    p = viaggio(giorni_partenza=1, durata=(14, 14))
    top, prezzi = proposta_ar(p, venditore=700)
    testo = interfaccia.messaggio_telegram(p, top, prezzi, cop(), [], "🚀 avvio")
    assert testo.startswith("🚀 avvio")
    assert "🏷" not in testo  # il venditore costa piu' della lista: non lo mostra


def test_descrivi_prezzo_e_riassunto():
    p = viaggio(giorni_partenza=1, durata=(14, 14))
    top, prezzi = proposta_ar(p)
    v = next(iter(prezzi.values()))
    assert interfaccia.descrivi_prezzo(v).startswith("656 EUR su lastminute.com (674 EUR in lista")
    assert interfaccia.riassunto(top[0]) == f"656 EUR A/R Osaka, {tra(60)} -> {tra(74)} (14 gg)"


def test_giudizio_fasce():
    base = {"fascia": [900, 1200], "tipico": 1000}
    assert interfaccia.giudizio({**base, "prezzo": 850}).startswith("BASSO: -15%")
    assert interfaccia.giudizio({**base, "prezzo": 950}).startswith("nella media, parte bassa")
    assert interfaccia.giudizio({**base, "prezzo": 1050}).startswith("nella media:")
    assert interfaccia.giudizio({**base, "prezzo": 1150}).startswith("nella media, parte alta")
    assert interfaccia.giudizio({**base, "prezzo": 1300}).startswith("ALTO")
    assert interfaccia.giudizio({"prezzo": 800}) == ""


def test_ritmo_livelli():
    r = ricerca.Ritmo()
    assert (r.budget(30), r.pausa(), r.intervallo_minuti(30)) == (100, 3, 30)
    r.livello = 3
    assert (r.budget(30), r.pausa(), r.intervallo_minuti(30)) == (12, 24, 240)
    assert "livello 3/3" in r.descrizione(30)


def test_ritmo_budget_limitato_dalla_frequenza():
    r = ricerca.Ritmo()
    assert r.budget(1) == 10  # 60 s / (3 s pausa + 3 s ricerca)
    r.livello = 3
    assert r.budget(1) == 2  # mai meno di 2


def test_nome_tratta():
    assert interfaccia.nome_tratta(viaggio()) == "Roma -> Osaka"
    diversa = viaggio(tipo="diversa")
    assert interfaccia.nome_tratta(diversa) == "Roma -> Osaka, ritorno Osaka -> Roma"
    assert ROMA["nome"] in interfaccia.nome_tratta(viaggio(arrivi=(OSAKA,)))


def test_bandiera():
    assert interfaccia.bandiera("FR") == "🇫🇷"
    assert interfaccia.bandiera("it") == "🇮🇹"
    assert interfaccia.bandiera("EUR") == ""
    assert interfaccia.bandiera("") == ""


def test_posizione_servizio_di_riserva(monkeypatch):
    risposte = iter([OSError("rete"), b'{"ip": "203.0.113.7", "country": "fr"}'])

    class Risposta:
        def __init__(self, dati):
            self.dati = dati

        def read(self):
            return self.dati

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def apri(url, timeout):
        r = next(risposte)
        if isinstance(r, Exception):
            raise r
        return Risposta(r)

    monkeypatch.setattr(google_flights.urllib.request, "urlopen", apri)
    assert google_flights.posizione() == {"ip": "203.0.113.7", "paese": "FR", "citta": ""}


def test_messaggi_della_libreria_di_rete_nel_file(tmp_path, capsys):
    import logging
    file = tmp_path / "data" / "errori_rete.log"
    try:
        tracker.log_rete(file)
        logging.getLogger("primp").warning("h2 connection driver error: excessive load generating behavior")
        logging.shutdown()
        assert "excessive load" in file.read_text(encoding="utf-8")
        assert "excessive load" not in capsys.readouterr().err
    finally:
        logging.basicConfig(force=True, handlers=[logging.NullHandler()])


def test_notifica_macos_con_accenti(monkeypatch):
    chiamate = []
    monkeypatch.setattr(interfaccia.sys, "platform", "darwin")
    monkeypatch.setattr(interfaccia.subprocess, "run", lambda args, check: chiamate.append(args))
    interfaccia.notifica("Volo Città", "656 EUR → Osaka")
    script = chiamate[0][2]
    assert "Città" in script and "→" in script and "\\u" not in script


def test_risposte_colorate_solo_sul_terminale(monkeypatch, capsys):
    domande = []
    monkeypatch.setattr("builtins.input", lambda d: domande.append(d) or "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(interfaccia.sys.stdout, "isatty", lambda: True)
    assert interfaccia.leggi("Domanda: ") == "1"
    assert domande[-1] == "Domanda: " + interfaccia.COLORE_RISPOSTE
    assert capsys.readouterr().out.endswith(interfaccia.RESET)
    monkeypatch.setenv("NO_COLOR", "1")
    interfaccia.leggi("Domanda: ")
    assert domande[-1] == "Domanda: "


def test_colore_spento_anche_con_ctrl_c(monkeypatch, capsys):
    def interrompi(d):
        raise KeyboardInterrupt
    monkeypatch.setattr("builtins.input", interrompi)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(interfaccia.sys.stdout, "isatty", lambda: True)
    with pytest.raises(KeyboardInterrupt):
        interfaccia.leggi("Domanda: ")
    assert capsys.readouterr().out.endswith(interfaccia.RESET)
