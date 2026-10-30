"""
Pruefwerte fuer die entdoppelte Nutzung (ADR 0004, #352).

Fuer Punkte und "Diese Woche oft genutzt" zaehlt eine Nutzung hoechstens einmal je
Person (bei Besuchern je Sitzung), Beitrag und Tag. Dafuer muss sich der Dienst einen
Tag lang merken, dass diese Person diesen Beitrag schon genutzt hat, ohne festzuhalten,
wer was genutzt hat (DSFA zu #374, Massnahme M2). Gemerkt wird deshalb nur ein
Pruefwert: ein HMAC ueber das Tagespseudonym (GLOSSARY.md) und den Beitrag. Ohne den
geheimen Schluessel laesst er sich weder auf die Person noch auf den Beitrag
zurueckfuehren, und am naechsten Tag passt er zu nichts mehr. Die Tabelle
``nutzung_heute`` verwirft pruefwerte_verwerfen_im_takt, ein eigener Hintergrund-Task
aus main.py, nach jedem Tageswechsel (UTC).

Der Paar-Pruefwert dient den Muster-Hinweisen: Er merkt sich sieben Tage lang, dass
ein Konto einen Beitrag eines anderen genutzt hat (welchen, steht nirgends), ebenfalls
nur als HMAC, hier aber ueber beide Kennungen statt ueber Tagespseudonyme: Er muss
gleich bleiben, solange das Fenster laeuft (services/muster_hinweise_service.py).
"""

import asyncio
import hashlib
import hmac
import uuid
from datetime import datetime
from typing import Optional

from core.logging import get_logger
from repositories.usage_tracking_repository import UsageTrackingRepository
from services.search_tracking_service import pseudonym_schluessel, tagespseudonym
from utils.utc_tag import sekunden_bis_mitternacht

logger = get_logger(__name__)

ANONYM = "anonymous"


def _hmac(text: str) -> str:
    # Derselbe Schluessel wie beim Tagespseudonym; ohne Konfiguration der
    # Zufallsschluessel des Prozesses (nach einem Neustart zaehlt eine Nutzung am
    # selben Tag dann noch einmal).
    return hmac.new(
        pseudonym_schluessel().encode("utf-8"), text.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def pruefwert(
    user_id: Optional[str],
    session_id: Optional[str],
    content_id: uuid.UUID,
    moment: Optional[datetime] = None,
) -> Optional[str]:
    """
    Der Pruefwert dieser Nutzung: gleich fuer dieselbe Person (angemeldet: Kennung,
    sonst Sitzung) und denselben Beitrag am selben UTC-Tag. None, wenn niemand zu
    erkennen ist; eine solche Nutzung laesst sich nicht entdoppeln und zaehlt nur am
    Zaehler der Karte.
    """
    person = user_id if user_id and user_id != ANONYM else None
    pseudonym = tagespseudonym(user_id=person, session_id=session_id, moment=moment)
    if pseudonym is None:
        return None
    return _hmac(f"nutzung|{pseudonym}|{content_id}")


def paar_pruefwert(nutzende: str, autor: str) -> str:
    """Der Pruefwert fuer "``nutzende`` hat einen Beitrag von ``autor`` genutzt"."""
    return _hmac(f"paar|{nutzende}|{autor}")


async def pruefwerte_verwerfen_im_takt(
    nutzung: UsageTrackingRepository, takt_sekunden: Optional[float] = None
) -> None:
    """
    Hintergrund-Task: verwirft die Pruefwerte vergangener Tage sofort und dann nach
    jedem Tageswechsel (UTC), bis er abgebrochen wird. Laeuft unabhaengig von Punkten
    und Usage-Cleanup: Die Entdoppelung wirkt immer.
    """
    while True:
        try:
            verworfen = await asyncio.to_thread(nutzung.vergangene_tage_verwerfen)
            logger.info(f"Discarded {verworfen} check values of past days")
        except Exception as e:
            logger.error(f"Error discarding check values: {e}", exc_info=True)
        await asyncio.sleep(
            sekunden_bis_mitternacht() + 1 if takt_sekunden is None else takt_sekunden
        )
