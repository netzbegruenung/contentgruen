"""
Einladungen (#429): Ein Admin legt im Admin-Dashboard eine Einladung an (Notiz, Zahl
erlaubter Einloesungen, letzter gueltiger Tag), und wer den Link hat, legt damit selbst ein
Konto im Realm von Gut gesagt an. Gruppenlink und persoenlicher Link sind derselbe
Mechanismus, nur mit anderen Zahlen.

Ablauf beim Einloesen: einen Platz der Einladung belegen (atomar in der Datenbank),
dann das Konto ueber die Keycloak-Admin-Schnittstelle anlegen; Keycloak schickt die
Mail "Passwort festlegen". Scheitert Keycloak, wird der Platz wieder frei. Gibt es zur
Adresse schon ein Konto, bleibt er belegt: Der Zaehler zaehlt Einloesungen, nicht
angelegte Konten. Wuerde der Platz frei, verriete /pruefen danach, dass die Adresse ein
Konto hat (etwa bei einem persoenlichen Link mit einer fremden Adresse).

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
EINLOESUNGEN_MAX = 1000
# Laenger als ein Jahr gilt keine Einladung; wer mehr braucht, legt eine neue an.
GUELTIG_TAGE_MAX = 366
# 16 Bytes Zufall, URL-sicher kodiert: 22 Zeichen, nicht zu erraten.
CODE_BYTES = 16


class EinladungUngueltig(Exception):
    """Den Code gibt es nicht, oder die Einladung ist abgeschaltet, abgelaufen oder aufgebraucht."""


class EinloesenNichtEingerichtet(Exception):
    """Kein Zugang zur Keycloak-Admin-Schnittstelle konfiguriert."""


class KontoAnlegenFehlgeschlagen(Exception):
    """Keycloak hat das Konto nicht angelegt oder die Mail nicht verschickt."""


class KontoAnlegen(enum.Enum):
    ANGELEGT = "angelegt"
    # Zu der Mail-Adresse gibt es schon ein Konto; es wird nichts geaendert.
    VORHANDEN = "vorhanden"


class EinladungZustand(str, enum.Enum):
    AKTIV = "aktiv"
    ABGESCHALTET = "abgeschaltet"
    ABGELAUFEN = "abgelaufen"
    AUFGEBRAUCHT = "aufgebraucht"


class KontenImRealm(Protocol):
    def konto_anlegen(self, email: str) -> KontoAnlegen: ...


@dataclass(frozen=True)
class Einladung:
    id: uuid.UUID
    code: str
    notiz: str
    erlaubte_einloesungen: int
    einloesungen: int
    gueltig_bis: date
    abgeschaltet: bool
    angelegt_am: date

    @classmethod
    def aus_zeile(cls, z) -> "Einladung":
        return cls(
            z.id,
            z.code,
            z.notiz,
            z.erlaubte_einloesungen,
            z.einloesungen,
            z.gueltig_bis,
            z.abgeschaltet,
            z.angelegt_am,
        )

    def zustand(self, heute: Optional[date] = None) -> EinladungZustand:
        """Nur eine aktive Einladung laesst sich einloesen."""
        if self.abgeschaltet:
            return EinladungZustand.ABGESCHALTET
        if self.gueltig_bis < (heute or heute_utc()):
            return EinladungZustand.ABGELAUFEN
        if self.einloesungen >= self.erlaubte_einloesungen:
            return EinladungZustand.AUFGEBRAUCHT
        return EinladungZustand.AKTIV


class EinladungService:
    def __init__(
        self, repository: EinladungRepository, konten: Optional[KontenImRealm]
    ):
        self._repository = repository
        self._konten = konten

    @property
    def einloesen_eingerichtet(self) -> bool:
        return self._konten is not None

    def anlegen(
        self,
        notiz: str,
        erlaubte_einloesungen: int,
        gueltig_bis: date,
        heute: Optional[date] = None,
    ) -> Einladung:
        zeile = self._repository.anlegen(
            code=secrets.token_urlsafe(CODE_BYTES),
            notiz=notiz,
            erlaubte_einloesungen=erlaubte_einloesungen,
            gueltig_bis=gueltig_bis,
            angelegt_am=heute or heute_utc(),
        )
        return Einladung.aus_zeile(zeile)

    def alle(self) -> List[Einladung]:
        return [Einladung.aus_zeile(z) for z in self._repository.alle()]

    def schalten(
        self, einladung_id: uuid.UUID, abgeschaltet: bool
    ) -> Optional[Einladung]:
        """Ab- oder wieder einschalten; der Zaehler bleibt."""
        zeile = self._repository.schalten(einladung_id, abgeschaltet)
        return Einladung.aus_zeile(zeile) if zeile is not None else None

    def ist_einloesbar(self, code: str, heute: Optional[date] = None) -> bool:
        zeile = self._repository.nach_code(code)
        return (
            zeile is not None
            and Einladung.aus_zeile(zeile).zustand(heute) is EinladungZustand.AKTIV
        )

    def einloesen(self, code: str, email: str, heute: Optional[date] = None) -> None:
        """
        Legt ueber die Einladung ein Konto an. Gibt es zur Adresse schon eines, endet
        der Aufruf genauso und zaehlt genauso: Ob eine Adresse ein Konto hat, erfaehrt
        hier niemand.
        """
        if self._konten is None:
            raise EinloesenNichtEingerichtet()
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
            logger.info("Invitation redeemed for an existing account")
        else:
            logger.info("Account created via invitation")
