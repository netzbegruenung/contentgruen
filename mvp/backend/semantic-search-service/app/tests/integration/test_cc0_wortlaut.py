"""
Die Kennung des CC0-Hinweises (#431) gegen echtes PostgreSQL und Qdrant: Einwurf
und Satz tragen sie in ihrer Zeile, ein Beitrag im Payload, und Bestand ohne
Kennung bleibt lesbar.

PostgreSQL: Wegwerf-Schema aus der Fixture ``datenbank`` von
``test_loeschkommando.py``. Qdrant: wie ``test_post_type.py``.
"""

import datetime
import uuid
from contextlib import contextmanager

import pytest

from domain.content_registry import REGISTRY, create_content_service
from domain.models.content_origin import ContentOrigin
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from domain.models.post import PostDbEntry
from infrastructure.database.models import RawInput, RawInputDraft
from repositories.raw_input_repository import RawInputRepository
from tests.integration.conftest import requires_qdrant
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

FORMULAR = "2026-10-29-formular"
SATZ = "2026-10-29-satz"

pytestmark = pytest.mark.integration


class _SitzungWieImDienst:
    """
    Das Repository committet selbst; die Sitzung des Wegwerf-Schemas oeffnet aber
    schon eine Transaktion. Hier daher Sitzungen wie in DatabaseConnection.
    """

    def __init__(self, datenbank):
        self._datenbank = datenbank

    @contextmanager
    def get_session(self):
        session = self._datenbank.sessions()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


@pytest.fixture
def repository(datenbank):  # noqa: F811
    return RawInputRepository(_SitzungWieImDienst(datenbank))


def _spalte(datenbank, modell, **filter):  # noqa: F811
    with datenbank.get_session() as s:
        return s.query(modell.cc0_wortlaut).filter_by(**filter).scalar()


class TestPostgres:
    def test_einwurf_traegt_die_kennung(self, datenbank, repository):  # noqa: F811
        einwurf = repository.create(
            content="Fundstueck", submitted_by="alice", cc0_wortlaut=FORMULAR
        )

        assert _spalte(datenbank, RawInput, id=uuid.UUID(einwurf["id"])) == FORMULAR

    def test_einwurf_ohne_kennung_bleibt_null(
        self, datenbank, repository  # noqa: F811
    ):
        einwurf = repository.create(content="Fundstueck", submitted_by="alice")

        assert _spalte(datenbank, RawInput, id=uuid.UUID(einwurf["id"])) is None

    def test_satz_traegt_die_kennung_des_letzten_speicherns(
        self, datenbank, repository  # noqa: F811
    ):
        einwurf_id = uuid.UUID(repository.create(content="Fundstueck")["id"])

        repository.save_draft(einwurf_id, "alice", "Erster Satz")
        assert _spalte(datenbank, RawInputDraft, raw_input_id=einwurf_id) is None

        repository.save_draft(einwurf_id, "alice", "Zweiter Satz", cc0_wortlaut=SATZ)
        assert _spalte(datenbank, RawInputDraft, raw_input_id=einwurf_id) == SATZ


@requires_qdrant
@pytest.mark.asyncio
class TestQdrant:
    async def test_beitrag_traegt_die_kennung_im_payload(
        self, integration_settings, real_repository_factory
    ):
        service = create_content_service(
            REGISTRY[ContentType.POST], integration_settings, real_repository_factory
        )
        jetzt = datetime.datetime.now(datetime.timezone.utc)

        def eintrag(**extra) -> PostDbEntry:
            return PostDbEntry(
                text="Verkehrswende und Klimaschutz gehoeren zusammen",
                id=uuid.uuid4(),
                created=jetzt,
                last_modified=jetzt,
                original_author="tester",
                last_modified_by="tester",
                title="Klimapost",
                platform="mastodon",
                author="@gruen",
                status=ContentStatus.VISIBLE,
                origin=ContentOrigin.MANUALLY_CREATED,
                **extra,
            )

        mit = eintrag(cc0_wortlaut=FORMULAR)
        ohne = eintrag()
        await service._upsert(mit)
        await service._upsert(ohne)

        assert (await service.get(mit.id)).cc0_wortlaut == FORMULAR
        assert (await service.get(ohne.id)).cc0_wortlaut is None
