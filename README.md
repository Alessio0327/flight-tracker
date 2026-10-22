# flight-tracker

Monitor da terminale dei prezzi dei voli andata/ritorno su Google Flights.
Gli dai la tratta, il periodo di partenza e la durata del viaggio. Il tool cerca
tutte le combinazioni di date ogni N minuti, ti mostra la top dei prezzi migliori
e ti avvisa (notifica macOS e Telegram) quando trova un nuovo minimo.

- Città al posto dei codici IATA: scrivi "Roma" e scegli Fiumicino, Ciampino o entrambi.
- Più destinazioni insieme (es. "Tokyo, Osaka"), e solo gli aeroporti che ti vanno bene.
- Periodo di partenza: un mese intero oppure una data ± N giorni.
- Durata minima e massima del viaggio, numero massimo di scali.
- Giudizio sul prezzo (basso / nella media / alto) rispetto alla fascia tipica di Google.
- Prezzi delle agenzie (lastminute, Gotogate, ...) che spesso costano meno del prezzo in lista.
- Più istanze in parallelo, una per terminale, ognuna con i suoi dati.
- Rallenta da solo se Google limita le richieste.

## Installazione

Serve Python 3.11 o più recente.

```bash
git clone https://github.com/Alessio0327/flight-tracker.git
cd flight-tracker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Utilizzo

```bash
.venv/bin/python tracker.py
```

All'avvio il tool fa alcune domande. Esempio di sessione:

```
Citta' di partenza (es. Roma): roma
  [1] Roma, IT  (FCO Fiumicino, CIA Ciampino)
  [2] Roma, AU  (RMA Roma)
  Quale 'roma'? (Invio = 1):
  [1] FCO Fiumicino
  [2] CIA Ciampino
  Aeroporti (Invio = tutti, oppure es. 1,2): 1
Citta' di destinazione (piu' di una separate da virgola, es. Tokyo, Osaka): osaka
  [1] UKB Kobe
  [2] KIX Kansai International
  [3] ITM Itami
  Aeroporti (Invio = tutti, oppure es. 1,2): 2,3
Periodo di partenza: [1] un mese  [2] intorno a una data: 2
Data (es. 15/10/2027): 10/03/27
Quanti giorni prima/dopo quella data: 10
Durata minima viaggio (giorni): 12
Durata massima viaggio (giorni): 21
Massimo scali per tratta (0 = solo diretti, Invio = qualsiasi):
Quanti migliori risultati mostrare: 5
Frequenza aggiornamento (minuti): 30
```

Risposte accettate:

| Domanda | Esempi |
|---|---|
| Città | `roma`, `Tokyo, Osaka`, codice aeroporto `FCO`, codice città `ROM` |
| Aeroporti | Invio = tutti, oppure numeri separati da virgola: `1,3` |
| Mese | `10/2027`, `10/27`, `2027-10` |
| Data | `15/10/2027`, `15/10/27`, `2027-10-15` |
| Scali | `0` = solo diretti, `1`, `2`, Invio = qualsiasi |

Poi il tool lavora da solo finché non premi Ctrl+C. Durante un giro mostra
una barra di avanzamento, alla fine la top e un conto alla rovescia fino al
giro successivo:

```
✓ Calendario [████████████████████████] 30/30 100% · in 41 s · 210 date stimate, da 672 EUR
Verifica precisa: 100 combinazioni (top attuale 5, stime migliori 15, a rotazione 80)
★ nuovo minimo: 751 EUR  2027-03-08 -> 2027-03-24  China Eastern, Shanghai Airlines [FCO-PVG PVG-KIX]
✓ Verifica   [████████████████████████] 100/100 100% · in 7 min 52 s · minimo 674 EUR
✓ Venditori  [████████████████████████] 5/5 100% · in 3 min 40 s · minimo 656 EUR

Top 5 Fiumicino (FCO) -> Osaka (KIX, ITM), partenza 2027-02-28 .. 2027-03-20, 12-21 giorni, scali qualsiasi
Stimate 210/210 combinazioni, verificate col prezzo completo 120/210 (scansione in corso)

1. 656 EUR su lastminute.com (674 EUR in lista, andata 08:55, ritorno 17:55)  2027-03-01 -> 2027-03-16 (15 gg)  Qatar Airways  [FCO-DOH DOH-KIX]
   Prezzo BASSO: -33% sul tipico 986 EUR, fascia 870-1400 EUR, minimo ultimi 60 gg 674 EUR
   https://www.google.com/travel/flights/search?tfs=...
...

Prossimo aggiornamento tra 18:42 (alle 17:34)
```

### Più istanze

Apri un terminale per ogni ricerca e lancia `tracker.py` in ognuno.
Ogni combinazione di parametri ha la sua cartella in `data/`. Se rilanci con
gli stessi parametri, il tool riprende i prezzi già trovati. Due istanze con
parametri identici non possono girare insieme.

Tutte le istanze usano lo stesso IP: con molte istanze, o con frequenze basse,
Google comincia prima a limitare le richieste.

## Notifiche Telegram (opzionale)

```bash
.venv/bin/python tracker.py --setup-telegram
```

1. Su Telegram apri @BotFather, invia `/newbot` e copia il token.
2. Incolla il token quando il tool lo chiede.
3. Invia un messaggio qualsiasi al tuo bot: il tool riconosce la chat e ti manda un messaggio di prova.

La configurazione finisce in `telegram.json` (permessi 600, escluso da git):

```json
{"token": "123456789:AA...", "chat_id": 123456789}
```

Il bot scrive quando:
- trova un nuovo prezzo minimo: top completa, con copertura della scansione e orario del prossimo controllo;
- rallenta o riaccelera perché Google limita le richieste: nuovo ritmo e orario del prossimo controllo.

## Come funziona

Ogni giro ha tre fasi.

1. **Calendario (stima veloce).** Il grafico prezzi di Google restituisce, con una
   richiesta, il prezzo indicativo di tutte le date di partenza per una durata e una
   coppia di aeroporti. Copre tutte le combinazioni in pochi secondi, ma non vede
   tutte le tariffe.
2. **Verifica (prezzo vero).** Ricerca completa sulla singola coppia di date, come
   su Google Flights: prezzo, compagnie, scali, giudizio sul prezzo, link.
   Ogni giro verifica la top attuale, le 15 stime più basse e, a rotazione, tutte
   le altre combinazioni: così anche una stima sbagliata prima o poi viene corretta.
3. **Venditori.** Per la top, il tool apre le pagine di prenotazione degli
   itinerari più economici e tiene il venditore che costa meno, agenzie comprese.

La top e le notifiche usano solo prezzi verificati (fase 2 o 3).

### Velocità adattiva

Con un errore HTTP 429, un captcha o 5 errori di fila, il giro si interrompe e il
tool sale di livello. A ogni livello le ricerche per giro si dimezzano, le pause e
l'intervallo tra i giri raddoppiano. Dopo un giro senza problemi scende di un livello.

| Livello | Ricerche per giro | Pausa | Intervallo (con 30 min) |
|---|---|---|---|
| 0 | 100 | 3 s | 30 min |
| 1 | 50 | 6 s | 60 min |
| 2 | 25 | 12 s | 120 min |
| 3 | 12 | 24 s | 240 min |

### Parametri avanzati

Costanti in cima a `tracker.py`:

| Costante | Default | Significato |
|---|---|---|
| `RICERCHE_MAX_PER_GIRO` | 100 | ricerche precise per giro a ritmo normale |
| `PAUSA_SECONDI` | 3 | pausa tra due ricerche precise |
| `VERIFICA_DA_STIMA` | 15 | stime del calendario più basse da verificare ogni giro |
| `ITINERARI_VENDITORI` | 4 | itinerari di cui aprire la pagina di prenotazione |
| `PAUSA_CALENDARIO` | 1 | pausa tra due richieste al calendario |

## File

| Percorso | Contenuto |
|---|---|
| `tracker.py` | programma principale |
| `luoghi.py` | ricerca città e aeroporti (dataset Travelpayouts, cache 30 giorni) |
| `telegram_bot.py` | configurazione e invio dei messaggi Telegram |
| `data/<parametri>/top.txt` | ultima top |
| `data/<parametri>/storico.csv` | tutti i prezzi trovati |
| `data/<parametri>/prezzi.json` | stato corrente delle combinazioni |

## Limiti

- Usa API interne di Google Flights, non documentate e non ufficiali
  (tramite [fast-flights](https://github.com/AWeirdDev/fast-flights),
  [fli](https://github.com/punitarani/fli) e chiamate dirette). Se Google cambia
  formato, il tool può smettere di funzionare.
- Le date troppo lontane (circa oltre 11 mesi) non sono ancora in vendita:
  compaiono man mano.
- Le offerte delle agenzie cambiano spesso e da utente a utente: un prezzo visto
  nel browser può non comparire al tool, e viceversa.
- Prezzi in EUR, 1 adulto, classe economy.

Progetto personale, per uso privato e a basso volume. Le condizioni d'uso di
Google vietano l'accesso automatico ai suoi servizi: usalo a tuo rischio, senza
abbassare troppo la frequenza e senza moltiplicare le istanze.

## Licenza

[MIT](LICENSE)
