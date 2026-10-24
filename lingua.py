"""Testi del tool in italiano e inglese.

TESTI[chiave] = (italiano, inglese): stringhe per str.format, con i valori passati per
nome. La lingua si sceglie all'avvio (o con il campo "lingua" del file JSON) e vale
per terminale, top.txt e Telegram.
"""

LINGUE = ("it", "en")
LINGUA = "it"
# Valuta dei prezzi (codice ISO 4217): la usano le ricerche su Google e i testi ({valuta}).
VALUTA = "EUR"


def imposta(lingua):
    global LINGUA
    if lingua not in LINGUE:
        raise ValueError(lingua)
    LINGUA = lingua


def imposta_valuta(valuta):
    global VALUTA
    VALUTA = valuta


def t(chiave, **valori):
    # {valuta} e' sempre disponibile; un valore passato esplicitamente ha la precedenza.
    return TESTI[chiave][LINGUE.index(LINGUA)].format(**{"valuta": VALUTA, **valori})


TESTI = {
    # --- avvio ---------------------------------------------------------------
    "lingua_domanda": ("Lingua / Language: [1] Italiano  [2] English (Invio/Enter = 1): ",) * 2,
    "telegram_non_attivo": (
        "(Notifiche Telegram non attive: per attivarle .venv/bin/python tracker.py --setup-telegram)\n",
        "(Telegram notifications are off: to turn them on .venv/bin/python tracker.py --setup-telegram)\n",
    ),
    "modo_domanda": (
        "Parametri: [1] rispondo alle domande  [2] leggo da un file JSON (Invio = 1): ",
        "Parameters: [1] answer the questions  [2] read a JSON file (Enter = 1): ",
    ),
    "date_cercabili": (
        "Date cercabili: partenza da domani, ultimo volo entro il {limite} "
        "(limite di Google Flights, oggi + {giorni} giorni).\n",
        "Searchable dates: departure from tomorrow, last flight by {limite} "
        "(Google Flights limit, today + {giorni} days).\n",
    ),
    "tipo_domanda": (
        "Tipo di viaggio: [1] andata e ritorno sulla stessa citta'  [2] ritorno da un'altra citta': ",
        "Trip type: [1] round trip to the same city  [2] return from a different city: ",
    ),
    "titolo_andata": ("ANDATA", "OUTBOUND"),
    "titolo_ritorno": ("RITORNO", "RETURN"),
    "ruolo_partenza": ("partenza", "departure"),
    "ruolo_arrivo": ("arrivo", "arrival"),
    "ruolo_partenza_ritorno": ("partenza del ritorno", "return departure"),
    "ruolo_arrivo_ritorno": ("arrivo del ritorno", "return arrival"),
    "quante_citta": ("Quante citta' di {ruolo}? [1/2]{suggerimento}: ",
                     "How many {ruolo} cities? [1/2]{suggerimento}: "),
    "invio_uguale": (" (Invio = {valore})", " (Enter = {valore})"),
    "citta_domanda": ("  Citta' di {ruolo}{numero}: ", "  {Ruolo} city{numero}: "),
    "citta_doppia": ("  {nome} e' gia' tra le citta' scelte: scegline un'altra", "  {nome} is already chosen: pick another city"),
    "citta_doppie": ("{dove}: due citta' con lo stesso nome", "{dove}: two cities with the same name"),
    "nessuna_citta": ("  nessuna citta' trovata per '{testo}'", "  no city found for '{testo}'"),
    "quale_citta": ("  Quale '{testo}'? (Invio = 1): ", "  Which '{testo}'? (Enter = 1): "),
    "aeroporti_domanda": ("  Aeroporti (Invio = tutti, oppure es. 1,2): ",
                          "  Airports (Enter = all, or e.g. 1,2): "),
    "periodo_domanda": ("Periodo di partenza: [1] un mese  [2] intorno a una data: ",
                        "Departure period: [1] a month  [2] around a date: "),
    "mese_domanda": ("Mese (es. 10/2027): ", "Month (e.g. 10/2027): "),
    "data_domanda": ("Data (es. 15/10/2027): ", "Date, day/month/year (e.g. 15/10/2027): "),
    "giorni_domanda": ("Quanti giorni prima/dopo quella data: ", "How many days before/after that date: "),
    "modo_durata_domanda": ("Durata: [1] libera (giorni minimi e massimi)  [2] weekend (1-4 giorni con sabato o domenica) (Invio = 1): ",
                            "Trip length: [1] free (minimum and maximum days)  [2] weekend (1-4 days including Saturday or Sunday) (Enter = 1): "),
    "weekend_min_domanda": ("Giorni minimi del viaggio, partenza e ritorno compresi (1-4): ",
                            "Minimum trip days, departure and return included (1-4): "),
    "weekend_max_domanda": ("Giorni massimi del viaggio, partenza e ritorno compresi ({minimo}-4): ",
                            "Maximum trip days, departure and return included ({minimo}-4): "),
    "serve_tra": ("serve un numero tra {minimo} e {massimo}", "a number between {minimo} and {massimo} is needed"),
    "durata_weekend_non_valida": ("durata: in modalita' weekend serve 1 <= min <= max <= 4 (giorni di calendario)",
                                  "durata: in weekend mode 1 <= min <= max <= 4 is needed (calendar days)"),
    "durata_min_domanda": ("Durata minima viaggio (giorni): ", "Minimum trip length (days): "),
    "durata_max_domanda": ("Durata massima viaggio (giorni): ", "Maximum trip length (days): "),
    "scali_domanda": ("Massimo scali per tratta (0 = solo diretti, Invio = qualsiasi): ",
                      "Maximum stops per leg (0 = direct only, Enter = any): "),
    "top_domanda": ("Quanti migliori risultati mostrare: ", "How many top results to show: "),
    "valuta_domanda": ("Valuta dei prezzi (es. EUR, USD, GBP; Invio = EUR): ",
                       "Price currency (e.g. EUR, USD, GBP; Enter = EUR): "),
    "frequenza_domanda": ("Frequenza aggiornamento (minuti): ", "Update frequency (minutes): "),
    "avvisi_domanda": ("Avvisi Telegram: [1] a ogni nuovo prezzo minimo  [2] solo sotto un prezzo che scegli  "
                       "[3] nessuno, ricerca privata (Invio = 1): ",
                       "Telegram alerts: [1] at every new lowest price  [2] only below a price you choose  "
                       "[3] none, private search (Enter = 1): "),
    "obiettivo_domanda": ("Prezzo obiettivo ({valuta}): ", "Target price ({valuta}): "),
    "percorso_domanda": ("Percorso del file JSON: ", "JSON file path: "),
    "riassunto_file": (
        "  Andata {andata_da} -> {andata_a}\n  Ritorno {ritorno_da} -> {ritorno_a}\n"
        "  Partenza dal {inizio} al {fine}, durata {durata}, {scali}, top {top}, ogni {frequenza} min, "
        "prezzi in {valuta}{obiettivo}",
        "  Outbound {andata_da} -> {andata_a}\n  Return {ritorno_da} -> {ritorno_a}\n"
        "  Departure from {inizio} to {fine}, trip length {durata}, {scali}, top {top}, every {frequenza} min, "
        "prices in {valuta}{obiettivo}",
    ),

    # --- errori di input -------------------------------------------------------
    "numeri_tra": ("numeri tra 1 e {massimo}, separati da virgola", "numbers between 1 and {massimo}, comma-separated"),
    "formato_mese": ("formato: 10/2027, 10/27 oppure 2027-10", "format: 10/2027, 10/27 or 2027-10"),
    "mese_non_valido": ("mese non valido", "invalid month"),
    "formato_data": ("formato: 15/10/2027, 15/10/27 oppure 2027-10-15",
                     "format: 15/10/2027 (day/month/year), 15/10/27 or 2027-10-15"),
    "serve_intero": ("serve un numero intero >= {minimo}", "a whole number >= {minimo} is needed"),
    "rispondi": ("rispondi {valori}", "answer {valori}"),
    "oppure": (" o ", " or "),
    "scrivi_percorso": ("scrivi il percorso del file", "type the file path"),
    "file_illeggibile": ("non riesco a leggere il file: {errore}", "cannot read the file: {errore}"),
    "json_non_valido": ("JSON non valido (riga {riga}): {errore}", "invalid JSON (line {riga}): {errore}"),
    "manca_campo": ("manca il campo {campo}", "missing field {campo}"),
    "struttura_non_valida": ("struttura non valida: confronta il file con ricerche/esempio.json",
                             "invalid structure: compare the file with ricerche/esempio.json"),
    "lista_citta": ("{dove}: serve una lista di 1 o 2 citta'", "{dove}: a list of 1 or 2 cities is needed"),
    "formato_citta": ('{dove}: ogni citta\' e\' {{"nome": "Roma", "aeroporti": ["FCO"]}}',
                      '{dove}: each city is {{"nome": "Rome", "aeroporti": ["FCO"]}}'),
    "periodo_vuoto": ("periodo vuoto o gia' passato", "empty or past period"),
    "durata_non_valida": ("durata: serve 1 <= min <= max", "durata: 1 <= min <= max is needed"),
    "valori_non_validi": ("top e frequenza_minuti devono essere >= 1, max_scali >= 0",
                          "top and frequenza_minuti must be >= 1, max_scali >= 0"),
    "file_lingua_aggiornata": ("  Lingua del file aggiornata: {file}", "  File language updated: {file}"),
    "formato_valuta": ("serve un codice di 3 lettere, es. EUR, USD, GBP", "a 3-letter code is needed, e.g. EUR, USD, GBP"),
    "valuta_non_valida": ('valuta: serve un codice di 3 lettere, es. "EUR"', 'valuta: a 3-letter code is needed, e.g. "EUR"'),
    "obiettivo_non_valido": ("avvisa_sotto: serve un prezzo intero >= 1, oppure null",
                             "avvisa_sotto: a whole price >= 1 is needed, or null"),
    "lingua_non_valida": ('lingua: usa "it" o "en"', 'lingua: use "it" or "en"'),

    # --- controllo del periodo -------------------------------------------------
    "periodo_passato": ("  Periodo gia' passato.", "  The period is already over."),
    "oltre_limite": (
        "  Google Flights cerca voli solo fino al {limite}: partenze dal {inizio} non sono ancora cercabili.",
        "  Google Flights searches flights only up to {limite}: departures from {inizio} are not searchable yet.",
    ),
    "oltre_limite_scelta": (
        "  [1] cambia periodo  [2] monitora comunque, in attesa che entrino in vendita: ",
        "  [1] change period  [2] monitor anyway, until they go on sale: ",
    ),
    "oltre_calendario": (
        "  Il calendario prezzi arriva al {limite}: non posso verificare in anticipo, lo fara' la ricerca completa.",
        "  The price calendar reaches {limite}: I cannot check in advance, the full search will.",
    ),
    "lato_andata": ("Andata", "Outbound"),
    "lato_ritorno": ("Ritorno", "Return"),
    "controllo_vendita": ("  Controllo i voli in vendita...", "  Checking flights on sale..."),
    "verifica_fallita": ("  Verifica non riuscita ({errore}), proseguo.", "  Check failed ({errore}), going on."),
    "nessun_volo": (
        "  {lato}: nessun volo in vendita da {da} a {a} tra il {inizio} e il {fine}.",
        "  {lato}: no flights on sale from {da} to {a} between {inizio} and {fine}.",
    ),
    "controlla_citta": ("  Controlla città e aeroporti scelti ({da} -> {a}): un aeroporto piccolo o una città\n"
                        "  con lo stesso nome in un altro paese possono non avere voli.",
                        "  Check the chosen cities and airports ({da} -> {a}): a small airport, or a city\n"
                        "  with the same name in another country, may have no flights."),
    "cambia_scelta": ("  Cambia [1] periodo  [2] citta': ", "  Change [1] period  [2] city: "),
    "voli_trovati": (
        "  {lato}: voli in {date} date su {totale}, solo andata da {prezzo} {valuta}.",
        "  {lato}: flights on {date} of {totale} dates, one-way from {prezzo} {valuta}.",
    ),
    "calendario_non_vede": (
        "  Dopo il {limite} il calendario non vede: quelle date le verifica la ricerca completa.",
        "  The calendar does not see beyond {limite}: the full search checks those dates.",
    ),
    "ricerche_future": (
        "  {future} ricerche su {totale} riguardano voli dopo il {limite}: le faccio man mano che diventano possibili.",
        "  {future} of {totale} searches involve flights after {limite}: I will run them as they become possible.",
    ),
    "nessuna_cercabile": (
        "  Per ora nessuna e' cercabile: la prima lo diventa il {data}.",
        "  None is searchable yet: the first one becomes searchable on {data}.",
    ),
    "cambia_durata": ("  [1] cambia durata  [2] monitora comunque: ", "  [1] change trip length  [2] monitor anyway: "),

    # --- Google e ritmo --------------------------------------------------------
    "http_429": ("HTTP 429, troppe richieste", "HTTP 429, too many requests"),
    "captcha": ("captcha di Google", "Google captcha"),
    "risposta_inattesa": ("risposta Google inattesa (pagina senza risultati)",
                          "unexpected Google response (page without results)"),
    "calendario_http": ("calendario HTTP {codice}", "calendar HTTP {codice}"),
    "ritmo": (
        "livello {livello}/{massimo}: max {ricerche} ricerche per giro, pausa {pausa} s, un giro ogni {intervallo} min",
        "level {livello}/{massimo}: max {ricerche} searches per check, pause {pausa} s, one check every {intervallo} min",
    ),

    # --- prezzi ----------------------------------------------------------------
    "scali_qualsiasi": ("scali qualsiasi", "any stops"),
    "scali_0": ("solo diretti", "direct only"),
    "scali_1": ("max 1 scalo", "max 1 stop"),
    "scali_n": ("max {n} scali", "max {n} stops"),
    "prezzo_venditore": ("{prezzo} {valuta} su {nome} ({lista} {valuta} in lista, {orari})",
                         "{prezzo} {valuta} on {nome} ({lista} {valuta} listed, {orari})"),
    "orari": ("andata {andata}, ritorno {ritorno}", "outbound {andata}, return {ritorno}"),
    "giudizio_basso": ("BASSO", "LOW"),
    "giudizio_alto": ("ALTO", "HIGH"),
    "giudizio_media_bassa": ("nella media, parte bassa", "typical, lower end"),
    "giudizio_media_alta": ("nella media, parte alta", "typical, upper end"),
    "giudizio_media": ("nella media", "typical"),
    "giudizio": ("{etichetta}: {diff:+d}% sul tipico {tipico} {valuta}, fascia {basso}-{alto} {valuta}",
                 "{etichetta}: {diff:+d}% vs typical {tipico} {valuta}, range {basso}-{alto} {valuta}"),
    "minimo_60": (", minimo ultimi 60 gg {prezzo} {valuta}", ", lowest in the last 60 days {prezzo} {valuta}"),

    # --- giro ------------------------------------------------------------------
    "barra_calendario": ("Calendario", "Calendar"),
    "barra_verifica": ("Verifica", "Verify"),
    "barra_venditori": ("Venditori", "Sellers"),
    "barra_rimasti": ("~{tempo} rimasti", "~{tempo} left"),
    "barra_stima": ("stima tempo...", "estimating time..."),
    "errore_calendario": ("[errore calendario] {tratta}: {errore}", "[calendar error] {tratta}: {errore}"),
    "stop_calendario": ("[stop calendario] troppi errori, continuo con la ricerca precisa",
                        "[calendar stopped] too many errors, going on with the full search"),
    "prezzi_stimati": ("{n} prezzi stimati", "{n} estimated prices"),
    "verifica_precisa": (
        "\nVerifica precisa: {n} ricerche (top attuale {top}, stime migliori {stima}, a rotazione {rotazione}{fuori})",
        "\nFull search: {n} searches (current top {top}, best estimates {stima}, rotation {rotazione}{fuori})",
    ),
    "fuori_periodo_conta": (", fuori periodo {n}", ", outside the period {n}"),
    "errore_ricerca": ("[errore] {chiave}: {errore}", "[error] {chiave}: {errore}"),
    "cinque_errori": ("5 errori di fila, probabile limitazione", "5 errors in a row, probably rate-limited"),
    "nuovo_minimo": ("★ nuovo minimo: {testo}", "★ new lowest price: {testo}"),
    "nuovo_minimo_venditore": ("★ nuovo minimo: {prezzo} {valuta} su {nome}  {andata} -> {ritorno}  ({orari})",
                               "★ new lowest price: {prezzo} {valuta} on {nome}  {andata} -> {ritorno}  ({orari})"),
    "minimo_barra": ("minimo {prezzo} {valuta}", "lowest {prezzo} {valuta}"),
    "venditori_titolo": ("\nPrezzi dei venditori (agenzie comprese) per {n} A/R in top",
                         "\nSeller prices (agencies included) for the round trips in the top list: {n}"),
    "http_429_prenotazione": ("HTTP 429 sulle pagine di prenotazione", "HTTP 429 on booking pages"),
    "errore_venditori": ("[errore venditori] {andata} -> {ritorno}: {errore}",
                         "[seller error] {andata} -> {ritorno}: {errore}"),
    "venditore_storico": ("{nome} (venditore)", "{nome} (seller)"),
    "blocco": ("[blocco] Google limita le richieste: {motivo}. Giro interrotto.",
               "[blocked] Google is limiting requests: {motivo}. Check interrupted."),
    "top_titolo": (
        "Top {n} {tratta}, partenza {inizio} .. {fine}, {durata}, {scali} (aggiornato {adesso})",
        "Top {n} {tratta}, departure {inizio} .. {fine}, {durata}, {scali} (updated {adesso})",
    ),
    "nessun_prezzo_top": ("Nessun prezzo ancora: date forse non in vendita.", "No prices yet: the dates may not be on sale."),
    "notifica_titolo": ("Volo {tratta}: nuovo minimo", "Flight {tratta}: new lowest price"),

    # --- posizione (IP) -------------------------------------------------------
    "posizione": ("🌍 Ricerche da {bandiera} {paese}{citta} (IP {ip})", "🌍 Searching from {bandiera} {paese}{citta} (IP {ip})"),
    "posizione_ignota": ("🌍 Paese di uscita non rilevato (servizio di geolocalizzazione non raggiungibile)",
                         "🌍 Exit country not detected (geolocation service unreachable)"),
    "posizione_cambiata": (
        "⚠️ IP cambiato dall'ultimo controllo: prima {prima}, ora {ora}. I prezzi possono cambiare con il paese.",
        "⚠️ IP changed since the last check: before {prima}, now {ora}. Prices can change with the country.",
    ),
    "tg_posizione": ("🌍 Ricerche da {bandiera} {paese}", "🌍 Searching from {bandiera} {paese}"),
    "tg_posizione_cambiata": ("⚠️ Paese di uscita cambiato: prima {prima}, ora {ora}",
                              "⚠️ Exit country changed: before {prima}, now {ora}"),

    # --- copertura -------------------------------------------------------------
    "copertura": ("stimate {stimate}/{totale} ricerche, verificate col prezzo completo {verificate}/{totale}",
                  "estimated {stimate}/{totale} searches, verified with the full price {verificate}/{totale}"),
    "scansione_completa": (" (scansione completa)", " (scan complete)"),
    "scansione_in_corso": (" (scansione in corso)", " (scan in progress)"),
    "copertura_migliori": (". Le {n} combinazioni piu' economiche secondo il calendario sono gia' verificate",
                           ". The {n} cheapest combinations according to the calendar are already verified"),
    "copertura_altre": (
        "; le altre {n} ricerche ai prossimi controlli (massimo {budget} per controllo, per non farsi bloccare da Google)",
        "; the other {n} searches in the next checks (at most {budget} per check, to avoid being blocked by Google)",
    ),
    "copertura_future": ("; altre {n} non ancora possibili (voli oltre il {limite})",
                         "; {n} more not possible yet (flights after {limite})"),

    # --- proposte --------------------------------------------------------------
    "ar": ("A/R", "Round trip"),
    "due_biglietti": ("2 biglietti", "2 tickets"),
    "durata_gg": ("({n} gg)", "({n} days)"),
    "durata_gg_weekend": ("({n} gg, {da} → {a})", "({n} days, {da} → {a})"),
    "giorni_settimana": ("lun mar mer gio ven sab dom", "Mon Tue Wed Thu Fri Sat Sun"),
    "durata_libera": ("{min}-{max} giorni", "{min}-{max} days"),
    "durata_weekend": ("weekend, {min}-{max} giorni con sabato o domenica",
                       "weekend, {min}-{max} days including Saturday or Sunday"),
    "riassunto_2b": ("2 biglietti, andata {va} / ritorno da {torna}", "2 tickets, outbound {va} / return from {torna}"),
    "dettaglio_2b": ("{prezzo} {valuta}  2 biglietti: andata {va}, ritorno da {torna}",
                     "{prezzo} {valuta}  2 tickets: outbound {va}, return from {torna}"),
    "visto": ("visto {quando}", "seen {quando}"),
    "prezzo_giudizio": ("   Prezzo {giudizio}", "   Price {giudizio}"),
    "biglietti_separati": ("biglietti separati: se un volo cambia o salta, l'altro non è protetto",
                           "separate tickets: if one flight changes or is cancelled, the other is not protected"),
    "tratta_ritorno": ("{andata}, ritorno {da} -> {a}", "{andata}, return {da} -> {a}"),
    "confronto_titolo": ("Confronto varianti (prezzi verificati):", "Variant comparison (verified prices):"),
    "confronto_riga": ("  Andata {va}, ritorno da {torna}: ", "  Outbound {va}, return from {torna}: "),
    "stima": ("~{prezzo} {valuta} (stima)", "~{prezzo} {valuta} (estimate)"),
    "non_disponibile": ("n.d.", "n/a"),
    "migliore": ("  ← migliore", "  ← best"),
    "risparmi": ("risparmi {n} {valuta}", "you save {n} {valuta}"),
    "ci_sono_voli": ("ci sono voli", "there are flights"),
    "suggerimento": ("💡 Partendo il {giorno} (fuori dal tuo periodo) {risparmio}: {testo}",
                     "💡 Leaving on {giorno} (outside your period) {risparmio}: {testo}"),

    # --- Telegram --------------------------------------------------------------
    "riassunto_privata": (", senza Telegram", ", no Telegram"),
    "telegram_disattivato": ("Telegram disattivato per questa ricerca: nessun messaggio al bot e ai suoi iscritti.\n",
                             "Telegram is off for this search: no messages to the bot and its subscribers.\n"),
    "telegram_non_valido": ("telegram: usa true o false", "telegram: use true or false"),
    "riassunto_obiettivo": (", avviso sotto {prezzo} {valuta}", ", alert below {prezzo} {valuta}"),
    "tg_obiettivo_raggiunto": ("🎯 <b>Sotto il tuo obiettivo</b>: {prezzo} {valuta} (obiettivo {obiettivo} {valuta})",
                               "🎯 <b>Below your target</b>: {prezzo} {valuta} (target {obiettivo} {valuta})"),
    "obiettivo_riga": ("🎯 Obiettivo {obiettivo} {valuta} · ora {prezzo} {valuta} (mancano {mancano} {valuta})",
                       "🎯 Target {obiettivo} {valuta} · now {prezzo} {valuta} ({mancano} {valuta} to go)"),
    "obiettivo_riga_raggiunto": ("🎯 Obiettivo {obiettivo} {valuta} · ora {prezzo} {valuta}: raggiunto",
                                 "🎯 Target {obiettivo} {valuta} · now {prezzo} {valuta}: reached"),
    "obiettivo_riga_senza_prezzo": ("🎯 Obiettivo {obiettivo} {valuta}", "🎯 Target {obiettivo} {valuta}"),
    "tg_avviato_breve": ("🚀 <b>Tracker avviato</b> · {tratta}\n{obiettivo}", "🚀 <b>Tracker started</b> · {tratta}\n{obiettivo}"),
    "tg_nuovo_minimo": ("✈️ <b>Nuovo prezzo minimo</b>", "✈️ <b>New lowest price</b>"),
    "tg_avviato": ("🚀 <b>Tracker avviato</b>: prezzi migliori attuali", "🚀 <b>Tracker started</b>: current best prices"),
    "tg_partenza": ("📅 Partenza dal {inizio} al {fine}", "📅 Departure from {inizio} to {fine}"),
    "tg_durata": ("🧳 Durata min: {min} gg - max: {max} giorni · {scali} · controllo ogni {frequenza} min · {valuta}",
                  "🧳 Trip length min: {min} d - max: {max} days · {scali} · check every {frequenza} min · {valuta}"),
    "tg_durata_weekend": ("🧳 Weekend: min {min} - max {max} giorni, con sabato o domenica · {scali} · controllo ogni {frequenza} min · {valuta}",
                          "🧳 Weekend: min {min} - max {max} days, including Saturday or Sunday · {scali} · check every {frequenza} min · {valuta}"),
    "tg_completa": ("🔎 <b>Scansione completa</b>: {verificate}/{totale} ricerche verificate",
                    "🔎 <b>Scan complete</b>: {verificate}/{totale} searches verified"),
    "tg_in_corso": ("🔎 <b>Scansione in corso</b>: {verificate}/{totale} ricerche verificate, {stimate}/{totale} stimate",
                    "🔎 <b>Scan in progress</b>: {verificate}/{totale} searches verified, {stimate}/{totale} estimated"),
    "tg_migliori": ("✅ Le {n} combinazioni più economiche del calendario sono già verificate",
                    "✅ The {n} cheapest combinations in the calendar are already verified"),
    "tg_altre": ("⏳ Le altre {n} ai prossimi controlli (max {budget} per controllo, per non farsi bloccare da Google)",
                 "⏳ The other {n} in the next checks (max {budget} per check, to avoid being blocked by Google)"),
    "tg_future": ("🔒 Altre {n} non ancora cercabili (voli oltre il {limite})",
                  "🔒 {n} more not searchable yet (flights after {limite})"),
    "tg_venditore": ("   🏷 su {nome} ({lista} {valuta} in lista, {orari})", "   🏷 on {nome} ({lista} {valuta} listed, {orari})"),
    "tg_apri_google": ("Apri su Google Flights", "Open on Google Flights"),
    "tg_apri": ("apri", "open"),
    "tg_confronto": ("⚖️ <b>Confronto varianti</b> (prezzi verificati)", "⚖️ <b>Variant comparison</b> (verified prices)"),
    "tg_rallento": ("⚠️ <b>Rallento</b>: Google limita le richieste ({motivo}).",
                    "⚠️ <b>Slowing down</b>: Google is limiting requests ({motivo})."),
    "tg_ancora_limita": ("⚠️ Google limita ancora le richieste ({motivo}), resto al ritmo minimo.",
                         "⚠️ Google is still limiting requests ({motivo}), staying at the slowest pace."),
    "tg_accelero": ("✅ <b>Accelero</b>: Google risponde di nuovo normalmente.",
                    "✅ <b>Speeding up</b>: Google answers normally again."),
    "tg_prossimo": ("⏱ Prossimo controllo alle {ora}", "⏱ Next check at {ora}"),
    "ritmo_ora": ("Ora {stato}.", "Now {stato}."),
    "ritmo_terminale": ("\n[ritmo] {avviso} Ora {stato}.", "\n[pace] {avviso} Now {stato}."),
    "tg_fermato_utente": ("⏹ <b>Tracker fermato</b> da te (Ctrl+C)\n{tratta}",
                          "⏹ <b>Tracker stopped</b> by you (Ctrl+C)\n{tratta}"),
    "tg_fermato_errore": ("❌ <b>Tracker fermato</b> per un errore\n{tratta}\n<code>{errore}</code>\nRilancialo dal terminale.",
                          "❌ <b>Tracker stopped</b> by an error\n{tratta}\n<code>{errore}</code>\nRestart it from the terminal."),

    # --- terminale -------------------------------------------------------------
    "luoghi_offline": ("Non riesco a scaricare l'elenco di citta' e aeroporti ({errore}). Serve internet al primo "
                       "avvio; poi resta una copia locale per 30 giorni.",
                       "Cannot download the list of cities and airports ({errore}). Internet is needed on the first "
                       "start; then a local copy is kept for 30 days."),
    "ricerche_concluse": ("({n} ricerche in data/ hanno il periodo gia' passato: se non ti servono puoi cancellarne "
                          "le cartelle, es. {esempio})\n",
                          "({n} searches in data/ have a period that is already over: if you do not need them you can "
                          "delete their folders, e.g. {esempio})\n"),
    "altra_istanza": ("Un'altra istanza con questi parametri e' gia' attiva ({cartella}).",
                      "Another instance with these parameters is already running ({cartella})."),
    "da_monitorare": ("\n{totale} ricerche da monitorare ({ar} A/R, {sole} sole andate){future}. Dati in {cartella}",
                      "\n{totale} searches to monitor (round trip: {ar}, one-way: {sole}){future}. Data in {cartella}"),
    "future_breve": (", +{n} non ancora possibili", ", +{n} not possible yet"),
    "aggiornamento_ogni": ("Aggiornamento ogni {minuti} min (si allunga da solo se Google limita). Ctrl+C per fermare.",
                           "Update every {minuti} min (gets longer by itself if Google limits requests). Ctrl+C to stop."),
    "prossimo_alle": ("\nProssimo aggiornamento alle {ora}.", "\nNext update at {ora}."),
    "prossimo_tra": ("\rProssimo aggiornamento tra {timer} (alle {ora})  ", "\rNext update in {timer} (at {ora})  "),
    "fermato": ("\nFermato.", "\nStopped."),

    # --- bot Telegram ----------------------------------------------------------
    "bot_benvenuto": ("✅ Iscritto alle notifiche voli.\n"
                      "Riceverai i prossimi aggiornamenti dei tracker attivi. Invia /stop per smettere.",
                      "✅ Subscribed to flight notifications.\n"
                      "You will get the next updates of the running trackers. Send /stop to stop."),
    "bot_congedo": ("👋 Notifiche disattivate. Premi /start per riattivarle.",
                    "👋 Notifications turned off. Press /start to turn them on again."),
    "bot_aiuto": ("Questo bot manda solo notifiche sui prezzi dei voli. /start per iscriverti, /stop per smettere.",
                  "This bot only sends flight price notifications. /start to subscribe, /stop to stop."),
    "bot_invio_fallito": ("[telegram] invio a {chat} fallito dopo {tentativi} tentativi: {errore}",
                          "[telegram] sending to {chat} failed after {tentativi} attempts: {errore}"),
    "bot_config_illeggibile": ("[telegram] configurazione illeggibile: {errore}",
                               "[telegram] unreadable configuration: {errore}"),
    "setup_passo_1": ("1. Su Telegram apri @BotFather, invia /newbot e segui le istruzioni.",
                      "1. On Telegram open @BotFather, send /newbot and follow the instructions."),
    "setup_passo_2": ("2. Copia il token che ti da' (tipo 123456:ABC-...).\n",
                      "2. Copy the token it gives you (like 123456:ABC-...).\n"),
    "setup_token": ("Token del bot: ", "Bot token: "),
    "setup_token_errato": ("  token non valido ({errore}), riprova", "  invalid token ({errore}), try again"),
    "setup_passo_3": ("\n3. Apri il bot @{bot} su Telegram e premi Avvia (o invia /start).",
                      "\n3. Open the bot @{bot} on Telegram and press Start (or send /start)."),
    "setup_chiunque": ("   Chiunque faccia lo stesso, anche dopo, riceve le notifiche mentre il tracker gira.",
                       "   Anyone who does the same, even later, gets the notifications while the tracker runs."),
    "setup_attesa": ("   In attesa del primo /start...", "   Waiting for the first /start..."),
    "setup_fatto": ("\nFatto. Configurazione in {file}", "\nDone. Configuration in {file}"),
}
