"""Valuta dei prezzi."""

import json

import pytest

import lingua
import tracker
from conftest import OSAKA, ROMA, parametri, tra
from test_testi import cop, proposta_ar


def test_risposta_valuta():
    assert tracker.valuta("") == "EUR"
    assert tracker.valuta("usd") == "USD"
    for sbagliata in ("US", "EURO", "12$"):
        with pytest.raises(ValueError):
            tracker.valuta(sbagliata)


def test_testi_in_altra_valuta():
    lingua.imposta_valuta("USD")
    p = parametri(giorni_partenza=1, durata=(14, 14))
    top, prezzi = proposta_ar(p)
    testo = tracker.messaggio_telegram(p, top, prezzi, cop(), [])
    assert "1. <b>656 USD</b>" in testo and "674 USD in lista" in testo
    assert "EUR" not in testo
    assert tracker.riassunto(top[0]).startswith("656 USD")
    assert "tipico 986 USD" in tracker.giudizio(next(iter(prezzi.values())))


def test_campo_valuta_nel_file(tmp_path):
    f = {"valuta": "gbp", "andata": {"da": [ROMA], "a": [OSAKA]},
         "periodo": {"data": tra(60).strftime("%d/%m/%Y"), "giorni_prima_dopo": 2},
         "durata": {"min": 14, "max": 15}}
    path = tmp_path / "f.json"
    path.write_text(json.dumps(f))
    assert tracker.parametri_da_file(path)["valuta"] == "GBP"
    del f["valuta"]
    path.write_text(json.dumps(f))
    assert tracker.parametri_da_file(path)["valuta"] == "EUR"
    f["valuta"] = "euro"
    path.write_text(json.dumps(f))
    with pytest.raises(ValueError, match="valuta"):
        tracker.parametri_da_file(path)


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
        tracker.cerca_sola_andata(Client(), tra(60).isoformat(), ["FCO"], ["KIX"])
    assert chieste["curr"] == "USD"


def test_riassunto_del_file_con_valuta(tmp_path, capsys):
    """Regressione: valuta passata esplicitamente a t() insieme a quella automatica."""
    p = parametri()
    p["valuta"] = "USD"
    tracker.stampa_riassunto(p)
    assert "prezzi in USD" in capsys.readouterr().out
    assert lingua.t("minimo_barra", prezzo=5, valuta="GBP") == "minimo 5 GBP"
