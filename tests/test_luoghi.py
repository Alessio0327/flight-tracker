"""Ricerca delle citta': a parita' di nome, prima quelle del paese dell'utente."""

import luoghi

AEROPORTI = [
    {"code": "NAP", "city_code": "NAP", "name": "Napoli Capodichino", "iata_type": "airport", "flightable": True,
     "name_translations": {}},
    {"code": "APF", "city_code": "APF", "name": "Naples", "iata_type": "airport", "flightable": True,
     "name_translations": {}},
]
CITTA = [  # ordine apposta sfavorevole: la citta' americana per prima
    {"code": "APF", "name": "Napoli", "country_code": "US", "name_translations": {"en": "Naples"}},
    {"code": "NAP", "name": "Napoli", "country_code": "IT", "name_translations": {"en": "Naples"}},
]
PAESI = [
    {"code": "IT", "name": "Italia", "name_translations": {"en": "Italy"}},
    {"code": "US", "name": "Stati Uniti", "name_translations": {"en": "United States"}},
]


def nuovi_luoghi(monkeypatch, **argomenti):
    dati = {"airports": AEROPORTI, "cities": CITTA, "countries": PAESI}
    monkeypatch.setattr(luoghi, "_carica", lambda nome: dati[nome])
    return luoghi.Luoghi(**argomenti)


def test_prima_il_paese_dell_utente(monkeypatch):
    l = nuovi_luoghi(monkeypatch, lingua="it", paese="IT")
    assert [c["code"] for c in l.cerca("napoli")] == ["NAP", "APF"]
    assert [c["code"] for c in l.cerca("naples")] == ["NAP", "APF"]
    l = nuovi_luoghi(monkeypatch, lingua="en", paese="US")
    assert [c["code"] for c in l.cerca("naples")] == ["APF", "NAP"]


def test_nomi_dei_paesi(monkeypatch):
    assert nuovi_luoghi(monkeypatch, lingua="it").nome_paese("US") == "Stati Uniti"
    l = nuovi_luoghi(monkeypatch, lingua="en")
    assert l.nome_paese("IT") == "Italy" and l.nome_paese("XX") == "XX"
