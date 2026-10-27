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
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import unquote

from repositories.user_repository import UserRepository, get_user_repository

logger = logging.getLogger(__name__)

ANONYM = "anonymous"
MAX_LAENGE = 100

# Platzhalter fuer die Kennung einer Person, die ihr Konto geloescht hat, an ihren
# Beitraegen (Loeschkonzept Schritt 3, services/wartung/beitraege_anonymisieren.py).
# Ein gemeinsamer fuer alle Geloeschten: Er verbindet nichts, was nicht schon jede
# andere geloeschte Person teilt. Der Name kommt von hier, nicht aus users - so
# braucht der Platzhalter keine Zeile, die ein Loeschlauf mit abraeumen koennte.
# Saetze im Fangkorb tragen stattdessen je einen eigenen "ehemalige-person-<UUID>"
# mit Zeile in users (mvp/scripts/manual/person_loeschen.sql). Kennung und Praefix
# sind reserviert: Das BFF lehnt Beta-Zugaenge damit ab (ManagedUserService.cs,
# EhemaligePersonKennung) - wer sie hier aendert, aendert sie dort mit.
EHEMALIGE_PERSON_KENNUNG = "ehemalige-person"
EHEMALIGE_PERSON_NAME = "ehemalige Person"


# Was an einem Beitrag eine Person bezeichnet: zwei Felder mit der Kennung und zwei
# Listen, deren Eintraege sie unter dem genannten Schluessel tragen. Geleert fuer
# anonyme Aufrufer (kennungsfelder_leer), ersetzt im Loeschkonzept Schritt 3
# (services/wartung/beitraege_anonymisieren.py).
KENNUNGSFELDER = ("original_author", "last_modified_by")
KENNUNGSLISTEN = (("authors", "name"), ("edit_history", "editor"))


def kennungsfelder_leer() -> Dict[str, Any]:
    """
    Was an einem Beitrag eine Person bezeichnet, geleert - fuer anonyme Aufrufer.
    Leer statt entfernt, weil das Schema die Felder als Pflicht fuehrt; jedes Mal
    frisch, damit sich keine zwei Antworten eine Liste teilen.
    """
    return {
        **{feld: "" for feld in KENNUNGSFELDER},
        **{liste: [] for liste, _ in KENNUNGSLISTEN},
    }


def angemeldet(user_id: Optional[str]) -> bool:
    """Namen gehen nur an angemeldete Aufrufer; "anonymous" ist die Kennung des BFF fuer niemanden."""
    return bool(user_id) and user_id != ANONYM


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
        if not angemeldet(user_id) or user_id == EHEMALIGE_PERSON_KENNUNG:
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
        """
        Kennung -> Anzeigename, eine Abfrage fuer alle. Scheitert die Abfrage,
        kommt die Antwort ohne Namen - die Karte zeigt dann "Mitglied". Der
        Platzhalter einer geloeschten Person heisst immer "ehemalige Person".
        """
        user_ids = set(user_ids)
        try:
            namen = dict(self._repository.anzeigenamen(user_ids))
        except Exception as e:
            logger.warning(
                f"Anzeigenamen konnten nicht gelesen werden: {type(e).__name__}"
            )
            namen = {}
        if EHEMALIGE_PERSON_KENNUNG in user_ids:
            namen[EHEMALIGE_PERSON_KENNUNG] = EHEMALIGE_PERSON_NAME
        return namen

    def mit_autor_name(self, inhalt) -> Dict[str, Any]:
        """Ein einzelner Beitrag als Antwort-Dict mit ``autor_name`` daneben."""
        antwort = inhalt.model_dump(mode="json")
        self.an_eintraege([antwort])
        return antwort

    def an_eintraege(
        self,
        eintraege: List[Dict[str, Any]],
        kennung: str = "original_author",
        feld: str = "autor_name",
    ) -> None:
        """Je Eintrag ``feld`` aus ``kennung`` setzen, eine Abfrage fuer alle."""
        namen = self.namen(eintrag.get(kennung) for eintrag in eintraege)
        for eintrag in eintraege:
            eintrag[feld] = namen.get(eintrag.get(kennung))

    def fuer_aufrufer(
        self, aufrufer: Optional[str], beitraege: List[Dict[str, Any]]
    ) -> None:
        """
        Beitraege fuer eine Liste aufbereiten: Angemeldete bekommen den
        Anzeigenamen dazu, Besucher weder Namen noch Kennungen.
        """
        if angemeldet(aufrufer):
            self.an_eintraege(beitraege)
        else:
            for beitrag in beitraege:
                beitrag.update(kennungsfelder_leer())


_anzeigename_service: Optional[AnzeigenameService] = None


def get_anzeigename_service() -> AnzeigenameService:
    global _anzeigename_service
    if _anzeigename_service is None:
        _anzeigename_service = AnzeigenameService(get_user_repository())
    return _anzeigename_service
