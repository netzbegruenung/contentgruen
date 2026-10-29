"""
Loeschfristen (#421) gegen echtes PostgreSQL und echtes Qdrant.

PostgreSQL: Die Repositories loeschen bearbeitete Meldungen nach ihrer Frist und
Einwuerfe ohne Beitrag nach der letzten Arbeit daran, samt Saetzen und Platzhaltern
ehemaliger Personen; beim endgueltigen Entfernen eines Beitrags gehen seine Stimmen und
"ausformuliert in". Qdrant: Der Task stempelt geloeschte Beitraege und entfernt sie nach
ihrer Frist ueber den Weg der Moderation.

Jeder PostgreSQL-Test bekommt ein eigenes Schema (``conftest.py``, ``postgres.py``).
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

from domain.content_registry import REGISTRY, create_content_service
from domain.models.content_status import FELD_GELOESCHT_AM, ContentStatus
from domain.models.content_type import ContentType
from infrastructure.database.models import (
    Base,
    ContentReport,
    RawInput,
    RawInputContentLink,
    RawInputDraft,
    User,
)
from repositories.content_report_repository import ContentReportRepository
from repositories.implementations.qdrant.moderation_repository import (
    QdrantModerationRepository,
)
from repositories.raw_input_repository import RawInputRepository
from repositories.vote_repository import VoteRepository
from services.loeschfristen_service import LoeschfristenService
from services.moderation_service import ModerationService
from tests.integration.beitrag_helfer import post_beitrag
from tests.integration.conftest import requires_qdrant

pytestmark = pytest.mark.integration

GRENZE = datetime(2026, 5, 2, tzinfo=timezone.utc)
ALT = GRENZE - timedelta(seconds=1)
JUNG = GRENZE + timedelta(days=1)


@pytest.fixture
def datenbank(wegwerf_schema):
    Base.metadata.create_all(wegwerf_schema.engine)
    with wegwerf_schema.engine.begin() as c:
        # votes legt vote_repository.py per Hand an, nicht create_all.
        c.execute(
            text(
                "CREATE TABLE votes (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
                " user_id VARCHAR(255) NOT NULL, content_id UUID NOT NULL,"
                " vote_type VARCHAR(20) NOT NULL, created TIMESTAMP NOT NULL"
                " DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, content_id))"
            )
        )
    return wegwerf_schema


def _mit(datenbank, modul: str, klasse):
    with patch(f"repositories.{modul}.get_app_database", return_value=datenbank):
        return klasse()


class TestMeldungen:
    def _meldung(self, session, status, reviewed_at, created=ALT) -> uuid.UUID:
        meldung = ContentReport(
            content_id=uuid.uuid4(),
            content_type="post",
            reported_by_session_id="sitzung",
            reason="spam",
            status=status,
            reviewed_at=reviewed_at,
            created=created,
        )
        session.add(meldung)
        session.flush()
        return meldung.id

    def test_bearbeitete_nach_frist_weg_offene_bleiben(self, datenbank):
        with datenbank.get_session() as s:
            offen = self._meldung(s, "pending", None)
            bearbeitet_alt = self._meldung(s, "reviewed", ALT)
            abgewiesen_alt = self._meldung(s, "dismissed", ALT)
            bearbeitet_jung = self._meldung(s, "reviewed", JUNG)
            altbestand = self._meldung(s, "reviewed", None)
            altbestand_jung = self._meldung(s, "dismissed", None, created=JUNG)

        repo = _mit(datenbank, "content_report_repository", ContentReportRepository)
        assert repo.bearbeitete_loeschen_vor(GRENZE) == 3

        with datenbank.get_session() as s:
            uebrig = {m.id for m in s.query(ContentReport)}
        assert uebrig == {offen, bearbeitet_jung, altbestand_jung}
        assert not uebrig & {bearbeitet_alt, abgewiesen_alt, altbestand}

    def test_nur_offene_bearbeiten_laesst_entscheidungen_stehen(self, datenbank):
        """Endgueltiges Entfernen bearbeitet offene Meldungen, nicht die anderen."""
        with datenbank.get_session() as s:
            offen = self._meldung(s, "pending", None)
            abgewiesen = self._meldung(s, "dismissed", ALT)
            beitrag = s.get(ContentReport, offen).content_id
            s.get(ContentReport, abgewiesen).content_id = beitrag

        repo = _mit(datenbank, "content_report_repository", ContentReportRepository)
        assert (
            repo.update_reports_by_content_id(
                beitrag, status="reviewed", nur_offene=True
            )
            == 1
        )

        with datenbank.get_session() as s:
            assert s.get(ContentReport, offen).status == "reviewed"
            alt = s.get(ContentReport, abgewiesen)
            assert (alt.status, alt.reviewed_at) == ("dismissed", ALT)


class TestEinwuerfe:
    def _einwurf(self, session, created_at=ALT, status="open") -> uuid.UUID:
        einwurf = RawInput(
            content="ein Fundstueck",
            submitted_by="einwerfer",
            status=status,
            created_at=created_at,
        )
        session.add(einwurf)
        session.flush()
        return einwurf.id

    def _satz(self, session, einwurf, von, updated_at=ALT) -> None:
        session.add(
            RawInputDraft(
                raw_input_id=einwurf,
                user_id=von,
                sentence="Waermepumpen lohnen sich auch im Altbau",
                updated_at=updated_at,
            )
        )

    def test_ohne_arbeit_seit_frist_weg(self, datenbank):
        platzhalter = f"ehemalige-person-{uuid.uuid4()}"
        with datenbank.get_session() as s:
            alt = self._einwurf(s)
            verworfen = self._einwurf(s, status="discarded")
            mit_altem_satz = self._einwurf(s, status="in_progress")
            self._satz(s, mit_altem_satz, platzhalter)
            mit_jungem_satz = self._einwurf(s, status="in_progress")
            self._satz(s, mit_jungem_satz, "destillierer", updated_at=JUNG)
            ausformuliert = self._einwurf(s, status="processed")
            s.add(
                RawInputContentLink(raw_input_id=ausformuliert, content_id=uuid.uuid4())
            )
            jung = self._einwurf(s, created_at=JUNG)
            s.add(User(user_id=platzhalter, anzeigename="ehemalige Person"))
            s.add(User(user_id="destillierer", anzeigename="Anna B."))

        repo = RawInputRepository(db=datenbank)
        assert repo.ohne_beitrag_loeschen_vor(GRENZE) == 3

        with datenbank.get_session() as s:
            uebrig = {e.id for e in s.query(RawInput)}
            saetze = {d.raw_input_id for d in s.query(RawInputDraft)}
            personen = {u.user_id for u in s.query(User)}
        assert uebrig == {mit_jungem_satz, ausformuliert, jung}
        assert not uebrig & {alt, verworfen, mit_altem_satz}
        assert saetze == {mit_jungem_satz}
        # Der Platzhalter ging mit seinem Satz, die echte Person bleibt.
        assert personen == {"destillierer"}

    def test_ohne_ausformuliert_in_wie_ohne_beitrag(self, datenbank):
        """Ist der Beitrag endgueltig entfernt, zaehlt der Einwurf als ohne Beitrag."""
        beitrag = uuid.uuid4()
        with datenbank.get_session() as s:
            einwurf = self._einwurf(s, status="processed")
            s.add(RawInputContentLink(raw_input_id=einwurf, content_id=beitrag))

        repo = RawInputRepository(db=datenbank)
        assert repo.ohne_beitrag_loeschen_vor(GRENZE) == 0
        assert repo.ausformuliert_in_loeschen(beitrag) == 1
        assert repo.ohne_beitrag_loeschen_vor(GRENZE) == 1


def test_stimmen_eines_beitrags_weg_andere_bleiben(datenbank):
    beitrag, anderer = uuid.uuid4(), uuid.uuid4()
    with datenbank.engine.begin() as c:
        for person, inhalt, art in [
            ("person-1", beitrag, "like"),
            ("person-2", beitrag, "dislike"),
            ("person-1", anderer, "like"),
        ]:
            c.execute(
                text(
                    "INSERT INTO votes (user_id, content_id, vote_type)"
                    " VALUES (:p, :i, :a)"
                ),
                {"p": person, "i": inhalt, "a": art},
            )
    repo = _mit(datenbank, "vote_repository", VoteRepository)

    assert repo.loeschen_fuer_beitrag(beitrag) == 2

    assert repo.get_vote_counts(beitrag) == {"likes": 0, "dislikes": 0}
    assert repo.get_vote_counts(anderer)["likes"] == 1


@requires_qdrant
@pytest.mark.asyncio
class TestGeloeschteBeitraege:
    @pytest.fixture
    def beitraege(self, real_embeddings_manager):
        return QdrantModerationRepository(embeddings_manager=real_embeddings_manager)

    @pytest.fixture
    def service(self, beitraege):
        moderation = ModerationService(
            report_repo=MagicMock(),
            moderation_repo=beitraege,
            vote_repo=MagicMock(),
            raw_input_repo=MagicMock(),
            sperre_repo=MagicMock(),
        )
        meldungen = MagicMock(**{"bearbeitete_loeschen_vor.return_value": 0})
        einwuerfe = MagicMock(**{"ohne_beitrag_loeschen_vor.return_value": 0})
        sperren = MagicMock(**{"aufgehobene_loeschen_vor.return_value": 0})
        return LoeschfristenService(
            meldungen, einwuerfe, beitraege, moderation, sperren
        )

    @pytest.fixture
    def post_service(self, integration_settings, real_repository_factory):
        return create_content_service(
            REGISTRY[ContentType.POST], integration_settings, real_repository_factory
        )

    async def _anlegen(self, post_service, manager, status, **felder) -> str:
        beitrag = post_beitrag(uuid.uuid4()).model_copy(update={"status": status})
        await post_service._upsert(beitrag)
        if felder:
            await manager.async_client.set_payload(
                collection_name=manager.collection_name,
                payload=felder,
                points=[str(beitrag.id)],
                wait=True,
            )
        return str(beitrag.id)

    async def test_frist_stempelt_und_entfernt_nach_30_tagen(
        self, real_embeddings_manager, beitraege, service, post_service
    ):
        heute = date(2026, 10, 29)

        async def anlegen(status, **felder):
            return await self._anlegen(
                post_service, real_embeddings_manager, status, **felder
            )

        neu = await anlegen(ContentStatus.DELETED)
        faellig = await anlegen(
            ContentStatus.DELETED,
            **{FELD_GELOESCHT_AM: "2026-09-28"},
        )
        knapp = await anlegen(
            ContentStatus.DELETED,
            **{FELD_GELOESCHT_AM: "2026-09-29"},
        )
        sichtbar = await anlegen(ContentStatus.VISIBLE)
        gesperrt = await anlegen(
            ContentStatus.BLOCKED,
            **{FELD_GELOESCHT_AM: "2026-01-01"},
        )

        geloeschte = {b["id"] for b in await beitraege.geloeschte_laden()}
        assert {neu, faellig, knapp} <= geloeschte
        assert not {sichtbar, gesperrt} & geloeschte

        await service.fristen_anwenden(heute)

        assert await real_embeddings_manager.get_by_id(faellig) is None
        for bleibt in (neu, knapp, sichtbar, gesperrt):
            assert await real_embeddings_manager.get_by_id(bleibt) is not None
        punkt = await real_embeddings_manager.get_by_id(neu)
        assert punkt[FELD_GELOESCHT_AM] == heute.isoformat()
        assert FELD_GELOESCHT_AM not in await real_embeddings_manager.get_by_id(
            sichtbar
        )
