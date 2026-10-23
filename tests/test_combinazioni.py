"""Ricerche da fare, limiti di date di Google, proposte e confronto tra varianti."""

import tracker
from conftest import OSAKA, ROMA, TOKYO, parametri, tra


def test_numero_ricerche_stessa_citta():
    p = parametri(giorni_partenza=3, durata=(14, 15))
    assert len(tracker.combinazioni(p)) == 3 * 2
    # sole andate: 3 giorni di andata + ritorni dal giorno 14 al giorno 2+15
    assert len(tracker.sole_andate(p)) == 3 + (2 + 15 - 14 + 1)


def test_numero_ricerche_tokyo_osaka_come_nel_readme():
    p = parametri(tipo="diversa", arrivi=(TOKYO, OSAKA), giorni_partenza=21, durata=(14, 21))
    assert len(tracker.combinazioni(p)) == 168
    assert len(tracker.sole_andate(p)) == 98
    assert len(tracker.chiavi(p)) == 266


def test_formato_chiavi():
    p = parametri(giorni_partenza=1, durata=(14, 14))
    assert tracker.combinazioni(p) == [f"{tra(60).isoformat()}|{tra(74).isoformat()}"]
    assert f"out|Osaka|{tra(60).isoformat()}" in tracker.sole_andate(p)
    assert f"ret|Osaka|{tra(74).isoformat()}" in tracker.sole_andate(p)


def test_partenze_non_prima_di_domani():
    p = parametri(tra_giorni=-3, giorni_partenza=6)
    inizio, fine = tracker.finestra_partenze(p)
    assert inizio == tra(1) and fine == tra(2)


def test_limite_330_giorni():
    lim = tracker.LIMITE_RICERCA_GIORNI
    p = parametri(tra_giorni=lim - 20, giorni_partenza=10, durata=(14, 14))
    cercabili = tracker.combinazioni(p)
    tutte = tracker.combinazioni(p, anche_future=True)
    assert len(tutte) == 10
    assert all(tracker.ultima_data(k) <= tra(lim) for k in cercabili)
    assert len(cercabili) == 7  # ritorni da oggi+324 a oggi+330
    assert len(tracker.chiavi(p)) < len(tracker.chiavi(p, anche_future=True))


def test_finestre_calendario_spezzate_e_limitate():
    finestre = list(tracker._finestre(tra(1), tra(200)))
    assert finestre[0] == (tra(1), tra(61))
    assert all((a - da).days < tracker.MAX_GIORNI_CALENDARIO for da, a in finestre)
    assert finestre[-1][1] == tra(200)
    oltre = list(tracker._finestre(tra(300), tra(320)))
    assert oltre[-1][1] == tra(tracker.LIMITE_CALENDARIO_GIORNI)


def test_periodo_allargato_e_fuori_periodo():
    p = parametri(giorni_partenza=3)
    largo = tracker.periodo_allargato(p)
    giorni = tracker.GIORNI_FUORI_PERIODO
    assert largo["inizio"] == tra(60 - giorni).isoformat()
    assert largo["fine"] == tra(62 + giorni).isoformat()
    assert tracker.fuori_periodo(p, {"andata": tra(59).isoformat()})
    assert not tracker.fuori_periodo(p, {"andata": tra(60).isoformat()})
    assert not tracker.fuori_periodo(p, {"andata": tra(62).isoformat()})
    assert tracker.fuori_periodo(p, {"andata": tra(63).isoformat()})


# --- A/R su un biglietto: quando vale --------------------------------------

def test_citta_ar_stessa_e_diversa():
    assert tracker.citta_ar(parametri()) == [OSAKA]
    diversa = parametri(tipo="diversa", arrivi=(TOKYO, OSAKA), ritorno_da=(OSAKA,))
    assert tracker.citta_ar(diversa) == [OSAKA]  # solo Osaka e' sia arrivo che partenza del ritorno
    altra = parametri(tipo="diversa", arrivi=(TOKYO,), ritorno_da=(OSAKA,))
    assert tracker.citta_ar(altra) == []
    assert tracker.combinazioni(altra) == []


def test_niente_ar_se_il_ritorno_va_altrove():
    p = parametri(tipo="diversa")
    p["ritorno"]["a"] = [{"nome": "Milano", "aeroporti": ["MXP"]}]
    assert tracker.citta_ar(p) == []


# --- proposte ----------------------------------------------------------------

def prezzi_finti(p, ar=800, andata=400, ritorno=450):
    prezzi = {k: ar for k in tracker.combinazioni(p)}
    for k in tracker.sole_andate(p):
        prezzi[k] = andata if k.startswith("out|") else ritorno
    return prezzi


def test_proposte_ordinate_e_due_biglietti_sommati():
    p = parametri(giorni_partenza=2, durata=(14, 14))
    prezzi = prezzi_finti(p, ar=900, andata=300, ritorno=350)
    proposte = tracker.proposte(p, prezzi)
    assert [x["prezzo"] for x in proposte] == sorted(x["prezzo"] for x in proposte)
    due = next(x for x in proposte if x["tipo"] == "2b")
    assert due["prezzo"] == 650 and len(due["chiavi"]) == 2
    assert proposte[0]["tipo"] == "2b"


def test_stessa_citta_non_mescola_le_citta():
    p = parametri(arrivi=(TOKYO, OSAKA), giorni_partenza=1, durata=(14, 14))
    for x in tracker.proposte(p, prezzi_finti(p)):
        assert x["tipo"] == "ar" or x["va"] == x["torna"]


def test_diversa_propone_le_varianti_miste():
    p = parametri(tipo="diversa", arrivi=(TOKYO, OSAKA), giorni_partenza=1, durata=(14, 14))
    coppie = {(x["va"], x["torna"]) for x in tracker.proposte(p, prezzi_finti(p)) if x["tipo"] == "2b"}
    assert coppie == {("Tokyo", "Tokyo"), ("Tokyo", "Osaka"), ("Osaka", "Tokyo"), ("Osaka", "Osaka")}


def test_proposte_ignorano_prezzi_mancanti():
    p = parametri(giorni_partenza=1, durata=(14, 14))
    assert tracker.proposte(p, {}) == []


def test_proposte_verificate_citta_dalle_tratte_e_venditore():
    p = parametri(arrivi=(TOKYO, OSAKA), giorni_partenza=1, durata=(14, 14))
    k = tracker.combinazioni(p)[0]
    prezzi = {k: {"prezzo": 700, "tratte": "FCO-DOH DOH-KIX", "venditore": {"prezzo": 650}}}
    x = tracker.proposte_verificate(p, prezzi)[0]
    assert (x["va"], x["prezzo"]) == ("Osaka", 650)


def test_confronto_varianti_segna_la_migliore():
    p = parametri(tipo="diversa", arrivi=(TOKYO, OSAKA), giorni_partenza=1, durata=(14, 14))
    prezzi = prezzi_finti(p, ar=900, andata=400, ritorno=450)
    righe = tracker.confronto_varianti(p, tracker.proposte(p, prezzi), {})
    assert righe[0].startswith("Confronto varianti")
    assert len(righe) == 1 + 4
    assert sum("← migliore" in r for r in righe) >= 1
    assert any("Andata Tokyo, ritorno da Osaka: 2 biglietti 850 EUR" in r for r in righe)


def test_confronto_varianti_stima_e_dato_mancante():
    p = parametri(giorni_partenza=1, durata=(14, 14))
    stime = tracker.proposte(p, prezzi_finti(p, ar=800))
    righe = tracker.confronto_varianti(p, [], stime)
    assert "~800 EUR (stima)" in righe[1]
    assert "n.d." in tracker.confronto_varianti(p, [], [])[1]


def test_un_solo_aeroporto_di_partenza_nei_testi():
    assert tracker.etichetta([ROMA, OSAKA]) == "Roma (FCO) / Osaka (KIX, ITM)"
    assert tracker.nomi([TOKYO, OSAKA]) == "Tokyo/Osaka"
    assert tracker.aeroporti([TOKYO, {"nome": "X", "aeroporti": ["NRT", "KIX"]}]) == ["HND", "NRT", "KIX"]
