"""
Das Loeschkommando (mvp/scripts/manual/person_loeschen.sql) gegen ein echtes PostgreSQL.

Das Skript ist fuer psql geschrieben; hier laeuft es Anweisung fuer Anweisung ueber
SQLAlchemy auf einer Verbindung, ``:'uid'`` wird zum Bind-Parameter - das ist
dieselbe Ersetzung, die psql mit ``-v uid=...`` vornimmt. Die Zerlegung an ``;``
traegt, solange das Skript keine Strings mit Semikolon und keine $$-Bloecke hat.
Jeder Test bekommt ein eigenes Schema und raeumt es wieder ab, die Daten der
Datenbank bleiben unberuehrt.

Ohne erreichbares PostgreSQL wird das Modul uebersprungen. Ziel ueber
``LOESCHKOMMANDO_DATABASE_URL``, sonst der Dev-Stack (Port 5433).
"""

import os
import uuid
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from api.v1.raw_input import _mit_namen
from infrastructure.database.models import Base, RawInput, RawInputDraft, User
from repositories.raw_input_repository import RawInputRepository
from repositories.user_repository import UserRepository
from services.anzeigename_service import AnzeigenameService

DATABASE_URL = os.environ.get(
    "LOESCHKOMMANDO_DATABASE_URL",
    "postgresql+psycopg2://app_user:changeme@localhost:5433/gutgesagt_app",
)
REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
SKRIPT = REPO_WURZEL / "mvp" / "scripts" / "manual" / "person_loeschen.sql"

PERSON = "person-die-loescht"
ANDERE = "andere-person"
DRITTE = "dritte-person"

SATZ_DER_PERSON = "Waermepumpen lohnen sich auch im Altbau"
SATZ_DER_ANDEREN = "Die Foerderung macht den Unterschied"


def _postgres_erreichbar() -> bool:
    try:
        engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 2})
        with engine.connect():
            return True
    except OperationalError:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _postgres_erreichbar(), reason="PostgreSQL nicht erreichbar"
    ),
]


def _anweisungen(skript: str):
    """Das psql-Skript in einzelne Anweisungen zerlegen, ohne Kommentarzeilen."""
    ohne_kommentare = "\n".join(
        zeile for zeile in skript.splitlines() if not zeile.lstrip().startswith("--")
    )
    for anweisung in ohne_kommentare.split(";"):
        if anweisung.strip():
            yield anweisung.replace(":'uid'", ":uid")


class _Datenbank:
    """Ein Wegwerf-Schema; ``get_session`` wie bei AppDatabase, fuer die Repositories."""

    def __init__(self, schema: str):
        self.schema = schema
        # NullPool: jeder Lauf des Skripts ist eine eigene Sitzung, wie bei psql.
        self.engine = create_engine(
            DATABASE_URL,
            poolclass=NullPool,
            connect_args={"options": f"-csearch_path={schema}"},
        )
        self.sessions = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self):
        with self.sessions.begin() as session:
            yield session


@pytest.fixture
def datenbank():
    schema = f"itest_loeschung_{uuid.uuid4().hex[:8]}"
    with create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT").connect() as c:
        c.execute(text(f"CREATE SCHEMA {schema}"))
    db = _Datenbank(schema)
    Base.metadata.create_all(db.engine)
    with db.engine.begin() as c:
        # votes legt vote_repository.py per Hand an, nicht create_all.
        c.execute(
            text(
                "CREATE TABLE votes (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
                " user_id VARCHAR(255) NOT NULL, content_id UUID NOT NULL,"
                " vote_type VARCHAR(20) NOT NULL, created TIMESTAMP NOT NULL"
                " DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, content_id))"
            )
        )
    yield db
    db.engine.dispose()
    with create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT").connect() as c:
        c.execute(text(f"DROP SCHEMA {schema} CASCADE"))


def _loeschen(datenbank, uid: str = PERSON) -> None:
    skript = SKRIPT.read_text(encoding="utf-8")
    with datenbank.engine.connect().execution_options(
        isolation_level="AUTOCOMMIT"
    ) as c:
        for anweisung in _anweisungen(skript):
            c.execute(text(anweisung), {"uid": uid})


def _einwurf(session, von: str, destilled_by=None) -> uuid.UUID:
    einwurf = RawInput(
        content="ein Fundstueck",
        submitted_by=von,
        status="in_progress" if destilled_by else "open",
        destilled_by=destilled_by,
    )
    session.add(einwurf)
    session.flush()
    return einwurf.id


def _satz(session, einwurf: uuid.UUID, von: str, satz: str) -> None:
    session.add(RawInputDraft(raw_input_id=einwurf, user_id=von, sentence=satz))


def _saetze(datenbank, einwurf: uuid.UUID):
    """Satz -> Kennung an einem Einwurf."""
    with datenbank.get_session() as s:
        return {
            d.sentence: d.user_id
            for d in s.query(RawInputDraft).filter_by(raw_input_id=einwurf)
        }


def _destilled_by(datenbank, einwurf: uuid.UUID):
    with datenbank.get_session() as s:
        return s.get(RawInput, einwurf).destilled_by


def _anzeigenamen(datenbank, kennungen):
    return UserRepository(datenbank).anzeigenamen(kennungen)


def _im_fangkorb(datenbank, einwurf: uuid.UUID, aufrufer: str = ANDERE):
    """Der Einwurf, wie der Fangkorb ihn einer angemeldeten Person ausliefert."""
    zeile = RawInputRepository(datenbank).get_by_id(einwurf, current_user=aufrufer)
    dienst = AnzeigenameService(UserRepository(datenbank))
    with patch("api.v1.raw_input.get_anzeigename_service", return_value=dienst):
        return _mit_namen([zeile], aufrufer)[0]


def _kennung_irgendwo(datenbank, uid: str):
    """Jede Text-Spalte jeder Tabelle im Schema, in der die Kennung noch steht."""
    with datenbank.engine.connect() as c:
        spalten = c.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns"
                " WHERE table_schema = :schema"
                " AND data_type IN ('character varying', 'text')"
            ),
            {"schema": datenbank.schema},
        ).all()
        return [
            f"{tabelle}.{spalte}"
            for tabelle, spalte in spalten
            if c.execute(
                text(f'SELECT count(*) FROM "{tabelle}" WHERE "{spalte}" = :uid'),
                {"uid": uid},
            ).scalar()
        ]


@pytest.fixture
def fangkorb(datenbank):
    """
    Ein fremder Einwurf, den die Person als Erste destilliert hat, daneben der Satz
    einer anderen Person; ein eigener Einwurf mit einem fremden Satz daran.
    """
    with datenbank.get_session() as s:
        fremd = _einwurf(s, von=ANDERE, destilled_by=PERSON)
        _satz(s, fremd, PERSON, SATZ_DER_PERSON)
        _satz(s, fremd, ANDERE, SATZ_DER_ANDEREN)
        eigen = _einwurf(s, von=PERSON, destilled_by=ANDERE)
        _satz(s, eigen, ANDERE, "Ein Satz an einem Einwurf der Person")
        s.add(User(user_id=PERSON, anzeigename="Anna B."))
        s.add(User(user_id=ANDERE, anzeigename="Ben C."))
    return SimpleNamespace(fremd=fremd, eigen=eigen)


class TestSaetzeAnFremdenEinwuerfen:
    def test_satz_bleibt_ohne_kennung_der_person(self, datenbank, fangkorb):
        _loeschen(datenbank)

        saetze = _saetze(datenbank, fangkorb.fremd)
        assert set(saetze) == {SATZ_DER_PERSON, SATZ_DER_ANDEREN}
        assert PERSON not in saetze.values()
        assert saetze[SATZ_DER_ANDEREN] == ANDERE

    def test_fangkorb_zeigt_ehemalige_person(self, datenbank, fangkorb):
        _loeschen(datenbank)

        einwurf = _im_fangkorb(datenbank, fangkorb.fremd)
        namen = {d["sentence"]: d["user_name"] for d in einwurf["drafts"]}
        assert namen == {
            SATZ_DER_PERSON: "ehemalige Person",
            SATZ_DER_ANDEREN: "Ben C.",
        }
        assert einwurf["own_draft"] == SATZ_DER_ANDEREN

    def test_destillierer_ist_der_platzhalter_des_satzes(self, datenbank, fangkorb):
        _loeschen(datenbank)

        destilled_by = _destilled_by(datenbank, fangkorb.fremd)
        assert destilled_by != PERSON
        assert destilled_by == _saetze(datenbank, fangkorb.fremd)[SATZ_DER_PERSON]

    def test_destillierer_ohne_eigenen_satz_wird_ersetzt(self, datenbank):
        """Wer den ersten Satz spaeter geleert hat, bleibt trotzdem Destillierer."""
        with datenbank.get_session() as s:
            einwurf = _einwurf(s, von=ANDERE, destilled_by=PERSON)
            _satz(s, einwurf, ANDERE, "Nur noch dieser Satz steht da")

        _loeschen(datenbank)

        destilled_by = _destilled_by(datenbank, einwurf)
        assert destilled_by not in (None, PERSON)
        assert _anzeigenamen(datenbank, [destilled_by]) == {
            destilled_by: "ehemalige Person"
        }

    def test_zwei_geloeschte_personen_am_selben_einwurf(self, datenbank, fangkorb):
        """Der eindeutige Index (Einwurf, Person) laesst keinen gemeinsamen Platzhalter zu."""
        with datenbank.get_session() as s:
            _satz(s, fangkorb.fremd, DRITTE, "Ein dritter Satz")

        _loeschen(datenbank, PERSON)
        _loeschen(datenbank, DRITTE)

        saetze = _saetze(datenbank, fangkorb.fremd)
        assert len(saetze) == 3
        assert PERSON not in saetze.values() and DRITTE not in saetze.values()
        ersatz = {saetze[SATZ_DER_PERSON], saetze["Ein dritter Satz"]}
        assert len(ersatz) == 2
        assert set(_anzeigenamen(datenbank, ersatz).values()) == {"ehemalige Person"}

    def test_platzhalter_am_geloeschten_einwurf_verschwindet(self, datenbank):
        """Loescht spaeter der Einwerfer, geht mit dem Satz auch sein Platzhalter."""
        with datenbank.get_session() as s:
            einwurf = _einwurf(s, von=ANDERE, destilled_by=PERSON)
            _satz(s, einwurf, PERSON, SATZ_DER_PERSON)
        _loeschen(datenbank, PERSON)
        platzhalter = _saetze(datenbank, einwurf)[SATZ_DER_PERSON]

        _loeschen(datenbank, ANDERE)

        assert _anzeigenamen(datenbank, [platzhalter]) == {}


class TestLoeschkommando:
    def test_keine_kennung_mehr_in_postgresql(self, datenbank, fangkorb):
        with datenbank.get_session() as s:
            s.execute(
                text(
                    "INSERT INTO votes (user_id, content_id, vote_type)"
                    " VALUES (:uid, gen_random_uuid(), 'like')"
                ),
                {"uid": PERSON},
            )

        _loeschen(datenbank)

        assert _kennung_irgendwo(datenbank, PERSON) == []

    def test_eigene_einwuerfe_samt_saetzen_weg(self, datenbank, fangkorb):
        _loeschen(datenbank)

        assert RawInputRepository(datenbank).get_by_id(fangkorb.eigen) is None
        assert _saetze(datenbank, fangkorb.eigen) == {}

    def test_zweiter_lauf_aendert_nichts(self, datenbank, fangkorb):
        _loeschen(datenbank)
        vorher = _saetze(datenbank, fangkorb.fremd)

        _loeschen(datenbank)

        assert _saetze(datenbank, fangkorb.fremd) == vorher
