# flight-tracker

[![test](https://github.com/Alessio0327/flight-tracker/actions/workflows/test.yml/badge.svg)](https://github.com/Alessio0327/flight-tracker/actions/workflows/test.yml)

🇬🇧 **English** · 🇮🇹 [Italiano](README.it.md)

A terminal tool that monitors flight prices on Google Flights.

You give it the cities, the departure period and the trip length. Every N minutes
the tool tries every combination of dates, shows the best ones and alerts you on
Telegram (and with a macOS notification) when the price drops.

The tool speaks Italian or English: choose at startup. The examples below show the
Italian version, with explanations in English.

- City names instead of IATA codes: type "Roma" and pick Fiumicino, Ciampino or both.
- Up to 2 cities per side (e.g. arrival in Tokyo or Osaka), with only the airports you want.
- Return from the same city or from a different one (e.g. Rome→Tokyo, then Osaka→Rome).
- Compares a round trip on one ticket with two one-way tickets.
- Period: a month, a date ± N days, or a date range.
- Suggests departures up to 7 days outside the period when they are cheaper.
- Price rating (low / typical / high) against Google's typical range.
- Agency prices (lastminute, Gotogate, ...), often lower than the listed price.
- Parameters from interactive questions or from a JSON file.
- Italian or English: questions, terminal and Telegram messages.
- Telegram notifications for anyone who presses Start on the bot.
- Several searches in parallel, one per terminal; data is kept between runs.
- Slows down by itself when Google limits requests.

## Contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Trip types](#trip-types)
- [Entering the parameters](#entering-the-parameters)
- [What the terminal shows](#what-the-terminal-shows)
- [Telegram notifications](#telegram-notifications)
- [Several searches and resuming data](#several-searches-and-resuming-data)
- [How it works](#how-it-works)
- [How many requests to Google](#how-many-requests-to-google)
- [Troubleshooting](#troubleshooting)
- [Development and tests](#development-and-tests)
- [Limitations](#limitations)

## Installation

Requires Python 3.11 or later.

```bash
git clone https://github.com/Alessio0327/flight-tracker.git
cd flight-tracker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Quick start

1. (Optional) Connect the Telegram bot, once:
   ```bash
   .venv/bin/python tracker.py --setup-telegram
   ```
2. Start the tracker (the first question is the language, `1` Italian or `2` English):
   ```bash
   .venv/bin/python tracker.py
   ```
3. Answer the questions, or choose `2` and give a JSON file
   (e.g. `ricerche/esempio.json`).
4. Leave the terminal open. The tool works on its own until you press Ctrl+C.

## Trip types

The first interactive question is the trip type
(`Tipo di viaggio: [1] andata e ritorno sulla stessa citta'  [2] ritorno da un'altra citta'`).

### [1] Round trip to the same city

The return leaves from the arrival city and goes back to the departure city.
Example: Rome → Osaka, return Osaka → Rome.

With two arrival cities (e.g. Tokyo and Osaka) the tool searches both, but never
mixes them: outbound and return are always on the same city.

For each date combination the tool searches:
- a **round trip on a single ticket** (usually the cheapest on long-haul flights);
- **two one-way tickets**, for comparison.

### [2] Return from a different city

You choose the outbound cities and the return cities separately (1 or 2 per side).
Example: outbound Rome → Tokyo or Osaka, return Tokyo or Osaka → Rome.

The tool tries every city combination:

| Variant | How it is searched |
|---|---|
| Outbound Tokyo, return from Tokyo | round trip on one ticket + two one-way tickets |
| Outbound Osaka, return from Osaka | round trip on one ticket + two one-way tickets |
| Outbound Tokyo, return from Osaka | two one-way tickets |
| Outbound Osaka, return from Tokyo | two one-way tickets |

A single-ticket round trip is possible only when the return leaves from the arrival
city and goes back to the departure city. For mixed variants the tool combines two
one-way tickets, because the single "multi-city" ticket is not available in the APIs
used.

At the end of each check you get a comparison of the variants, with the best one marked.

### Which one to choose

| You want... | Type | Example |
|---|---|---|
| The best price to one city | 1 | Rome → Osaka |
| To know whether Tokyo or Osaka is cheaper | 1, two arrival cities | Rome → Tokyo, Osaka |
| A trip entering and leaving through different cities | 2 | Rome → Tokyo, return Osaka → Rome |
| Every combination of two cities | 2, two cities per side | as above, with Tokyo and Osaka on both sides |

More cities and more days mean more searches: see
[How many requests to Google](#how-many-requests-to-google).

## Entering the parameters

At startup the tool asks for the language (questions, terminal, `top.txt` and
Telegram), then whether to answer questions (`1`) or read a JSON file (`2`):

```
Lingua / Language: [1] Italiano  [2] English (Invio/Enter = 1): 2
Parameters: [1] answer the questions  [2] read a JSON file (Enter = 1):
```

With `2` (English) every question and message below is in English; the examples
show the Italian version:

```
Parametri: [1] rispondo alle domande  [2] leggo da un file JSON (Invio = 1):
```

### With the questions

Example with a return from a different city:

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

The questions, in order:

| Question | Meaning |
|---|---|
| `Date cercabili: ...` | first and last date Google can search (today + 330 days) |
| `Tipo di viaggio` | trip type, see above |
| `ANDATA` / `RITORNO` | outbound / return cities. For the return, Enter reuses the outbound cities reversed |
| `Quante citta'` | how many cities on that side (1 or 2) |
| `Aeroporti` | which airports of the city (Enter = all) |
| `Periodo di partenza` | departure period: `1` = a month, `2` = around a date |
| `Quanti giorni prima/dopo` | days before and after that date |
| `Durata minima/massima` | minimum / maximum trip length in days |
| `Massimo scali` | maximum stops per leg |
| `Quanti migliori risultati` | how many results to show |
| `Frequenza aggiornamento` | minutes between checks |

Before asking for the trip length, the tool checks Google's calendar for flights on
sale in the period. If there are none, it immediately asks for another period or
city, without making you answer the remaining questions.

Accepted answers:

| Question | Examples |
|---|---|
| City | `roma`, `Tokyo`, airport code `FCO`, city code `ROM` |
| Airports | Enter = all, or comma-separated numbers: `1,3` |
| Month | `10/2027`, `10/27`, `2027-10` |
| Date | `15/10/2027`, `15/10/27`, `2027-10-15` (day/month/year) |
| Days before/after | `10` = 10 days before and 10 after the date |
| Stops | `0` = direct only, `1`, `2`, Enter = any |

Mind the period: with `20/03/27` and `10`, departures go from 10/03 to 30/03.
A flight leaving on 03/03 is outside (at most it appears as a 💡 suggestion).

### From a JSON file

Answer `2` and type the file path. You can also drag the file into the Terminal:
quotes and escaped spaces are removed automatically. The tool prints a summary and
starts without further questions:

```
Parametri: [1] rispondo alle domande  [2] leggo da un file JSON (Invio = 1): 2
Percorso del file JSON: ricerche/esempio.json
  Andata Roma (FCO) -> Tokyo (HND, NRT) / Osaka (KIX, ITM)
  Ritorno Tokyo (HND, NRT) / Osaka (KIX, ITM) -> Roma (FCO)
  Partenza dal 28/02/2027 al 20/03/2027, durata 14-21 giorni, max 1 scalo, top 5, ogni 60 min
```

Example file (`ricerche/esempio.json`):

```json
{
  "lingua": "it",
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

| Field | Required | Values |
|---|---|---|
| `lingua` | no | `"it"` or `"en"`, default `"it"`. Used on direct start; when you load the file from the questions, it is updated with the language chosen at startup |
| `andata.da`, `andata.a` | yes | outbound from / to: 1 or 2 cities, each `{"nome": "...", "aeroporti": ["..."]}` |
| `ritorno.da`, `ritorno.a` | no | return from / to, same format. Without `ritorno` the trip is type 1 (same city) |
| `periodo` | yes | `{"data": "10/03/2027", "giorni_prima_dopo": 10}`, `{"mese": "03/2027"}` or `{"dal": "01/03/2027", "al": "20/03/2027"}` |
| `durata` | yes | trip length: `{"min": 14, "max": 21}` |
| `max_scali` | no | max stops: `null` or missing = any, `0` = direct only, `1`, `2` |
| `top` | no | number of results, default 5 |
| `frequenza_minuti` | no | minutes between checks, default 30 |

In the file, cities are written with airport codes: name lookup works only in the
questions. `nome` is used only in messages. If the file is not valid, the tool says
what is wrong (e.g. `manca il campo 'periodo'` = missing field) and asks for the
path again.

`ricerche/esempio.json` has a fixed date: update it before use, otherwise after that
date the tool answers "periodo vuoto o gia' passato" (empty or past period).

### Direct start from a file

```bash
.venv/bin/python tracker.py ricerche/esempio.json
```

No questions: language and parameters come from the file. If the file is not valid,
the tool stops and says why.

Language rule:
- **direct start:** the file's `lingua` field applies (Italian if missing);
- **file loaded from the questions:** the language chosen at startup applies, and the
  tool writes it into the file's `lingua` field, so file and tool stay consistent on
  the next direct start.

One file per search makes it easy to restart the same search, or several searches in
different terminals, without answering the questions every time.

## What the terminal shows

During a check, a one-line progress bar for each phase:

```
✓ Calendario [████████████████████████] 40/40 100% · in 44 s · 434 prezzi stimati

Verifica precisa: 100 ricerche (top attuale 5, stime migliori 15, a rotazione 80)
★ nuovo minimo: 672 EUR A/R Osaka, 2027-03-01 -> 2027-03-22 (21 gg)
✓ Verifica   [████████████████████████] 100/100 100% · in 7 min 00 s · minimo 672 EUR

Prezzi dei venditori (agenzie comprese) per 5 A/R in top
★ nuovo minimo: 656 EUR su lastminute.com  2027-03-01 -> 2027-03-22  (andata 08:55, ritorno 17:55)
✓ Venditori  [████████████████████████] 5/5 100% · in 6 min 02 s · minimo 656 EUR
```

At the end, the top results and a countdown to the next check:

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

How to read it:

- **Price.** "656 EUR su lastminute.com (674 EUR in lista)": the lowest price found
  among sellers, and in brackets the price shown in Google's list.
- **Rating.** Compared with Google's typical range for the route and the lowest price
  of the last 60 days. "BASSO" (low) close to the 60-day minimum is a good sign to book.
- **Coverage.** "Stimate" (estimated) = indicative price from the calendar.
  "Verificate" (verified) = real price from a full search. The top list uses only
  verified prices.
- **Variant comparison** (`Confronto varianti`). The best price for each city
  combination. "(stima)" means that variant has not been verified yet.
- **💡 Suggestion.** A departure up to 7 days before or after the period that costs
  less than the top. It never enters the top list.
- **Two tickets.** A proposal with two one-way tickets shows both flights with price
  and link, and a warning that they are not linked: if one flight changes or is
  cancelled, the other is not protected.

The top list is also saved in `data/<folder>/top.txt`.

## Telegram notifications

### Setup (once)

```bash
.venv/bin/python tracker.py --setup-telegram
```

1. On Telegram open @BotFather, send `/newbot` and copy the token.
2. Paste the token when the tool asks for it.
3. Open your bot and press **Start**: your chat is subscribed.

### Who gets the notifications

Anyone who opens the bot and presses **Start** (`/start`) receives the notifications of
every running tracker, and the bot answers "✅ Iscritto alle notifiche voli"
(subscribed). With `/stop` they stop.

- While a tracker is running, the tool checks for new messages every 10 seconds.
- If no tracker is running, the subscription happens at the next start (Telegram
  keeps messages for 24 hours).
- Anyone who blocks the bot is removed automatically.
- Anyone who finds the bot's name can subscribe and see routes, dates and prices:
  share it only with people who should see them.

The configuration is in `telegram.json` (permissions 600, excluded from git). To
remove a chat by hand, delete its number from `chat_ids`:

```json
{"token": "123456789:AA...", "chat_ids": [123456789, 987654321], "offset": 0}
```

### Messages

| When | Message |
|---|---|
| First check after start | 🚀 Tracker avviato (tracker started), with the full top list |
| New lowest price | ✈️ Nuovo prezzo minimo (new lowest price), with the full top list |
| Check finished, no new lowest price | ✅ Check ok, nessun prezzo migliore trovato, with the current lowest price |
| Check interrupted by Google | ⚠️ Check interrotto, plus ⚠️ Rallento (slowing down) with the new pace |
| Google answers normally again | ✅ Accelero (speeding up) |
| Ctrl+C | ⏹ Tracker fermato da te (stopped by you) |
| Unexpected error | ❌ Tracker fermato per un errore (stopped by an error), with the error message |

Every check message gives the time of the next check. If nothing arrives by then, the
tracker has stopped (or the Mac went to sleep).

Example of a message with the top list:

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

## Several searches and resuming data

- Open one terminal per search and run `tracker.py` in each.
- Each set of parameters has its own folder in `data/`.
- Restarting with the same parameters (questions or file) resumes the prices already
  found: coverage does not start from zero and a known price is not reported as a
  "new lowest price".
- Two instances with identical parameters cannot run at the same time.
- All instances share the same IP: 2 or 3 at once are fine, more make Google's limits
  arrive sooner.

A useful setup: one instance over the whole period you care about, and a small one
over the few days where you saw a good price.

## How it works

Each check has three phases.

1. **Calendar (quick estimate).** Google's price graph returns, in one request, the
   indicative price of every departure date for a pair of airports: for a round trip
   of fixed length, or for a one-way flight. It covers everything in under a minute,
   but does not see every fare.
2. **Verification (real price).** A full search on a single combination, as on Google
   Flights: price, airlines, stops, rating, link. Each check verifies, in this order:
   - the current top list;
   - the 15 cheapest combinations according to the calendar;
   - in rotation, all the others, first the never-verified ones and then the oldest.
     At least a quarter of each check is always kept for the rotation.

   This way a wrong estimate is eventually corrected, and every price is refreshed
   periodically. With more searches than the per-check maximum (100), the first full
   coverage takes several checks; after that the tool keeps refreshing the oldest
   prices.
3. **Sellers.** For round trips in the top list, the tool opens the booking pages of
   the cheapest itineraries and keeps the cheapest seller, agencies included. Google
   gives no sellers for one-way tickets: the listed price is used.

**Dates outside the period.** The calendar also looks 7 days before and after the
period, with the same trip lengths. One calendar request covers up to 61 days, so this
usually costs no extra requests. If the cheapest estimate outside the period is lower
than the best inside it, the tool verifies it (1 or 2 searches) and, if the real price
beats the top list, shows it as a 💡 suggestion.

## How many requests to Google

Google does not publish limits for Google Flights. The tool starts at a cautious pace
and slows down by itself.

- Number of searches: one per round-trip date pair, plus one per day and city for
  one-way flights. Example: Rome → Tokyo/Osaka, 21 departure days, trip length 14-21
  days = 266 searches, covered in 3 checks.
- With HTTP 429, a captcha or 5 errors in a row, the check stops and the tool moves up
  one level. After a clean check it moves down one level.

| Level | Searches per check | Pause | Interval (with 30 min) |
|---|---|---|---|
| 0 | 100 | 3 s | 30 min |
| 1 | 50 | 6 s | 60 min |
| 2 | 25 | 12 s | 120 min |
| 3 | 12 | 24 s | 240 min |

Constants at the top of `tracker.py`:

| Constant | Default | Meaning |
|---|---|---|
| `RICERCHE_MAX_PER_GIRO` | 100 | full searches per check at normal pace |
| `PAUSA_SECONDI` | 3 | pause between two full searches |
| `VERIFICA_DA_STIMA` | 15 | cheapest calendar estimates verified at each check |
| `ITINERARI_VENDITORI` | 4 | itineraries whose booking page is opened |
| `PAUSA_CALENDARIO` | 1 | pause between two calendar requests |
| `GIORNI_FUORI_PERIODO` | 7 | days before/after the period searched for cheaper dates |

## Troubleshooting

**No Telegram messages for hours.** Check that the terminal is open and the Mac is not
asleep. Every check sends at least "✅ Check ok": if it does not arrive at the stated
time, the tracker is not running.

**I pressed Start on the bot and nothing happens.** The bot answers only while a
tracker is running. Start a tracker: the subscription arrives within 10 seconds.

**"verificate 100/266 (scansione in corso)".** This is normal: each check makes at most
100 full searches. The cheapest combinations are verified first, the others in the
next checks.

**After a restart it says "nessun prezzo migliore" (no better price).** The tool
resumed the prices already found with the same parameters. The first message after
start still contains the full top list.

**A price I see on Google Flights does not show up.** Check that the departure date is
inside the period and that the stops are within the maximum. Agency offers can also
differ from user to user.

**`errori_rete.log` in the data folder.** It holds the network library's internal
messages (e.g. `excessive load generating behavior`): Google closes a connection and
the tool opens another one. It is not a block.

## Development and tests

The tests check the tool's logic without any request to Google or Telegram: dates and
combinations, JSON files, proposals and comparison, message texts, bot subscriptions
and a full check with fake answers.

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

No test uses hand-written dates: dates start from the day the tests run, so they stay
valid over the years. The code reads the current day only through `oggi()` in
`tracker.py`, which the tests freeze for the whole run.

On every push GitHub Actions runs the tests on Python 3.11 and 3.13
(`.github/workflows/test.yml`). The result is in the badge at the top of this page and
in the repository's **Actions** tab.

## Files

| Path | Content |
|---|---|
| `tracker.py` | main program |
| `lingua.py` | Italian and English texts |
| `luoghi.py` | city and airport lookup (Travelpayouts dataset, 30-day cache) |
| `telegram_bot.py` | Telegram setup, subscriptions and messages |
| `ricerche/esempio.json` | example parameter file |
| `tests/` | automated tests |
| `.github/workflows/test.yml` | test run on GitHub |
| `telegram.json` | bot token and subscribed chats (excluded from git) |
| `data/<parameters>/top.txt` | latest top list |
| `data/<parameters>/storico.csv` | every price found |
| `data/<parameters>/prezzi.json` | current state of the searches |
| `data/<parameters>/parametri.json` | search parameters |
| `data/<parameters>/errori_rete.log` | network library's internal messages |

## Limitations

- Uses internal, undocumented and unofficial Google Flights APIs (through
  [fast-flights](https://github.com/AWeirdDev/fast-flights),
  [fli](https://github.com/punitarani/fli) and direct calls). If Google changes the
  format, the tool may stop working.
- Google Flights searches flights only up to today + 330 days (the return counts) and
  the price calendar up to today + 305. The tool shows the limit at startup.
  Combinations beyond the limit are searched as they become searchable.
- The single "multi-city" ticket (outbound to one city, return from another) is not
  supported: for that variant the tool combines two one-way tickets.
- One-way tickets have no seller prices.
- Prices in EUR, 1 adult, economy class.
- The code and the JSON field names are in Italian.

Personal project, for private and low-volume use. Google's terms of service forbid
automated access to its services: use it at your own risk, without lowering the
frequency too much and without multiplying instances.

## License

[MIT](LICENSE)
