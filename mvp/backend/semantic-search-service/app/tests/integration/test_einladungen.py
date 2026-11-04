"""
Einladungen (#429) gegen ein echtes PostgreSQL.

Service und Repository zusammen bis in die Tabelle, Keycloak als Attrappe: Eine
Einladung laesst genau so viele Konten anlegen, wie sie erlaubt, auch wenn Anfragen
gleichzeitig kommen; abgeschaltet oder abgelaufen keines. Die Tabelle traegt keine
Mail-Adresse, und eine Einloesung zaehlt auch fuer eine Adresse mit Konto. Dazu laeuft die Migration auf einer Datenbank ohne die Tabelle.

Jeder Test bekommt ein eigenes Schema und raeumt es wieder ab; Datenbank und
Schema kommen aus ``conftest.py`` (siehe ``postgres.py``).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import inspect, text

from infrastructure.database.models import Base, EinladungZeile
from repositories.einladung_repository import EinladungRepository
from domain.interfaces.konten_im_realm import KontoErgebnis
from services.einladung_service import (
    EinladungService,
    EinladungUngueltig,
    EinladungZustand,
    KontoAnlegenFehlgeschlagen,
)
from tests.integration import postgres
from tests.integration.postgres import Datenbank

MIGRATION = postgres.MIGRATIONEN / "2026-10-30-429-einladungen.sql"

HEUTE = date(2026, 10, 30)
LETZTER_TAG = date(2026, 11, 13)

pytestmark = pytest.mark.integration


class KontenAttrappe:
    def __init__(self, ergebnis=KontoErgebnis.ANGELEGT, fehler=False):
        self.ergebnis = ergebnis
        self.fehler = fehler
        self.adressen = []

    def konto_anlegen(self, email):
        if self.fehler:
            raise RuntimeError("Keycloak nicht erreichbar")
        self.adressen.append(email)
        return self.ergebnis


@pytest.fixture
def neue_datenbank(postgres_url):
    with postgres.schema(postgres_url, "itest_einl") as db:
        Base.metadata.create_all(db.engine, tables=[EinladungZeile.__table__])
        yield db


def _repository(db: Datenbank) -> EinladungRepository:
    with patch(
        "repositories.einladung_repository.get_app_database",
        return_value=db,
    ):
        return EinladungRepository()


def _service(db: Datenbank, konten=None) -> EinladungService:
    return EinladungService(_repository(db), konten)


def test_einladung_laesst_genau_so_viele_konten_anlegen_wie_erlaubt(neue_datenbank):
    konten = KontenAttrappe()
    service = _service(neue_datenbank, konten)
    code = service.anlegen("Zwei Plaetze", 2, LETZTER_TAG, heute=HEUTE).code

    service.einloesen(code, "a@example.org", heute=HEUTE)
    service.einloesen(code, "b@example.org", heute=HEUTE)
    with pytest.raises(EinladungUngueltig):
        service.einloesen(code, "c@example.org", heute=HEUTE)

    assert konten.adressen == ["a@example.org", "b@example.org"]
    [einladung] = service.alle()
    assert einladung.einloesungen == 2
    assert einladung.zustand(HEUTE) is EinladungZustand.AUFGEBRAUCHT


def test_gleichzeitige_anfragen_bekommen_die_letzte_einloesung_nur_einmal(
    neue_datenbank,
):
    repository = _repository(neue_datenbank)
    service = EinladungService(repository, KontenAttrappe())
    code = service.anlegen("Eine Einloesung", 1, LETZTER_TAG, heute=HEUTE).code

    with ThreadPoolExecutor(max_workers=8) as pool:
        belegt = list(
            pool.map(lambda _: repository.einloesung_zaehlen(code, HEUTE), range(8))
        )

    assert belegt.count(True) == 1
    assert service.alle()[0].einloesungen == 1


def test_abgeschaltet_und_abgelaufen_legen_kein_konto_an(neue_datenbank):
    konten = KontenAttrappe()
    service = _service(neue_datenbank, konten)
    einladung = service.anlegen("Aus", 5, LETZTER_TAG, heute=HEUTE)
    service.schalten(einladung.id, True)

    with pytest.raises(EinladungUngueltig):
        service.einloesen(einladung.code, "a@example.org", heute=HEUTE)

    service.schalten(einladung.id, False)
    with pytest.raises(EinladungUngueltig):
        service.einloesen(einladung.code, "a@example.org", heute=date(2026, 11, 14))

    # Am letzten Tag gilt sie noch.
    service.einloesen(einladung.code, "a@example.org", heute=LETZTER_TAG)
    assert konten.adressen == ["a@example.org"]


def test_vorhandenes_konto_zaehlt_wie_ein_neues(neue_datenbank):
    service = _service(neue_datenbank, KontenAttrappe(KontoErgebnis.VORHANDEN))
    code = service.anlegen("Eine Einloesung", 1, LETZTER_TAG, heute=HEUTE).code

    service.einloesen(code, "alt@example.org", heute=HEUTE)

    assert service.alle()[0].einloesungen == 1
    assert not service.ist_einloesbar(code, heute=HEUTE)


def test_gescheitertes_anlegen_nimmt_die_einloesung_zurueck(neue_datenbank):
    service = _service(neue_datenbank, KontenAttrappe(fehler=True))
    code = service.anlegen("Eine Einloesung", 1, LETZTER_TAG, heute=HEUTE).code

    with pytest.raises(KontoAnlegenFehlgeschlagen):
        service.einloesen(code, "neu@example.org", heute=HEUTE)

    assert service.alle()[0].einloesungen == 0
    assert service.ist_einloesbar(code, heute=HEUTE)


def test_tabelle_kennt_keine_mail_adresse(neue_datenbank):
    service = _service(neue_datenbank, KontenAttrappe())
    code = service.anlegen("Gruppe", 3, LETZTER_TAG, heute=HEUTE).code
    service.einloesen(code, "a@example.org", heute=HEUTE)

    spalten = {
        s["name"]
        for s in inspect(neue_datenbank.engine).get_columns(
            "einladungen", schema=neue_datenbank.schema
        )
    }
    assert spalten == {
        "id",
        "code",
        "notiz",
        "erlaubte_einloesungen",
        "einloesungen",
        "gueltig_bis",
        "abgeschaltet",
        "angelegt_am",
    }
    with neue_datenbank.engine.connect() as c:
        inhalt = c.execute(text("SELECT * FROM einladungen")).all()
    assert "a@example.org" not in repr(inhalt)


def test_migration_legt_die_tabelle_an_und_darf_zweimal_laufen(postgres_url):
    with postgres.schema(postgres_url, "itest_einl") as db:
        postgres.migration(db, MIGRATION)
        postgres.migration(db, MIGRATION)

        service = _service(db, KontenAttrappe())
        code = service.anlegen("nach der Migration", 1, LETZTER_TAG, heute=HEUTE).code
        service.einloesen(code, "a@example.org", heute=HEUTE)

        assert service.alle()[0].einloesungen == 1
