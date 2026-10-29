"""
Pruefwerte fuer die entdoppelte Nutzung (ADR 0004, #352).

Fuer Punkte und "Diese Woche oft genutzt" zaehlt eine Nutzung hoechstens einmal je
Person (bei Besuchern je Sitzung), Beitrag und Tag. Dafuer muss sich der Dienst einen
Tag lang merken, dass diese Person diesen Beitrag schon genutzt hat, ohne festzuhalten,
wer was genutzt hat (DSFA zu #374, Massnahme M2). Gemerkt wird deshalb nur ein
Pruefwert: ein HMAC ueber das Tagespseudonym (GLOSSARY.md) und den Beitrag. Ohne den
geheimen Schluessel laesst er sich weder auf die Person noch auf den Beitrag
zurueckfuehren, und am naechsten Tag passt er zu nichts mehr. Die Tabelle
``nutzung_heute`` verwirft der taegliche Lauf (services/muster_hinweise_service.py).

Der Paar-Pruefwert dient den Muster-Hinweisen: Er merkt sich fuer einen Tag, dass ein
Konto ein Beitrag eines anderen genutzt hat, ebenfalls nur als HMAC.
"""

import hashlib
import hmac
import uuid
from datetime import datetime
from typing import Optional

from services.search_tracking_service import pseudonym_schluessel, tagespseudonym

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


def paar_pruefwert(
    nutzende: str, autor: str, moment: Optional[datetime] = None
) -> Optional[str]:
    """Der Pruefwert fuer "``nutzende`` hat heute einen Beitrag von ``autor`` genutzt"."""
    von = tagespseudonym(user_id=nutzende, moment=moment)
    an = tagespseudonym(user_id=autor, moment=moment)
    if von is None or an is None:
        return None
    return _hmac(f"paar|{von}|{an}")
