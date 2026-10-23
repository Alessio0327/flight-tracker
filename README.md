# flight-tracker

[![test](https://github.com/Alessio0327/flight-tracker/actions/workflows/test.yml/badge.svg)](https://github.com/Alessio0327/flight-tracker/actions/workflows/test.yml)

🇬🇧 **English** · 🇮🇹 [Italiano](README.it.md)

**Finds the cheapest flight among hundreds of date combinations, and tells you on
Telegram when the price drops.**

flight-tracker is a terminal program that searches Google Flights for you. You tell it
where you want to go, in which period and for how many days. It tries every possible
date combination, shows you the cheapest ones and keeps checking them every hour (or as
often as you choose) until you stop it.

> **It is not an online service.** It is a program for personal use that lives in your
> computer's terminal: it works only while the terminal is open and the computer is on
> and awake. When you close the terminal or the computer goes to sleep, checks stop.

## Why

Example: you want to go to Japan in early March, for 2 or 3 weeks. Landing in Tokyo or
Osaka are both fine, and maybe you would fly home from the other city.

On Google Flights you would try one pair of dates at a time: departures from 23/02 to
09/03 and trips of 14 to 21 days make 120 combinations for round trips alone, and almost
200 once you add one-way flights between the two cities. On top of that, prices change
every day, and agencies (lastminute, Gotogate, ...) are often cheaper than the price in
Google's list.

flight-tracker does those checks for you:

```
1. 656 EUR on lastminute.com (674 EUR listed, outbound 08:55, return 17:55)  Round trip Osaka  2027-03-01 -> 2027-03-16 (15 days)  Qatar Airways  [FCO-DOH DOH-KIX]
   Price LOW: -32% vs typical 986 EUR, range 870-1400 EUR, lowest in the last 60 days 674 EUR
```

Here it found a 656 EUR flight from an agency, against 674 EUR in Google's list and a
typical 986 EUR for that route.

## What it does

- **Tries every date:** departure period (a month, a date ± N days, or a range) for every
  trip length between a minimum and a maximum.
- **Cities, not codes:** type "Rome" and pick Fiumicino, Ciampino or both. Up to 2 cities
  per side (e.g. Tokyo or Osaka).
- **Return from a different city:** e.g. Rome → Tokyo, then Osaka → Rome.
- **Round trip vs two tickets:** compares a round trip on one ticket with two one-way
  tickets, and tells you which variant is cheaper.
- **Agency prices:** for the best results it opens the booking pages and keeps the
  cheapest seller.
- **Price rating:** low, typical or high, against Google's typical range and the lowest
  price of the last 60 days.
- **Nearby dates:** if leaving up to 7 days before or after your period is cheaper, it
  tells you separately.
- **Telegram notifications:** when the price drops, to anyone who presses Start on your bot.
- **Search country:** shows the IP and country your searches leave from (e.g. through a
  VPN), because Google adapts prices to the country.
- **Italian or English, any currency** (EUR, USD, GBP, ...).
- **Runs on its own for days:** resumes its data after a restart and slows down when
  Google limits requests.

## Installation

Requires Python 3.11 or later.

```bash
git clone https://github.com/Alessio0327/flight-tracker.git
cd flight-tracker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## First run

```bash
.venv/bin/python tracker.py
```

The tool asks a few questions. Here is a full session for the Japan example
(Enter accepts the proposed value):

```
Lingua / Language: [1] Italiano  [2] English (Invio/Enter = 1): 2
Parameters: [1] answer the questions  [2] read a JSON file (Enter = 1): 1
Searchable dates: departure from tomorrow, last flight by 18/09/2027 (Google Flights limit, today + 330 days).

Trip type: [1] round trip to the same city  [2] return from a different city: 2
OUTBOUND
How many departure cities? [1/2] (Enter = 1):
  Departure city: rome
  [1] FCO Fiumicino
  [2] CIA Ciampino
  Airports (Enter = all, or e.g. 1,2): 1
How many arrival cities? [1/2] (Enter = 1): 2
  Arrival city 1: tokyo
  Airports (Enter = all, or e.g. 1,2):
  Arrival city 2: osaka
  [1] UKB Kobe
  [2] KIX Kansai International
  [3] ITM Itami
  Airports (Enter = all, or e.g. 1,2): 2,3
RETURN
How many return departure cities? [1/2] (Enter = Tokyo (HND, NRT) / Osaka (KIX, ITM)):
How many return arrival cities? [1/2] (Enter = Rome (FCO)):
Departure period: [1] a month  [2] around a date: 2
Date, day/month/year (e.g. 15/10/2027): 02/03/27
How many days before/after that date: 7
  Checking flights on sale...
  Outbound: flights on 15 of 15 dates, one-way from 562 EUR.
  Return: flights on 45 of 45 dates, one-way from 556 EUR.
Minimum trip length (days): 14
Maximum trip length (days): 21
Maximum stops per leg (0 = direct only, Enter = any): 1
How many top results to show: 5
Update frequency (minutes): 60
Price currency (e.g. EUR, USD, GBP; Enter = EUR):

194 searches to monitor (120 round trips, 74 one-way). Data in .../data/FCO-HND_NRT_KIX_ITM-...
Update every 60 min (gets longer by itself if Google limits requests). Ctrl+C to stop.
```

Then the tool works on its own. Leave the terminal open and stop it with Ctrl+C once
you have booked.

Accepted answers:

| Question | Examples |
|---|---|
| City | `rome`, `Tokyo`, airport code `FCO`, city code `ROM` |
| Airports | Enter = all, or comma-separated numbers: `1,3` |
| Month | `10/2027`, `10/27`, `2027-10` |
| Date | `15/10/2027`, `15/10/27`, `2027-10-15` (day/month/year) |
| Days before/after | `7` = 7 days before and 7 after the date |
| Stops | `0` = direct only, `1`, `2`, Enter = any |
| Currency | 3-letter code: `EUR`, `USD`, `GBP`, `JPY`, ... Enter = EUR |

Before asking for the trip length, the tool checks that flights are on sale in the
period. If there are none, it immediately asks for another period or city.

## What you see during a check

```
🌍 Searching from 🇮🇹 IT, Milan (IP 203.0.113.7)

✓ Calendar   [████████████████████████] 40/40 100% · in 44 s · 434 estimated prices

Full search: 100 searches (current top 0, best estimates 15, rotation 85)
★ new lowest price: 672 EUR Round trip Osaka, 2027-03-01 -> 2027-03-22 (21 days)
✓ Verify     [████████████████████████] 100/100 100% · in 7 min 00 s · lowest 672 EUR

Seller prices (agencies included) for 5 round trips in the top list
★ new lowest price: 656 EUR on lastminute.com  2027-03-01 -> 2027-03-16  (outbound 08:55, return 17:55)
✓ Sellers    [████████████████████████] 5/5 100% · in 6 min 02 s · lowest 656 EUR

================================================================================
Top 5 Rome -> Tokyo/Osaka, return Tokyo/Osaka -> Rome, departure 2027-02-23 .. 2027-03-09, 14-21 days, max 1 stop
Estimated 194/194 searches, verified with the full price 100/194 (scan in progress). The 15 cheapest combinations
according to the calendar are already verified; the other 94 searches in the next checks (at most 100 per check,
to avoid being blocked by Google)
🌍 Searching from 🇮🇹 IT, Milan (IP 203.0.113.7)

1. 656 EUR on lastminute.com (674 EUR listed, outbound 08:55, return 17:55)  Round trip Osaka  2027-03-01 -> 2027-03-16 (15 days)  Qatar Airways  [FCO-DOH DOH-KIX]
   Price LOW: -32% vs typical 986 EUR, range 870-1400 EUR, lowest in the last 60 days 674 EUR
   https://www.google.com/travel/flights/search?tfs=...
2. ...

Variant comparison (verified prices):
  Outbound Tokyo, return from Tokyo: Round trip 777 EUR · 2 tickets 1109 EUR
  Outbound Tokyo, return from Osaka: 2 tickets 1118 EUR
  Outbound Osaka, return from Tokyo: 2 tickets 1121 EUR
  Outbound Osaka, return from Osaka: Round trip 656 EUR · 2 tickets 1130 EUR  ← best

Next update in 48:25 (at 23:40)
```

How to read it:

| Item | Meaning |
|---|---|
| 🌍 Searching from | IP and country the requests leave from. If they change between two checks (e.g. you turn on a VPN) a warning appears: prices can change with the country |
| Calendar | quick estimate of every date from Google's price graph |
| Full search | complete search, date by date, as on Google Flights |
| Sellers | agency prices for the round trips in the top list |
| 656 EUR on lastminute.com (674 EUR listed) | best price among sellers; in brackets the price in Google's list |
| Price LOW | rating against Google's typical range. LOW and close to the 60-day minimum = good time to book |
| Estimated / verified | estimated = indicative price from the calendar; verified = real price. The top list uses verified prices only |
| Variant comparison | the best price for each city combination. "(estimate)" = not verified yet |
| 💡 Leaving on ... | a date up to 7 days outside the period that costs less than the top (never in the top list) |

Each check makes at most 100 full searches: with 194 searches, full coverage arrives at
the second check. The cheapest combinations are verified first.

The latest top list is also in `data/<search>/top.txt`.

## Which search to set up

### Trip type

**[1] Same city.** The return leaves from the arrival city and goes back to the
departure city. With two arrival cities (Tokyo and Osaka) the tool searches both without
mixing them.

**[2] Return from a different city.** You choose outbound and return cities separately,
and the tool tries every combination:

| Variant | How it is searched |
|---|---|
| Outbound Tokyo, return from Tokyo | round trip on one ticket + two one-way tickets |
| Outbound Osaka, return from Osaka | round trip on one ticket + two one-way tickets |
| Outbound Tokyo, return from Osaka | two one-way tickets |
| Outbound Osaka, return from Tokyo | two one-way tickets |

A single "multi-city" ticket is not available in the APIs used: for mixed variants the
tool combines two one-way tickets and reminds you they are not linked (if one flight
changes or is cancelled, the other is not protected).

### Examples

| You want... | Setup |
|---|---|
| The best price to Osaka in March | type 1, Rome → Osaka, month `03/2027` |
| To know whether Tokyo or Osaka is cheaper | type 1, Rome → Tokyo and Osaka |
| To fly into Tokyo and out of Osaka | type 2, Rome → Tokyo, return Osaka → Rome |
| Every combination of the two cities | type 2, Tokyo and Osaka on both sides |
| To watch a good price seen on a few days | date ± 3, narrow trip length (e.g. 14-16) |

### The period is counted from the date

With date `20/03/27` and `10` days, departures go from 10/03 to 30/03. A flight leaving
on 03/03 is outside: at most it appears as a 💡 suggestion if it is within 7 days.

### How many searches

One per round-trip date pair, plus one per day and city for one-way flights. More
cities and more days mean more searches and more checks to full coverage. Examples:
Rome → Osaka, 9 departure days, trip length 14-21 = 97 searches (one check); the Japan
example = 194 searches (two checks).

## Parameter file and direct start

To skip the questions, save the search in a JSON file. Example, in the
format of `ricerche/esempio.json` (field names are in Italian):

```json
{
  "lingua": "en",
  "andata": {
    "da": [{"nome": "Rome", "aeroporti": ["FCO"]}],
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
    "a": [{"nome": "Rome", "aeroporti": ["FCO"]}]
  },
  "periodo": {"data": "02/03/2027", "giorni_prima_dopo": 7},
  "durata": {"min": 14, "max": 21},
  "max_scali": 1,
  "top": 5,
  "frequenza_minuti": 60,
  "valuta": "EUR"
}
```

Two ways to use it:

```bash
# direct start: no questions, everything from the file
.venv/bin/python tracker.py ricerche/esempio.json

# from the questions: choose the language, then 2 and the file path
.venv/bin/python tracker.py
```

| Field | Required | Values |
|---|---|---|
| `lingua` (language) | no | `"it"` or `"en"`, default `"it"`. Used on direct start; when you load the file from the questions, the tool updates it with the chosen language |
| `andata.da`, `andata.a` (outbound from / to) | yes | 1 or 2 cities, each `{"nome": "...", "aeroporti": ["..."]}` |
| `ritorno.da`, `ritorno.a` (return from / to) | no | same format. Without `ritorno`: same city (type 1) |
| `periodo` (period) | yes | `{"data": "02/03/2027", "giorni_prima_dopo": 7}`, `{"mese": "03/2027"}` or `{"dal": "01/03/2027", "al": "20/03/2027"}` |
| `durata` (trip length) | yes | `{"min": 14, "max": 21}` |
| `max_scali` (max stops) | no | `null` or missing = any, `0` = direct only, `1`, `2` |
| `top` | no | number of results, default 5 |
| `frequenza_minuti` | no | minutes between checks, default 30 |
| `valuta` (currency) | no | 3-letter code, default `"EUR"` |

In the file, cities are written with airport codes; `nome` is only used in messages.
If the file is not valid the tool says what is wrong (e.g. `missing field 'periodo'`).
The example has a fixed date: update it before use.

## Telegram notifications

### Setup (once)

```bash
.venv/bin/python tracker.py --setup-telegram
```

1. On Telegram open @BotFather, send `/newbot` and copy the token.
2. Paste the token when the tool asks for it.
3. Open your bot and press **Start**.

Anyone who presses **Start** (`/start`) on your bot gets the notifications of every
running tracker; with `/stop` they stop. Anyone who finds the bot's name can subscribe
and see routes, dates and prices: share it only with people who should see them. To
remove a chat by hand, delete its number from `chat_ids` in `telegram.json`.

### What you get

| When | Message |
|---|---|
| First check after start | 🚀 Tracker started, with the full top list |
| New lowest price | ✈️ New lowest price, with the full top list |
| Google limits requests | ⚠️ Slowing down, with the new pace |
| Google back to normal | ✅ Speeding up |
| Ctrl+C | ⏹ Tracker stopped by you |
| Unexpected error | ❌ Tracker stopped by an error |

A check without a better price sends nothing: the bot writes only when there is news. The
bot cannot tell you whether the tracker is running: it is a process in your computer's
terminal, not an always-on service, and if the computer sleeps or you close the window
it stops without being able to warn you. To check, look at the terminal (countdown to
the next check) or at the time of `top.txt`, which is updated at every check.

Every message shows the search parameters, the country searches leave from (never the
IP) and the time of the next check.

```
✈️ New lowest price

🛫 Rome (FCO) → Tokyo (HND, NRT) / Osaka (KIX, ITM)
🛬 Tokyo (HND, NRT) / Osaka (KIX, ITM) → Rome (FCO)
📅 Departure from 23/02/2027 to 09/03/2027
🧳 Trip length min: 14 d - max: 21 days · max 1 stop · check every 60 min · EUR
🌍 Searching from 🇮🇹 IT

🔎 Scan in progress: 100/194 searches verified, 194/194 estimated
✅ The 15 cheapest combinations in the calendar are already verified
⏳ The other 94 in the next checks (max 100 per check, to avoid being blocked by Google)

🏆 Top 5

1. 656 EUR · Round trip Osaka
   📆 01/03 → 16/03 (15 days)
   🏷 on lastminute.com (674 EUR listed, outbound 08:55, return 17:55)
   🛩 Qatar Airways [FCO-DOH DOH-KIX]
   📊 LOW: -32% vs typical 986 EUR, range 870-1400 EUR, lowest in the last 60 days 674 EUR
   🔗 Open on Google Flights
...

⏱ Next check at 23:40
```

## Running it for days

- **Several searches at once:** one terminal per search. Each search has its own folder
  in `data/`; two instances with identical parameters cannot run together. 2 or 3
  instances are fine; more make Google's limits arrive sooner.
- **Restarts:** restarting with the same parameters resumes the prices already found.
  The first message after start still contains the full top list.
- **Keep the Mac awake:** if the Mac sleeps, checks stop. On macOS you can start it with
  `caffeinate`, which keeps the Mac awake while the tool runs:
  ```bash
  caffeinate -i .venv/bin/python tracker.py ricerche/esempio.json
  ```
- **Currency and country:** the same search in another currency has a separate folder.
  If you use a VPN, remember that Google adapts prices to the IP's country: you see it in
  the 🌍 line.

## How it works

Each check has three phases:

1. **Calendar (quick estimate).** Google's price graph returns, in one request, the
   indicative price of every departure date for a pair of airports. It covers
   everything in under a minute, but does not see every fare.
2. **Verification (real price).** A full search on a single combination. Each check
   verifies the current top list, the 15 cheapest combinations according to the
   calendar and, in rotation, all the others (never-verified first, then the oldest).
   This way a wrong estimate is eventually corrected.
3. **Sellers.** For round trips in the top list it opens the booking pages of the
   cheapest itineraries and keeps the cheapest seller, agencies included. Google gives
   no sellers for one-way tickets: the listed price is used.

The calendar also looks 7 days before and after the period: if a cheaper date is there,
the tool verifies it (1 or 2 searches) and shows it with 💡.

At the start of each check the tool asks ipinfo.io (or api.country.is) for the exit IP
and country: one request per check.

### Requests to Google and how not to get blocked

Google does not publish limits for Google Flights. The tool uses an **adaptive rate
limiter**: it starts at a cautious pace, slows down by itself when Google pushes back and
speeds up again when things are back to normal.

**What it does at each check**
- at most 100 full searches, with a 3-second pause between them (about 6 seconds per
  search, i.e. around ten minutes per check);
- never more searches than fit in the interval: with a 5-minute frequency, for example,
  at most 50;
- about one calendar request per airport pair and trip length, with a 1-second pause;
- for round trips in the top list, a few booking pages for agency prices.

**When it slows down.** With HTTP 429 (too many requests), a Google captcha or 5 errors
in a row, the tool stops the check and moves up one level. Each level halves the
searches, doubles the pauses and doubles the interval between checks. After a clean
check it moves down one level. Every change is also sent to Telegram.

| Level | Searches per check | Pause | Interval (with 30 min) |
|---|---|---|---|
| 0 | 100 | 3 s | 30 min |
| 1 | 50 | 6 s | 60 min |
| 2 | 25 | 12 s | 120 min |
| 3 | 12 | 24 s | 240 min |

The `excessive load generating behavior` warning in `errori_rete.log` is **not** a
block: Google closes a connection after many close requests and the tool opens another
one. A real block is a 429 or a captcha.

**Recommended settings.** What matters is the total number of full searches per hour,
adding up every instance running on the same IP:

```
searches per hour ≈ instances × min(100, searches of the search) × 60 / frequency in minutes
```

| Setup | Full searches per hour | Verdict |
|---|---|---|
| 1 instance, frequency 60 | up to 100 | safe |
| 1 instance, frequency 30 | up to 200 | safe |
| 2 instances, frequency 60 | up to 200 | safe |
| 3 instances, frequency 60 | up to 300 | borderline |
| 3 instances, frequency 30 | up to 600 | not recommended |

Practical advice:
- **frequency 30-60 minutes**; 60 if the search has more than 100 combinations (full
  coverage takes several checks anyway);
- **at most 2 or 3 instances** at once on the same IP;
- narrow the search instead of multiplying instances: fewer days, tighter trip lengths
  or a single city mean fewer searches;
- **do not lower** `PAUSA_SECONDI` below 3 and do not raise `RICERCHE_MAX_PER_GIRO` above
  100 (constants at the top of `tracker.py`);
- if "⚠️ Slowing down" arrives, let the limiter work; if it happens often, raise the
  frequency or close an instance.

Measured reference: on a test day, with up to 3 instances, the tool made about 1300-1500
requests (up to about 200 full searches per hour) without any 429 or captcha. This is a
measurement on one IP, not a guaranteed limit: Google can change its thresholds at any
time.

The other constants at the top of `tracker.py` are `VERIFICA_DA_STIMA` (estimates
verified at each check, 15), `ITINERARI_VENDITORI` (booking pages per combination, 4),
`PAUSA_CALENDARIO` (1 s) and `GIORNI_FUORI_PERIODO` (7).

## Troubleshooting

**Nothing arrives on Telegram.** Usually it means the price has not dropped: the bot
writes only with a new lowest price. To be sure, check that the terminal is open, that
the Mac is not asleep and the time of `top.txt`.

**I pressed Start on the bot and nothing happens.** The bot answers only while a
tracker is running: start one and the subscription arrives within 10 seconds.

**"verified 100/194 (scan in progress)".** Normal: at most 100 full searches per check.
The cheapest ones are already verified.

**A price seen on Google Flights does not show up.** Check that the departure is in the
period and the stops within the maximum. Agency offers also change from user to user,
and from country to country.

**`errori_rete.log`.** Internal messages of the network library, e.g. `excessive load
generating behavior`: Google closes a connection and the tool opens another one. It is
not a block.

## Development and tests

The tests check the logic without any request to Google or Telegram, and never use
hand-written dates (they start from the day they run).

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

On every push GitHub Actions runs them on Python 3.11 and 3.13: the result is in the
badge at the top and in the **Actions** tab.

| File | Content |
|---|---|
| `tracker.py` | main program |
| `lingua.py` | Italian and English texts |
| `luoghi.py` | city and airport lookup (Travelpayouts dataset, 30-day cache) |
| `telegram_bot.py` | Telegram subscriptions and messages |
| `ricerche/esempio.json` | example parameters |
| `tests/`, `.github/workflows/test.yml` | tests and their run on GitHub |
| `telegram.json` | bot token and subscribed chats (excluded from git) |
| `data/<search>/` | `top.txt`, `storico.csv` (every price found, with the country), `prezzi.json`, `parametri.json`, `errori_rete.log` |

## Limitations

- Uses internal, undocumented and unofficial Google Flights APIs (through
  [fast-flights](https://github.com/AWeirdDev/fast-flights),
  [fli](https://github.com/punitarani/fli) and direct calls). If Google changes the
  format, the tool may stop working.
- Google searches flights up to today + 330 days (the return counts); the price
  calendar up to today + 305. Combinations beyond the limit are searched once they
  become searchable.
- No single multi-city ticket; no seller prices for one-way flights.
- Prices for 1 adult, economy class. The currency must be supported by Google Flights:
  the tool only checks that the code has 3 letters.
- The code and the JSON field names are in Italian.

Personal project, for private and low-volume use. Google's terms of service forbid
automated access to its services: use it at your own risk, without lowering the
frequency too much and without multiplying instances.

## License

[MIT](LICENSE)
