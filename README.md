# flight-tracker

Monitor da terminale dei prezzi dei voli andata/ritorno su Google Flights.
Gli dai la tratta, il periodo di partenza e la durata del viaggio. Il tool cerca
tutte le combinazioni di date ogni N minuti, ti mostra la top dei prezzi migliori
e ti avvisa (notifica macOS e Telegram) quando trova un nuovo minimo.

- Città al posto dei codici IATA: scrivi "Roma" e scegli Fiumicino, Ciampino o entrambi.
- Fino a 2 città per ogni lato (es. arrivo Tokyo o Osaka), e solo gli aeroporti che ti vanno bene.
- Ritorno anche da un'altra città (es. andata Roma→Tokyo, ritorno Osaka→Roma).
- Confronta l'andata e ritorno sullo stesso biglietto con due biglietti di sola andata,
  e mostra il miglior prezzo per ogni combinazione di città.
- Periodo di partenza: un mese intero oppure una data ± N giorni.
- Suggerisce partenze fino a 7 giorni prima o dopo il periodo, se costano meno.
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

All'avvio il tool mostra fino a che data si può cercare e fa alcune domande.
Esempio di sessione con ritorno da un'altra città:

```
Date cercabili: partenza da domani, ultimo volo entro il 17/09/2027 (limite di Google Flights, oggi + 330 giorni).

Tipo di viaggio: [1] andata e ritorno sulla stessa citta'  [2] ritorno da un'altra citta': 2
ANDATA
Quante citta' di partenza? [1/2] (Invio = 1):
  Citta' di partenza: roma
  [1] Roma, IT  (FCO Fiumicino, CIA Ciampino)
  [2] Roma, AU  (RMA Roma)
  Quale 'roma'? (Invio = 1):
  [1] FCO Fiumicino
  [2] CIA Ciampino
  Aeroporti (Invio = tutti, oppure es. 1,2): 1
Quante citta' di arrivo? [1/2] (Invio = 1): 2
  Citta' di arrivo 1: tokyo
  Aeroporti (Invio = tutti, oppure es. 1,2):
  Citta' di arrivo 2: osaka
  [1] UKB Kobe
  [2] KIX Kansai International
  [3] ITM Itami
  Aeroporti (Invio = tutti, oppure es. 1,2): 2,3
RITORNO
Quante citta' di partenza del ritorno? [1/2] (Invio = Tokyo (HND, NRT) / Osaka (KIX, ITM)):
Quante citta' di arrivo del ritorno? [1/2] (Invio = Roma (FCO)):
Periodo di partenza: [1] un mese  [2] intorno a una data: 2
Data (es. 15/10/2027): 10/03/27
Quanti giorni prima/dopo quella data: 10
  Controllo i voli in vendita...
  Andata: voli in 21 date su 21, solo andata da 562 EUR.
  Ritorno: voli in 51 date su 51, solo andata da 556 EUR.
Durata minima viaggio (giorni): 12
Durata massima viaggio (giorni): 21
Massimo scali per tratta (0 = solo diretti, Invio = qualsiasi):
Quanti migliori risultati mostrare: 5
Frequenza aggiornamento (minuti): 30
```

### Parametri da file

Alla prima domanda (`Parametri: [1] rispondo alle domande  [2] leggo da un file JSON`)
rispondi `2` e indica il percorso del file (puoi anche trascinarlo nel Terminale).
Esempio, in `ricerche/esempio.json`:

```json
{
  "andata": {
    "da": [{"nome": "Roma", "aeroporti": ["FCO"]}],
    "a": [
      {"nome": "Tokyo", "aeroporti": ["HND", "NRT"]},
      {"nome": "Osaka", "aeroporti": ["KIX", "ITM"]}
    ]
  },
  "ritorno": {
    "da": [
      {"nome": "Tokyo", "aeroporti": ["HND", "NRT"]},
      {"nome": "Osaka", "aeroporti": ["KIX", "ITM"]}
    ],
    "a": [{"nome": "Roma", "aeroporti": ["FCO"]}]
  },
  "periodo": {"data": "10/03/2027", "giorni_prima_dopo": 10},
  "durata": {"min": 14, "max": 21},
  "max_scali": 1,
  "top": 5,
  "frequenza_minuti": 60
}
```

| Campo | Valori |
|---|---|
| `andata`, `ritorno` | 1 o 2 città per lato, ognuna con nome e codici aeroporto. Senza `ritorno`: andata e ritorno sulla stessa città |
| `periodo` | `{"data": "10/03/2027", "giorni_prima_dopo": 10}`, `{"mese": "03/2027"}` oppure `{"dal": "01/03/2027", "al": "20/03/2027"}` |
| `durata` | `{"min": 14, "max": 21}` |
| `max_scali` | `null` = qualsiasi, `0` = solo diretti, `1`, `2` |
| `top`, `frequenza_minuti` | facoltativi, default 5 e 30 |

Con il tipo `1` il ritorno parte dalle città di arrivo dell'andata e torna a quelle
di partenza, senza mescolare le città. Se nel periodo non c'è nessun volo in
vendita, il tool chiede subito un altro periodo o un'altra città.

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
✓ Calendario [████████████████████████] 12/12 100% · in 14 s · 20 prezzi stimati
Verifica precisa: 20 ricerche (top attuale 0, stime migliori 15, a rotazione 5)
★ nuovo minimo: 820 EUR A/R Tokyo, 2027-03-07 -> 2027-03-22 (15 gg)
✓ Verifica   [████████████████████████] 20/20 100% · in 1 min 22 s · minimo 820 EUR
✓ Venditori  [████████████████████████] 3/3 100% · in 2 min 10 s · minimo 787 EUR

Top 3 Fiumicino -> Tokyo/Osaka, ritorno Tokyo/Osaka -> Fiumicino, partenza 2027-03-07 .. 2027-03-09, 14-15 giorni
Stimate 20/20 ricerche, verificate col prezzo completo 20/20 (scansione completa)

1. 787 EUR su lastminute.com (820 EUR in lista, andata 22:00, ritorno 19:35)  A/R Tokyo  2027-03-07 -> 2027-03-22 (15 gg)  Asiana Airlines  [FCO-ICN ICN-NRT]
...

Confronto varianti (prezzi verificati):
  Andata Tokyo, ritorno da Tokyo: A/R 787 EUR · 2 biglietti 1139 EUR  ← migliore
  Andata Tokyo, ritorno da Osaka: 2 biglietti 1158 EUR
  Andata Osaka, ritorno da Tokyo: 2 biglietti 1139 EUR
  Andata Osaka, ritorno da Osaka: A/R 827 EUR · 2 biglietti 1165 EUR

Prossimo aggiornamento tra 26:12 (alle 18:29)
```

Una proposta con due biglietti mostra i due voli separati, con il loro prezzo e link,
e l'avviso che i biglietti non sono collegati: se un volo cambia o salta, l'altro non
è protetto.

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
3. Apri il bot e premi Avvia (`/start`): la tua chat è iscritta.

Chiunque apra il bot e prema Avvia, anche più tardi, riceve le notifiche: mentre il
tracker gira, il tool controlla i nuovi messaggi ogni 10 secondi. Con `/stop` la chat
smette di riceverle. Chi trova il nome del bot può iscriversi e vedere tratte, date e
prezzi: non condividerlo con chi non deve vederli.

La configurazione finisce in `telegram.json` (permessi 600, escluso da git). Per
togliere una chat a mano, cancella il suo numero da `chat_ids`:

```json
{"token": "123456789:AA...", "chat_ids": [123456789, 987654321], "offset": 0}
```

Il bot scrive quando:
- trova un nuovo prezzo minimo: top completa, con copertura della scansione e orario del prossimo controllo;
- finisce un controllo senza nuovo minimo: "✅ Check ok, nessun prezzo migliore trovato", con il minimo attuale e il prossimo controllo;
- si ferma: "⏹ Tracker fermato" con Ctrl+C, "❌ Tracker fermato per un errore" con il messaggio d'errore;
- rallenta o riaccelera perché Google limita le richieste: nuovo ritmo e orario del prossimo controllo.

## Come funziona

Ogni giro ha tre fasi.

1. **Calendario (stima veloce).** Il grafico prezzi di Google restituisce, con una
   richiesta, il prezzo indicativo di tutte le date di partenza per una coppia di
   aeroporti: per l'andata e ritorno con durata fissa, oppure per la sola andata. Copre tutte le combinazioni in pochi secondi, ma non vede
   tutte le tariffe.
2. **Verifica (prezzo vero).** Ricerca completa sulla singola coppia di date, come
   su Google Flights: prezzo, compagnie, scali, giudizio sul prezzo, link.
   Ogni giro verifica la top attuale, le 15 stime più basse e, a rotazione, tutte
   le altre combinazioni: così anche una stima sbagliata prima o poi viene corretta.
   Le ricerche sono di due tipi: andata e ritorno sullo stesso biglietto (solo se il
   ritorno parte da una città di arrivo e torna alla città di partenza) e voli di sola
   andata per ogni città, poi combinati in coppie andata + ritorno.
3. **Venditori.** Per gli A/R in top, il tool apre le pagine di prenotazione degli
   itinerari più economici e tiene il venditore che costa meno, agenzie comprese.
   Per i biglietti di sola andata questa fase non è disponibile: si usa il prezzo in lista.

La top e le notifiche usano solo prezzi verificati (fase 2 o 3).

**Date fuori dal periodo.** Il calendario guarda anche 7 giorni prima e dopo il periodo
di partenza (con le stesse durate). Una richiesta al calendario copre fino a 61 giorni,
quindi di solito non servono richieste in più. Se la stima più economica fuori dal
periodo costa meno del meglio nel periodo, il tool la verifica (1 o 2 ricerche) e, se
il prezzo vero è più basso della top, la mostra a parte:

```
💡 Partendo il 03/03 (fuori dal tuo periodo) risparmi 131 EUR: 656 EUR A/R Osaka, 2027-03-03 -> 2027-03-22 (19 gg)
```

Queste date non entrano mai nella top.

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
| `GIORNI_FUORI_PERIODO` | 7 | giorni prima/dopo il periodo in cui cercare date più economiche |

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
- Google Flights cerca voli solo fino a oggi + 330 giorni (conta il ritorno) e il
  calendario prezzi fino a oggi + 305. All'avvio il tool mostra la data limite e
  controlla sul calendario che nel periodo scelto ci siano voli in vendita; se non ce
  ne sono, chiede subito un altro periodo o un'altra città. Le combinazioni oltre il
  limite vengono cercate man mano che diventano cercabili.
- Le offerte delle agenzie cambiano spesso e da utente a utente: un prezzo visto
  nel browser può non comparire al tool, e viceversa.
- Prezzi in EUR, 1 adulto, classe economy.
- Il biglietto unico "multi-città" (andata su una città, ritorno da un'altra, stesso
  biglietto) non è supportato dalle API usate: per quella variante il tool combina
  due biglietti di sola andata.

Progetto personale, per uso privato e a basso volume. Le condizioni d'uso di
Google vietano l'accesso automatico ai suoi servizi: usalo a tuo rischio, senza
abbassare troppo la frequenza e senza moltiplicare le istanze.

## Licenza

[MIT](LICENSE)
