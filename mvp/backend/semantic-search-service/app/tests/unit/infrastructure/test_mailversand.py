"""
Mailversand ueber SMTP (#493, infrastructure/mail/versand.py).

smtplib ist ersetzt; geprueft wird, was beim Server ankaeme: Verschluesselung,
Anmeldung, Kopfzeilen. Und dass ein Fehler die Adresse nicht weitertraegt.
"""

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from core.config import Settings
from infrastructure.mail.versand import (
    Mail,
    MailNichtVerschickt,
    SmtpVersand,
    get_mailversand,
)

MAIL = Mail(an="anna@example.org", betreff="Betreff", text="Grüße aus dem Test")

pytestmark = pytest.mark.unit


@pytest.fixture
def smtp():
    verbindung = MagicMock()
    verbindung.__enter__.return_value = verbindung
    with patch("smtplib.SMTP", return_value=verbindung) as klasse, patch(
        "smtplib.SMTP_SSL", return_value=verbindung
    ) as ssl_klasse:
        yield verbindung, klasse, ssl_klasse


def _gesendet(verbindung):
    [aufruf] = verbindung.send_message.call_args_list
    return aufruf.args[0]


class TestSmtpVersand:
    def test_starttls_meldet_sich_an_und_verschickt(self, smtp):
        verbindung, klasse, _ = smtp

        SmtpVersand(
            "smtp.example.org",
            "gutgesagt@example.org",
            benutzer="konto",
            passwort="geheim",
            antwort_an="kontakt@example.org",
        ).senden(MAIL)

        assert klasse.call_args.args == ("smtp.example.org", 587)
        verbindung.starttls.assert_called_once()
        verbindung.login.assert_called_once_with("konto", "geheim")
        nachricht = _gesendet(verbindung)
        assert nachricht["From"] == "gutgesagt@example.org"
        assert nachricht["To"] == "anna@example.org"
        assert nachricht["Reply-To"] == "kontakt@example.org"
        assert nachricht["Auto-Submitted"] == "auto-generated"
        assert nachricht["Message-ID"].endswith("@example.org>")
        assert nachricht.get_content().strip() == "Grüße aus dem Test"

    def test_absender_mit_namen_gibt_eine_gueltige_message_id(self, smtp):
        verbindung, _, _ = smtp

        SmtpVersand("smtp.example.org", "Gut gesagt <a@example.org>").senden(MAIL)

        assert _gesendet(verbindung)["Message-ID"].endswith("@example.org>")
        assert not _gesendet(verbindung)["Message-ID"].endswith(">>")

    def test_ssl_ohne_anmeldung(self, smtp):
        verbindung, klasse, ssl_klasse = smtp

        SmtpVersand(
            "smtp.example.org", "a@example.org", port=465, verschluesselung="ssl"
        ).senden(MAIL)

        klasse.assert_not_called()
        assert ssl_klasse.call_args.args == ("smtp.example.org", 465)
        verbindung.starttls.assert_not_called()
        verbindung.login.assert_not_called()
        assert "Reply-To" not in _gesendet(verbindung)

    def test_ohne_verschluesselung_abgelehnt(self):
        with pytest.raises(ValueError):
            SmtpVersand("relay", "a@example.org", port=25, verschluesselung="keine")

    def test_server_ohne_starttls_bekommt_keine_mail(self, smtp):
        verbindung, _, _ = smtp
        verbindung.starttls.side_effect = smtplib.SMTPNotSupportedError()

        with pytest.raises(MailNichtVerschickt):
            SmtpVersand("smtp.example.org", "a@example.org").senden(MAIL)

        verbindung.send_message.assert_not_called()

    def test_fehler_nennt_nur_den_typ_nicht_die_adresse(self, smtp):
        verbindung, _, _ = smtp
        verbindung.send_message.side_effect = smtplib.SMTPRecipientsRefused(
            {"anna@example.org": (550, b"no such user")}
        )

        with pytest.raises(MailNichtVerschickt) as fehler:
            SmtpVersand("smtp.example.org", "a@example.org").senden(MAIL)

        assert str(fehler.value) == "SMTPRecipientsRefused"
        assert fehler.value.__cause__ is None

    def test_zeilenumbruch_im_betreff_wird_nicht_verschickt(self, smtp):
        verbindung, _, _ = smtp

        with pytest.raises(MailNichtVerschickt):
            SmtpVersand("smtp.example.org", "a@example.org").senden(
                Mail(an="anna@example.org", betreff="x\nBcc: b@example.org", text="")
            )

        verbindung.send_message.assert_not_called()


class TestEinrichtung:
    def test_ohne_host_kein_versand(self):
        assert get_mailversand(Settings(mail_absender="a@example.org")) is None

    def test_ohne_absender_kein_versand(self):
        assert get_mailversand(Settings(smtp_host="smtp.example.org")) is None

    def test_einstellungen_lehnen_klartext_ab(self):
        with pytest.raises(ValueError):
            Settings(smtp_verschluesselung="keine")

    def test_mit_host_und_absender(self):
        versand = get_mailversand(
            Settings(
                smtp_host="smtp.example.org",
                smtp_port=465,
                smtp_verschluesselung="ssl",
                mail_absender="a@example.org",
            )
        )

        assert versand.host == "smtp.example.org"
        assert versand.port == 465
        assert versand.verschluesselung == "ssl"
