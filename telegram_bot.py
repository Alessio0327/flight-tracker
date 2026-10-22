"""Notifiche Telegram tramite un bot.

Configurazione (una volta): .venv/bin/python tracker.py --setup-telegram
Token e chat id finiscono in telegram.json (permessi 600). Senza quel file le
notifiche Telegram sono semplicemente disattivate.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / "telegram.json"
API = "https://api.telegram.org/bot{token}/{metodo}"
MAX_CARATTERI = 4096


def _chiama(token, metodo, **params):
    dati = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(API.format(token=token, metodo=metodo), data=dati, timeout=30) as r:
        risposta = json.loads(r.read())
    if not risposta.get("ok"):
        raise RuntimeError(risposta.get("description", "errore Telegram"))
    return risposta["result"]


def configurato():
    return CONFIG.exists()


def invia(testo_html):
    """Invia un messaggio HTML. Un errore viene stampato, mai propagato."""
    if not CONFIG.exists():
        return
    try:
        cfg = json.loads(CONFIG.read_text())
        if len(testo_html) > MAX_CARATTERI:
            testo_html = testo_html[: MAX_CARATTERI - 20].rsplit("\n", 1)[0] + "\n…"
        _chiama(
            cfg["token"], "sendMessage",
            chat_id=cfg["chat_id"], text=testo_html, parse_mode="HTML", disable_web_page_preview="true",
        )
    except (OSError, ValueError, KeyError, RuntimeError) as e:
        print(f"[telegram] invio fallito: {e}", file=sys.stderr)


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

    print(f"\n3. Apri il bot @{bot['username']} su Telegram e inviagli un messaggio qualsiasi (es. /start).")
    print("   In attesa del messaggio...")
    offset = 0
    while True:
        aggiornamenti = _chiama(token, "getUpdates", offset=offset, timeout=25)
        for u in aggiornamenti:
            offset = u["update_id"] + 1
            msg = u.get("message")
            if msg:
                chat = msg["chat"]
                CONFIG.write_text(json.dumps({"token": token, "chat_id": chat["id"]}))
                os.chmod(CONFIG, 0o600)
                nome = chat.get("first_name") or chat.get("title") or chat["id"]
                invia("✅ Notifiche voli attive.")
                print(f"\nFatto: notifiche inviate a {nome}. Configurazione in {CONFIG}")
                return
        time.sleep(1)
