"""Iscrizioni e invio Telegram, con l'API di Telegram finta (nessun messaggio vero)."""

import json

import pytest

import telegram_bot
from lingua import t


@pytest.fixture
def bot(tmp_path, monkeypatch):
    """Bot finto: registra i messaggi inviati e restituisce gli aggiornamenti in coda."""
    monkeypatch.setattr(telegram_bot, "CONFIG", tmp_path / "telegram.json")
    monkeypatch.setattr(telegram_bot, "LOCK", tmp_path / "telegram.lock")
    monkeypatch.setattr(telegram_bot.time, "sleep", lambda s: None)

    class Finto:
        def __init__(self):
            self.inviati, self.coda, self.bloccati, self.offset_chiesti = [], [], set(), []

        def chiama(self, token, metodo, **params):
            if metodo == "getUpdates":
                self.offset_chiesti.append(params["offset"])
                return [u for u in self.coda if u["update_id"] >= params["offset"]]
            if metodo == "sendMessage":
                if params["chat_id"] in self.bloccati:
                    raise RuntimeError("Forbidden: bot was blocked by the user")
                self.inviati.append((params["chat_id"], params["text"]))
                return {}
            raise AssertionError(metodo)

        def config(self):
            return json.loads(telegram_bot.CONFIG.read_text())

    finto = Finto()
    monkeypatch.setattr(telegram_bot, "_chiama", finto.chiama)
    telegram_bot.CONFIG.write_text(json.dumps({"token": "T", "chat_ids": [1]}))
    return finto


def messaggio(update_id, chat, testo):
    return {"update_id": update_id, "message": {"chat": {"id": chat}, "text": testo}}


def test_start_iscrive_e_risponde(bot):
    bot.coda = [messaggio(10, 2, "/start")]
    assert telegram_bot.controlla_iscrizioni() == [2]
    assert bot.config()["chat_ids"] == [1, 2]
    assert bot.config()["offset"] == 11
    assert bot.inviati == [(2, t("bot_benvenuto"))]


def test_start_ripetuto_non_duplica(bot):
    bot.coda = [messaggio(10, 1, "/start")]
    assert telegram_bot.controlla_iscrizioni() == []
    assert bot.config()["chat_ids"] == [1]


def test_stop_toglie_la_chat(bot):
    bot.coda = [messaggio(10, 1, "/stop")]
    telegram_bot.controlla_iscrizioni()
    assert bot.config()["chat_ids"] == []
    assert bot.inviati == [(1, t("bot_congedo"))]


def test_altri_messaggi_ricevono_aiuto(bot):
    bot.coda = [messaggio(10, 3, "ciao")]
    telegram_bot.controlla_iscrizioni()
    assert bot.config()["chat_ids"] == [1]
    assert bot.inviati == [(3, t("bot_aiuto"))]


def test_offset_salvato_tra_due_controlli(bot):
    bot.coda = [messaggio(10, 2, "/start")]
    telegram_bot.controlla_iscrizioni()
    telegram_bot.controlla_iscrizioni()
    assert bot.offset_chiesti == [0, 11]


def test_invia_a_tutti_e_toglie_chi_ha_bloccato(bot):
    telegram_bot.CONFIG.write_text(json.dumps({"token": "T", "chat_ids": [1, 2, 3]}))
    bot.bloccati = {2}
    telegram_bot.invia("<b>ciao</b>")
    assert [c for c, _ in bot.inviati] == [1, 3]
    assert bot.config()["chat_ids"] == [1, 3]


def test_migrazione_dal_vecchio_formato(bot):
    telegram_bot.CONFIG.write_text(json.dumps({"token": "T", "chat_id": 7}))
    telegram_bot.invia("x")
    assert bot.inviati == [(7, "x")]
    cfg = bot.config()
    assert cfg["chat_ids"] == [7] and "chat_id" not in cfg


def test_messaggio_troppo_lungo_troncato(bot):
    telegram_bot.invia("riga\n" * 2000)
    testo = bot.inviati[0][1]
    assert len(testo) <= telegram_bot.MAX_CARATTERI and testo.endswith("…")


def test_senza_configurazione_non_invia(bot):
    telegram_bot.CONFIG.unlink()
    telegram_bot.invia("x")
    assert bot.inviati == [] and not telegram_bot.configurato()


def test_permessi_del_file(bot):
    bot.coda = [messaggio(10, 2, "/start")]
    telegram_bot.controlla_iscrizioni()
    assert telegram_bot.CONFIG.stat().st_mode & 0o777 == 0o600
