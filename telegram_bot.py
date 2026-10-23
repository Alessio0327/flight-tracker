"""Notifiche Telegram tramite un bot.

Configurazione (una volta): .venv/bin/python tracker.py --setup-telegram
Token e chat iscritte finiscono in telegram.json (permessi 600). Senza quel file le
notifiche Telegram sono semplicemente disattivate.

Chiunque apre il bot e preme Avvia (/start) riceve le notifiche; con /stop smette.
Mentre il tracker gira, un thread controlla i nuovi messaggi ogni ASCOLTO_SECONDI.
"""

import fcntl
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / "telegram.json"
LOCK = CONFIG.with_name("telegram.lock")
API = "https://api.telegram.org/bot{token}/{metodo}"
MAX_CARATTERI = 4096
TENTATIVI = 3
ASCOLTO_SECONDI = 10

BENVENUTO = ("✅ Iscritto alle notifiche voli.\n"
             "Riceverai i prossimi aggiornamenti dei tracker attivi. Invia /stop per smettere.")
CONGEDO = "👋 Notifiche disattivate. Premi /start per riattivarle."
AIUTO = "Questo bot manda solo notifiche sui prezzi dei voli. /start per iscriverti, /stop per smettere."


def _chiama(token, metodo, **params):
    dati = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(API.format(token=token, metodo=metodo), data=dati, timeout=30) as r:
            risposta = json.loads(r.read())
    except urllib.error.HTTPError as e:
        # Telegram risponde 4xx con un JSON che spiega l'errore (es. bot bloccato).
        try:
            risposta = json.loads(e.read())
        except ValueError:
            raise RuntimeError(f"HTTP {e.code}") from None
    if not risposta.get("ok"):
        raise RuntimeError(risposta.get("description", "errore Telegram"))
    return risposta["result"]


@contextmanager
def _config_bloccata():
    """Legge telegram.json in esclusiva (piu' istanze del tracker lo modificano) e lo
    riscrive all'uscita. Le versioni precedenti avevano un solo "chat_id"."""
    with open(LOCK, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cfg = json.loads(CONFIG.read_text())
        prima = json.dumps(cfg, sort_keys=True)
        if "chat_id" in cfg:
            cfg["chat_ids"] = [cfg.pop("chat_id")]
        cfg.setdefault("chat_ids", [])
        yield cfg
        if json.dumps(cfg, sort_keys=True) != prima:
            CONFIG.write_text(json.dumps(cfg))
            os.chmod(CONFIG, 0o600)


def configurato():
    return CONFIG.exists()


def _invia_a(token, chat_id, testo_html):
    """True se inviato, False se la chat non esiste piu' (bot bloccato o chat cancellata)."""
    for tentativo in range(1, TENTATIVI + 1):
        try:
            _chiama(token, "sendMessage", chat_id=chat_id, text=testo_html,
                    parse_mode="HTML", disable_web_page_preview="true")
            return True
        except RuntimeError as e:
            if "blocked" in str(e) or "chat not found" in str(e) or "deactivated" in str(e):
                return False
            errore = e
        except OSError as e:
            errore = e
        if tentativo < TENTATIVI:
            time.sleep(5 * tentativo)  # errori di rete spesso momentanei
    print(f"[telegram] invio a {chat_id} fallito dopo {TENTATIVI} tentativi: {errore}", file=sys.stderr)
    return True


def invia(testo_html):
    """Invia un messaggio HTML a tutte le chat iscritte. Un errore viene stampato, mai propagato."""
    if not CONFIG.exists():
        return
    if len(testo_html) > MAX_CARATTERI:
        testo_html = testo_html[: MAX_CARATTERI - 20].rsplit("\n", 1)[0] + "\n…"
    try:
        with _config_bloccata() as cfg:
            token, chat_ids = cfg["token"], list(cfg["chat_ids"])
    except (OSError, ValueError, KeyError) as e:
        print(f"[telegram] configurazione illeggibile: {e}", file=sys.stderr)
        return
    perse = [c for c in chat_ids if not _invia_a(token, c, testo_html)]
    if perse:
        with _config_bloccata() as cfg:
            cfg["chat_ids"] = [c for c in cfg["chat_ids"] if c not in perse]


def controlla_iscrizioni():
    """Legge i nuovi messaggi al bot: /start iscrive la chat, /stop la toglie.
    Ritorna le chat iscritte in questa chiamata."""
    nuove = []
    with _config_bloccata() as cfg:
        token = cfg["token"]
        aggiornamenti = _chiama(token, "getUpdates", offset=cfg.get("offset", 0), timeout=0)
        for u in aggiornamenti:
            cfg["offset"] = u["update_id"] + 1
            msg = u.get("message")
            if not msg:
                continue
            chat, testo = msg["chat"]["id"], (msg.get("text") or "").strip().lower()
            if testo.startswith("/start"):
                if chat not in cfg["chat_ids"]:
                    cfg["chat_ids"].append(chat)
                    nuove.append(chat)
                risposta = BENVENUTO
            elif testo.startswith("/stop"):
                cfg["chat_ids"] = [c for c in cfg["chat_ids"] if c != chat]
                risposta = CONGEDO
            else:
                risposta = AIUTO
            try:
                _chiama(token, "sendMessage", chat_id=chat, text=risposta)
            except (OSError, RuntimeError):
                pass
    return nuove


def ascolta_in_background():
    """Thread che gestisce /start e /stop mentre il tracker gira."""
    def ciclo():
        while True:
            try:
                controlla_iscrizioni()
            except (OSError, ValueError, KeyError, RuntimeError):
                pass  # rete assente o conflitto con un'altra istanza: si riprova dopo
            time.sleep(ASCOLTO_SECONDI)

    if configurato():
        threading.Thread(target=ciclo, daemon=True).start()


def setup():
    print("1. Su Telegram apri @BotFather, invia /newbot e segui le istruzioni.")
    print("2. Copia il token che ti da' (tipo 123456:ABC-...).\n")
    while True:
        token = input("Token del bot: ").strip()
        try:
            bot = _chiama(token, "getMe")
            break
        except (OSError, RuntimeError) as e:
            print(f"  token non valido ({e}), riprova")

    # Con lo stesso bot si tengono le chat gia' iscritte; con un bot nuovo si riparte.
    try:
        vecchio = json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        vecchio = {}
    chat_ids = vecchio.get("chat_ids") or ([vecchio["chat_id"]] if "chat_id" in vecchio else [])
    CONFIG.write_text(json.dumps({"token": token, "chat_ids": chat_ids if vecchio.get("token") == token else []}))
    os.chmod(CONFIG, 0o600)

    print(f"\n3. Apri il bot @{bot['username']} su Telegram e premi Avvia (o invia /start).")
    print("   Chiunque faccia lo stesso, anche dopo, riceve le notifiche mentre il tracker gira.")
    print("   In attesa del primo /start...")
    while not controlla_iscrizioni():
        time.sleep(2)
    print(f"\nFatto. Configurazione in {CONFIG}")
