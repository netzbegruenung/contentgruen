"""
Pruefwerte fuer die entdoppelte Nutzung (ADR 0004, #352).

Fuer Punkte und "Diese Woche oft genutzt" zaehlt eine Nutzung hoechstens einmal je
Person (bei Besuchern je Besuchermerkmal, #446), Beitrag und Tag. Dafuer muss sich der
Dienst einen Tag lang merken, dass diese Person diesen Beitrag schon genutzt hat, ohne
festzuhalten, wer was genutzt hat (DSFA zu #374, Massnahme M2). Gemerkt wird deshalb
nur ein Pruefwert: ein HMAC ueber Person, Beitrag und Tag.

Die Schluessel liegen nur im Speicher, nach dem Muster des Tagesschluessels der
Besucher (utils/besucher_pseudonym.py), und haben keinen Bezug zu
SEMANTIC_SEARCH_ACTOR_HASH_SECRET (BanSe/todo#266, DSFA Risiko 2): Wer Datenbank und
Konfiguration hat, kann einen Pruefwert nicht nachrechnen, auch nicht fuer eine
bekannte Person und einen bekannten Beitrag. Der Preis, laut DSFA hinnehmbar: Nach
einem Neustart zaehlt eine Nutzung am selben Tag ein zweites Mal, und ein Muster
beginnt neu. Wie beim Tagesschluessel setzt das einen uvicorn-Worker voraus.

- Pruefwert (Tabelle ``nutzung_heute``): Schluessel je UTC-Tag (Tagesschluessel).
  pruefwerte_verwerfen_im_takt, ein eigener Hintergrund-Task aus main.py, verwirft
  die Zeilen nach jedem Tageswechsel; danach passt ohnehin keine mehr.
- Paar-Pruefwert (Tabelle ``muster_pruefwerte``) fuer die Muster-Hinweise
  (services/muster_hinweise_service.py): Er muss MUSTER_FENSTER_TAGE lang
  vergleichbar bleiben. Ein Tagesschluessel reicht dafuer nicht, ein Schluessel fuer
  die ganze Laufzeit hielte Werte unbegrenzt nachrechenbar. Deshalb ein
  Fensterschluessel: neu je Block von MUSTER_FENSTER_TAGE Tagen, der vorige bleibt
  einen Block lang zum Vergleich. Sieben aufeinanderfolgende Tage beruehren hoechstens
  zwei Bloecke, also liegt jeder Wert aus dem Fenster unter dem aktuellen oder dem
  vorigen Schluessel. Gemerkt wird mit dem aktuellen, verglichen mit beiden
  (paar_pruefwerte_im_fenster); nach zwei Bloecken ist ein Schluessel weg.
"""

import asyncio
import hashlib
import hmac
import secrets
import threading
import uuid
from datetime import date, datetime, timezone
from typing import Callable, List, Optional, Tuple

from core.logging import get_logger
from repositories.usage_tracking_repository import UsageTrackingRepository
from utils.aufrufer import ANONYM
from utils.besucher_pseudonym import Tagesschluessel
from utils.utc_tag import sekunden_bis_mitternacht

logger = get_logger(__name__)

MUSTER_FENSTER_TAGE = 7
"""So viele Tage (der heutige eingeschlossen) duerfen zwischen A->B und B->A liegen."""


class Fensterschluessel:
    """
    Ein zufaelliger Schluessel je Block von ``tage`` Tagen, nur im Prozessspeicher;
    der des vorigen Blocks bleibt bis zum naechsten Wechsel.
    """

    def __init__(self, tage: int):
        self._tage = tage
        self._block: Optional[int] = None
        self._aktuell = b""
        self._vorig: Optional[bytes] = None
        self._lock = threading.Lock()

    def fuer(self, tag: date) -> Tuple[bytes, Optional[bytes]]:
        """
        Schluessel des Blocks von ``tag`` und der des vorigen (None, wenn es ihn im
        Speicher nicht gibt). Ein vergangener Block bekommt wie beim Tagesschluessel
        einen Einmalschluessel: Verworfene Schluessel kommen nicht zurueck.
        """
        block = tag.toordinal() // self._tage
        with self._lock:
            if self._block is None or block > self._block:
                folgt = self._block is not None and block == self._block + 1
                self._vorig = self._aktuell if folgt else None
                self._aktuell = secrets.token_bytes(32)
                self._block = block
            elif block < self._block:
                return secrets.token_bytes(32), None
            return self._aktuell, self._vorig


_NUTZUNG_SCHLUESSEL = Tagesschluessel()
_PAAR_SCHLUESSEL = Fensterschluessel(tage=MUSTER_FENSTER_TAGE)


def _hmac(schluessel: bytes, text: str) -> str:
    return hmac.new(schluessel, text.encode("utf-8"), hashlib.sha256).hexdigest()


def pruefwert(
    user_id: Optional[str],
    besucher_merkmal: Optional[str],
    content_id: uuid.UUID,
    moment: Optional[datetime] = None,
) -> Optional[str]:
    """
    Der Pruefwert dieser Nutzung: gleich fuer dieselbe Person (angemeldet: Kennung,
    sonst Besuchermerkmal, utils/besucher_pseudonym.py) und denselben Beitrag am
    selben UTC-Tag, solange der Prozess laeuft. None, wenn niemand zu erkennen ist;
    eine solche Nutzung laesst sich nicht entdoppeln und zaehlt nur am Zaehler der
    Karte.
    """
    if user_id and user_id != ANONYM:
        person = f"konto:{user_id}"
    elif besucher_merkmal:
        person = f"besucher:{besucher_merkmal}"
    else:
        return None
    tag = (moment or datetime.now(timezone.utc)).astimezone(timezone.utc).date()
    return _hmac(
        _NUTZUNG_SCHLUESSEL.fuer(tag),
        f"nutzung|{person}|{content_id}|{tag.isoformat()}",
    )


def paar_pruefwert(nutzende: str, autor: str, tag: date) -> str:
    """
    Der Pruefwert fuer "``nutzende`` hat einen Beitrag von ``autor`` genutzt", wie er
    an ``tag`` gemerkt wird (Schluessel des laufenden Blocks).
    """
    aktuell, _ = _PAAR_SCHLUESSEL.fuer(tag)
    return _hmac(aktuell, f"paar|{nutzende}|{autor}")


def paar_pruefwerte_im_fenster(nutzende: str, autor: str, tag: date) -> List[str]:
    """
    Alle Werte, unter denen "``nutzende`` hat einen Beitrag von ``autor`` genutzt"
    seit ``tag`` - MUSTER_FENSTER_TAGE + 1 gemerkt sein kann: mit dem aktuellen und,
    falls noch im Speicher, dem vorigen Schluessel.
    """
    return [
        _hmac(schluessel, f"paar|{nutzende}|{autor}")
        for schluessel in _PAAR_SCHLUESSEL.fuer(tag)
        if schluessel is not None
    ]


async def pruefwerte_verwerfen_im_takt(
    nutzung: UsageTrackingRepository,
    takt_sekunden: Optional[float] = None,
    gepostet: Optional[Callable[[], None]] = None,
) -> None:
    """
    Hintergrund-Task: verwirft die Pruefwerte vergangener Tage sofort und dann nach
    jedem Tageswechsel (UTC), bis er abgebrochen wird. Laeuft unabhaengig von Punkten
    und Usage-Cleanup: Die Entdoppelung wirkt immer.

    ``gepostet``: verdichtet die Pruefwerte "Ja, gepostet" vergangener Wochen (#643),
    unabhaengig vom Schalter, damit sie auch ohne neue Meldung nach ihrer Woche weg sind.
    """
    while True:
        try:
            verworfen = await asyncio.to_thread(nutzung.vergangene_tage_verwerfen)
            logger.info(f"Discarded {verworfen} check values of past days")
        except Exception as e:
            logger.error(
                f"Error discarding check values: {type(e).__name__}", exc_info=True
            )
        if gepostet is not None:
            try:
                await asyncio.to_thread(gepostet)
            except Exception as e:
                logger.error(
                    f"Error condensing Gepostet check values: {type(e).__name__}",
                    exc_info=True,
                )
        await asyncio.sleep(
            sekunden_bis_mitternacht() + 1 if takt_sekunden is None else takt_sekunden
        )
