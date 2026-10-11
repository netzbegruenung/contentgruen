"""
Anzeigenamen aus dem BFF-Header ablegen und fuer Antworten nachschlagen.

Das BFF leitet den Namen aus den Claims ab ("Anna B.") und schickt ihn bei jedem
Request angemeldeter Personen prozentkodiert in X-User-Display-Name. Abgelegt wird
nur, wenn er sich gegenueber dem Prozess-Cache geaendert hat - also einmal je
Person und Prozessstart, nicht bei jedem Request. Der Dienst laeuft mit einem
Worker (Dockerfile), der Cache ist damit der einzige.

Fehlt der Header, bleibt ein gespeicherter Name stehen: Das ist auch der Fall
eines BFF ohne diese Funktion, und der soll nichts loeschen.
"""

import logging
import unicodedata
from typing import Dict, Iterable, Optional
from urllib.parse import unquote

from repositories.user_repository import UserRepository, get_user_repository

logger = logging.getLogger(__name__)

ANONYM = "anonymous"
MAX_LAENGE = 100


def anzeigename_aus_header(roh: Optional[str]) -> Optional[str]:
    """
    Den Header dekodieren. Was sich nicht als UTF-8 lesen laesst, leer ist oder
    nur aus Steuerzeichen besteht, ist kein Name.
    """
    if not roh:
        return None
    try:
        name = unquote(roh, errors="strict")
    except UnicodeDecodeError:
        return None
    name = "".join(z for z in name if unicodedata.category(z)[0] != "C")
    name = " ".join(name.split())[:MAX_LAENGE].strip()
    return name or None


class AnzeigenameService:
    def __init__(self, repository: UserRepository):
        self._repository = repository
        self._bekannt: Dict[str, str] = {}

    def merken(self, user_id: Optional[str], roh: Optional[str]) -> None:
        """Den Namen aus dem Header ablegen, falls er neu ist. Wirft nie."""
        if not user_id or user_id == ANONYM:
            return
        name = anzeigename_aus_header(roh)
        if name is None or self._bekannt.get(user_id) == name:
            return
        try:
            self._repository.anzeigename_speichern(user_id, name)
        except Exception as e:
            # Ohne Namen und ohne Kennung im Log: der naechste Request versucht es neu.
            logger.warning(
                f"Anzeigename konnte nicht gespeichert werden: {type(e).__name__}"
            )
            return
        self._bekannt[user_id] = name

    def namen(self, user_ids: Iterable[Optional[str]]) -> Dict[str, str]:
        """Kennung -> Anzeigename, eine Abfrage fuer alle."""
        return self._repository.anzeigenamen(user_ids)


_anzeigename_service: Optional[AnzeigenameService] = None


def get_anzeigename_service() -> AnzeigenameService:
    global _anzeigename_service
    if _anzeigename_service is None:
        _anzeigename_service = AnzeigenameService(get_user_repository())
    return _anzeigename_service
