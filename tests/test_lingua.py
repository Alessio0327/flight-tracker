"""Testi in italiano e inglese."""

import json
import string

import pytest

import lingua
import tracker
from conftest import OSAKA, ROMA, TOKYO, parametri, tra
from test_testi import cop, proposta_ar


def segnaposti(testo):
    return {campo for _, campo, _, _ in string.Formatter().parse(testo) if campo}


@pytest.mark.parametrize("chiave", sorted(lingua.TESTI))
def test_ogni_testo_ha_entrambe_le_lingue_con_gli_stessi_valori(chiave):
    it, en = lingua.TESTI[chiave]
    assert it and en
    # {Ruolo} e' solo inglese (ruolo con l'iniziale maiuscola); il resto deve coincidere.
    assert segnaposti(it) - {"Ruolo"} <= segnaposti(en) | {"ruolo"}
    assert segnaposti(en) - {"Ruolo"} <= segnaposti(it)


def test_lingua_sconosciuta():
    with pytest.raises(ValueError):
        lingua.imposta("fr")


def test_testi_in_inglese(inglese):
    assert tracker.testo_scali(None) == "any stops"
    assert tracker.testo_scali(1) == "max 1 stop"
    assert tracker.testo_copertura(cop(verificate=266)).endswith("(scan complete)")
    assert tracker.nome_tratta(parametri(tipo="diversa")) == "Roma -> Osaka, return Osaka -> Roma"
    assert tracker.giudizio({"fascia": [900, 1200], "tipico": 1000, "prezzo": 850}).startswith("LOW: -15% vs typical")


def test_messaggio_telegram_in_inglese(inglese):
    p = parametri(giorni_partenza=1, durata=(14, 14))
    top, prezzi = proposta_ar(p)
    testo = tracker.messaggio_telegram(p, top, prezzi, cop(), [])
    assert testo.startswith("✈️ <b>New lowest price</b>")
    assert "📅 Departure from" in testo
    assert "1. <b>656 EUR</b> · Round trip Osaka" in testo
    assert "(14 days)" in testo
    assert "🏷 on lastminute.com (674 EUR listed, outbound 08:55, return 17:55)" in testo
    assert "Open on Google Flights" in testo


def test_orari_vecchi_dati_salvati():
    assert tracker.orari({"orari": "andata 08:55, ritorno 17:55"}) == "andata 08:55, ritorno 17:55"


def test_confronto_in_inglese(inglese):
    p = parametri(tipo="diversa", arrivi=(TOKYO, OSAKA), giorni_partenza=1, durata=(14, 14))
    prezzi = {k: 800 for k in tracker.combinazioni(p)}
    prezzi.update({k: 400 for k in tracker.sole_andate(p)})
    righe = tracker.confronto_varianti(p, tracker.proposte(p, prezzi), {})
    assert righe[0] == "Variant comparison (verified prices):"
    assert any(r.startswith("  Outbound Tokyo, return from Osaka: 2 tickets 800 EUR") for r in righe)


def test_campo_lingua_nel_file(tmp_path):
    f = {
        "lingua": "en",
        "andata": {"da": [ROMA], "a": [OSAKA]},
        "periodo": {"data": tra(60).strftime("%d/%m/%Y"), "giorni_prima_dopo": 2},
        "durata": {"min": 14, "max": 15},
    }
    path = tmp_path / "f.json"
    path.write_text(json.dumps(f))
    p = tracker.parametri_da_file(path)
    assert p["lingua"] == "en" and lingua.LINGUA == "en"


def test_campo_lingua_non_valido(tmp_path):
    path = tmp_path / "f.json"
    path.write_text(json.dumps({"lingua": "fr"}))
    with pytest.raises(ValueError, match="lingua"):
        tracker.parametri_da_file(path)


def test_errori_di_input_in_inglese(inglese):
    with pytest.raises(ValueError, match="format: 15/10/2027"):
        tracker.data("nope")
    with pytest.raises(ValueError, match="answer 1 or 2"):
        tracker.scelta("1", "2")("3")


def file_osaka(tmp_path, **campi):
    f = {**campi, "andata": {"da": [ROMA], "a": [OSAKA]},
         "periodo": {"data": tra(60).strftime("%d/%m/%Y"), "giorni_prima_dopo": 2},
         "durata": {"min": 14, "max": 15}}
    path = tmp_path / "f.json"
    path.write_text(json.dumps(f))
    return path


def test_lingua_scelta_vince_e_aggiorna_il_file(tmp_path, inglese, capsys):
    path = file_osaka(tmp_path, lingua="it")
    p = tracker.parametri_da_file(path, lingua_scelta="en")
    assert p["lingua"] == "en" and lingua.LINGUA == "en"
    salvato = json.loads(path.read_text())
    assert salvato["lingua"] == "en"
    assert salvato["durata"] == {"min": 14, "max": 15}  # il resto del file non cambia
    assert "File language updated" in capsys.readouterr().out


def test_stessa_lingua_file_non_riscritto(tmp_path):
    path = file_osaka(tmp_path, lingua="it")
    prima = path.read_text()
    tracker.parametri_da_file(path, lingua_scelta="it")
    assert path.read_text() == prima


def test_lingua_scelta_aggiunta_se_manca(tmp_path, inglese):
    path = file_osaka(tmp_path)
    tracker.parametri_da_file(path, lingua_scelta="en")
    assert json.loads(path.read_text())["lingua"] == "en"


def test_avvio_diretto_senza_campo_lingua_e_italiano(tmp_path, inglese):
    p = tracker.parametri_da_file(file_osaka(tmp_path))
    assert p["lingua"] == "it" and lingua.LINGUA == "it"
