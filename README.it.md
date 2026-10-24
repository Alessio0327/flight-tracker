# flight-tracker

[![test](https://github.com/Alessio0327/flight-tracker/actions/workflows/test.yml/badge.svg)](https://github.com/Alessio0327/flight-tracker/actions/workflows/test.yml)

🇬🇧 [English](README.md) · 🇮🇹 **Italiano**

**Trova il volo più economico tra centinaia di combinazioni di date, e ti avvisa su
Telegram quando il prezzo scende.**

flight-tracker è un programma da terminale che interroga Google Flights per te. Gli dici
dove vuoi andare, in che periodo e per quanti giorni. Lui prova tutte le combinazioni di
date possibili, ti mostra le più economiche e continua a controllarle ogni ora (o con la
frequenza che scegli) finché non lo fermi.

> **Non è un servizio online.** È un programma per uso personale che vive nel terminale
> del tuo computer: lavora solo mentre il terminale è aperto e il computer acceso e
> sveglio. Quando chiudi il terminale o il computer va in stop, i controlli si fermano.

## Perché

Amo viaggiare e cerco di farlo il più spesso possibile. Per questo, ho passato ore a cercare
la combinazione perfetta di voli per trovare le tariffe più convenienti.

A un certo punto mi sono chiesto: perché perdere così tanto tempo a cercare, quando potrei
creare uno strumento che lo faccia al posto mio?

Ed eccolo qui!

Esempio: vuoi andare negli Stati Uniti a maggio, per 10-14 giorni. Ti va bene arrivare
a New York o a Boston, e magari tornare dall'altra città.

Su Google Flights dovresti provare una coppia di date alla volta: partenza dal 03/05 al
17/05 e durata da 10 a 14 giorni fanno 75 combinazioni solo per l'andata e ritorno, e
circa 140 se aggiungi i voli di sola andata tra le due città. Per di più i prezzi
cambiano ogni giorno, e le agenzie (lastminute, Gotogate, ...) spesso costano meno del
prezzo mostrato nella lista.

flight-tracker fa quei controlli al posto tuo:

```
1. 489 EUR su Gotogate (512 EUR in lista, andata 06:00, ritorno 18:40)  A/R New York  2027-05-06 -> 2027-05-18 (12 gg)  TAP Air Portugal  [FCO-LIS LIS-JFK]
   Prezzo BASSO: -29% sul tipico 690 EUR, fascia 560-950 EUR, minimo ultimi 60 gg 512 EUR
```

In questo caso ha trovato un volo da 489 EUR su un'agenzia, contro i 512 EUR della
lista di Google e i 690 EUR tipici per quella tratta.

## Cosa fa

- **Prova tutte le date:** periodo di partenza (un mese, una data ± N giorni, o un
  intervallo) per ogni durata tra un minimo e un massimo.
- **Modalità weekend:** viaggi da 1 a 4 giorni che toccano sabato o domenica, per tutti
  i weekend del periodo.
- **Città, non codici:** scrivi "Roma" e scegli Fiumicino, Ciampino o entrambi. Fino a 2
  città per lato (es. New York o Boston).
- **Ritorno da un'altra città:** es. andata Roma → New York, ritorno Boston → Roma.
- **A/R contro due biglietti:** confronta l'andata e ritorno su un biglietto con due
  biglietti di sola andata, e ti dice quale variante conviene.
- **Prezzi delle agenzie:** per i migliori risultati apre le pagine di prenotazione e
  prende il venditore che costa meno.
- **Giudizio sul prezzo:** basso, nella media o alto, rispetto alla fascia tipica di
  Google e al minimo degli ultimi 60 giorni.
- **Date vicine:** se partire fino a 7 giorni prima o dopo il periodo costa meno, te lo
  segnala a parte.
- **Notifiche Telegram:** quando il prezzo scende, a chiunque prema Avvia sul tuo bot.
- **Prezzo obiettivo:** se vuoi, il bot ti avvisa solo quando il prezzo scende sotto la
  cifra che hai scelto.
- **Ricerca privata:** una ricerca può non mandare niente su Telegram.
- **Paese di ricerca:** mostra IP e paese da cui partono le ricerche (es. con una VPN),
  perché Google adatta i prezzi al paese.
- **Italiano o inglese, valuta a scelta** (EUR, USD, GBP, ...).
- **Lavora da solo per giorni:** riprende i dati dopo un riavvio e rallenta se Google
  limita le richieste.

## Installazione

Serve Python 3.11 o più recente. Funziona su macOS, Linux e Windows.

macOS e Linux:

```bash
git clone https://github.com/Alessio0327/flight-tracker.git
cd flight-tracker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Windows (PowerShell o Windows Terminal):

```powershell
git clone https://github.com/Alessio0327/flight-tracker.git
cd flight-tracker
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Negli esempi di questa pagina i comandi sono quelli di macOS e Linux: su Windows usa
`.venv\Scripts\python` al posto di `.venv/bin/python`, per esempio
`.venv\Scripts\python tracker.py`. Usa Windows Terminal: il vecchio `cmd.exe` può
mostrare male emoji e barra di avanzamento. La notifica di sistema c'è solo su macOS;
quelle Telegram funzionano ovunque.

## Primo utilizzo

```bash
.venv/bin/python tracker.py
```

Il tool fa alcune domande. Ecco una sessione completa per l'esempio di New York e Boston
(Invio accetta il valore proposto):

```
Lingua / Language: [1] Italiano  [2] English (Invio/Enter = 1): 1
Parametri: [1] rispondo alle domande  [2] leggo da un file JSON (Invio = 1): 1
Date cercabili: partenza da domani, ultimo volo entro il 18/09/2027 (limite di Google Flights, oggi + 330 giorni).

Tipo di viaggio: [1] andata e ritorno sulla stessa citta'  [2] ritorno da un'altra citta': 2
ANDATA
Quante citta' di partenza? [1/2] (Invio = 1):
  Citta' di partenza: roma
  [1] Roma, Italia  (FCO Fiumicino, CIA Ciampino)
  [2] Roma, Australia  (RMA Roma)
  Quale 'roma'? (Invio = 1):
  [1] FCO Fiumicino
  [2] CIA Ciampino
  Aeroporti (Invio = tutti, oppure es. 1,2): 1
Quante citta' di arrivo? [1/2] (Invio = 1): 2
  Citta' di arrivo 1: new york
  [1] JFK John F. Kennedy International
  [2] LGA LaGuardia
  [3] EWR Newark Liberty International
  Aeroporti (Invio = tutti, oppure es. 1,2): 1,3
  Citta' di arrivo 2: boston
RITORNO
Quante citta' di partenza del ritorno? [1/2] (Invio = New York (JFK, EWR) / Boston (BOS)):
Quante citta' di arrivo del ritorno? [1/2] (Invio = Roma (FCO)):
Valuta dei prezzi (es. EUR, USD, GBP; Invio = EUR):
Periodo di partenza: [1] un mese  [2] intorno a una data: 2
Data (es. 15/10/2027): 10/05/27
Quanti giorni prima/dopo quella data: 7
  Controllo i voli in vendita...
  Andata: voli in 15 date su 15, solo andata da 289 EUR.
  Ritorno: voli in 45 date su 45, solo andata da 305 EUR.
Durata: [1] libera (giorni minimi e massimi)  [2] weekend (1-4 giorni con sabato o domenica) (Invio = 1):
Durata minima viaggio (giorni): 10
Durata massima viaggio (giorni): 14
Massimo scali per tratta (0 = solo diretti, Invio = qualsiasi): 1
Quanti migliori risultati mostrare: 5
Frequenza aggiornamento (minuti): 60
Avvisi Telegram: [1] a ogni nuovo prezzo minimo  [2] solo sotto un prezzo che scegli  [3] nessuno, ricerca privata (Invio = 1): 2
Prezzo obiettivo (EUR): 450

143 ricerche da monitorare (75 A/R, 68 sole andate). Dati in .../data/FCO-JFK_EWR_BOS-...
Aggiornamento ogni 60 min (si allunga da solo se Google limita). Ctrl+C per fermare.
```

Le tue risposte compaiono in verde, per distinguerle dalle domande. Se il tuo terminale
non mostra bene i colori, lancia il tool con `NO_COLOR=1 .venv/bin/python tracker.py`.

Poi il tool lavora da solo. Lascia il terminale aperto e fermalo con Ctrl+C quando hai
prenotato.

Risposte accettate:

| Domanda | Esempi |
|---|---|
| Città | `roma`, `Boston`, codice aeroporto `FCO`, codice città `ROM` |
| Aeroporti | Invio = tutti, oppure numeri separati da virgola: `1,3` |
| Mese | `10/2027`, `10/27`, `2027-10` |
| Data | `15/10/2027`, `15/10/27`, `2027-10-15` |
| Giorni prima/dopo | `7` = 7 giorni prima e 7 dopo la data |
| Durata | Invio o `1` = giorni minimi e massimi; `2` = weekend, poi giorni da 1 a 4 |
| Scali | `0` = solo diretti, `1`, `2`, Invio = qualsiasi |
| Avvisi | Invio o `1` = a ogni nuovo minimo; `2` = solo sotto il prezzo obiettivo, che il tool chiede subito dopo; `3` = nessun messaggio Telegram (ricerca privata) |
| Valuta | codice di 3 lettere: `EUR`, `USD`, `GBP`, `JPY`, ... Invio = EUR |

**Scelta delle città.** Quando più città hanno lo stesso nome, il tool le elenca con il
paese per intero (`Napoli, Italia` / `Napoli, Stati Uniti`) e mette prima quelle del
paese da cui stai cercando (lo ricava dall'IP, o dalla lingua). Controlla comunque la
riga prima di premere Invio: Naples in Florida, in italiano, si chiama anche lei "Napoli".
Sullo stesso lato non puoi scegliere due volte la stessa città, né due città con lo
stesso nome: le ricerche le distinguono per nome.

Prima di chiedere la durata, il tool controlla che nel periodo ci siano voli in
vendita. Se non ce ne sono, chiede subito un altro periodo o un'altra città, e ti
ricorda di controllare città e aeroporti scelti: un aeroporto piccolo (es. Salerno) o una
città omonima in un altro paese possono non avere voli.

## Cosa vedi durante un controllo

```
🌍 Ricerche da 🇮🇹 IT, Roma (IP 203.0.113.7)

✓ Calendario [████████████████████████] 21/21 100% · in 23 s · 212 prezzi stimati

Verifica precisa: 100 ricerche (top attuale 0, stime migliori 15, a rotazione 85)
★ nuovo minimo: 512 EUR A/R New York, 2027-05-06 -> 2027-05-18 (12 gg)
✓ Verifica   [████████████████████████] 100/100 100% · in 7 min 00 s · minimo 512 EUR

Prezzi dei venditori (agenzie comprese) per 5 A/R in top
★ nuovo minimo: 489 EUR su Gotogate  2027-05-06 -> 2027-05-18  (andata 06:00, ritorno 18:40)
✓ Venditori  [████████████████████████] 5/5 100% · in 6 min 02 s · minimo 489 EUR

================================================================================
Top 5 Roma -> New York/Boston, ritorno New York/Boston -> Roma, partenza 2027-05-03 .. 2027-05-17, 10-14 giorni, max 1 scalo
Stimate 143/143 ricerche, verificate col prezzo completo 100/143 (scansione in corso). Le 15 combinazioni piu'
economiche secondo il calendario sono gia' verificate; le altre 43 ricerche ai prossimi controlli (massimo 100
per controllo, per non farsi bloccare da Google)
🌍 Ricerche da 🇮🇹 IT, Roma (IP 203.0.113.7)

1. 489 EUR su Gotogate (512 EUR in lista, andata 06:00, ritorno 18:40)  A/R New York  2027-05-06 -> 2027-05-18 (12 gg)  TAP Air Portugal  [FCO-LIS LIS-JFK]
   Prezzo BASSO: -29% sul tipico 690 EUR, fascia 560-950 EUR, minimo ultimi 60 gg 512 EUR
   https://www.google.com/travel/flights/search?tfs=...
2. ...

Confronto varianti (prezzi verificati):
  Andata New York, ritorno da New York: A/R 489 EUR · 2 biglietti 641 EUR  ← migliore
  Andata New York, ritorno da Boston: 2 biglietti 668 EUR
  Andata Boston, ritorno da New York: 2 biglietti 655 EUR
  Andata Boston, ritorno da Boston: A/R 534 EUR · 2 biglietti 690 EUR

Prossimo aggiornamento tra 48:25 (alle 23:40)
```

Come leggerlo:

| Voce | Significato |
|---|---|
| 🌍 Ricerche da | IP e paese da cui partono le richieste. Se cambiano tra due controlli (es. accendi una VPN) compare un avviso: i prezzi possono cambiare con il paese |
| Calendario | stima veloce di tutte le date dal grafico prezzi di Google |
| Verifica precisa | ricerca completa, data per data, come su Google Flights |
| Venditori | prezzi delle agenzie per gli A/R in top |
| 489 EUR su Gotogate (512 EUR in lista) | prezzo migliore tra i venditori; tra parentesi quello della lista di Google |
| Prezzo BASSO | giudizio rispetto alla fascia tipica di Google. BASSO e vicino al minimo dei 60 giorni = buon momento per prenotare |
| Stimate / verificate | stimate = prezzo indicativo dal calendario; verificate = prezzo vero. La top usa solo prezzi verificati |
| Confronto varianti | il prezzo migliore per ogni combinazione di città. "(stima)" = non ancora verificato |
| 💡 Partendo il ... | data fino a 7 giorni fuori dal periodo che costa meno della top (non entra nella top) |

Ogni controllo fa al massimo 100 ricerche complete: con 143 ricerche la copertura completa
arriva al secondo controllo. Le combinazioni più economiche vengono verificate per prime.

L'ultima top è anche in `data/<ricerca>/top.txt`.

## Che ricerca impostare

### Tipo di viaggio

**[1] Stessa città.** Il ritorno parte dalla città di arrivo e torna a quella di
partenza. Con due città di arrivo (New York e Boston) il tool cerca entrambe senza
mescolarle.

**[2] Ritorno da un'altra città.** Scegli separatamente le città dell'andata e del
ritorno, e il tool prova tutte le combinazioni:

| Variante | Come la cerca |
|---|---|
| Andata New York, ritorno da New York | A/R su un biglietto + 2 biglietti di sola andata |
| Andata Boston, ritorno da Boston | A/R su un biglietto + 2 biglietti di sola andata |
| Andata New York, ritorno da Boston | 2 biglietti di sola andata |
| Andata Boston, ritorno da New York | 2 biglietti di sola andata |

Il biglietto unico "multi-città" non è disponibile nelle API usate: per le varianti
miste il tool combina due biglietti di sola andata e ti ricorda che non sono collegati
(se un volo cambia o salta, l'altro non è protetto).

### Esempi

| Vuoi... | Impostazione |
|---|---|
| Il prezzo migliore per Boston a maggio | tipo 1, Roma → Boston, mese `05/2027` |
| Capire se conviene New York o Boston | tipo 1, Roma → New York e Boston |
| Entrare da New York e uscire da Boston | tipo 2, Roma → New York, ritorno Boston → Roma |
| Tutte le combinazioni tra le due città | tipo 2, New York e Boston su entrambi i lati |
| Un weekend fuori a marzo, 2-3 giorni | durata `2` (weekend), mese `03/2027`, giorni 2-3 |
| Tenere d'occhio un buon prezzo visto su pochi giorni | data ± 3, durata stretta (es. 10-12) |

### Weekend

Alla domanda `Durata` rispondi `2`: il tool chiede quanti giorni deve durare il viaggio,
**contando partenza e ritorno** (ven → dom = 3 giorni, sab in giornata = 1), da 1 a 4.
Poi tiene solo i viaggi che toccano **almeno un giorno tra sabato e domenica**, per ogni
weekend del periodo: ven → sab, sab → lun, dom → mar sì; lun → gio o ven in giornata no.

```
Durata: [1] libera (giorni minimi e massimi)  [2] weekend (1-4 giorni con sabato o domenica) (Invio = 1): 2
Giorni minimi del viaggio, partenza e ritorno compresi (1-4): 2
Giorni massimi del viaggio, partenza e ritorno compresi (2-4): 3
...
1. 72 EUR  A/R Barcellona  2027-03-06 -> 2027-03-08 (3 gg, sab → lun)  Wizz Air  [FCO-BCN]
```

Per un mese di weekend, usa come periodo il mese intero (`03/2027`). Nel file JSON:
`"weekend": true`, con `durata` in giorni di calendario (facoltativa, default 1-4).

### Il periodo si conta dalla data

Con data `20/05/27` e `10` giorni, le partenze vanno dal 10/05 al 30/05. Un volo che
parte il 03/05 resta fuori: al massimo compare come suggerimento 💡 se è entro 7 giorni.

### Quante ricerche

Una per ogni coppia di date A/R, più una per ogni giorno e città di sola andata.
Più città e più giorni vogliono dire più ricerche e più controlli per la copertura
completa. Esempi: Roma → Boston, 9 giorni di partenza, durata 10-14 = 67 ricerche (un
controllo); l'esempio di New York e Boston = 143 ricerche (due controlli).

## Parametri da file e avvio diretto

Per non rispondere ogni volta alle domande, salva la ricerca in un file JSON. Esempio, nel
formato di `ricerche/esempio.json`:

```json
{
  "lingua": "it",
  "andata": {
    "da": [{"nome": "Roma", "aeroporti": ["FCO"]}],
    "a": [
      {"nome": "New York", "aeroporti": ["JFK", "EWR"]},
      {"nome": "Boston", "aeroporti": ["BOS"]}
    ]
  },
  "ritorno": {
    "da": [
      {"nome": "New York", "aeroporti": ["JFK", "EWR"]},
      {"nome": "Boston", "aeroporti": ["BOS"]}
    ],
    "a": [{"nome": "Roma", "aeroporti": ["FCO"]}]
  },
  "periodo": {"data": "10/05/2027", "giorni_prima_dopo": 7},
  "durata": {"min": 10, "max": 14},
  "max_scali": 1,
  "top": 5,
  "frequenza_minuti": 60,
  "valuta": "EUR",
  "avvisa_sotto": null,
  "telegram": true
}
```

Due modi di usarlo:

```bash
# avvio diretto: nessuna domanda, tutto dal file
.venv/bin/python tracker.py ricerche/esempio.json

# dalle domande: scegli la lingua, poi 2 e il percorso del file
.venv/bin/python tracker.py
```

| Campo | Obbligatorio | Valori |
|---|---|---|
| `lingua` | no | `"it"` o `"en"`, default `"it"`. Vale nell'avvio diretto; se carichi il file dalle domande, il tool lo aggiorna con la lingua scelta |
| `andata.da`, `andata.a` | sì | 1 o 2 città, ognuna `{"nome": "...", "aeroporti": ["..."]}` |
| `ritorno.da`, `ritorno.a` | no | come sopra. Senza `ritorno`: stessa città (tipo 1) |
| `periodo` | sì | `{"data": "10/05/2027", "giorni_prima_dopo": 7}`, `{"mese": "05/2027"}` oppure `{"dal": "01/05/2027", "al": "20/05/2027"}` |
| `durata` | sì | `{"min": 10, "max": 14}`. Con `weekend`: giorni di calendario da 1 a 4, facoltativa (default 1-4) |
| `weekend` | no | `true` = modalità weekend: solo viaggi che toccano sabato o domenica |
| `max_scali` | no | `null` o assente = qualsiasi, `0` = solo diretti, `1`, `2` |
| `top` | no | numero di risultati, default 5 |
| `frequenza_minuti` | no | minuti tra un controllo e l'altro, default 30 |
| `valuta` | no | codice di 3 lettere, default `"EUR"` |
| `telegram` | no | `false` = ricerca privata: nessun messaggio al bot e ai suoi iscritti. Default `true` |
| `avvisa_sotto` | no | prezzo obiettivo (intero, nella valuta della ricerca): avvisi solo sotto questa cifra. Assente o `null` = a ogni nuovo minimo |

Nel file le città si scrivono con i codici aeroporto; `nome` serve solo per i messaggi.
Se il file non è valido il tool dice cosa non va (es. `manca il campo 'periodo'`).
L'esempio ha una data fissa: aggiornala prima di usarlo.

## Notifiche Telegram

### Configurazione (una volta)

```bash
.venv/bin/python tracker.py --setup-telegram
```

1. Su Telegram apri @BotFather, invia `/newbot` e copia il token.
2. Incolla il token quando il tool lo chiede.
3. Apri il tuo bot e premi **Avvia**.

Chiunque prema **Avvia** (`/start`) sul tuo bot riceve le notifiche di tutti i tracker
attivi; con `/stop` smette. Chi trova il nome del bot può iscriversi e vedere tratte,
date e prezzi: condividilo solo con chi deve vederli. Per togliere una chat a mano,
cancella il suo numero da `chat_ids` in `telegram.json`.

### Cosa ricevi

| Quando | Messaggio |
|---|---|
| Primo controllo dopo l'avvio | 🚀 Tracker avviato, con la top completa. Con un prezzo obiettivo non ancora raggiunto, una riga sola: `🚀 Tracker avviato · Napoli -> Milano` e `🎯 Obiettivo 30 EUR · ora 33 EUR (mancano 3 EUR)` |
| Nuovo prezzo minimo | ✈️ Nuovo prezzo minimo, con la top completa |
| Nuovo minimo sotto il prezzo obiettivo (se l'hai impostato) | 🎯 Sotto il tuo obiettivo, con la top completa. Sopra l'obiettivo non arriva niente |
| Google limita le richieste | ⚠️ Rallento, con il nuovo ritmo |
| Google torna normale | ✅ Accelero |
| Ctrl+C | ⏹ Tracker fermato da te |
| Errore imprevisto | ❌ Tracker fermato per un errore |

**Ricerca privata.** Alla domanda sugli avvisi rispondi `3` (nel file JSON
`"telegram": false`): quella ricerca non manda nessun messaggio, né di avvio né di
arresto, al bot e a chi è iscritto. Le altre ricerche continuano a usare Telegram
normalmente; la notifica di sistema su macOS resta.

**Prezzo obiettivo.** Se l'hai impostato, il bot scrive solo quando un nuovo minimo è
uguale o sotto l'obiettivo (🎯), una volta per ogni ribasso. All'avvio, se l'obiettivo non è
ancora raggiunto, arriva solo una riga con l'obiettivo e quanto manca, senza la top. Nel terminale, in `top.txt` e
nei messaggi c'è la riga `🎯 Obiettivo 450 EUR · ora 489 EUR (mancano 39 EUR)`. Cambiare
l'obiettivo non cambia la cartella dei dati: rilanci e il tool riprende i prezzi trovati.

Un controllo senza un prezzo migliore non manda niente: il bot scrive solo quando c'è una
novità. Il bot non può dirti se il tracker sta girando: è un processo nel terminale del
tuo computer, non un servizio sempre attivo, e se il computer va in stop o chiudi la
finestra si ferma senza poter avvisare. Per controllare guarda il terminale (conto alla
rovescia fino al prossimo controllo) o l'ora di `top.txt`, che si aggiorna a ogni
controllo.

Ogni messaggio riporta i parametri della ricerca, il paese da cui partono le ricerche
(mai l'IP) e l'orario del prossimo controllo.

```
✈️ Nuovo prezzo minimo

🛫 Roma (FCO) → New York (JFK, EWR) / Boston (BOS)
🛬 New York (JFK, EWR) / Boston (BOS) → Roma (FCO)
📅 Partenza dal 03/05/2027 al 17/05/2027
🧳 Durata min: 10 gg - max: 14 giorni · max 1 scalo · controllo ogni 60 min · EUR
🌍 Ricerche da 🇮🇹 IT

🔎 Scansione in corso: 100/143 ricerche verificate, 143/143 stimate
✅ Le 15 combinazioni più economiche del calendario sono già verificate
⏳ Le altre 43 ai prossimi controlli (max 100 per controllo, per non farsi bloccare da Google)

🏆 Top 5

1. 489 EUR · A/R New York
   📆 06/05 → 18/05 (12 gg)
   🏷 su Gotogate (512 EUR in lista, andata 06:00, ritorno 18:40)
   🛩 TAP Air Portugal [FCO-LIS LIS-JFK]
   📊 BASSO: -29% sul tipico 690 EUR, fascia 560-950 EUR, minimo ultimi 60 gg 512 EUR
   🔗 Apri su Google Flights
...

⏱ Prossimo controllo alle 23:40
```

## Farlo girare per giorni

- **Più ricerche insieme:** un terminale per ricerca. Ogni ricerca ha la sua cartella in
  `data/`; due istanze con parametri identici non possono girare insieme. Con 2 o 3
  istanze sei tranquillo, di più fanno arrivare prima i limiti di Google.
- **Riavvii:** rilanciando con gli stessi parametri il tool riprende i prezzi già
  trovati. Il primo messaggio dopo l'avvio contiene comunque la top completa.
- **Computer sveglio:** se il computer va in stop i controlli si fermano. Su macOS puoi
  lanciarlo con `caffeinate`, che tiene sveglio il Mac finché il tool gira:
  ```bash
  caffeinate -i .venv/bin/python tracker.py ricerche/esempio.json
  ```
  Su Windows imposta la sospensione su "Mai" mentre il tool gira (Impostazioni →
  Sistema → Alimentazione); su Linux usa ad esempio `systemd-inhibit`.
- **Valuta e paese:** la stessa ricerca in un'altra valuta ha una cartella separata. Se
  usi una VPN, ricorda che Google adatta i prezzi al paese dell'IP: lo vedi nella riga 🌍.

## Come funziona

Ogni controllo ha tre fasi:

1. **Calendario (stima veloce).** Il grafico prezzi di Google dà, con una richiesta, il
   prezzo indicativo di tutte le date di partenza per una coppia di aeroporti. Copre
   tutto in meno di un minuto, ma non vede tutte le tariffe.
2. **Verifica (prezzo vero).** Ricerca completa sulla singola combinazione. Ogni
   controllo verifica la top attuale, le 15 combinazioni più economiche secondo il
   calendario e, a rotazione, tutte le altre (prima le mai verificate, poi le più
   vecchie). Così anche una stima sbagliata prima o poi viene corretta.
3. **Venditori.** Per gli A/R in top apre le pagine di prenotazione degli itinerari più
   economici e tiene il venditore più conveniente, agenzie comprese. Per i biglietti di
   sola andata Google non dà i venditori: si usa il prezzo in lista.

Il calendario guarda anche 7 giorni prima e dopo il periodo: se lì c'è una data più
economica, il tool la verifica (1 o 2 ricerche) e la segnala con 💡.

All'inizio di ogni controllo il tool chiede a ipinfo.io (o api.country.is) IP e paese
di uscita: una richiesta per controllo.

### Richieste a Google e come non farsi bloccare

Google non pubblica limiti per Google Flights. Il tool usa un **limitatore adattivo**:
parte con un ritmo prudente, rallenta da solo quando Google protesta e riaccelera quando
torna tutto normale.

**Cosa fa a ogni controllo**
- al massimo 100 ricerche complete, con 3 secondi di pausa tra una e l'altra (circa 6
  secondi a ricerca, cioè una decina di minuti per controllo);
- mai più ricerche di quante ne stanno nell'intervallo: con una frequenza di 5 minuti,
  per esempio, ne fa al massimo 50;
- circa una richiesta al calendario per coppia di aeroporti e durata, con 1 secondo di
  pausa;
- per gli A/R in top, qualche pagina di prenotazione per i prezzi delle agenzie.

**Quando rallenta.** Con un HTTP 429 (troppe richieste), un captcha di Google o 5 errori
di fila, il tool interrompe il controllo e sale di un livello. A ogni livello dimezza le
ricerche, raddoppia le pause e raddoppia l'intervallo tra i controlli. Dopo un controllo
senza problemi scende di un livello. Ogni cambio arriva anche su Telegram.

| Livello | Ricerche per controllo | Pausa | Intervallo (con 30 min) |
|---|---|---|---|
| 0 | 100 | 3 s | 30 min |
| 1 | 50 | 6 s | 60 min |
| 2 | 25 | 12 s | 120 min |
| 3 | 12 | 24 s | 240 min |

L'avviso `excessive load generating behavior` in `errori_rete.log` **non** è un blocco:
Google chiude una connessione dopo molte richieste ravvicinate e il tool ne apre
un'altra. Il blocco vero è il 429 o il captcha.

**Parametri consigliati.** Il numero che conta è il totale di ricerche complete all'ora,
sommando tutte le istanze aperte sullo stesso IP:

```
ricerche all'ora ≈ istanze × min(100, ricerche della ricerca) × 60 / frequenza in minuti
```

| Configurazione | Ricerche complete all'ora | Giudizio |
|---|---|---|
| 1 istanza, frequenza 60 | fino a 100 | tranquillo |
| 1 istanza, frequenza 30 | fino a 200 | tranquillo |
| 2 istanze, frequenza 60 | fino a 200 | tranquillo |
| 3 istanze, frequenza 60 | fino a 300 | al limite |
| 3 istanze, frequenza 30 | fino a 600 | sconsigliato |

Indicazioni pratiche:
- **frequenza 30-60 minuti**; 60 se la ricerca ha più di 100 combinazioni (tanto la
  copertura completa richiede comunque più controlli);
- **al massimo 2 o 3 istanze** insieme sullo stesso IP;
- restringi la ricerca invece di moltiplicare le istanze: meno giorni, durate più
  strette o una città sola danno meno ricerche;
- **non abbassare** `PAUSA_SECONDI` sotto 3 e non alzare `RICERCHE_MAX_PER_GIRO` sopra 100
  (costanti in cima a `ricerca.py`);
- se arriva "⚠️ Rallento", lascia lavorare il limitatore; se succede spesso, alza la
  frequenza o chiudi un'istanza.

Riferimento misurato: in una giornata di prova, con fino a 3 istanze, il tool ha fatto
circa 1300-1500 richieste (fino a circa 200 ricerche complete all'ora) senza nessun 429
né captcha. È una misura su un IP, non un limite garantito: Google può cambiare soglie
in qualsiasi momento.

Le altre costanti sono `VERIFICA_DA_STIMA` (stime verificate a
ogni controllo, 15), `ITINERARI_VENDITORI` (pagine di prenotazione per combinazione, 4, in `google_flights.py`),
`PAUSA_CALENDARIO` (1 s) e `GIORNI_FUORI_PERIODO` (7).

## Problemi comuni

**pip non trova `fast-flights==3.1.0` ("from versions: … 2.2").** Il Python con cui hai
creato `.venv` è troppo vecchio: le versioni 3.x di fast-flights richiedono Python 3.10 e il
tool 3.11. Controlla con `python3 --version` (su Windows `py -0` elenca le versioni
installate), installa Python 3.11 o più recente, cancella la cartella `.venv` e ricreala,
per esempio `python3.13 -m venv .venv` (su Windows `py -3.13 -m venv .venv`).

**"🛠 Google sembra aver cambiato formato".** Il tool non riesce più a leggere le risposte
di Google: succede quando Google cambia le sue pagine. Aggiorna con `git pull`; se
l'avviso resta, segnala il problema su GitHub. In questo caso il tool non rallenta e
riprova a ogni controllo; quando la lettura torna regolare arriva un "✅".

**"Nessun volo in vendita".** Controlla città e paese scelti (es. `Napoli, Italia` e non
`Napoli, Stati Uniti`) e gli aeroporti: un aeroporto piccolo può non avere la rotta.
Prova un aeroporto vicino più grande, oppure un altro periodo.

**Su Telegram non arriva niente.** Di solito vuol dire che il prezzo non è sceso: il bot
scrive solo con un nuovo minimo. Per esserne sicuro controlla che il terminale sia
aperto, che il computer non sia in stop e l'ora di `top.txt`.

**Ho premuto Avvia sul bot e non succede nulla.** Il bot risponde solo mentre un tracker
è attivo: avvialo e l'iscrizione arriva entro 10 secondi.

**"verificate 100/143 (scansione in corso)".** Normale: al massimo 100 ricerche complete
per controllo. Le più economiche sono già verificate.

**Un prezzo visto su Google Flights non compare.** Controlla che la partenza sia nel
periodo e gli scali nel massimo. Le offerte delle agenzie cambiano anche da utente a
utente, e da paese a paese.

**Primo avvio senza internet.** L'elenco di città e aeroporti si scarica al primo avvio
(poi resta una copia locale per 30 giorni): senza rete il tool si ferma con un messaggio.

**`errori_rete.log`.** Messaggi interni della libreria di rete, es. `excessive load
generating behavior`: Google chiude una connessione e il tool ne apre un'altra. Non è
un blocco.

## Versioni

Le novità di ogni versione sono in [CHANGELOG.md](CHANGELOG.md) (in inglese) e nella pagina
[Releases](https://github.com/Alessio0327/flight-tracker/releases). La versione installata
si vede all'avvio o con `.venv/bin/python tracker.py --version`. Per aggiornare: `git pull`.

## Sviluppo e test

I test controllano la logica senza fare richieste a Google né a Telegram, e non usano
date scritte a mano (partono dal giorno in cui girano).

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

A ogni push GitHub Actions li esegue su Linux, Windows e macOS, con Python 3.11 e 3.13: il risultato è nel badge in
cima e nella scheda **Actions**.

| File | Contenuto |
|---|---|
| `tracker.py` | avvio e ciclo dei controlli |
| `parametri.py` | domande all'avvio, controllo del periodo, file JSON |
| `ricerca.py` | date, combinazioni, limiti di Google, proposte, ritmo |
| `google_flights.py` | richieste a Google Flights e IP di uscita |
| `interfaccia.py` | testi della top, messaggi Telegram, barra di avanzamento |
| `lingua.py` | testi in italiano e inglese |
| `luoghi.py` | ricerca città e aeroporti (dataset Travelpayouts, cache 30 giorni) |
| `telegram_bot.py` | iscrizioni e messaggi Telegram |
| `blocco.py` | blocco dei file, uguale su macOS, Linux e Windows |
| `ricerche/esempio.json` | esempio di parametri |
| `CHANGELOG.md` | novità di ogni versione |
| `tests/`, `.github/workflows/test.yml` | test e loro esecuzione su GitHub |
| `telegram.json` | token del bot e chat iscritte (escluso da git) |
| `data/<ricerca>/` | `top.txt`, `storico.csv` (ogni prezzo trovato, con il paese), `prezzi.json`, `parametri.json`, `errori_rete.log` |

`storico.csv` ha le colonne `controllato, andata, ritorno, prezzo, compagnie, voli, paese`.
Per le sole andate `ritorno` è `out|<città>` o `ret|<città>`; per i prezzi delle agenzie
`compagnie` è il nome del venditore e `voli` gli orari. Oltre 5 MB lo storico diventa
`storico.1.csv`, oltre 1 MB il log diventa `errori_rete.log.1`: si tiene una sola copia
precedente. All'avvio il tool segnala le ricerche in `data/` con il periodo già passato,
senza cancellarle.

## Limiti

- Usa API interne di Google Flights, non documentate e non ufficiali (tramite
  [fast-flights](https://github.com/AWeirdDev/fast-flights),
  [fli](https://github.com/punitarani/fli) e chiamate dirette). Se Google cambia
  formato, il tool può smettere di funzionare.
- Google cerca voli fino a oggi + 330 giorni (conta il ritorno); il calendario prezzi
  fino a oggi + 305. Le combinazioni oltre il limite vengono cercate quando diventano
  cercabili.
- Niente biglietto unico multi-città; niente prezzi dei venditori per la sola andata.
- Prezzi per 1 adulto, classe economy. La valuta deve essere supportata da Google
  Flights: il tool controlla solo che il codice abbia 3 lettere.

Progetto personale, per uso privato e a basso volume. Le condizioni d'uso di Google
vietano l'accesso automatico ai suoi servizi: usalo a tuo rischio, senza controllare
troppo spesso (almeno 30 minuti tra un controllo e l'altro) e con poche istanze insieme.

## Licenza

[MIT](LICENSE)
