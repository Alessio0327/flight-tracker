"""Valuta dei prezzi."""

import json

import pytest

import lingua
import google_flights
import interfaccia
import parametri
from conftest import OSAKA, ROMA, viaggio, tra
from test_testi import cop, proposta_ar


def test_risposta_valuta():
    assert parametri.valuta("") == "EUR"
    assert parametri.valuta("usd") == "USD"
    for sbagliata in ("US", "EURO", "12$"):
        with pytest.raises(ValueError):
            parametri.valuta(sbagliata)


def test_testi_in_altra_valuta():
    lingua.imposta_valuta("USD")
    p = viaggio(giorni_partenza=1, durata=(14, 14))
    top, prezzi = proposta_ar(p)
    testo = interfaccia.messaggio_telegram(p, top, prezzi, cop(), [])
    assert "1. <b>656 USD</b>" in testo and "674 USD in lista" in testo
    assert "EUR" not in testo
    assert interfaccia.riassunto(top[0]).startswith("656 USD")
    assert "tipico 986 USD" in interfaccia.giudizio(next(iter(prezzi.values())))


def test_campo_valuta_nel_file(tmp_path):
    f = {"valuta": "gbp", "andata": {"da": [ROMA], "a": [OSAKA]},
         "periodo": {"data": tra(60).strftime("%d/%m/%Y"), "giorni_prima_dopo": 2},
         "durata": {"min": 14, "max": 15}}
    path = tmp_path / "f.json"
    path.write_text(json.dumps(f))
    assert parametri.parametri_da_file(path)["valuta"] == "GBP"
    del f["valuta"]
    path.write_text(json.dumps(f))
    assert parametri.parametri_da_file(path)["valuta"] == "EUR"
    f["valuta"] = "euro"
    path.write_text(json.dumps(f))
    with pytest.raises(ValueError, match="valuta"):
        parametri.parametri_da_file(path)


def test_ricerca_google_usa_la_valuta(monkeypatch):
    lingua.imposta_valuta("USD")
    chieste = {}

    class Risposta:
        status_code, url, text = 200, "", "<html></html>"

    class Client:
        def get(self, url, params):
            chieste.update(params)
            return Risposta()

    with pytest.raises(RuntimeError):  # pagina finta senza risultati
        google_flights.cerca_sola_andata(Client(), tra(60).isoformat(), ["FCO"], ["KIX"])
    assert chieste["curr"] == "USD"


def test_riassunto_del_file_con_valuta(tmp_path, capsys):
    """Regressione: valuta passata esplicitamente a t() insieme a quella automatica."""
    p = viaggio()
    p["valuta"] = "USD"
    parametri.stampa_riassunto(p)
    assert "prezzi in USD" in capsys.readouterr().out
    assert lingua.t("minimo_barra", prezzo=5, valuta="GBP") == "minimo 5 GBP"
