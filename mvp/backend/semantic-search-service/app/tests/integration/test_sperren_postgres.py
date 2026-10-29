"""
Sperren mit Sperrgrund und Widerspruch (#448) gegen ein echtes PostgreSQL.

Das Repository bis in die Tabelle: je Beitrag hoechstens eine aktive Sperre, nur der
Autor widerspricht und nur einmal, Bestaetigen nur bei offenem Widerspruch, Entsperren
schliesst einen offenen Widerspruch ab, und die Frist loescht nur aufgehobene Sperren.
Dazu laeuft die Migration auf einer Datenbank ohne die Tabelle.

Jeder Test bekommt ein eigenes Schema und raeumt es wieder ab (siehe ``postgres.py``).
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError

from infrastructure.database.models import Base, Sperre
from domain.models.widerspruch import (
    PRUEFERGEBNIS_ENTSPERRT,
    PRUEFERGEBNIS_SPERRE_BLEIBT,
    Widerspruchsergebnis,
)
from repositories.sperre_repository import SperreRepository
from tests.integration import postgres
from tests.integration.postgres import Datenbank

MIGRATION = postgres.MIGRATIONEN / "2026-10-29-448-sperren.sql"

JETZT = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)

pytestmark = pytest.mark.integration


@pytest.fixture
def neue_datenbank(postgres_url):
    with postgres.schema(postgres_url, "itest_sp") as db:
        Base.metadata.create_all(db.engine, tables=[Sperre.__table__])
        yield db


def _repo(db: Datenbank) -> SperreRepository:
    with patch("repositories.sperre_repository.get_app_database", return_value=db):
        return SperreRepository()


def _sperren(repo: SperreRepository, autor="autorin-1", content_id=None) -> Sperre:
    return repo.anlegen(
        content_id=content_id or uuid.uuid4(),
        sperrgrund="unterstellung",
        begruendung="Unterstellt Bosheit.",
        gesperrt_von="admin-1",
        autor=autor,
    )


def test_anlegen_speichert_grund_und_autor(neue_datenbank):
    repo = _repo(neue_datenbank)
    sperre = _sperren(repo)

    [gelesen] = repo.fuer_autor("autorin-1")
    assert gelesen.id == sperre.id
    assert gelesen.sperrgrund == "unterstellung"
    assert gelesen.begruendung == "Unterstellt Bosheit."
    assert gelesen.gesperrt_von == "admin-1"
    assert gelesen.gesperrt_am is not None
    assert repo.fuer_autor("andere") == []


def test_zweites_sperren_behaelt_die_aktive_sperre(neue_datenbank):
    repo = _repo(neue_datenbank)
    erste = _sperren(repo)

    zweite = repo.anlegen(
        content_id=erste.content_id,
        sperrgrund="ohne_bezug",
        begruendung="anders",
        gesperrt_von="admin-2",
        autor="autorin-1",
    )

    assert zweite is None
    [gelesen] = _alle(neue_datenbank)
    assert gelesen.id == erste.id
    assert gelesen.sperrgrund == "unterstellung"


def test_hoechstens_eine_aktive_sperre_je_beitrag(neue_datenbank):
    content_id = uuid.uuid4()
    with neue_datenbank.get_session() as session:
        session.add_all(
            [
                Sperre(content_id=content_id, sperrgrund="x", begruendung="y"),
                Sperre(content_id=content_id, sperrgrund="x", begruendung="y"),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_nach_entsperren_neue_sperre_moeglich(neue_datenbank):
    repo = _repo(neue_datenbank)
    erste = _sperren(repo)
    assert repo.aufheben(erste.content_id, "admin-1", JETZT)

    zweite = _sperren(repo, content_id=erste.content_id)

    assert zweite.id != erste.id
    assert [s.id for s in repo.fuer_autor("autorin-1")] == [zweite.id]
    assert set(repo.aktive_je_beitrag()) == {erste.content_id}


def test_aufheben_ohne_aktive_sperre(neue_datenbank):
    assert not _repo(neue_datenbank).aufheben(uuid.uuid4(), "admin-1", JETZT)


def test_widerspruch_nur_vom_autor_und_nur_einmal(neue_datenbank):
    repo = _repo(neue_datenbank)
    sperre = _sperren(repo)

    assert (
        repo.widersprechen(sperre.id, "jemand-anders", "nein", JETZT)
        is Widerspruchsergebnis.NICHT_GEFUNDEN
    )
    assert (
        repo.widersprechen(sperre.id, "autorin-1", "Das ist belegt.", JETZT)
        is Widerspruchsergebnis.ANGENOMMEN
    )
    assert (
        repo.widersprechen(sperre.id, "autorin-1", "Nochmal", JETZT)
        is Widerspruchsergebnis.SCHON_WIDERSPROCHEN
    )

    gelesen = repo.aktive(sperre.content_id)
    assert gelesen.widerspruch == "Das ist belegt."
    assert gelesen.widerspruch_am == JETZT
    assert gelesen.pruefergebnis is None


def test_ohne_autor_kann_niemand_widersprechen(neue_datenbank):
    repo = _repo(neue_datenbank)
    sperre = _sperren(repo, autor=None)

    assert (
        repo.widersprechen(sperre.id, "autorin-1", None, JETZT)
        is Widerspruchsergebnis.NICHT_GEFUNDEN
    )


def test_widerspruch_gegen_aufgehobene_sperre_geht_nicht(neue_datenbank):
    repo = _repo(neue_datenbank)
    sperre = _sperren(repo)
    repo.aufheben(sperre.content_id, "admin-1", JETZT)

    assert (
        repo.widersprechen(sperre.id, "autorin-1", None, JETZT)
        is Widerspruchsergebnis.NICHT_GEFUNDEN
    )


def test_bestaetigen_nur_bei_offenem_widerspruch(neue_datenbank):
    repo = _repo(neue_datenbank)
    sperre = _sperren(repo)

    assert not repo.sperre_bestaetigen(sperre.id, "admin-2", "bleibt", JETZT)

    repo.widersprechen(sperre.id, "autorin-1", None, JETZT)
    assert repo.sperre_bestaetigen(sperre.id, "admin-2", "bleibt", JETZT)
    assert not repo.sperre_bestaetigen(sperre.id, "admin-2", "nochmal", JETZT)

    gelesen = repo.aktive(sperre.content_id)
    assert gelesen.pruefergebnis == PRUEFERGEBNIS_SPERRE_BLEIBT
    assert gelesen.pruefung_begruendung == "bleibt"
    assert gelesen.geprueft_von == "admin-2"
    assert gelesen.aufgehoben_am is None


def test_entsperren_schliesst_offenen_widerspruch_ab(neue_datenbank):
    repo = _repo(neue_datenbank)
    sperre = _sperren(repo)
    repo.widersprechen(sperre.id, "autorin-1", None, JETZT)

    repo.aufheben(sperre.content_id, "admin-2", JETZT)

    [gelesen] = _alle(neue_datenbank)
    assert gelesen.aufgehoben_am == JETZT
    assert gelesen.pruefergebnis == PRUEFERGEBNIS_ENTSPERRT
    assert gelesen.geprueft_von == "admin-2"


def test_autor_sieht_aktive_und_nach_widerspruch_aufgehobene(neue_datenbank):
    repo = _repo(neue_datenbank)
    aktiv, nach_widerspruch, ohne_widerspruch = (_sperren(repo) for _ in range(3))
    repo.widersprechen(nach_widerspruch.id, "autorin-1", None, JETZT)
    repo.aufheben(nach_widerspruch.content_id, "admin-1", JETZT)
    repo.aufheben(ohne_widerspruch.content_id, "admin-1", JETZT)

    assert {s.id for s in repo.fuer_autor("autorin-1")} == {
        aktiv.id,
        nach_widerspruch.id,
    }


def test_entfernen_laesst_offenen_widerspruch_ohne_ergebnis(neue_datenbank):
    repo = _repo(neue_datenbank)
    sperre = _sperren(repo)
    repo.widersprechen(sperre.id, "autorin-1", None, JETZT)

    repo.aufheben(sperre.content_id, "admin-2", JETZT, entsperrt=False)

    [gelesen] = _alle(neue_datenbank)
    assert gelesen.aufgehoben_am == JETZT
    assert gelesen.pruefergebnis is None
    assert repo.fuer_autor("autorin-1") == []


def test_gleichzeitig_angelegte_sperre_gewinnt(neue_datenbank):
    """Legt eine andere Anfrage die Sperre zwischen Lesen und Schreiben an, gewinnt sie."""
    repo = _repo(neue_datenbank)
    content_id = uuid.uuid4()
    erste = {}
    echtes_aktiv = SperreRepository._aktiv

    def aktiv_mit_zwischenruf(cid):
        if erste:
            return echtes_aktiv(cid)
        # Die andere Anfrage legt die Sperre an, waehrend diese noch keine sieht.
        erste["laeuft"] = True
        erste["sperre"] = _sperren(_repo(neue_datenbank), content_id=cid)
        return echtes_aktiv(uuid.uuid4())

    with patch.object(SperreRepository, "_aktiv", staticmethod(aktiv_mit_zwischenruf)):
        zweite = repo.anlegen(
            content_id=content_id,
            sperrgrund="ohne_bezug",
            begruendung="anders",
            gesperrt_von="admin-2",
            autor="autorin-1",
        )

    assert zweite is None
    [gelesen] = _alle(neue_datenbank)
    assert gelesen.id == erste["sperre"].id


def test_entsperren_ohne_widerspruch_ohne_pruefung(neue_datenbank):
    repo = _repo(neue_datenbank)
    sperre = _sperren(repo)

    repo.aufheben(sperre.content_id, "admin-2", JETZT)

    [gelesen] = _alle(neue_datenbank)
    assert gelesen.pruefergebnis is None


def test_frist_loescht_nur_aufgehobene(neue_datenbank):
    repo = _repo(neue_datenbank)
    alt, jung, aktiv = _sperren(repo), _sperren(repo), _sperren(repo)
    repo.aufheben(alt.content_id, None, JETZT - timedelta(days=181))
    repo.aufheben(jung.content_id, None, JETZT - timedelta(days=179))

    assert repo.aufgehobene_loeschen_vor(JETZT - timedelta(days=180)) == 1

    assert {s.id for s in _alle(neue_datenbank)} == {jung.id, aktiv.id}


def test_migration_legt_die_tabelle_an_und_darf_zweimal_laufen(postgres_url):
    with postgres.schema(postgres_url, "itest_sp") as db:
        postgres.migration(db, MIGRATION)
        postgres.migration(db, MIGRATION)

        sperre = _sperren(_repo(db))

        assert _repo(db).aktive(sperre.content_id).id == sperre.id


def _alle(db: Datenbank):
    with db.get_session() as session:
        zeilen = session.query(Sperre).all()
        session.expunge_all()
        return zeilen
