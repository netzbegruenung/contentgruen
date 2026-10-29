"""
Einladungen (#429): Ein Admin legt im Admin-Dashboard eine Einladung an (Notiz, Zahl
erlaubter Konten, letzter gueltiger Tag), und wer den Link hat, legt damit selbst ein
Konto im Realm von Gut gesagt an. Gruppenlink und persoenlicher Link sind derselbe
Mechanismus, nur mit anderen Zahlen.

Ablauf beim Einloesen: einen Platz der Einladung belegen (atomar in der Datenbank),
dann das Konto ueber die Keycloak-Admin-Schnittstelle anlegen; Keycloak schickt die
Mail "Passwort festlegen". Scheitert Keycloak oder gibt es das Konto schon, wird der
Platz wieder frei: Der Zaehler zaehlt nur Konten, die ueber die Einladung entstanden.

Datenschutz: Am Konto steht nicht, ueber welche Einladung es entstand, und an der
Einladung keine Mail-Adresse, nur der Zaehler. Sonst liesse sich aus einer Einladung
etwa fuer eine bestimmte Gruppe die Zugehoerigkeit einer Person ableiten (Art. 9
DSGVO). Keycloak bekommt deshalb nie den Code, die Datenbank nie die Mail-Adresse,
und keine Logzeile nennt eines von beiden.
"""

import enum
import secrets
import uuid
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Protocol

from core.logging import get_logger
from repositories.einladung_repository import EinladungRepository
from utils.utc_tag import heute_utc

logger = get_logger(__name__)

NOTIZ_MAX = 200
ERLAUBTE_KONTEN_MAX = 1000
# Laenger als ein Jahr gilt keine Einladung; wer mehr braucht, legt eine neue an.
GUELTIG_TAGE_MAX = 366
# 16 Bytes Zufall, URL-sicher kodiert: 22 Zeichen, nicht zu erraten.
CODE_BYTES = 16


class EinladungUngueltig(Exception):
    """Den Code gibt es nicht, oder die Einladung ist abgeschaltet, abgelaufen oder aufgebraucht."""


class RegistrierungNichtEingerichtet(Exception):
    """Kein Zugang zur Keycloak-Admin-Schnittstelle konfiguriert."""


class KontoAnlegenFehlgeschlagen(Exception):
    """Keycloak hat das Konto nicht angelegt oder die Mail nicht verschickt."""


class KontoAnlegen(enum.Enum):
    ANGELEGT = "angelegt"
    # Zu der Mail-Adresse gibt es schon ein Konto; es wird nichts geaendert.
    VORHANDEN = "vorhanden"


class KeycloakKonten(Protocol):
    def konto_anlegen(self, email: str) -> KontoAnlegen: ...


@dataclass(frozen=True)
class Einladung:
    id: uuid.UUID
    code: str
    notiz: str
    erlaubte_konten: int
    angelegte_konten: int
    gueltig_bis: date
    abgeschaltet: bool
    angelegt_am: date

    @classmethod
    def aus_zeile(cls, z) -> "Einladung":
        return cls(
            z.id,
            z.code,
            z.notiz,
            z.erlaubte_konten,
            z.angelegte_konten,
            z.gueltig_bis,
            z.abgeschaltet,
            z.angelegt_am,
        )

    def zustand(self, heute: Optional[date] = None) -> str:
        """aktiv, abgeschaltet, abgelaufen oder aufgebraucht; nur "aktiv" laesst ein Konto anlegen."""
        if self.abgeschaltet:
            return "abgeschaltet"
        if self.gueltig_bis < (heute or heute_utc()):
            return "abgelaufen"
        if self.angelegte_konten >= self.erlaubte_konten:
            return "aufgebraucht"
        return "aktiv"


class EinladungService:
    def __init__(
        self, repository: EinladungRepository, konten: Optional[KeycloakKonten]
    ):
        self._repository = repository
        self._konten = konten

    @property
    def registrierung_eingerichtet(self) -> bool:
        return self._konten is not None

    def anlegen(
        self,
        notiz: str,
        erlaubte_konten: int,
        gueltig_bis: date,
        heute: Optional[date] = None,
    ) -> Einladung:
        zeile = self._repository.anlegen(
            code=secrets.token_urlsafe(CODE_BYTES),
            notiz=notiz,
            erlaubte_konten=erlaubte_konten,
            gueltig_bis=gueltig_bis,
            angelegt_am=heute or heute_utc(),
        )
        return Einladung.aus_zeile(zeile)

    def alle(self) -> List[Einladung]:
        return [Einladung.aus_zeile(z) for z in self._repository.alle()]

    def abschalten(
        self, einladung_id: uuid.UUID, abgeschaltet: bool
    ) -> Optional[Einladung]:
        zeile = self._repository.abschalten(einladung_id, abgeschaltet)
        return Einladung.aus_zeile(zeile) if zeile is not None else None

    def ist_einloesbar(self, code: str, heute: Optional[date] = None) -> bool:
        zeile = self._repository.nach_code(code)
        return (
            zeile is not None and Einladung.aus_zeile(zeile).zustand(heute) == "aktiv"
        )

    def einloesen(self, code: str, email: str, heute: Optional[date] = None) -> None:
        """
        Legt ueber die Einladung ein Konto an. Gibt es zur Adresse schon eines, endet
        der Aufruf genauso still: Ob eine Adresse ein Konto hat, erfaehrt hier niemand.
        """
        if self._konten is None:
            raise RegistrierungNichtEingerichtet()
        if not self._repository.platz_belegen(code, heute or heute_utc()):
            raise EinladungUngueltig()
        try:
            ergebnis = self._konten.konto_anlegen(email)
        except Exception as e:
            self._repository.platz_freigeben(code)
            # Ohne Adresse und Code, nur die Art des Fehlers.
            logger.error(f"Creating account via invitation failed: {type(e).__name__}")
            raise KontoAnlegenFehlgeschlagen() from e
        if ergebnis is KontoAnlegen.VORHANDEN:
            self._repository.platz_freigeben(code)
            logger.info("Invitation redeemed for an existing account; not counted")
        else:
            logger.info("Account created via invitation")
