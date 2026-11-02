"""
Was die meldende Person per Mail erfaehrt (#493, Glossar "Meldung").

Art. 16 Abs. 4 DSA: Wer bei der Meldung eine E-Mail-Adresse angibt, bekommt den
Eingang bestaetigt. Abs. 5: Sie erfaehrt die Entscheidung ueber die Meldung und
ihre Moeglichkeiten, dagegen vorzugehen; Abs. 6: ob automatisiert entschieden
wurde (bei Gut gesagt nie, NB Abschnitt 7).

Die Mails enthalten nur festen Text und den Titel des gemeldeten Beitrags, nichts
aus der Meldung selbst: Die Melde-Route ist ohne Anmeldung offen, und wer eine
fremde Adresse eintraegt, soll darueber keinen eigenen Text verschicken koennen.

Ein gescheiterter Versand aendert an Meldung und Entscheidung nichts; er steht im
Log, ohne Adresse.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from infrastructure.mail.versand import (
    Mail,
    MailNichtVerschickt,
    Mailversand,
    get_mailversand,
)
from core.config import settings

logger = logging.getLogger(__name__)

# Laenger wird der Titel in der Mail nicht; Titel von Kommentaren haben hoechstens
# 120 Zeichen, Bildtitel 200 und Posts gar keinen (dann der Anfang des Texts).
TITEL_HOECHSTENS = 120

MONATE = (
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)


class Entscheidung(Enum):
    """Wie eine Meldung erledigt wurde."""

    GESPERRT = "gesperrt"
    ABGEWIESEN = "abgewiesen"
    # Ein Admin hat den Beitrag endgueltig entfernt.
    ENTFERNT = "entfernt"
    # Die Loeschfrist hat den Beitrag entfernt (etwa nachdem sein Autor ihn
    # geloescht hat); niemand hat ueber die Meldung entschieden.
    NICHT_MEHR_DA = "nicht_mehr_da"


ERGEBNIS = {
    Entscheidung.GESPERRT: (
        "wir haben den Beitrag geprüft und gesperrt. Er ist in Suche und Ansicht "
        "nicht mehr zu sehen."
    ),
    Entscheidung.ABGEWIESEN: (
        "wir haben den Beitrag geprüft und nicht gesperrt: Wir sehen darin weder einen "
        "Verstoß gegen unsere Nutzungsbedingungen noch einen rechtswidrigen Inhalt. "
        "Der Beitrag bleibt sichtbar."
    ),
    Entscheidung.ENTFERNT: (
        "wir haben den Beitrag geprüft und endgültig von Gut gesagt entfernt."
    ),
    Entscheidung.NICHT_MEHR_DA: (
        "der Beitrag ist inzwischen nicht mehr auf Gut gesagt; er wurde gelöscht, "
        "bevor wir über deine Meldung entschieden haben. Deine Meldung ist damit "
        "erledigt."
    ),
}

VON_MENSCHEN = (
    "Entschieden haben Menschen aus unserem Team, kein automatisiertes System."
)

RECHTSBEHELFE = (
    "Bist du mit der Entscheidung nicht einverstanden, schreib uns innerhalb von "
    "sechs Monaten; antworte dazu einfach auf diese Mail. Ein Mensch aus unserem "
    "Team prüft die Entscheidung dann erneut (Art. 20 der Verordnung (EU) 2022/2065, "
    "DSA). Du kannst dich außerdem an eine zugelassene außergerichtliche "
    "Streitbeilegungsstelle wenden (Art. 21 DSA) oder dich an ein Gericht wenden. "
    "Beschwerden darüber, wie wir den DSA einhalten, nimmt die Bundesnetzagentur als "
    "Koordinator für digitale Dienste entgegen."
)


def _datum(zeitpunkt: datetime) -> str:
    """Tagesdatum in deutscher Zeit, z. B. "2. November 2026"."""
    try:
        zeitpunkt = zeitpunkt.astimezone(ZoneInfo("Europe/Berlin"))
    except ZoneInfoNotFoundError:
        zeitpunkt = zeitpunkt.astimezone(timezone.utc)
    return f"{zeitpunkt.day}. {MONATE[zeitpunkt.month - 1]} {zeitpunkt.year}"


def _beitrag(titel: Optional[str]) -> str:
    """Wie die Mail den gemeldeten Beitrag nennt."""
    titel = " ".join((titel or "").split())
    if not titel:
        return "einem Beitrag"
    if len(titel) > TITEL_HOECHSTENS:
        titel = titel[: TITEL_HOECHSTENS - 1].rstrip() + "…"
    return f"dem Beitrag „{titel}“"


class MeldungMitteilung:
    """Schreibt und verschickt die Mails an die meldende Person.

    Ohne Versand (None, nicht eingerichtet) geht nichts hinaus; die Methoden
    melden dann False.
    """

    def __init__(self, versand: Optional[Mailversand], app_url: Optional[str] = None):
        self.versand = versand
        self.app_url = (app_url or "").rstrip("/") or None

    def _gruss(self) -> str:
        zeilen = ["Viele Grüße", "Gut gesagt"]
        if self.app_url:
            zeilen.append(self.app_url)
        return "\n".join(zeilen)

    def _senden(self, mail: Mail, anlass: str) -> bool:
        if self.versand is None:
            logger.info(f"{anlass} nicht verschickt: Mailversand nicht eingerichtet")
            return False
        try:
            self.versand.senden(mail)
        except MailNichtVerschickt:
            # Den Fehlertyp hat der Versand schon ins Log geschrieben.
            logger.warning(f"{anlass} nicht verschickt")
            return False
        except Exception as e:
            logger.warning(f"{anlass} nicht verschickt ({type(e).__name__})")
            return False
        logger.info(f"{anlass} verschickt")
        return True

    def eingang_bestaetigen(
        self,
        an: str,
        titel: Optional[str],
        eingegangen: Optional[datetime] = None,
    ) -> bool:
        """Art. 16 Abs. 4 DSA: Die Meldung ist eingegangen."""
        tag = _datum(eingegangen or datetime.now(timezone.utc))
        text = "\n\n".join(
            [
                "Hallo,",
                f"deine Meldung zu {_beitrag(titel)} ist am {tag} bei uns eingegangen. "
                "Menschen aus unserem Team prüfen sie. Unsere Entscheidung teilen wir "
                "dir an diese Adresse mit.",
                "Hast du nichts gemeldet, hat jemand deine Adresse eingetragen; dann "
                "kannst du diese Mail ignorieren oder uns darauf antworten.",
                self._gruss(),
            ]
        )
        return self._senden(
            Mail(an=an, betreff="Gut gesagt: Deine Meldung ist eingegangen", text=text),
            "Eingangsbestaetigung",
        )

    def entscheidung_mitteilen(
        self, an: str, entscheidung: Entscheidung, titel: Optional[str]
    ) -> bool:
        """Art. 16 Abs. 5 DSA: die Entscheidung ueber die Meldung."""
        absaetze = [
            "Hallo,",
            f"du hast uns zu {_beitrag(titel)} eine Meldung geschickt. Unsere "
            "Entscheidung: " + ERGEBNIS[entscheidung],
        ]
        if entscheidung is not Entscheidung.NICHT_MEHR_DA:
            absaetze += [VON_MENSCHEN, RECHTSBEHELFE]
        absaetze.append(self._gruss())
        return self._senden(
            Mail(
                an=an,
                betreff="Gut gesagt: Entscheidung über deine Meldung",
                text="\n\n".join(absaetze),
            ),
            f"Entscheidung ({entscheidung.value})",
        )


def get_meldung_mitteilung() -> MeldungMitteilung:
    return MeldungMitteilung(get_mailversand(settings), settings.app_url)
