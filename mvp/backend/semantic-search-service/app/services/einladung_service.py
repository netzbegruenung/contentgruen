"""
Einladungen (#429): Ein Admin legt im Admin-Dashboard eine Einladung an (Notiz, Zahl
erlaubter Einloesungen, letzter gueltiger Tag), und wer den Link hat, legt damit selbst ein
Konto im Realm von Gut gesagt an. Gruppenlink und persoenlicher Link sind derselbe
Mechanismus, nur mit anderen Zahlen.

Ablauf beim Einloesen: die Einloesung zaehlen (atomar in der Datenbank, nur solange
die Einladung aktiv ist), dann das Konto ueber die Keycloak-Admin-Schnittstelle
anlegen; Keycloak schickt die Mail "Passwort festlegen". Scheitert Keycloak, wird die
Einloesung zurueckgenommen. Gibt es zur Adresse schon ein Konto, bleibt sie gezaehlt:
Der Zaehler zaehlt Einloesungen, nicht angelegte Konten. Wuerde sie zurueckgenommen,
verriete /pruefen danach, dass die Adresse ein Konto hat (etwa bei einem persoenlichen
Link mit einer fremden Adresse). Auch eine Adresse mit Tippfehler zaehlt; das Konto
entsteht dann fuer sie, und die Mail geht dorthin.

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
from typing import List, Optional

from core.logging import get_logger
from domain.interfaces.konten_im_realm import IKontenImRealm, KontoErgebnis
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


class EinladungZustand(str, enum.Enum):
    AKTIV = "aktiv"
    ABGESCHALTET = "abgeschaltet"
    ABGELAUFEN = "abgelaufen"
    AUFGEBRAUCHT = "aufgebraucht"


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
            id=z.id,
            code=z.code,
            notiz=z.notiz,
            erlaubte_einloesungen=z.erlaubte_einloesungen,
            einloesungen=z.einloesungen,
            gueltig_bis=z.gueltig_bis,
            abgeschaltet=z.abgeschaltet,
            angelegt_am=z.angelegt_am,
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
        self, repository: EinladungRepository, konten: Optional[IKontenImRealm]
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
        if not self._repository.einloesung_zaehlen(code, heute or heute_utc()):
            raise EinladungUngueltig()
        try:
            ergebnis = self._konten.konto_anlegen(email)
        except Exception as e:
            self._repository.einloesung_zuruecknehmen(code)
            # Ohne Adresse und Code, nur die Art des Fehlers.
            logger.error(f"Creating account via invitation failed: {type(e).__name__}")
            raise KontoAnlegenFehlgeschlagen() from e
        if ergebnis is KontoErgebnis.VORHANDEN:
            logger.info("Invitation redeemed for an existing account")
        else:
            logger.info("Account created via invitation")
