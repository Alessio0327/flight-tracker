"""Logica della ricerca: date, combinazioni, limiti di Google, proposte, ritmo.

Nessuna richiesta di rete e nessun testo per l'utente (salvo la descrizione del ritmo).
Il giorno corrente si legge solo da oggi(), che i test sostituiscono.
"""

from datetime import date, timedelta

from lingua import t


PAUSA_SECONDI = 3


RICERCHE_MAX_PER_GIRO = 100  # a ritmo normale; dimezzato a ogni rallentamento


VERIFICA_DA_STIMA = 15  # combinazioni piu' economiche del calendario da verificare ogni giro


# Limiti di Google Flights, misurati: la ricerca completa accetta voli fino a oggi + 330
# giorni (conta l'ultimo volo, cioe' il ritorno), il calendario prezzi fino a oggi + 305.
LIMITE_RICERCA_GIORNI = 330


LIMITE_CALENDARIO_GIORNI = 305


PAUSA_CALENDARIO = 1


GIORNI_FUORI_PERIODO = 7  # giorni prima/dopo il periodo in cui cercare date piu' economiche


def aeroporti(citta):
    return list(dict.fromkeys(a for c in citta for a in c["aeroporti"]))


def etichetta(citta):
    return " / ".join(f"{c['nome']} ({', '.join(c['aeroporti'])})" for c in citta)


def nomi(citta):
    return "/".join(c["nome"] for c in citta)


def citta_ar(p):
    """Citta' per cui ha senso l'andata e ritorno sullo stesso biglietto.

    Sono quelle di arrivo dell'andata da cui si puo' anche ripartire, se il ritorno
    arriva dove e' partita l'andata. Lista vuota = solo biglietti di sola andata.
    """
    if aeroporti(p["ritorno"]["a"]) != aeroporti(p["andata"]["da"]):
        return []
    return [c for c in p["andata"]["a"] if c in p["ritorno"]["da"]]


# --- ricerca -----------------------------------------------------------------

def oggi():
    """Data di oggi. Unico punto da cui il codice legge il giorno corrente: i test la sostituiscono."""
    return date.today()


def limite(giorni):
    return oggi() + timedelta(days=giorni)


def _giorni(da, a):
    while da <= a:
        yield da
        da += timedelta(days=1)


def finestra_partenze(p):
    return max(date.fromisoformat(p["inizio"]), oggi() + timedelta(days=1)), date.fromisoformat(p["fine"])


def finestra_ritorni(p):
    inizio, fine = finestra_partenze(p)
    return inizio + timedelta(days=p["giorni_min"]), fine + timedelta(days=p["giorni_max"])


def periodo_allargato(p):
    """Parametri con il periodo di partenza allargato di GIORNI_FUORI_PERIODO per lato."""
    giorni = timedelta(days=GIORNI_FUORI_PERIODO)
    return {**p, "inizio": (date.fromisoformat(p["inizio"]) - giorni).isoformat(),
            "fine": (date.fromisoformat(p["fine"]) + giorni).isoformat()}


def fuori_periodo(p, x):
    return not p["inizio"] <= x["andata"] <= p["fine"]


def combinazioni(p, anche_future=False):
    """Coppie "andata|ritorno" per l'andata e ritorno sullo stesso biglietto.

    Senza anche_future: solo quelle gia' cercabili (ritorno entro il limite di Google).
    Ogni giorno il limite avanza e se ne aggiungono altre.
    """
    if not citta_ar(p):
        return []
    out = []
    for andata in _giorni(*finestra_partenze(p)):
        for durata in range(p["giorni_min"], p["giorni_max"] + 1):
            ritorno = andata + timedelta(days=durata)
            if anche_future or ritorno <= limite(LIMITE_RICERCA_GIORNI):
                out.append(f"{andata.isoformat()}|{ritorno.isoformat()}")
    return out


def sole_andate(p, anche_future=False):
    """Voli di sola andata da cercare: "out|<citta' di arrivo>|data" e "ret|<citta' di partenza>|data"."""
    out = []
    for lato, citta, finestra in (("out", p["andata"]["a"], finestra_partenze(p)),
                                  ("ret", p["ritorno"]["da"], finestra_ritorni(p))):
        for c in citta:
            for giorno in _giorni(*finestra):
                if anche_future or giorno <= limite(LIMITE_RICERCA_GIORNI):
                    out.append(f"{lato}|{c['nome']}|{giorno.isoformat()}")
    return out


def chiavi(p, anche_future=False):
    """Tutte le ricerche precise: andate e ritorni sullo stesso biglietto + sole andate."""
    return combinazioni(p, anche_future) + sole_andate(p, anche_future)


def ultima_data(k):
    return date.fromisoformat(k.split("|")[-1])


def citta_per_nome(p, lato, nome):
    elenco = p["andata"]["a"] if lato == "out" else p["ritorno"]["da"]
    return next(c for c in elenco if c["nome"] == nome)


def tratta_sola_andata(p, k):
    """(giorno, aeroporti di partenza, aeroporti di arrivo) per una chiave di sola andata."""
    lato, nome, giorno = k.split("|")
    c = citta_per_nome(p, lato, nome)
    if lato == "out":
        return giorno, aeroporti(p["andata"]["da"]), c["aeroporti"]
    return giorno, c["aeroporti"], aeroporti(p["ritorno"]["a"])


class Ritmo:
    """Velocita' adattiva: rallenta quando Google limita, riaccelera dopo un giro pulito.

    A ogni livello: meta' ricerche per giro, pause doppie, intervallo tra giri doppio.
    """

    LIVELLO_MAX = 3

    def __init__(self):
        self.livello = 0

    @property
    def fattore(self):
        return 2 ** self.livello

    def pausa(self):
        return PAUSA_SECONDI * self.fattore

    def pausa_calendario(self):
        return PAUSA_CALENDARIO * self.fattore

    def budget(self, frequenza_minuti):
        # Non piu' ricerche di quante ne stanno nell'intervallo (circa 3 s a ricerca + pausa).
        entro_intervallo = frequenza_minuti * 60 // (self.pausa() + 3)
        return max(2, min(RICERCHE_MAX_PER_GIRO // self.fattore, entro_intervallo))

    def intervallo_minuti(self, frequenza_minuti):
        return frequenza_minuti * self.fattore

    def descrizione(self, frequenza_minuti):
        return t("ritmo", livello=self.livello, massimo=self.LIVELLO_MAX, ricerche=self.budget(frequenza_minuti),
                 pausa=self.pausa(), intervallo=self.intervallo_minuti(frequenza_minuti))


def migliore(v):
    """Prezzo piu' basso noto per una combinazione: lista Google o venditore (agenzia)."""
    candidati = [v.get("prezzo"), (v.get("venditore") or {}).get("prezzo")]
    return min((x for x in candidati if x), default=None)


def proposte(p, prezzi_di):
    """Viaggi completi con il loro prezzo, dal piu' economico.

    prezzi_di: {chiave: prezzo} (prezzi verificati o stime). Ogni proposta e'
    {"prezzo", "tipo": "ar"|"2b", "andata", "ritorno", "chiavi", "va", "torna"}
    (va/torna = nomi delle citta' di arrivo dell'andata e di partenza del ritorno).
    """
    out = []
    nome_ar = nomi(citta_ar(p))
    for k in combinazioni(p):
        if prezzi_di.get(k):
            andata, ritorno = k.split("|")
            out.append({"prezzo": prezzi_di[k], "tipo": "ar", "andata": andata, "ritorno": ritorno,
                        "chiavi": [k], "va": nome_ar, "torna": nome_ar})
    for x in p["andata"]["a"]:
        for y in p["ritorno"]["da"]:
            if p["tipo"] == "stessa" and x["nome"] != y["nome"]:
                continue
            for andata in _giorni(*finestra_partenze(p)):
                k_out = f"out|{x['nome']}|{andata.isoformat()}"
                if not prezzi_di.get(k_out):
                    continue
                for durata in range(p["giorni_min"], p["giorni_max"] + 1):
                    ritorno = (andata + timedelta(days=durata)).isoformat()
                    k_ret = f"ret|{y['nome']}|{ritorno}"
                    if prezzi_di.get(k_ret):
                        out.append({"prezzo": prezzi_di[k_out] + prezzi_di[k_ret], "tipo": "2b",
                                    "andata": andata.isoformat(), "ritorno": ritorno,
                                    "chiavi": [k_out, k_ret], "va": x["nome"], "torna": y["nome"]})
    return sorted(out, key=lambda x: x["prezzo"])


def citta_da_tratte(p, tratte):
    """Citta' di arrivo dell'andata, dall'ultimo aeroporto delle tratte (es. "FCO-ICN ICN-KIX")."""
    arrivo = tratte.split()[-1].split("-")[-1] if tratte else ""
    return next((c["nome"] for c in citta_ar(p) if arrivo in c["aeroporti"]), nomi(citta_ar(p)))


def proposte_verificate(p, prezzi):
    """Proposte con soli prezzi verificati; per l'A/R la citta' viene dalle tratte trovate."""
    out = proposte(p, {k: migliore(v) for k, v in prezzi.items() if migliore(v)})
    for x in out:
        if x["tipo"] == "ar":
            x["va"] = x["torna"] = citta_da_tratte(p, prezzi[x["chiavi"][0]].get("tratte"))
    return out
