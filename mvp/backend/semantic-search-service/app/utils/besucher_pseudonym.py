"""
Tagespseudonym der Besucher: wer nicht angemeldet ist, wird am Server erkannt,
nicht ueber eine Kennung im Browser (#446).

Bis #446 erzeugte die SPA eine Sitzungskennung, legte sie fuer 30 Tage in
localStorage ab und schickte sie als X-Session-Id mit. Daraus wurde das
Tagespseudonym der Besucher gebildet. Jetzt bildet es der Server aus dem, was
jede Anfrage ohnehin mitbringt:

- der Adresse (X-Real-IP hinter nginx, siehe utils/client_identity.py), bei IPv6
  ihr /64, weil Datenschutz-Erweiterungen die Adresse darin laufend wechseln;
- dem User-Agent;
- dem UTC-Tag.

Darueber ein HMAC mit einem Schluessel, den Tagesschluessel je Tag zufaellig
erzeugt und nur im Speicher haelt. Mit dem Tag wechselt der Schluessel, der alte
ist danach weg. Zwei Folgen, beide gewollt:

- Pseudonyme verschiedener Tage lassen sich nicht verknuepfen, auch nicht von
  jemandem, der Datenbank und Konfiguration hat: den Schluessel gibt es nirgends.
- Aus einem gespeicherten Pseudonym laesst sich die Adresse nicht zurueckrechnen,
  auch nicht durch Durchprobieren aller IPv4-Adressen.

Der Preis: Nach einem Neustart am selben Tag hat derselbe Besucher ein anderes
Pseudonym und zaehlt ein zweites Mal. Der Schluessel setzt einen uvicorn-Worker
voraus wie die Merkliste der Suchen ohne Treffer; mit mehreren Workern zaehlte
ein Besucher je Worker.

Adresse und User-Agent werden dabei weder gespeichert noch geloggt; das
Merkmal existiert nur innerhalb der Anfrage.
"""

import hashlib
import hmac
import secrets
from datetime import date
from typing import Optional

from fastapi import Request

from utils.client_identity import anschluss, get_client_address


class Tagesschluessel:
    """Ein zufaelliger Schluessel je UTC-Tag, nur im Prozessspeicher."""

    def __init__(self):
        self._tag: Optional[date] = None
        self._schluessel = b""

    def fuer(self, tag: date) -> bytes:
        """
        Der Schluessel des Tages.

        Ein neuer Tag ersetzt den Schluessel. Fragt danach noch jemand nach dem
        vergangenen Tag (eine Anfrage, die vor Mitternacht begann), bekommt er einen
        Einmalschluessel: Der alte kommt nicht zurueck, und der laufende Tag bleibt.
        """
        if self._tag is None or tag > self._tag:
            self._tag = tag
            self._schluessel = secrets.token_bytes(32)
        elif tag < self._tag:
            return secrets.token_bytes(32)
        return self._schluessel


_TAGESSCHLUESSEL = Tagesschluessel()


def besucher_merkmal(request: Request) -> str:
    """
    Was einen Besucher an einem Tag ausmacht: Anschluss und User-Agent.

    Ein X-Session-Id-Header wird nicht mehr beachtet. Ohne lesbare Adresse teilen
    sich alle Aufrufer mit demselben User-Agent ein Merkmal; sie zaehlen dann als
    eine Person, was die sichere Richtung ist.
    """
    adresse = get_client_address(request)
    teil = anschluss(adresse) if adresse else "unknown"
    return f"{teil}|{request.headers.get('User-Agent', '')}"


def besucher_tagespseudonym(merkmal: str, tag: date) -> str:
    """
    HMAC-SHA256 ueber Merkmal und Tag mit dem Schluessel des Tages, 64 Hex-Zeichen.

    Der prozessweite Schluessel wird erst beim Aufruf nachgeschlagen, damit Tests
    ihn je Test ersetzen koennen (tests/conftest.py).
    """
    return hmac.new(
        _TAGESSCHLUESSEL.fuer(tag),
        f"{merkmal}|{tag.isoformat()}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
