"""Modalita' weekend: viaggi da 1 a 4 giorni di calendario che toccano sabato o domenica."""

import json
from datetime import timedelta

import pytest

import interfaccia
import parametri
import ricerca
from conftest import OSAKA, ROMA, tra, viaggio


def prossimo(giorno_settimana, dopo=30):
    """Prima data da oggi + dopo che cade nel giorno indicato (0 = lunedi')."""
    d = tra(dopo)
    return d + timedelta(days=(giorno_settimana - d.weekday()) % 7)


def settimana_weekend(giorni_min=1, giorni_max=4):
    """Partenze da un lunedi' alla domenica dopo; durata in giorni di calendario."""
    lunedi = prossimo(0)
    p = viaggio(durata=(giorni_min - 1, giorni_max - 1))
    p.update(inizio=lunedi.isoformat(), fine=(lunedi + timedelta(days=6)).isoformat(), weekend=True)
    return p, lunedi


def test_nel_weekend():
    venerdi = prossimo(4)
    assert ricerca.nel_weekend(venerdi, venerdi + timedelta(days=1))          # ven -> sab
    assert ricerca.nel_weekend(venerdi + timedelta(days=2), venerdi + timedelta(days=4))  # dom -> mar
    assert not ricerca.nel_weekend(venerdi, venerdi)                          # ven in giornata
    assert not ricerca.nel_weekend(venerdi - timedelta(days=3), venerdi)      # mar -> ven
    assert ricerca.nel_weekend(venerdi + timedelta(days=1), venerdi + timedelta(days=1))  # sab in giornata


def test_coppie_solo_con_sabato_o_domenica():
    p, lunedi = settimana_weekend()
    coppie = list(ricerca.coppie_date(p))
    assert coppie and all(ricerca.nel_weekend(a, r) for a, r in coppie)
    assert all(0 <= (r - a).days <= 3 for a, r in coppie)
    # controllo indipendente: tutte le coppie del periodo con 1-4 giorni che toccano il weekend
    attese = {(lunedi + timedelta(days=i), lunedi + timedelta(days=i + d))
              for i in range(7) for d in range(4)
              if any((lunedi + timedelta(days=i + k)).weekday() >= 5 for k in range(d + 1))}
    assert set(coppie) == attese
    assert (lunedi, lunedi + timedelta(days=3)) not in coppie  # lun -> gio non tocca il weekend


def test_ricerche_e_proposte_in_weekend():
    p, _ = settimana_weekend()
    ar = ricerca.combinazioni(p)
    assert len(ar) == len(list(ricerca.coppie_date(p)))
    # le sole andate coprono esattamente i giorni usati dalle coppie
    giorni_out = {k.split("|")[2] for k in ricerca.sole_andate(p) if k.startswith("out|")}
    assert giorni_out == {a.isoformat() for a, _ in ricerca.coppie_date(p)}
    prezzi = {k: 100 for k in ricerca.chiavi(p)}
    proposte = ricerca.proposte(p, prezzi)
    assert proposte and all(x["weekend"] for x in proposte)


def test_modalita_normale_invariata():
    p = viaggio(giorni_partenza=3, durata=(14, 15))
    assert not any(x.get("weekend") for x in ricerca.proposte(p, {k: 1 for k in ricerca.chiavi(p)}))
    assert len(ricerca.combinazioni(p)) == 6


def test_testi_weekend():
    p, _ = settimana_weekend(2, 4)
    assert interfaccia.testo_durata(p) == "weekend, 2-4 giorni con sabato o domenica"
    venerdi = prossimo(4)
    x = {"andata": venerdi.isoformat(), "ritorno": (venerdi + timedelta(days=2)).isoformat(), "weekend": True}
    assert interfaccia.durata_viaggio(x) == "(3 gg, ven → dom)"
    assert interfaccia.durata_viaggio({**x, "weekend": False}) == "(2 gg)"
    testo = interfaccia.intestazione_telegram(p, "t", {"totale": 1, "stimate": 1, "verificate": 1, "budget": 100,
                                                        "future": 0, "migliori": 0})
    assert "🧳 Weekend: min 2 - max 4 giorni, con sabato o domenica" in testo


def test_testi_weekend_in_inglese(inglese):
    venerdi = prossimo(4)
    x = {"andata": venerdi.isoformat(), "ritorno": (venerdi + timedelta(days=3)).isoformat(), "weekend": True}
    assert interfaccia.durata_viaggio(x) == "(4 days, Fri → Mon)"


def scrivi(tmp_path, **campi):
    f = {"andata": {"da": [ROMA], "a": [OSAKA]},
         "periodo": {"data": tra(60).strftime("%d/%m/%Y"), "giorni_prima_dopo": 7}, **campi}
    path = tmp_path / "f.json"
    path.write_text(json.dumps(f), encoding="utf-8")
    return path


def test_file_weekend(tmp_path):
    p = parametri.parametri_da_file(scrivi(tmp_path, weekend=True, durata={"min": 2, "max": 3}))
    assert p["weekend"] and (p["giorni_min"], p["giorni_max"]) == (1, 2)
    p = parametri.parametri_da_file(scrivi(tmp_path, weekend=True))  # durata facoltativa: 1-4 giorni
    assert (p["giorni_min"], p["giorni_max"]) == (0, 3)
    with pytest.raises(ValueError, match="weekend"):
        parametri.parametri_da_file(scrivi(tmp_path, weekend=True, durata={"min": 1, "max": 5}))
    p = parametri.parametri_da_file(scrivi(tmp_path, durata={"min": 14, "max": 21}))
    assert not p["weekend"] and (p["giorni_min"], p["giorni_max"]) == (14, 21)


def test_risposta_tra():
    assert parametri.tra(1, 4)("3") == 3
    for sbagliata in ("0", "5", "x", ""):
        with pytest.raises(ValueError):
            parametri.tra(1, 4)(sbagliata)
