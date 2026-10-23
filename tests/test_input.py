"""Risposte alle domande e parametri da file JSON."""

import json
from datetime import date, timedelta

import pytest

import parametri
import tracker
from conftest import OSAKA, ROMA, TOKYO, tra


@pytest.mark.parametrize("formato", ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"])
def test_data_formati_accettati(formato):
    giorno = tra(90)
    assert parametri.data(giorno.strftime(formato)) == giorno


@pytest.mark.parametrize("testo", ["", "domani", "32/01/2030", "2030/01/01"])
def test_data_rifiuta_formati_sbagliati(testo):
    with pytest.raises(ValueError):
        parametri.data(testo)


@pytest.mark.parametrize("formato", ["{m}/{a}", "{m}/{a2}", "{a}-{m:02d}"])
def test_mese_primo_e_ultimo_giorno(formato):
    giorno = tra(90)
    testo = formato.format(m=giorno.month, a=giorno.year, a2=giorno.year % 100)
    inizio, fine = parametri.mese(testo)
    assert inizio == giorno.replace(day=1)
    assert fine.replace(day=1) == inizio
    assert (fine + timedelta(days=1)).day == 1  # ultimo giorno del mese


def test_mese_non_valido():
    with pytest.raises(ValueError):
        parametri.mese(f"13/{tra(90).year}")


def test_intero_e_scali():
    assert parametri.intero(1)("14") == 14
    with pytest.raises(ValueError):
        parametri.intero(1)("0")
    with pytest.raises(ValueError):
        parametri.intero(1)("abc")
    assert parametri.scali("") is None
    assert parametri.scali("0") == 0


# --- file JSON ---------------------------------------------------------------

def scrivi(tmp_path, contenuto):
    path = tmp_path / "ricerca.json"
    path.write_text(contenuto if isinstance(contenuto, str) else json.dumps(contenuto))
    return path


def file_base(**modifiche):
    centro = tra(60)
    f = {
        "andata": {"da": [ROMA], "a": [TOKYO, OSAKA]},
        "ritorno": {"da": [TOKYO, OSAKA], "a": [ROMA]},
        "periodo": {"data": centro.strftime("%d/%m/%Y"), "giorni_prima_dopo": 5},
        "durata": {"min": 14, "max": 21},
        "max_scali": 1,
        "top": 5,
        "frequenza_minuti": 60,
    }
    f.update(modifiche)
    return f


def test_file_data_e_giorni(tmp_path):
    p = parametri.parametri_da_file(scrivi(tmp_path, file_base()))
    assert p["tipo"] == "diversa"
    assert p["inizio"] == tra(55).isoformat() and p["fine"] == tra(65).isoformat()
    assert (p["giorni_min"], p["giorni_max"], p["max_scali"]) == (14, 21, 1)
    assert p["andata"]["a"][1] == OSAKA


def test_file_mese(tmp_path):
    giorno = tra(90)
    p = parametri.parametri_da_file(scrivi(tmp_path, file_base(periodo={"mese": f"{giorno.month}/{giorno.year}"})))
    assert p["inizio"] == giorno.replace(day=1).isoformat()


def test_file_dal_al(tmp_path):
    periodo = {"dal": tra(40).strftime("%d/%m/%Y"), "al": tra(50).strftime("%d/%m/%Y")}
    p = parametri.parametri_da_file(scrivi(tmp_path, file_base(periodo=periodo)))
    assert (p["inizio"], p["fine"]) == (tra(40).isoformat(), tra(50).isoformat())


def test_file_senza_ritorno_e_stessa_citta(tmp_path):
    f = file_base()
    del f["ritorno"]
    p = parametri.parametri_da_file(scrivi(tmp_path, f))
    assert p["tipo"] == "stessa"
    assert p["ritorno"] == {"da": p["andata"]["a"], "a": p["andata"]["da"]}


def test_file_default_facoltativi(tmp_path):
    f = file_base()
    for campo in ("max_scali", "top", "frequenza_minuti"):
        del f[campo]
    p = parametri.parametri_da_file(scrivi(tmp_path, f))
    assert (p["max_scali"], p["top"], p["frequenza_minuti"]) == (None, 5, 30)


def test_file_periodo_iniziato_parte_da_domani(tmp_path):
    periodo = {"dal": tra(-5).strftime("%d/%m/%Y"), "al": tra(10).strftime("%d/%m/%Y")}
    p = parametri.parametri_da_file(scrivi(tmp_path, file_base(periodo=periodo)))
    assert p["inizio"] == tra(1).isoformat()


@pytest.mark.parametrize("modifica, errore", [
    ({"periodo": {"dal": "01/01/2000", "al": "02/01/2000"}}, "periodo"),
    ({"durata": {"min": 21, "max": 14}}, "durata"),
    ({"andata": {"da": [], "a": [OSAKA]}}, "andata.da"),
    ({"andata": {"da": [ROMA], "a": [{"nome": "Osaka"}]}}, "andata.a"),
    ({"top": 0}, "top"),
])
def test_file_valori_non_validi(tmp_path, modifica, errore):
    with pytest.raises(ValueError, match=errore):
        parametri.parametri_da_file(scrivi(tmp_path, file_base(**modifica)))


def test_file_campo_mancante(tmp_path):
    f = file_base()
    del f["durata"]
    with pytest.raises(ValueError, match="durata"):
        parametri.parametri_da_file(scrivi(tmp_path, f))


def test_file_json_rotto_e_inesistente(tmp_path):
    with pytest.raises(ValueError, match="JSON non valido"):
        parametri.parametri_da_file(scrivi(tmp_path, "{ non e' json"))
    with pytest.raises(ValueError, match="non riesco a leggere"):
        parametri.parametri_da_file(tmp_path / "manca.json")


def test_file_esempio_del_repository_ha_struttura_valida(tmp_path):
    """ricerche/esempio.json ha una data fissa (e' un esempio da modificare): qui si
    controlla solo la struttura, spostando il periodo nel futuro."""
    esempio = json.loads((tracker.BASE / "ricerche" / "esempio.json").read_text(encoding="utf-8"))
    esempio["periodo"] = {"data": tra(60).strftime("%d/%m/%Y"), "giorni_prima_dopo": 3}
    p = parametri.parametri_da_file(scrivi(tmp_path, esempio))
    assert isinstance(date.fromisoformat(p["inizio"]), date)
