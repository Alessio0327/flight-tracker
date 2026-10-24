# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html): MAJOR for
changes that break existing setups (e.g. the JSON file format), MINOR for new features,
PATCH for fixes.

## [Unreleased]

## [1.6.0] - 2026-10-24

### Added
- Alert when Google seems to have changed its format (unreadable responses, or no
  prices at all where there used to be some): one Telegram message, no slowdown, and a
  "✅" message once reading works again.
- README: what to do when pip finds `fast-flights` only up to 2.2 (Python too old).

### Fixed
- A failed search no longer stops the tracker with an error (the error text clashed with
  an internal parameter name since 1.2.0).
- `telegram.json` is no longer locked during requests to Telegram, so a slow network
  does not delay notifications from other instances.

## [1.5.0] - 2026-10-24

### Added
- Target price: optional alert only when a new lowest price is at or below a price you
  choose (startup question or `"avvisa_sotto"` in the JSON file); a 🎯 line shows the
  target and how far the current price is. At startup, with the target not reached yet,
  Telegram gets a one-line message instead of the full top list.
- Private search: a search can send nothing to Telegram (alerts option 3, or
  `"telegram": false` in the JSON file).
- User answers are shown in green in the terminal (disable with `NO_COLOR=1`).

## [1.4.0] - 2026-10-24

### Added
- Weekend mode: trips of 1 to 4 calendar days that include Saturday or Sunday, for every
  weekend in the period. JSON: optional `"weekend": true`, `durata` in calendar days.
- Results show weekdays in weekend mode, e.g. "(3 days, Sat → Mon)".
- Same-day return trips.
- City search puts same-name cities in the user's country first and shows full country
  names ("Napoli, Italia" / "Napoli, Stati Uniti").
- Hint to check cities and airports when no flights are on sale.
- `storico.csv` header row (also added to existing files).
- At startup, a list of searches in `data/` whose period is over (nothing is deleted).
- Version number: shown at startup and with `--version`; this changelog.

### Changed
- `storico.csv` rotates above 5 MB and `errori_rete.log` above 1 MB.
- The same city cannot be chosen twice on one side.

### Fixed
- `--setup-telegram` no longer waits forever when the chat is already subscribed.
- macOS notifications show accents and arrows instead of `\uXXXX` escapes.
- `ITINERARI_VENDITORI` is honoured (the library was always asked for 3 itineraries).
- Ctrl+C during the questions exits cleanly, without a traceback.
- First start without internet: clear message instead of a traceback.

## [1.3.0] - 2026-10-23

### Added
- Price currency: startup question and `valuta` field in the JSON file.
- Public IP and exit country at every check (terminal and `top.txt`; country only on
  Telegram), with a warning when it changes; country column in `storico.csv`.
- Windows support (`blocco.py` file lock, UTF-8 files, console setup); CI on Linux,
  Windows and macOS.
- READMEs rewritten around a real use case, with a rate limiter section and recommended
  settings.

### Changed
- `tracker.py` split into `parametri.py`, `ricerca.py`, `google_flights.py` and
  `interfaccia.py`.
- Telegram sends nothing when a check finds no better price.
- The currency is asked before the period check.

### Fixed
- Network library warnings no longer break the progress bar (they go to
  `errori_rete.log`).

## [1.2.0] - 2026-10-23

### Added
- Automated tests (pytest) and GitHub Actions CI on Python 3.11 and 3.13.
- Italian and English for questions, terminal output and Telegram (`lingua.py`).
- Direct start from a JSON file: `tracker.py ricerche/x.json`.
- English README (`README.md`) next to the Italian one (`README.it.md`).

### Fixed
- With a small budget (Google throttling) every search is eventually verified.
- `telegram.json` is saved after converting the old single `chat_id` format.

## [1.1.0] - 2026-10-22

### Added
- Return from a different city (up to 2 cities per side), comparing round trips with two
  one-way tickets.
- Searchable date limit shown at startup; early stop when no flights are on sale.
- Suggestions for cheaper departures up to 7 days outside the period.
- Search parameters from a JSON file.
- Telegram notifications for anyone who presses Start on the bot; "Tracker started",
  stop and error messages; clearer message layout.

## [1.0.0] - 2026-10-22

### Added
- First version: round-trip price monitor on Google Flights with city lookup, multiple
  airports, period and trip length, price rating, agency prices, adaptive rate limiter,
  progress bar, macOS and Telegram notifications.

[Unreleased]: https://github.com/Alessio0327/flight-tracker/compare/v1.6.0...HEAD
[1.6.0]: https://github.com/Alessio0327/flight-tracker/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/Alessio0327/flight-tracker/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/Alessio0327/flight-tracker/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/Alessio0327/flight-tracker/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Alessio0327/flight-tracker/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Alessio0327/flight-tracker/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Alessio0327/flight-tracker/releases/tag/v1.0.0
