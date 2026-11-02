"""
Mailversand ueber SMTP (#493): Eingangsbestaetigung und Entscheidung an die
meldende Person (services/meldung_mitteilen.py).

Nur die Standardbibliothek. Eingerichtet ist der Versand, wenn Host und Absender
gesetzt sind (``SEMANTIC_SEARCH_SMTP_HOST``, ``SEMANTIC_SEARCH_MAIL_ABSENDER``,
docs/DEPLOYMENT.md, "Mail"); sonst gibt ``get_mailversand`` None und es geht keine
Mail hinaus.

Adressen stehen nie im Log und nicht im Text von MailNichtVerschickt: Die
Ausnahmen von smtplib nennen den Empfaenger, deshalb reicht der Versand nur ihren
Typ weiter.
"""

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr
from typing import Optional, Protocol, get_args

from core.config import Settings, SmtpVerschluesselung, settings as standard_settings

logger = logging.getLogger(__name__)

# Sekunden je Schritt auf der SMTP-Verbindung (Verbinden, Lesen, Schreiben). Wie lange
# eine Anfrage insgesamt auf den Versand wartet, begrenzt MAIL_FRIST im ModerationService.
SMTP_TIMEOUT = 10

VERSCHLUESSELUNGEN = get_args(SmtpVerschluesselung)


@dataclass(frozen=True)
class Mail:
    """Eine Mail in reinem Text an genau eine Adresse."""

    an: str
    betreff: str
    text: str


class MailNichtVerschickt(Exception):
    """Der Versand ist gescheitert; der Text nennt nur den Typ des Fehlers."""


class Mailversand(Protocol):
    def senden(self, mail: Mail) -> None:
        """Verschickt die Mail oder wirft MailNichtVerschickt."""


class SmtpVersand:
    """Verschickt ueber einen SMTP-Server, je Mail eine Verbindung."""

    def __init__(
        self,
        host: str,
        absender: str,
        *,
        port: int = 587,
        benutzer: Optional[str] = None,
        passwort: Optional[str] = None,
        verschluesselung: SmtpVerschluesselung = "starttls",
        antwort_an: Optional[str] = None,
    ):
        if verschluesselung not in VERSCHLUESSELUNGEN:
            raise ValueError(f"Unbekannte Verschluesselung: {verschluesselung}")
        self.host = host
        self.port = port
        self.absender = absender
        self.benutzer = benutzer
        self.passwort = passwort
        self.verschluesselung = verschluesselung
        self.antwort_an = antwort_an

    def _nachricht(self, mail: Mail) -> EmailMessage:
        nachricht = EmailMessage()
        nachricht["From"] = self.absender
        nachricht["To"] = mail.an
        if self.antwort_an:
            nachricht["Reply-To"] = self.antwort_an
        nachricht["Subject"] = mail.betreff
        nachricht["Date"] = formatdate(localtime=False)
        # parseaddr: Der Absender darf einen Namen tragen ("Gut gesagt <a@example.org>").
        domain = parseaddr(self.absender)[1].rpartition("@")[2]
        nachricht["Message-ID"] = make_msgid(domain=domain or None)
        # RFC 3834: Abwesenheitsnotizen antworten nicht auf automatische Mails.
        nachricht["Auto-Submitted"] = "auto-generated"
        nachricht.set_content(mail.text)
        return nachricht

    def senden(self, mail: Mail) -> None:
        try:
            nachricht = self._nachricht(mail)
            kontext = ssl.create_default_context()
            if self.verschluesselung == "ssl":
                verbindung = smtplib.SMTP_SSL(
                    self.host, self.port, timeout=SMTP_TIMEOUT, context=kontext
                )
            else:
                verbindung = smtplib.SMTP(self.host, self.port, timeout=SMTP_TIMEOUT)
            with verbindung as smtp:
                if self.verschluesselung == "starttls":
                    # Ohne STARTTLS beim Server wirft starttls(); kein Rueckfall auf Klartext.
                    smtp.starttls(context=kontext)
                if self.benutzer:
                    smtp.login(self.benutzer, self.passwort or "")
                smtp.send_message(nachricht)
        except Exception as e:
            # Nur der Typ: SMTPRecipientsRefused und Co. tragen die Adresse.
            logger.warning(f"SMTP delivery failed ({type(e).__name__})")
            raise MailNichtVerschickt(type(e).__name__) from None


def get_mailversand(settings: Settings = standard_settings) -> Optional[SmtpVersand]:
    """Der eingerichtete Versand, oder None ohne Host oder Absender."""
    if not settings.smtp_host or not settings.mail_absender:
        return None
    return SmtpVersand(
        settings.smtp_host,
        settings.mail_absender,
        port=settings.smtp_port,
        benutzer=settings.smtp_benutzer,
        passwort=settings.smtp_passwort,
        verschluesselung=settings.smtp_verschluesselung,
        antwort_an=settings.mail_antwort_an,
    )
