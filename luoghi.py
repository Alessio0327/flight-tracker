"""Risolve nomi di citta' in aeroporti (codici IATA).

Usa i dataset pubblici Travelpayouts (nomi in italiano), scaricati una volta in
data/geo/ e aggiornati ogni 30 giorni.
"""

import json
import time
import unicodedata
import urllib.request
from pathlib import Path

GEO = Path(__file__).resolve().parent / "data" / "geo"
URL = "https://api.travelpayouts.com/data/it/{}.json"
VALIDITA_SECONDI = 30 * 24 * 3600


def _carica(nome):
    path = GEO / f"{nome}.json"
    if not path.exists() or time.time() - path.stat().st_mtime > VALIDITA_SECONDI:
        GEO.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(URL.format(nome), timeout=60) as r:
                path.write_bytes(r.read())
        except OSError:
            if not path.exists():
                raise  # senza copia locale non si puo' andare avanti
    return json.loads(path.read_text(encoding="utf-8"))


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return " ".join(s.lower().replace("-", " ").split())


class Luoghi:
    def __init__(self, lingua="it", paese=None):
        """paese: codice del paese dell'utente (es. "IT"): a parita' di nome le sue citta'
        vengono prima, cosi' "Napoli" propone Napoli (NAP) prima di Naples in Florida."""
        self.lingua, self.paese = lingua, paese
        try:
            self.paesi = {p["code"]: p for p in _carica("countries")}
        except OSError:
            self.paesi = {}  # senza nomi dei paesi si mostra il codice
        self.aeroporti = {}  # codice citta' -> [(iata, nome aeroporto)]
        for a in _carica("airports"):
            if a.get("iata_type") == "airport" and a.get("flightable"):
                nome = a.get("name") or a["name_translations"].get("en") or a["code"]
                self.aeroporti.setdefault(a["city_code"], []).append((a["code"], nome))
        self.citta = [c for c in _carica("cities") if c["code"] in self.aeroporti]
        self.per_aeroporto = {
            iata: (citta, nome) for citta, lista in self.aeroporti.items() for iata, nome in lista
        }

    def nome_paese(self, codice):
        p = self.paesi.get(codice)
        if not p:
            return codice
        if self.lingua != "it" and p["name_translations"].get(self.lingua):
            return p["name_translations"][self.lingua]
        return p.get("name") or codice

    def nome_citta(self, c):
        """Nome della citta' nella lingua scelta (il dataset e' in italiano, con le traduzioni)."""
        if self.lingua != "it" and c["name_translations"].get(self.lingua):
            return c["name_translations"][self.lingua]
        return c.get("name") or c["name_translations"].get("en") or c["code"]

    def cerca(self, testo):
        """Citta' che corrispondono al testo: esatte, poi per prefisso, poi contenute."""
        t = _norm(testo)
        if not t:
            return []
        punteggi = []
        for c in self.citta:
            nomi = {_norm(c.get("name")), *(_norm(v) for v in c["name_translations"].values())}
            if t in nomi or t == c["code"].lower():
                p = 0
            elif any(n.startswith(t) for n in nomi):
                p = 1
            elif any(t in n for n in nomi):
                p = 2
            else:
                continue
            # A parita': prima il paese dell'utente, poi le citta' con piu' aeroporti
            # (di solito le piu' grandi).
            altro_paese = c.get("country_code") != self.paese
            punteggi.append((p, altro_paese, -len(self.aeroporti[c["code"]]), self.nome_citta(c), c))
        punteggi.sort(key=lambda x: x[:4])
        return [x[4] for x in punteggi]
