"""File che il tool scrive nella cartella dati: storico, log, ricerche concluse."""

import json
import logging

import pytest

import parametri
import tracker
from conftest import tra, viaggio


def test_storico_nuovo_con_intestazione(tmp_path):
    file = tmp_path / "storico.csv"
    tracker.prepara_storico(file)
    assert file.read_text(encoding="utf-8") == ",".join(tracker.INTESTAZIONE_STORICO) + "\n"
    tracker.prepara_storico(file)  # una seconda volta non la ripete
    assert file.read_text(encoding="utf-8").count("controllato") == 1


def test_storico_vecchio_senza_intestazione(tmp_path):
    file = tmp_path / "storico.csv"
    file.write_text("2026-10-22T16:00:00,2027-03-01,2027-03-16,674,Qatar Airways,FCO-DOH DOH-KIX\n", encoding="utf-8")
    tracker.prepara_storico(file)
    righe = file.read_text(encoding="utf-8").splitlines()
    assert righe[0].startswith("controllato,") and righe[1].endswith("DOH-KIX")


def test_storico_a_rotazione(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "MAX_BYTE_STORICO", 50)
    file = tmp_path / "storico.csv"
    file.write_text("x" * 100, encoding="utf-8")
    tracker.prepara_storico(file)
    assert (tmp_path / "storico.1.csv").read_text(encoding="utf-8") == "x" * 100
    assert file.read_text(encoding="utf-8").startswith("controllato,")


def test_log_a_rotazione(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "MAX_BYTE_LOG", 200)
    file = tmp_path / "errori_rete.log"
    try:
        tracker.log_rete(file)
        for _ in range(20):
            logging.getLogger("primp").warning("h2 connection driver error: excessive load generating behavior")
        logging.shutdown()
        assert (tmp_path / "errori_rete.log.1").exists()
        assert file.stat().st_size <= 400
    finally:
        logging.basicConfig(force=True, handlers=[logging.NullHandler()])


def test_avviso_ricerche_concluse(tmp_path, capsys):
    for nome, fine in (("vecchia", tra(-10)), ("attiva", tra(30))):
        (tmp_path / "data" / nome).mkdir(parents=True)
        p = viaggio()
        p["fine"] = fine.isoformat()
        (tmp_path / "data" / nome / "parametri.json").write_text(json.dumps(p), encoding="utf-8")
    tracker.avvisa_ricerche_concluse(tmp_path / "data")
    out = capsys.readouterr().out
    assert "1 ricerche" in out and "vecchia" in out and "attiva" not in out


def test_primo_avvio_senza_internet(monkeypatch):
    def senza_rete(*a, **k):
        raise OSError("rete assente")
    monkeypatch.setattr(parametri, "Luoghi", senza_rete)
    monkeypatch.setattr(parametri.google_flights, "posizione", lambda: None)
    monkeypatch.setattr("builtins.input", lambda domanda: "1")
    with pytest.raises(SystemExit, match="Serve internet"):
        parametri.chiedi_parametri()
