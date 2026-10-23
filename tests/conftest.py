"""Strumenti comuni ai test.

Nessuna data e' scritta a mano: tutto parte da OGGI, il giorno in cui girano i test,
cosi' i test restano validi negli anni. Durante i test ricerca.oggi() restituisce
sempre OGGI, anche se l'esecuzione attraversa la mezzanotte.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lingua  # noqa: E402
import ricerca  # noqa: E402

OGGI = date.today()

ROMA = {"nome": "Roma", "aeroporti": ["FCO"]}
TOKYO = {"nome": "Tokyo", "aeroporti": ["HND", "NRT"]}
OSAKA = {"nome": "Osaka", "aeroporti": ["KIX", "ITM"]}


def tra(giorni):
    """Data a N giorni da oggi."""
    return OGGI + timedelta(days=giorni)


def viaggio(tipo="stessa", arrivi=(OSAKA,), ritorno_da=None, tra_giorni=60, giorni_partenza=3,
              durata=(14, 15), max_scali=1, top=5, frequenza=30):
    """Parametri come quelli prodotti dalle domande: partenze per giorni_partenza giorni
    a partire da oggi + tra_giorni."""
    arrivi = list(arrivi)
    ritorno_da = list(ritorno_da) if ritorno_da else arrivi
    return {
        "tipo": tipo,
        "andata": {"da": [ROMA], "a": arrivi},
        "ritorno": {"da": ritorno_da, "a": [ROMA]},
        "inizio": tra(tra_giorni).isoformat(),
        "fine": tra(tra_giorni + giorni_partenza - 1).isoformat(),
        "giorni_min": durata[0],
        "giorni_max": durata[1],
        "max_scali": max_scali,
        "top": top,
        "frequenza_minuti": frequenza,
    }


@pytest.fixture(autouse=True)
def oggi_fisso(monkeypatch):
    monkeypatch.setattr(ricerca, "oggi", lambda: OGGI)


@pytest.fixture(autouse=True)
def italiano():
    """Ogni test parte in italiano; i test in inglese usano la fixture `inglese`."""
    lingua.imposta("it")
    lingua.imposta_valuta("EUR")
    yield
    lingua.imposta("it")
    lingua.imposta_valuta("EUR")


@pytest.fixture
def inglese():
    lingua.imposta("en")
