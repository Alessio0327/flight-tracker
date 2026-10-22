# flight-tracker

Monitor da terminale dei prezzi dei voli su Google Flights.

Gli dai le città, il periodo di partenza e la durata del viaggio. Ogni N minuti il
tool prova tutte le combinazioni di date, ti mostra le migliori e ti avvisa su
Telegram (e con una notifica macOS) quando il prezzo scende.

- Città al posto dei codici IATA: scrivi "Roma" e scegli Fiumicino, Ciampino o entrambi.
- Fino a 2 città per lato (es. arrivo Tokyo o Osaka), con i soli aeroporti che ti vanno bene.
- Ritorno dalla stessa città o da un'altra (es. andata Roma→Tokyo, ritorno Osaka→Roma).
- Confronto tra andata e ritorno su un biglietto e due biglietti di sola andata.
- Periodo: un mese, una data ± N giorni, oppure un intervallo di date.
- Suggerimento di partenze fino a 7 giorni fuori dal periodo, se costano meno.
- Giudizio sul prezzo (basso / nella media / alto) rispetto alla fascia tipica di Google.
- Prezzi delle agenzie (lastminute, Gotogate, ...), spesso più bassi del prezzo in lista.
- Parametri da domande interattive o da un file JSON.
- Notifiche Telegram per chiunque prema Avvia sul bot.
- Più ricerche in parallelo, una per terminale; i dati restano tra un avvio e l'altro.
- Rallenta da solo se Google limita le richieste.

## Indice

- [Installazione](#installazione)
- [Avvio rapido](#avvio-rapido)
- [Modalità di viaggio](#modalità-di-viaggio)
- [Inserire i parametri](#inserire-i-parametri)
- [Cosa mostra il terminale](#cosa-mostra-il-terminale)
- [Notifiche Telegram](#notifiche-telegram)
- [Più ricerche e ripresa dei dati](#più-ricerche-e-ripresa-dei-dati)
- [Come funziona](#come-funziona)
- [Quante richieste a Google](#quante-richieste-a-google)
- [Problemi comuni](#problemi-comuni)
- [Limiti](#limiti)

## Installazione

Serve Python 3.11 o più recente.

```bash
git clone https://github.com/Alessio0327/flight-tracker.git
cd flight-tracker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Avvio rapido

1. (Facoltativo) Collega il bot Telegram, una volta sola:
   ```bash
   .venv/bin/python tracker.py --setup-telegram
   ```
2. Avvia il tracker:
   ```bash
   .venv/bin/python tracker.py
   ```
3. Rispondi alle domande, oppure scegli `2` e indica un file JSON
   (es. `ricerche/esempio.json`).
4. Lascia il terminale aperto. Il tool lavora da solo finché non premi Ctrl+C.

## Modalità di viaggio

La prima domanda del percorso interattivo è il tipo di viaggio.

### [1] Andata e ritorno sulla stessa città

Il ritorno parte dalla città di arrivo e torna alla città di partenza.
Esempio: Roma → Osaka, ritorno Osaka → Roma.

Con due città di arrivo (es. Tokyo e Osaka) il tool cerca entrambe, ma non le
mescola: andata e ritorno sono sempre sulla stessa città.

Per ogni combinazione di date il tool cerca:
- l'**andata e ritorno su un unico biglietto** (di solito la più economica sui voli lunghi);
- **due biglietti di sola andata**, come confronto.

### [2] Ritorno da un'altra città

Scegli separatamente le città dell'andata e quelle del ritorno (1 o 2 per lato).
Esempio: andata Roma → Tokyo o Osaka, ritorno Tokyo o Osaka → Roma.

Il tool prova tutte le combinazioni di città:

| Variante | Come la cerca |
|---|---|
| Andata Tokyo, ritorno da Tokyo | A/R su un biglietto + 2 biglietti di sola andata |
| Andata Osaka, ritorno da Osaka | A/R su un biglietto + 2 biglietti di sola andata |
| Andata Tokyo, ritorno da Osaka | 2 biglietti di sola andata |
| Andata Osaka, ritorno da Tokyo | 2 biglietti di sola andata |

L'A/R su un biglietto vale solo quando il ritorno parte dalla città di arrivo e torna
alla città di partenza. Per le varianti miste il tool combina due biglietti di sola
andata, perché il biglietto unico "multi-città" non è disponibile nelle API usate.

Alla fine di ogni controllo trovi il confronto tra le varianti, con la migliore segnata.

### Quale scegliere

| Vuoi... | Tipo | Esempio |
|---|---|---|
| Il prezzo migliore verso una città | 1 | Roma → Osaka |
| Sapere se conviene Tokyo o Osaka | 1, due città di arrivo | Roma → Tokyo, Osaka |
| Un viaggio con entrata e uscita da città diverse | 2 | Roma → Tokyo, ritorno Osaka → Roma |
| Tutte le combinazioni tra due città | 2, due città per lato | come sopra, con Tokyo e Osaka su entrambi i lati |

Più città e più giorni vogliono dire più ricerche: vedi
[Quante richieste a Google](#quante-richieste-a-google).

## Inserire i parametri

All'avvio:

```
Parametri: [1] rispondo alle domande  [2] leggo da un file JSON (Invio = 1):
```

### Con le domande

Esempio con ritorno da un'altra città:

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
Durata minima viaggio (giorni): 14
Durata massima viaggio (giorni): 21
Massimo scali per tratta (0 = solo diretti, Invio = qualsiasi): 1
Quanti migliori risultati mostrare: 5
Frequenza aggiornamento (minuti): 60
```

Nel ritorno, Invio riusa le città dell'andata al contrario.

Prima di chiedere la durata, il tool controlla sul calendario di Google che nel
periodo ci siano voli in vendita. Se non ce ne sono, chiede subito un altro periodo o
un'altra città, senza farti rispondere alle altre domande.

Risposte accettate:

| Domanda | Esempi |
|---|---|
| Città | `roma`, `Tokyo`, codice aeroporto `FCO`, codice città `ROM` |
| Aeroporti | Invio = tutti, oppure numeri separati da virgola: `1,3` |
| Mese | `10/2027`, `10/27`, `2027-10` |
| Data | `15/10/2027`, `15/10/27`, `2027-10-15` |
| Giorni prima/dopo | `10` = 10 giorni prima e 10 dopo la data |
| Scali | `0` = solo diretti, `1`, `2`, Invio = qualsiasi |

Attenzione al periodo: con `20/03/27` e `10` le partenze vanno dal 10/03 al 30/03.
Un volo che parte il 03/03 resta fuori (al massimo compare come suggerimento 💡).

### Da un file JSON

Rispondi `2` e scrivi il percorso del file. Puoi anche trascinare il file nel
Terminale: apici e spazi protetti vengono tolti da soli. Il tool mostra un riassunto
e parte senza altre domande:

```
Parametri: [1] rispondo alle domande  [2] leggo da un file JSON (Invio = 1): 2
Percorso del file JSON: ricerche/esempio.json
  Andata Roma (FCO) -> Tokyo (HND, NRT) / Osaka (KIX, ITM)
  Ritorno Tokyo (HND, NRT) / Osaka (KIX, ITM) -> Roma (FCO)
  Partenza dal 28/02/2027 al 20/03/2027, durata 14-21 giorni, max 1 scalo, top 5, ogni 60 min
```

Esempio di file (`ricerche/esempio.json`):

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

| Campo | Obbligatorio | Valori |
|---|---|---|
| `andata.da`, `andata.a` | sì | 1 o 2 città, ognuna `{"nome": "...", "aeroporti": ["..."]}` |
| `ritorno.da`, `ritorno.a` | no | come sopra. Senza `ritorno` il viaggio è di tipo 1 (stessa città) |
| `periodo` | sì | `{"data": "10/03/2027", "giorni_prima_dopo": 10}`, `{"mese": "03/2027"}` oppure `{"dal": "01/03/2027", "al": "20/03/2027"}` |
| `durata` | sì | `{"min": 14, "max": 21}` |
| `max_scali` | no | `null` o assente = qualsiasi, `0` = solo diretti, `1`, `2` |
| `top` | no | numero di risultati, default 5 |
| `frequenza_minuti` | no | minuti tra un controllo e l'altro, default 30 |

Nel file le città vanno scritte con i codici aeroporto: la ricerca per nome vale solo
nelle domande. Il `nome` serve solo per i messaggi. Se il file non è valido, il tool
dice cosa non va (es. `manca il campo 'periodo'`) e richiede il percorso.

Un file per ricerca è comodo per rilanciare la stessa ricerca, o più ricerche in
terminali diversi, senza rispondere ogni volta alle domande.

## Cosa mostra il terminale

Durante un controllo, una barra su una riga per ogni fase:

```
✓ Calendario [████████████████████████] 40/40 100% · in 44 s · 434 prezzi stimati

Verifica precisa: 100 ricerche (top attuale 5, stime migliori 15, a rotazione 80)
★ nuovo minimo: 672 EUR A/R Osaka, 2027-03-01 -> 2027-03-22 (21 gg)
✓ Verifica   [████████████████████████] 100/100 100% · in 7 min 00 s · minimo 672 EUR

Prezzi dei venditori (agenzie comprese) per 5 A/R in top
★ nuovo minimo: 656 EUR su lastminute.com  2027-03-01 -> 2027-03-22  (andata 08:55, ritorno 17:55)
✓ Venditori  [████████████████████████] 5/5 100% · in 6 min 02 s · minimo 656 EUR
```

Alla fine, la top e un conto alla rovescia fino al controllo successivo:

```
Top 5 Roma -> Tokyo/Osaka, ritorno Tokyo/Osaka -> Roma, partenza 2027-02-28 .. 2027-03-20, 14-21 giorni, max 1 scalo
Stimate 266/266 ricerche, verificate col prezzo completo 100/266 (scansione in corso). Le 15 combinazioni piu'
economiche secondo il calendario sono gia' verificate; le altre 166 ricerche ai prossimi controlli (massimo 100
per controllo, per non farsi bloccare da Google)

1. 656 EUR su lastminute.com (674 EUR in lista, andata 08:55, ritorno 17:55)  A/R Osaka  2027-03-01 -> 2027-03-16 (15 gg)  Qatar Airways  [FCO-DOH DOH-KIX]
   Prezzo BASSO: -32% sul tipico 986 EUR, fascia 870-1400 EUR, minimo ultimi 60 gg 674 EUR
   https://www.google.com/travel/flights/search?tfs=...
...

Confronto varianti (prezzi verificati):
  Andata Tokyo, ritorno da Tokyo: A/R 777 EUR · 2 biglietti 1109 EUR
  Andata Tokyo, ritorno da Osaka: 2 biglietti 1118 EUR
  Andata Osaka, ritorno da Tokyo: 2 biglietti 1121 EUR
  Andata Osaka, ritorno da Osaka: A/R 656 EUR · 2 biglietti 1130 EUR  ← migliore

💡 Partendo il 26/02 (fuori dal tuo periodo) risparmi 40 EUR: 616 EUR A/R Osaka, 2027-02-26 -> 2027-03-12 (14 gg)
   https://www.google.com/travel/flights/search?tfs=...

Prossimo aggiornamento tra 48:25 (alle 23:40)
```

Come leggerla:

- **Prezzo.** "656 EUR su lastminute.com (674 EUR in lista)": il prezzo più basso
  trovato tra i venditori, e tra parentesi quello mostrato nella lista di Google.
- **Giudizio.** Confronto con la fascia tipica di Google per quella tratta e il
  minimo degli ultimi 60 giorni. "BASSO" vicino al minimo dei 60 giorni è un buon
  segnale per prenotare.
- **Copertura.** "Stimate" = prezzo indicativo dal calendario. "Verificate" =
  prezzo vero da una ricerca completa. La top usa solo prezzi verificati.
- **Confronto varianti.** Il miglior prezzo per ogni combinazione di città. "(stima)"
  vuol dire che quella variante non è ancora stata verificata.
- **💡 Suggerimento.** Una partenza fino a 7 giorni prima o dopo il periodo che costa
  meno della top. Non entra mai nella top.
- **Due biglietti.** Una proposta con due biglietti di sola andata mostra i due voli
  con prezzo e link, e l'avviso che non sono collegati: se un volo cambia o salta,
  l'altro non è protetto.

La top finisce anche in `data/<cartella>/top.txt`.

## Notifiche Telegram

### Configurazione (una volta)

```bash
.venv/bin/python tracker.py --setup-telegram
```

1. Su Telegram apri @BotFather, invia `/newbot` e copia il token.
2. Incolla il token quando il tool lo chiede.
3. Apri il tuo bot e premi **Avvia**: la tua chat è iscritta.

### Chi riceve le notifiche

Chiunque apra il bot e prema **Avvia** (`/start`) riceve le notifiche di tutti i
tracker attivi e risponde "✅ Iscritto alle notifiche voli". Con `/stop` smette.

- Mentre un tracker gira, il tool controlla i nuovi messaggi ogni 10 secondi.
- Se nessun tracker è attivo, l'iscrizione avviene al prossimo avvio (Telegram
  conserva i messaggi per 24 ore).
- Chi blocca il bot viene tolto da solo.
- Chi trova il nome del bot può iscriversi e vedere tratte, date e prezzi:
  condividilo solo con chi deve vederli.

La configurazione è in `telegram.json` (permessi 600, escluso da git). Per togliere
una chat a mano, cancella il suo numero da `chat_ids`:

```json
{"token": "123456789:AA...", "chat_ids": [123456789, 987654321], "offset": 0}
```

### Messaggi

| Quando | Messaggio |
|---|---|
| Primo controllo dopo l'avvio | 🚀 Tracker avviato: prezzi migliori attuali, con la top completa |
| Nuovo prezzo minimo | ✈️ Nuovo prezzo minimo, con la top completa |
| Controllo finito, nessun minimo nuovo | ✅ Check ok, nessun prezzo migliore trovato, con il minimo attuale |
| Controllo interrotto da Google | ⚠️ Check interrotto, più ⚠️ Rallento con il nuovo ritmo |
| Google risponde di nuovo bene | ✅ Accelero |
| Ctrl+C | ⏹ Tracker fermato da te |
| Errore imprevisto | ❌ Tracker fermato per un errore, con il messaggio d'errore |

Ogni messaggio di controllo indica l'orario del prossimo. Se non arriva a
quell'ora, il tracker si è fermato (o il Mac è andato in stop).

Esempio di messaggio con la top:

```
✈️ Nuovo prezzo minimo

🛫 Roma (FCO) → Tokyo (HND, NRT) / Osaka (KIX, ITM)
🛬 Tokyo (HND, NRT) / Osaka (KIX, ITM) → Roma (FCO)
📅 Partenza dal 28/02/2027 al 20/03/2027
🧳 Durata min: 14 gg - max: 21 giorni · max 1 scalo · controllo ogni 60 min

🔎 Scansione in corso: 100/266 ricerche verificate, 266/266 stimate
✅ Le 15 combinazioni più economiche del calendario sono già verificate
⏳ Le altre 166 ai prossimi controlli (max 100 per controllo, per non farsi bloccare da Google)

🏆 Top 5

1. 656 EUR · A/R Osaka
   📆 01/03 → 16/03 (15 gg)
   🏷 su lastminute.com (674 EUR in lista, andata 08:55, ritorno 17:55)
   🛩 Qatar Airways [FCO-DOH DOH-KIX]
   📊 BASSO: -32% sul tipico 986 EUR, fascia 870-1400 EUR, minimo ultimi 60 gg 674 EUR
   🔗 Apri su Google Flights
...

⚖️ Confronto varianti (prezzi verificati)
  ...

⏱ Prossimo controllo alle 23:40
```

## Più ricerche e ripresa dei dati

- Apri un terminale per ogni ricerca e lancia `tracker.py` in ognuno.
- Ogni combinazione di parametri ha la sua cartella in `data/`.
- Rilanciando con gli stessi parametri (domande o file), il tool riprende i prezzi
  già trovati: la copertura non riparte da zero e un prezzo già noto non viene
  segnalato come "nuovo minimo".
- Due istanze con parametri identici non possono girare insieme.
- Tutte le istanze usano lo stesso IP: 2 o 3 insieme vanno bene, di più fanno
  arrivare prima i limiti di Google.

Esempio utile: un'istanza su tutto il periodo che ti interessa e una piccola su
pochi giorni dove hai visto un buon prezzo.

## Come funziona

Ogni controllo ha tre fasi.

1. **Calendario (stima veloce).** Il grafico prezzi di Google dà, con una richiesta,
   il prezzo indicativo di tutte le date di partenza per una coppia di aeroporti:
   per l'A/R con durata fissa, oppure per la sola andata. Copre tutto in meno di un
   minuto, ma non vede tutte le tariffe.
2. **Verifica (prezzo vero).** Ricerca completa sulla singola combinazione, come su
   Google Flights: prezzo, compagnie, scali, giudizio, link. Ogni controllo
   verifica, in quest'ordine:
   - la top attuale;
   - le 15 combinazioni più economiche secondo il calendario;
   - a rotazione tutte le altre, prima quelle mai verificate e poi le più vecchie.

   Così una stima sbagliata prima o poi viene corretta, e ogni prezzo viene
   aggiornato periodicamente. Con più ricerche del massimo per controllo (100), la
   prima copertura completa richiede più controlli; dopo, il tool continua ad
   aggiornare i prezzi più vecchi.
3. **Venditori.** Per gli A/R in top, il tool apre le pagine di prenotazione degli
   itinerari più economici e tiene il venditore che costa meno, agenzie comprese.
   Per i biglietti di sola andata Google non dà i venditori: si usa il prezzo in lista.

**Date fuori dal periodo.** Il calendario guarda anche 7 giorni prima e dopo il
periodo, con le stesse durate. Una richiesta al calendario copre fino a 61 giorni,
quindi di solito non costa richieste in più. Se la stima più economica fuori dal
periodo costa meno del meglio nel periodo, il tool la verifica (1 o 2 ricerche) e,
se il prezzo vero batte la top, la mostra come suggerimento 💡.

## Quante richieste a Google

Google non pubblica limiti per Google Flights. Il tool parte con un ritmo prudente
e rallenta da solo.

- Numero di ricerche: una per ogni coppia di date A/R, più una per ogni giorno e
  città di sola andata. Esempio: Roma → Tokyo/Osaka, 21 giorni di partenza, durata
  14-21 giorni = 266 ricerche, coperte in 3 controlli.
- Con un HTTP 429, un captcha o 5 errori di fila il controllo si interrompe e il
  tool sale di livello. Dopo un controllo senza problemi scende di un livello.

| Livello | Ricerche per controllo | Pausa | Intervallo (con 30 min) |
|---|---|---|---|
| 0 | 100 | 3 s | 30 min |
| 1 | 50 | 6 s | 60 min |
| 2 | 25 | 12 s | 120 min |
| 3 | 12 | 24 s | 240 min |

Costanti in cima a `tracker.py`:

| Costante | Default | Significato |
|---|---|---|
| `RICERCHE_MAX_PER_GIRO` | 100 | ricerche complete per controllo a ritmo normale |
| `PAUSA_SECONDI` | 3 | pausa tra due ricerche complete |
| `VERIFICA_DA_STIMA` | 15 | stime più basse del calendario da verificare a ogni controllo |
| `ITINERARI_VENDITORI` | 4 | itinerari di cui aprire la pagina di prenotazione |
| `PAUSA_CALENDARIO` | 1 | pausa tra due richieste al calendario |
| `GIORNI_FUORI_PERIODO` | 7 | giorni prima/dopo il periodo in cui cercare date più economiche |

## Problemi comuni

**Su Telegram non arriva niente da ore.** Controlla che il terminale sia aperto e il
Mac non sia in stop. Ogni controllo manda almeno "✅ Check ok": se manca all'orario
indicato, il tracker non sta girando.

**Ho premuto Avvia sul bot e non succede nulla.** Il bot risponde solo mentre un
tracker è attivo. Avvia un tracker: l'iscrizione arriva entro 10 secondi.

**"verificate 100/266 (scansione in corso)".** È normale: ogni controllo fa al
massimo 100 ricerche complete. Le combinazioni più economiche vengono verificate per
prime, le altre ai controlli successivi.

**Dopo un riavvio dice "nessun prezzo migliore".** Il tool ha ripreso i prezzi già
trovati con gli stessi parametri. Il primo messaggio dopo l'avvio contiene comunque
la top completa.

**Il prezzo che vedo su Google Flights non compare.** Controlla che la data di
partenza sia nel periodo e che gli scali rientrino nel massimo. Le offerte delle
agenzie cambiano anche da utente a utente.

**`errori_rete.log` nella cartella dei dati.** Contiene i messaggi interni della
libreria di rete (es. `excessive load generating behavior`): Google chiude una
connessione e il tool ne apre un'altra. Non è un blocco.

## File

| Percorso | Contenuto |
|---|---|
| `tracker.py` | programma principale |
| `luoghi.py` | ricerca città e aeroporti (dataset Travelpayouts, cache 30 giorni) |
| `telegram_bot.py` | configurazione, iscrizioni e invio dei messaggi Telegram |
| `ricerche/esempio.json` | esempio di parametri da file |
| `telegram.json` | token del bot e chat iscritte (escluso da git) |
| `data/<parametri>/top.txt` | ultima top |
| `data/<parametri>/storico.csv` | tutti i prezzi trovati |
| `data/<parametri>/prezzi.json` | stato corrente delle ricerche |
| `data/<parametri>/parametri.json` | parametri della ricerca |
| `data/<parametri>/errori_rete.log` | messaggi interni della libreria di rete |

## Limiti

- Usa API interne di Google Flights, non documentate e non ufficiali
  (tramite [fast-flights](https://github.com/AWeirdDev/fast-flights),
  [fli](https://github.com/punitarani/fli) e chiamate dirette). Se Google cambia
  formato, il tool può smettere di funzionare.
- Google Flights cerca voli solo fino a oggi + 330 giorni (conta il ritorno) e il
  calendario prezzi fino a oggi + 305. All'avvio il tool mostra la data limite. Le
  combinazioni oltre il limite vengono cercate man mano che diventano cercabili.
- Il biglietto unico "multi-città" (andata su una città, ritorno da un'altra) non è
  supportato: per quella variante il tool combina due biglietti di sola andata.
- Per i biglietti di sola andata non ci sono i prezzi dei venditori.
- Prezzi in EUR, 1 adulto, classe economy.

Progetto personale, per uso privato e a basso volume. Le condizioni d'uso di
Google vietano l'accesso automatico ai suoi servizi: usalo a tuo rischio, senza
abbassare troppo la frequenza e senza moltiplicare le istanze.

## Licenza

[MIT](LICENSE)
