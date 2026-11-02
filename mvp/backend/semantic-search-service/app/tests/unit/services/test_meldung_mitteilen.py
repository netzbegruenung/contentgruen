"""
Eingangsbestaetigung und Entscheidung per Mail an die meldende Person (#493).

Art. 16 Abs. 4 DSA: Wer eine E-Mail-Adresse angibt, bekommt den Eingang der
Meldung bestaetigt. Abs. 5: Sie erfaehrt die Entscheidung samt Rechtsbehelfen.
Getestet am ModerationService mit einem Mailversand, der nur mitschreibt; der
Versand selbst (SMTP) hat eigene Tests in tests/unit/infrastructure.
"""

import logging
import uuid
from unittest.mock import MagicMock

import pytest

from domain.models.meldung import MelderAdresse, MelderAngaben
from infrastructure.mail.versand import Mail, MailNichtVerschickt
from repositories.content_report_repository import ContentReportRepository
from repositories.implementations.qdrant.moderation_repository import (
    QdrantModerationRepository,
)
from services.meldung_mitteilen import MeldungMitteilung
from services.moderation_service import ModerationService
from tests.conftest import GRUND_FUER_SPERRE, create_base_content_fields

CONTENT_ID = str(uuid.uuid4())
ANNA = "anna@example.org"
BEN = "ben@example.org"


class Postausgang:
    """Ein Mailversand, der nur mitschreibt; mit ``kaputt`` scheitert jeder Versand."""

    def __init__(self):
        self.mails: list[Mail] = []
        self.kaputt = False

    def senden(self, mail: Mail) -> None:
        if self.kaputt:
            raise MailNichtVerschickt("SMTPServerDisconnected")
        self.mails.append(mail)

    def an(self, adresse: str) -> list[Mail]:
        return [mail for mail in self.mails if mail.an == adresse]


@pytest.fixture
def speicher(test_embeddings_manager):
    test_embeddings_manager.add_test_data(
        "commentary",
        [
            {
                **create_base_content_fields(),
                "id": CONTENT_ID,
                "title": "Wärmepumpen lohnen sich auch im Altbau",
                "text": "Gemeldeter Kommentar",
                "status": "visible",
            }
        ],
    )
    return test_embeddings_manager


@pytest.fixture
def postausgang():
    return Postausgang()


@pytest.fixture
def report_repo():
    repo = MagicMock(spec=ContentReportRepository)
    repo.has_report_from_user.return_value = False
    repo.create_report.return_value = MagicMock(id=uuid.uuid4())
    # Die offenen Meldungen mit Adresse; die Erledigen-Methoden geben sie wie das
    # echte Repository in melder_adressen zurueck.
    repo.offene = [
        MelderAdresse(uuid.UUID(CONTENT_ID), ANNA),
        MelderAdresse(uuid.UUID(CONTENT_ID), BEN),
    ]

    def erledigen(ergebnis):
        def methode(*args, melder_adressen=None, **kwargs):
            if melder_adressen is not None:
                melder_adressen.extend(repo.offene)
            return ergebnis

        return methode

    repo.update_reports_by_content_id.side_effect = erledigen(2)
    repo.update_report_status.side_effect = erledigen(MagicMock())
    return repo


@pytest.fixture
def service(speicher, postausgang, report_repo):
    return ModerationService(
        report_repo=report_repo,
        moderation_repo=QdrantModerationRepository(embeddings_manager=speicher),
        vote_repo=MagicMock(),
        raw_input_repo=MagicMock(),
        sperre_repo=MagicMock(**{"aktive.return_value": None}),
        mitteilung=MeldungMitteilung(postausgang),
    )


async def _melden(service, email=ANNA, user_id=None):
    return await service.report_content(
        CONTENT_ID,
        "commentary",
        "spam",
        user_id=user_id,
        session_id=None if user_id else "besucher:x",
        melder=MelderAngaben(guter_glaube=True, email=email),
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestEingangsbestaetigung:
    async def test_mit_email_geht_eine_bestaetigung_an_die_adresse(
        self, service, postausgang
    ):
        assert await _melden(service) is True

        [mail] = postausgang.an(ANNA)
        assert "eingegangen" in mail.betreff
        assert "Wärmepumpen lohnen sich auch im Altbau" in mail.text

    async def test_ohne_email_keine_mail(self, service, postausgang):
        assert await _melden(service, email=None) is True

        assert postausgang.mails == []

    async def test_doppelmeldung_bekommt_keine_zweite_bestaetigung(
        self, service, postausgang, report_repo
    ):
        report_repo.has_report_from_user.return_value = True

        assert await _melden(service, user_id="person-1") is True

        assert postausgang.mails == []

    async def test_gescheiterter_versand_laesst_die_meldung_stehen(
        self, service, postausgang, report_repo, caplog
    ):
        postausgang.kaputt = True

        with caplog.at_level(logging.DEBUG):
            assert await _melden(service) is True

        report_repo.create_report.assert_called_once()
        assert ANNA not in caplog.text
        assert "Eingangsbestaetigung" in caplog.text

    async def test_haengender_versand_haelt_die_meldung_nicht_auf(
        self, service, postausgang, monkeypatch, caplog
    ):
        # Das Timeout von smtplib gilt je Schritt; die Anfrage wartet hoechstens
        # MAIL_FRIST, danach laeuft der Versand im Thread zu Ende.
        import threading

        from services import moderation_service

        monkeypatch.setattr(moderation_service, "MAIL_FRIST", 0.05)
        frei = threading.Event()
        postausgang.senden = lambda mail: frei.wait(5)

        try:
            with caplog.at_level(logging.WARNING):
                assert await _melden(service) is True
            assert "deadline" in caplog.text
            assert ANNA not in caplog.text
        finally:
            frei.set()

    async def test_gesperrter_beitrag_bleibt_ohne_titel(
        self, service, postausgang, speicher
    ):
        # Die Melde-Route findet auch gesperrte Beitraege; ihr Titel soll nicht
        # per Mail an jemanden gehen, der nur die Kennung kennt.
        speicher.get_data()[CONTENT_ID]["status"] = "blocked"

        await _melden(service)

        [mail] = postausgang.an(ANNA)
        assert "Wärmepumpen" not in mail.text
        assert "einem Beitrag" in mail.text

    async def test_bestaetigung_enthaelt_keinen_text_der_meldung(
        self, service, postausgang
    ):
        # Die Route ist ohne Anmeldung offen: Wer fremde Adressen eintraegt, soll
        # damit keinen eigenen Text verschicken koennen.
        await service.report_content(
            CONTENT_ID,
            "commentary",
            "other",
            session_id="besucher:x",
            description="Kaufen Sie jetzt bei example.com",
            melder=MelderAngaben(guter_glaube=True, name="Gewinnspiel", email=ANNA),
        )

        [mail] = postausgang.an(ANNA)
        assert "example.com" not in mail.text
        assert "Gewinnspiel" not in mail.text


@pytest.mark.unit
@pytest.mark.asyncio
class TestEntscheidungMitteilen:
    async def test_sperren_teilt_allen_offenen_meldenden_die_sperre_mit(
        self, service, postausgang
    ):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND_FUER_SPERRE)

        for adresse in (ANNA, BEN):
            [mail] = postausgang.an(adresse)
            assert "gesperrt" in mail.text
            assert "Wärmepumpen lohnen sich auch im Altbau" in mail.text

    async def test_sperren_liest_die_adressen_beim_bearbeiten(
        self, service, report_repo
    ):
        # In derselben Transaktion: Eine Meldung, die zwischen Lesen und Bearbeiten
        # eingeht, wuerde sonst ohne Mail erledigt.
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND_FUER_SPERRE)

        aufruf = report_repo.update_reports_by_content_id.call_args.kwargs
        assert aufruf["content_id"] == uuid.UUID(CONTENT_ID)
        assert "melder_adressen" in aufruf

    async def test_abweisen_teilt_der_meldenden_person_die_abweisung_mit(
        self, service, postausgang, report_repo
    ):
        report_id = uuid.uuid4()
        report_repo.offene = [MelderAdresse(uuid.UUID(CONTENT_ID), ANNA)]

        assert await service.dismiss_report(str(report_id), "admin-1") is True

        assert report_repo.update_report_status.call_args.kwargs["report_id"] == (
            report_id
        )
        [mail] = postausgang.mails
        assert mail.an == ANNA
        assert "abgewiesen" in mail.text
        assert "Wärmepumpen lohnen sich auch im Altbau" in mail.text

    async def test_abweisen_behauptet_nicht_dass_der_beitrag_sichtbar_bleibt(
        self, service, postausgang, report_repo, speicher
    ):
        # Auch ein schon gesperrter Beitrag kann gemeldet und die Meldung abgewiesen werden.
        speicher.get_data()[CONTENT_ID]["status"] = "blocked"
        report_repo.offene = [MelderAdresse(uuid.UUID(CONTENT_ID), ANNA)]

        await service.dismiss_report(str(uuid.uuid4()), "admin-1")

        [mail] = postausgang.mails
        assert "sichtbar" not in mail.text
        assert "Wärmepumpen" not in mail.text

    async def test_abweisen_einer_erledigten_meldung_schickt_nichts(
        self, service, postausgang, report_repo
    ):
        report_repo.offene = []

        await service.dismiss_report(str(uuid.uuid4()), "admin-1")

        assert postausgang.mails == []

    async def test_admin_entfernt_beitrag_teilt_das_entfernen_mit(
        self, service, postausgang
    ):
        assert await service.delete_content(CONTENT_ID, "commentary", "admin-1")

        [mail] = postausgang.an(ANNA)
        assert "entfernt" in mail.text
        assert "Menschen" in mail.text

    async def test_loeschfrist_entfernt_beitrag_ohne_pruefung_durch_einen_menschen(
        self, service, postausgang
    ):
        # deleted_by None: die Loeschfrist hat entfernt, kein Admin hat entschieden.
        assert await service.delete_content(CONTENT_ID, "commentary", None)

        [mail] = postausgang.an(ANNA)
        assert "nicht mehr" in mail.text
        assert "Menschen" not in mail.text

    async def test_gleiche_adresse_bekommt_eine_mail(
        self, service, postausgang, report_repo
    ):
        report_repo.offene = [
            MelderAdresse(uuid.UUID(CONTENT_ID), ANNA),
            MelderAdresse(uuid.UUID(CONTENT_ID), ANNA.upper()),
        ]

        await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND_FUER_SPERRE)

        assert len(postausgang.mails) == 1

    async def test_viele_adressen_gehen_nacheinander_in_einem_thread(
        self, service, postausgang, report_repo
    ):
        # Nicht je Adresse ein Thread: 30 Meldungen belegten sonst den Thread-Pool.
        import threading

        report_repo.offene = [
            MelderAdresse(uuid.UUID(CONTENT_ID), f"person{i}@example.org")
            for i in range(30)
        ]
        threads = set()
        senden = postausgang.senden
        postausgang.senden = lambda mail: (
            threads.add(threading.get_ident()) or senden(mail)
        )

        await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND_FUER_SPERRE)

        assert len(postausgang.mails) == 30
        assert len(threads) == 1

    async def test_jede_entscheidung_nennt_die_rechtsbehelfe(
        self, service, postausgang
    ):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND_FUER_SPERRE)

        [mail] = postausgang.an(ANNA)
        assert "sechs Monate" in mail.text
        assert "Streitbeilegungsstelle" in mail.text
        assert "Gericht" in mail.text

    async def test_gescheiterter_versand_laesst_die_entscheidung_stehen(
        self, service, postausgang, report_repo, caplog
    ):
        postausgang.kaputt = True

        with caplog.at_level(logging.DEBUG):
            assert (
                await service.sperren(
                    CONTENT_ID, gesperrt_von="admin-1", **GRUND_FUER_SPERRE
                )
                is True
            )

        report_repo.update_reports_by_content_id.assert_called_once()
        assert ANNA not in caplog.text and BEN not in caplog.text

    async def test_ohne_einrichtung_des_versands_geht_nichts_schief(
        self, speicher, report_repo
    ):
        service = ModerationService(
            report_repo=report_repo,
            moderation_repo=QdrantModerationRepository(embeddings_manager=speicher),
            vote_repo=MagicMock(),
            raw_input_repo=MagicMock(),
            sperre_repo=MagicMock(**{"aktive.return_value": None}),
            mitteilung=MeldungMitteilung(None),
        )

        assert await _melden(service) is True
        assert await service.dismiss_report(str(uuid.uuid4()), "admin-1") is True
