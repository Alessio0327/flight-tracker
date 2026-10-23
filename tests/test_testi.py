"""Testi per terminale e Telegram, giudizio sul prezzo, velocita' adattiva."""

import tracker
from conftest import OSAKA, ROMA, parametri, tra


def cop(**modifiche):
    c = {"totale": 266, "stimate": 266, "verificate": 100, "budget": 100, "future": 0, "migliori": 15}
    c.update(modifiche)
    return c


def test_copertura_scansione_in_corso():
    testo = tracker.testo_copertura(cop())
    assert "verificate col prezzo completo 100/266 (scansione in corso)" in testo
    assert "Le 15 combinazioni piu' economiche" in testo
    assert "le altre 166 ricerche" in testo and "massimo 100 per controllo" in testo


def test_copertura_completa_senza_note():
    testo = tracker.testo_copertura(cop(verificate=266))
    assert testo.endswith("(scansione completa)")


def test_copertura_ricerche_future():
    testo = tracker.testo_copertura(cop(verificate=266, future=12))
    assert "altre 12 non ancora possibili" in testo
    assert tra(tracker.LIMITE_RICERCA_GIORNI).strftime("%d/%m/%Y") in testo


def test_intestazione_telegram():
    p = parametri(durata=(14, 21), max_scali=1, frequenza=60)
    testo = tracker.intestazione_telegram(p, "✈️ <b>Titolo</b>", cop())
    assert testo.startswith("✈️ <b>Titolo</b>")
    assert "🛫 Roma (FCO) → Osaka (KIX, ITM)" in testo
    assert f"📅 Partenza dal {tra(60):%d/%m/%Y} al {tra(62):%d/%m/%Y}" in testo
    assert "Durata min: 14 gg - max: 21 giorni · max 1 scalo · controllo ogni 60 min" in testo
    assert "✅ Le 15 combinazioni più economiche" in testo
    assert "⏳ Le altre 166" in testo


def test_intestazione_scansione_completa_e_scali():
    p = parametri(max_scali=None)
    testo = tracker.intestazione_telegram(p, "t", cop(verificate=266))
    assert "Scansione completa</b>: 266/266" in testo
    assert "⏳" not in testo
    assert "scali qualsiasi" in testo
    assert "max 2 scali" in tracker.intestazione_telegram(parametri(max_scali=2), "t", cop())


def test_html_protetto_nei_nomi():
    citta = {"nome": "A&B <x>", "aeroporti": ["AAA"]}
    p = parametri(arrivi=(citta,))
    testo = tracker.intestazione_telegram(p, "t", cop())
    assert "A&amp;B &lt;x&gt;" in testo and "<x>" not in testo


def proposta_ar(p, prezzo_lista=674, venditore=656):
    k = tracker.combinazioni(p)[0]
    prezzi = {k: {
        "prezzo": prezzo_lista, "compagnie": "Qatar Airways", "tratte": "FCO-DOH DOH-KIX",
        "link": "https://example.com/?a=1&b=2", "controllato": "x",
        "venditore": {"prezzo": venditore, "nome": "lastminute.com", "orari": "andata 08:55, ritorno 17:55"},
        "fascia": [870, 1400], "tipico": 986, "min_60gg": 674,
    }}
    return tracker.proposte_verificate(p, prezzi), prezzi


def test_messaggio_telegram_top():
    p = parametri(giorni_partenza=1, durata=(14, 14))
    top, prezzi = proposta_ar(p)
    testo = tracker.messaggio_telegram(p, top, prezzi, cop(), ["Confronto varianti (prezzi verificati):", "  riga"])
    assert "✈️ <b>Nuovo prezzo minimo</b>" in testo
    assert "1. <b>656 EUR</b> · A/R Osaka" in testo
    assert f"📆 {tra(60):%d/%m} → {tra(74):%d/%m} (14 gg)" in testo
    assert "🏷 su lastminute.com (674 EUR in lista" in testo
    assert "📊 <i>BASSO" in testo
    assert 'href="https://example.com/?a=1&amp;b=2"' in testo
    assert "⚖️ <b>Confronto varianti</b>" in testo


def test_messaggio_telegram_titolo_avvio_e_senza_venditore():
    p = parametri(giorni_partenza=1, durata=(14, 14))
    top, prezzi = proposta_ar(p, venditore=700)
    testo = tracker.messaggio_telegram(p, top, prezzi, cop(), [], "🚀 avvio")
    assert testo.startswith("🚀 avvio")
    assert "🏷" not in testo  # il venditore costa piu' della lista: non lo mostra


def test_descrivi_prezzo_e_riassunto():
    p = parametri(giorni_partenza=1, durata=(14, 14))
    top, prezzi = proposta_ar(p)
    v = next(iter(prezzi.values()))
    assert tracker.descrivi_prezzo(v).startswith("656 EUR su lastminute.com (674 EUR in lista")
    assert tracker.riassunto(top[0]) == f"656 EUR A/R Osaka, {tra(60)} -> {tra(74)} (14 gg)"


def test_giudizio_fasce():
    base = {"fascia": [900, 1200], "tipico": 1000}
    assert tracker.giudizio({**base, "prezzo": 850}).startswith("BASSO: -15%")
    assert tracker.giudizio({**base, "prezzo": 950}).startswith("nella media, parte bassa")
    assert tracker.giudizio({**base, "prezzo": 1050}).startswith("nella media:")
    assert tracker.giudizio({**base, "prezzo": 1150}).startswith("nella media, parte alta")
    assert tracker.giudizio({**base, "prezzo": 1300}).startswith("ALTO")
    assert tracker.giudizio({"prezzo": 800}) == ""


def test_ritmo_livelli():
    r = tracker.Ritmo()
    assert (r.budget(30), r.pausa(), r.intervallo_minuti(30)) == (100, 3, 30)
    r.livello = 3
    assert (r.budget(30), r.pausa(), r.intervallo_minuti(30)) == (12, 24, 240)
    assert "livello 3/3" in r.descrizione(30)


def test_ritmo_budget_limitato_dalla_frequenza():
    r = tracker.Ritmo()
    assert r.budget(1) == 10  # 60 s / (3 s pausa + 3 s ricerca)
    r.livello = 3
    assert r.budget(1) == 2  # mai meno di 2


def test_nome_tratta():
    assert tracker.nome_tratta(parametri()) == "Roma -> Osaka"
    diversa = parametri(tipo="diversa")
    assert tracker.nome_tratta(diversa) == "Roma -> Osaka, ritorno Osaka -> Roma"
    assert ROMA["nome"] in tracker.nome_tratta(parametri(arrivi=(OSAKA,)))
