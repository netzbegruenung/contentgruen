"""
"Suchen ohne Treffer" gegen ein echtes PostgreSQL (#243).

Die Unit-Tests pruefen das SQL nur als Text. Hier zaehlt erst das Repository allein,
dann Service und Repository zusammen bis in die Tabelle. Die Admin-Liste kommt aus dem
echten HAVING: Eine Aussage erscheint erst ab zwei verschiedenen Personen. Dazu laufen
die beiden Migrationen auf einer Tabelle im alten Schema.

Jeder Test bekommt ein eigenes Schema und raeumt es wieder ab; Datenbank und
Schema kommen aus ``conftest.py`` (siehe ``postgres.py``).
"""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import text

from domain.models.content_status import ContentStatus
from infrastructure.database.models import Base, SucheOhneTrefferZeile
from repositories.suchen_ohne_treffer_repository import SuchenOhneTrefferRepository
from services.suchen_ohne_treffer_service import (
    PersonenDesTages,
    SuchenOhneTrefferService,
)
from tests.integration import postgres
from tests.integration.postgres import Datenbank

TABELLE = postgres.MIGRATIONEN / "2026-10-26-suchen-ohne-treffer.sql"
PERSONEN = postgres.MIGRATIONEN / "2026-10-26-suchen-ohne-treffer-personen.sql"

AUSSAGE = uuid.UUID("11111111-1111-1111-1111-111111111111")
# Tage fuer den Service: Mittwoch und Donnerstag derselben Woche, dazu ein Tag der
# Vorwoche.
MITTWOCH = date(2026, 10, 28)
DONNERSTAG = date(2026, 10, 29)
VORWOCHE = date(2026, 10, 21)
# Wochenanfaenge (Montag) fuer das Repository: die Woche von MITTWOCH und die davor.
WOCHE = date(2026, 10, 26)
VORIGE_WOCHE = date(2026, 10, 19)
PERSON_A = "a" * 64
PERSON_B = "b" * 64

pytestmark = pytest.mark.integration


@pytest.fixture
def neue_datenbank(postgres_url):
    """Schema, wie create_all es in einer neuen Datenbank anlegt."""
    with postgres.schema(postgres_url, "itest_sot") as db:
        Base.metadata.create_all(db.engine, tables=[SucheOhneTrefferZeile.__table__])
        yield db


@pytest.fixture
def bestehende_datenbank(postgres_url):
    """Tabelle im Schema von #216, mit einer schon gezaehlten Woche."""
    with postgres.schema(postgres_url, "itest_sot") as db:
        postgres.migration(db, TABELLE)
        with db.engine.begin() as c:
            c.execute(
                text(
                    "INSERT INTO suchen_ohne_treffer (statement_id, woche, anzahl)"
                    " VALUES (:id, :woche, 5)"
                ),
                {"id": AUSSAGE, "woche": WOCHE},
            )
        yield db


def _repository(db: Datenbank) -> SuchenOhneTrefferRepository:
    with patch(
        "repositories.suchen_ohne_treffer_repository.get_app_database",
        return_value=db,
    ):
        return SuchenOhneTrefferRepository()


def _service(db: Datenbank) -> SuchenOhneTrefferService:
    repository = _repository(db)
    aussagen = Mock()
    aussagen.get = AsyncMock(
        return_value=SimpleNamespace(
            id=AUSSAGE,
            text="Lohnt sich eine Waermepumpe im Altbau?",
            status=ContentStatus.VISIBLE,
        )
    )
    return SuchenOhneTrefferService(repository, aussagen, PersonenDesTages())


async def _liste(service: SuchenOhneTrefferService):
    return [
        (e.statement_id, e.anzahl, e.personen)
        for e in await service.haeufigste(wochen=4, heute=DONNERSTAG)
    ]


def _zeilen(db: Datenbank) -> list:
    with db.engine.connect() as c:
        return c.execute(
            text(
                "SELECT statement_id, woche, anzahl, personen FROM suchen_ohne_treffer"
                " ORDER BY statement_id, woche"
            )
        ).all()


def _aussage(nummer: int) -> uuid.UUID:
    return uuid.UUID(int=nummer)


class TestRepository:
    """Das Repository allein, ohne Service: Hochzaehlen, Mindestanzahl, Blaettern."""

    def test_zaehlen_legt_an_und_zaehlt_hoch(self, neue_datenbank):
        repository = _repository(neue_datenbank)

        repository.zaehlen(AUSSAGE, WOCHE, neue_person=True)
        repository.zaehlen(AUSSAGE, WOCHE, neue_person=False)
        repository.zaehlen(AUSSAGE, WOCHE, neue_person=True)

        assert _zeilen(neue_datenbank) == [(AUSSAGE, WOCHE, 3, 2)]

    def test_zaehlen_je_woche_eine_zeile(self, neue_datenbank):
        repository = _repository(neue_datenbank)

        repository.zaehlen(AUSSAGE, VORIGE_WOCHE, neue_person=True)
        repository.zaehlen(AUSSAGE, WOCHE, neue_person=False)

        assert _zeilen(neue_datenbank) == [
            (AUSSAGE, VORIGE_WOCHE, 1, 1),
            (AUSSAGE, WOCHE, 1, 0),
        ]

    def test_haeufigste_nur_ab_mindestanzahl_personen(self, neue_datenbank):
        repository = _repository(neue_datenbank)
        for _ in range(5):
            repository.zaehlen(_aussage(1), WOCHE, neue_person=False)
        repository.zaehlen(_aussage(1), WOCHE, neue_person=True)
        repository.zaehlen(_aussage(2), WOCHE, neue_person=True)
        repository.zaehlen(_aussage(2), WOCHE, neue_person=True)

        assert repository.haeufigste(WOCHE, mindestanzahl=2, limit=10) == [
            (_aussage(2), 2, 2)
        ]
        assert repository.haeufigste(WOCHE, mindestanzahl=1, limit=10) == [
            (_aussage(1), 6, 1),
            (_aussage(2), 2, 2),
        ]

    def test_haeufigste_summiert_ab_der_woche(self, neue_datenbank):
        repository = _repository(neue_datenbank)
        repository.zaehlen(AUSSAGE, date(2026, 10, 12), neue_person=True)
        repository.zaehlen(AUSSAGE, VORIGE_WOCHE, neue_person=True)
        repository.zaehlen(AUSSAGE, WOCHE, neue_person=True)

        assert repository.haeufigste(VORIGE_WOCHE, mindestanzahl=1, limit=10) == [
            (AUSSAGE, 2, 2)
        ]

    def test_haeufigste_blaettert_in_fester_reihenfolge(self, neue_datenbank):
        """Absteigend nach Anzahl, bei gleicher Anzahl nach Aussage-ID."""
        repository = _repository(neue_datenbank)
        anzahlen = {_aussage(1): 1, _aussage(2): 3, _aussage(3): 1, _aussage(4): 2}
        for aussage, anzahl in anzahlen.items():
            for _ in range(anzahl):
                repository.zaehlen(aussage, WOCHE, neue_person=True)

        seiten = [
            repository.haeufigste(WOCHE, mindestanzahl=1, limit=2, offset=offset)
            for offset in (0, 2, 4)
        ]

        assert seiten == [
            [(_aussage(2), 3, 3), (_aussage(4), 2, 2)],
            [(_aussage(1), 1, 1), (_aussage(3), 1, 1)],
            [],
        ]

    def test_ueber_der_schwelle_alle_ab_mindestanzahl_personen(self, neue_datenbank):
        """Ohne Limit, Personen ueber die Wochen ab seit_woche summiert (#436)."""
        repository = _repository(neue_datenbank)
        for _ in range(5):
            repository.zaehlen(_aussage(1), WOCHE, neue_person=False)
        repository.zaehlen(_aussage(1), WOCHE, neue_person=True)
        repository.zaehlen(_aussage(2), VORIGE_WOCHE, neue_person=True)
        repository.zaehlen(_aussage(2), WOCHE, neue_person=True)
        repository.zaehlen(_aussage(3), date(2026, 10, 12), neue_person=True)
        repository.zaehlen(_aussage(3), WOCHE, neue_person=True)

        assert set(repository.ueber_der_schwelle(VORIGE_WOCHE, mindestanzahl=2)) == {
            _aussage(2)
        }

    def test_loeschen_vor_entfernt_nur_aeltere_wochen(self, neue_datenbank):
        repository = _repository(neue_datenbank)
        repository.zaehlen(AUSSAGE, date(2026, 10, 12), neue_person=True)
        repository.zaehlen(AUSSAGE, VORIGE_WOCHE, neue_person=True)
        repository.zaehlen(AUSSAGE, WOCHE, neue_person=True)

        assert repository.loeschen_vor(VORIGE_WOCHE) == 1
        assert [z.woche for z in _zeilen(neue_datenbank)] == [VORIGE_WOCHE, WOCHE]


@pytest.mark.asyncio
class TestMindestanzahlZaehltPersonen:
    async def test_eine_person_mehrfach_am_selben_tag_erscheint_nicht(
        self, neue_datenbank
    ):
        service = _service(neue_datenbank)

        for _ in range(3):
            service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)

        assert await _liste(service) == []

    async def test_zwei_personen_erscheinen_mit_der_zahl_der_suchen_und_personen(
        self, neue_datenbank
    ):
        service = _service(neue_datenbank)

        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, PERSON_B, heute=MITTWOCH)

        assert await _liste(service) == [(AUSSAGE, 3, 2)]

    async def test_ohne_pseudonym_zaehlt_keine_person(self, neue_datenbank):
        service = _service(neue_datenbank)

        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, None, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, None, heute=MITTWOCH)

        assert await _liste(service) == []

    async def test_personen_verschiedener_wochen_werden_summiert(self, neue_datenbank):
        """Zwei Wochen mit je einer Person ergeben zwei Personen im Zeitraum."""
        service = _service(neue_datenbank)

        service.erfassen(AUSSAGE, 0, PERSON_A, heute=VORWOCHE)
        service.erfassen(AUSSAGE, 0, PERSON_B, heute=MITTWOCH)

        assert await _liste(service) == [(AUSSAGE, 2, 2)]

    async def test_dieselbe_person_an_zwei_tagen_zaehlt_zweimal(self, neue_datenbank):
        """
        Der benannte Restfall: Die Merkliste beginnt jeden Tag neu (und das echte
        Tagespseudonym wechselt mit dem Datum ohnehin).
        """
        service = _service(neue_datenbank)

        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, PERSON_A, heute=DONNERSTAG)

        assert await _liste(service) == [(AUSSAGE, 2, 2)]

    async def test_ueber_der_schwelle_dieselbe_auswahl_wie_die_liste(
        self, neue_datenbank
    ):
        """Fuer Nicht-Admins zaehlen dieselben Aussagen wie in der Kennzahl (#436)."""
        service = _service(neue_datenbank)
        einzeln = _aussage(9)

        service.erfassen(AUSSAGE, 0, PERSON_A, heute=VORWOCHE)
        service.erfassen(AUSSAGE, 0, PERSON_B, heute=MITTWOCH)
        service.erfassen(einzeln, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(einzeln, 0, PERSON_A, heute=MITTWOCH)

        assert await service.ueber_der_schwelle(wochen=4, heute=DONNERSTAG) == {AUSSAGE}
        assert await service.ueber_der_schwelle(wochen=1, heute=DONNERSTAG) == set()


@pytest.mark.asyncio
class TestMigration:
    async def test_bestehende_zeilen_bekommen_null_personen(self, bestehende_datenbank):
        postgres.migration(bestehende_datenbank, PERSONEN)
        service = _service(bestehende_datenbank)

        assert await _liste(service) == []
        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, PERSON_B, heute=MITTWOCH)
        assert await _liste(service) == [(AUSSAGE, 7, 2)]

    def test_migration_darf_mehrfach_laufen(self, bestehende_datenbank):
        postgres.migration(bestehende_datenbank, PERSONEN)
        postgres.migration(bestehende_datenbank, PERSONEN)

        with bestehende_datenbank.engine.connect() as c:
            assert c.execute(
                text("SELECT anzahl, personen FROM suchen_ohne_treffer")
            ).all() == [(5, 0)]

    def test_migration_ergibt_dasselbe_schema_wie_create_all(
        self, bestehende_datenbank, neue_datenbank
    ):
        postgres.migration(bestehende_datenbank, PERSONEN)
        abfrage = text(
            "SELECT column_name, data_type, is_nullable, column_default"
            " FROM information_schema.columns"
            " WHERE table_schema = current_schema()"
            " AND table_name = 'suchen_ohne_treffer' ORDER BY column_name"
        )

        with bestehende_datenbank.engine.connect() as alt:
            spalten_alt = alt.execute(abfrage).all()
        with neue_datenbank.engine.connect() as neu:
            spalten_neu = neu.execute(abfrage).all()

        assert spalten_alt == spalten_neu
