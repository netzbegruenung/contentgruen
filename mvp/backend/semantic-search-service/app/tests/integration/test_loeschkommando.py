"""
Das Loeschkommando (mvp/scripts/manual/person_loeschen.sql) gegen ein echtes PostgreSQL.

Das Skript ist fuer psql geschrieben; hier laeuft es Anweisung fuer Anweisung ueber
SQLAlchemy auf einer Verbindung, ``:'uid'`` wird zum Bind-Parameter - das ist
dieselbe Ersetzung, die psql mit ``-v uid=...`` vornimmt. Jeder Lauf bekommt ein
eigenes Schema und raeumt es wieder ab, die Daten der Datenbank bleiben unberuehrt.

Ohne erreichbares PostgreSQL wird das Modul uebersprungen. Ziel ueber
``LOESCHKOMMANDO_DATABASE_URL``, sonst der Dev-Stack (Port 5433).
"""

import os
import re
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from infrastructure.database.models import Base, RawInput, RawInputDraft, User
from repositories.user_repository import UserRepository

DATABASE_URL = os.environ.get(
    "LOESCHKOMMANDO_DATABASE_URL",
    "postgresql+psycopg2://app_user:changeme@localhost:5433/gutgesagt_app",
)
SKRIPT = (
    Path(__file__).parents[6] / "mvp" / "scripts" / "manual" / "person_loeschen.sql"
)

PERSON = "person-die-loescht"
ANDERE = "andere-person"
DRITTE = "dritte-person"


def _postgres_erreichbar() -> bool:
    try:
        with create_engine(DATABASE_URL).connect():
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
            yield re.sub(r":'uid'", ":uid", anweisung)


@pytest.fixture
def datenbank():
    schema = f"itest_loeschung_{uuid.uuid4().hex[:8]}"
    with create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT").connect() as c:
        c.execute(text(f"CREATE SCHEMA {schema}"))
    # NullPool: jeder Lauf des Skripts ist eine eigene Sitzung, wie bei psql.
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        connect_args={"options": f"-csearch_path={schema}"},
    )
    Base.metadata.create_all(engine)
    with engine.begin() as c:
        # votes legt vote_repository.py per Hand an, nicht create_all.
        c.execute(
            text(
                "CREATE TABLE votes (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
                " user_id VARCHAR(255) NOT NULL, content_id UUID NOT NULL,"
                " vote_type VARCHAR(20) NOT NULL, created TIMESTAMP NOT NULL"
                " DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, content_id))"
            )
        )
    yield SimpleNamespace(engine=engine, schema=schema)
    engine.dispose()
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


def _saetze(session, einwurf: uuid.UUID):
    return {
        d.sentence: d.user_id
        for d in session.query(RawInputDraft).filter_by(raw_input_id=einwurf)
    }


def _anzeigenamen(datenbank, kennungen):
    repository = UserRepository.__new__(UserRepository)
    sessions = sessionmaker(bind=datenbank.engine)

    class _Db:
        def get_session(self):
            return sessions.begin()

    repository.db = _Db()
    return repository.anzeigenamen(kennungen)


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
    with sessionmaker(bind=datenbank.engine).begin() as s:
        fremd = _einwurf(s, von=ANDERE, destilled_by=PERSON)
        _satz(s, fremd, PERSON, "Waermepumpen lohnen sich auch im Altbau")
        _satz(s, fremd, ANDERE, "Die Foerderung macht den Unterschied")
        eigen = _einwurf(s, von=PERSON, destilled_by=ANDERE)
        _satz(s, eigen, ANDERE, "Ein Satz an einem Einwurf der Person")
        s.add(User(user_id=PERSON, anzeigename="Anna B."))
        s.add(User(user_id=ANDERE, anzeigename="Ben C."))
    return SimpleNamespace(fremd=fremd, eigen=eigen)


class TestSaetzeAnFremdenEinwuerfen:
    def test_satz_bleibt_ohne_kennung_der_person(self, datenbank, fangkorb):
        _loeschen(datenbank)

        with sessionmaker(bind=datenbank.engine)() as s:
            saetze = _saetze(s, fangkorb.fremd)
        assert set(saetze) == {
            "Waermepumpen lohnen sich auch im Altbau",
            "Die Foerderung macht den Unterschied",
        }
        assert PERSON not in saetze.values()
        assert saetze["Die Foerderung macht den Unterschied"] == ANDERE

    def test_fangkorb_zeigt_ehemalige_person(self, datenbank, fangkorb):
        _loeschen(datenbank)

        with sessionmaker(bind=datenbank.engine)() as s:
            saetze = _saetze(s, fangkorb.fremd)
        namen = _anzeigenamen(datenbank, saetze.values())
        assert namen[saetze["Waermepumpen lohnen sich auch im Altbau"]] == (
            "ehemalige Person"
        )
        assert namen[ANDERE] == "Ben C."

    def test_destillierer_ist_nicht_mehr_die_person(self, datenbank, fangkorb):
        _loeschen(datenbank)

        with sessionmaker(bind=datenbank.engine)() as s:
            einwurf = s.get(RawInput, fangkorb.fremd)
            saetze = _saetze(s, fangkorb.fremd)
        assert einwurf.destilled_by != PERSON
        assert einwurf.destilled_by == saetze["Waermepumpen lohnen sich auch im Altbau"]

    def test_destillierer_ohne_eigenen_satz_wird_ersetzt(self, datenbank):
        """Wer den ersten Satz spaeter geleert hat, bleibt trotzdem Destillierer."""
        with sessionmaker(bind=datenbank.engine).begin() as s:
            einwurf = _einwurf(s, von=ANDERE, destilled_by=PERSON)
            _satz(s, einwurf, ANDERE, "Nur noch dieser Satz steht da")

        _loeschen(datenbank)

        with sessionmaker(bind=datenbank.engine)() as s:
            destilled_by = s.get(RawInput, einwurf).destilled_by
        assert destilled_by not in (None, PERSON)

    def test_zwei_geloeschte_personen_am_selben_einwurf(self, datenbank, fangkorb):
        """Der eindeutige Index (Einwurf, Person) laesst keinen gemeinsamen Platzhalter zu."""
        with sessionmaker(bind=datenbank.engine).begin() as s:
            _satz(s, fangkorb.fremd, DRITTE, "Ein dritter Satz")

        _loeschen(datenbank, PERSON)
        _loeschen(datenbank, DRITTE)

        with sessionmaker(bind=datenbank.engine)() as s:
            saetze = _saetze(s, fangkorb.fremd)
        assert len(saetze) == 3
        assert PERSON not in saetze.values() and DRITTE not in saetze.values()
        ersatz = {saetze["Waermepumpen lohnen sich auch im Altbau"]}
        ersatz.add(saetze["Ein dritter Satz"])
        assert len(ersatz) == 2
        assert set(_anzeigenamen(datenbank, ersatz).values()) == {"ehemalige Person"}


class TestLoeschkommando:
    def test_keine_kennung_mehr_in_postgresql(self, datenbank, fangkorb):
        with sessionmaker(bind=datenbank.engine).begin() as s:
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

        with sessionmaker(bind=datenbank.engine)() as s:
            assert s.get(RawInput, fangkorb.eigen) is None
            assert _saetze(s, fangkorb.eigen) == {}

    def test_zweiter_lauf_aendert_nichts(self, datenbank, fangkorb):
        _loeschen(datenbank)
        with sessionmaker(bind=datenbank.engine)() as s:
            vorher = _saetze(s, fangkorb.fremd)

        _loeschen(datenbank)

        with sessionmaker(bind=datenbank.engine)() as s:
            assert _saetze(s, fangkorb.fremd) == vorher
