"""Blocco esclusivo di un file, uguale su macOS, Linux e Windows.

Serve per non far girare due istanze con gli stessi parametri e perche' piu' istanze
modificano telegram.json. Su macOS e Linux usa fcntl.flock, su Windows msvcrt.locking.
Il blocco si libera da solo quando il file viene chiuso (anche se il programma termina).
"""

import sys
import time

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


def blocca(f, attendi=True):
    """Blocca il file aperto f. Con attendi=False, BlockingIOError se e' gia' bloccato."""
    if sys.platform != "win32":
        fcntl.flock(f, fcntl.LOCK_EX if attendi else fcntl.LOCK_EX | fcntl.LOCK_NB)
        return
    f.seek(0)
    while True:
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            return
        except OSError:
            if not attendi:
                raise BlockingIOError from None
            time.sleep(0.1)
