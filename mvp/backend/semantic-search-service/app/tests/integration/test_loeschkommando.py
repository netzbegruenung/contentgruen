"""
Das Loeschkommando (mvp/scripts/manual/person_loeschen.sql) gegen ein echtes PostgreSQL.

Das Skript ist fuer psql geschrieben; hier laeuft es Anweisung fuer Anweisung ueber
SQLAlchemy auf einer Verbindung, ``:'uid'`` wird zum Bind-Parameter - das ist
dieselbe Ersetzung, die psql mit ``-v uid=...`` vornimmt. Datenbank und Wegwerf-Schema
kommen aus ``conftest.py`` (siehe ``postgres.py``).
"""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import text

from api.v1.raw_input import _einwuerfe_fuer_aufrufer
from infrastructure.database.models import (
    Base,
    ContentReport,
    GeseheneNutzung,
    MusterHinweisZeile,
    RawInput,
    RawInputContentLink,
    RawInputDraft,
    Sperre,
    UsageEvent,
    UsageTracking,
    User,
)
from repositories.raw_input_repository import RawInputRepository
from repositories.user_repository import UserRepository
from services.anzeigename_service import AnzeigenameService
from services.beitrag_fuer_aufrufer import Aufrufer
from tests.integration import postgres

SKRIPT = postgres.REPO_WURZEL / "mvp" / "scripts" / "manual" / "person_loeschen.sql"

PERSON = "person-die-loescht"
ANDERE = "andere-person"
DRITTE = "dritte-person"

SATZ_DER_PERSON = "Waermepumpen lohnen sich auch im Altbau"
SATZ_DER_ANDEREN = "Die Foerderung macht den Unterschied"

pytestmark = pytest.mark.integration


def _anweisungen(skript: str):
    """Die Anweisungen des Skripts, ``:'uid'`` als Bind-Parameter."""
    for anweisung in postgres.anweisungen(skript):
        anweisung = anweisung.replace(":'uid'", ":uid")
        # Was nur psql versteht, liefe hier still falsch: andere Variablen,
        # Metakommandos.
        assert ":'" not in anweisung and "\\" not in anweisung, anweisung
        yield anweisung


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
    with patch(
        "services.beitrag_fuer_aufrufer.get_anzeigename_service", return_value=dienst
    ):
        (sicht,) = _einwuerfe_fuer_aufrufer([zeile], Aufrufer(aufrufer))
    return sicht.model_dump()


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
def einwuerfe(datenbank):
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
    def test_satz_bleibt_ohne_kennung_der_person(self, datenbank, einwuerfe):
        _loeschen(datenbank)

        saetze = _saetze(datenbank, einwuerfe.fremd)
        assert set(saetze) == {SATZ_DER_PERSON, SATZ_DER_ANDEREN}
        assert PERSON not in saetze.values()
        assert saetze[SATZ_DER_ANDEREN] == ANDERE

    def test_fangkorb_zeigt_ehemalige_person(self, datenbank, einwuerfe):
        _loeschen(datenbank)

        einwurf = _im_fangkorb(datenbank, einwuerfe.fremd)
        namen = {d["sentence"]: d["user_name"] for d in einwurf["drafts"]}
        assert namen == {
            SATZ_DER_PERSON: "ehemalige Person",
            SATZ_DER_ANDEREN: "Ben C.",
        }
        assert einwurf["own_draft"] == SATZ_DER_ANDEREN

    def test_destillierer_ist_der_platzhalter_des_satzes(self, datenbank, einwuerfe):
        _loeschen(datenbank)

        destilled_by = _destilled_by(datenbank, einwuerfe.fremd)
        assert destilled_by != PERSON
        assert destilled_by == _saetze(datenbank, einwuerfe.fremd)[SATZ_DER_PERSON]

    def test_destillierer_ohne_eigenen_satz_wird_ersetzt(self, datenbank):
        """Wer den ersten Satz spaeter geleert hat, bleibt trotzdem Destillierer."""
        with datenbank.get_session() as s:
            einwurf = _einwurf(s, von=ANDERE, destilled_by=PERSON)
            _satz(s, einwurf, ANDERE, "Nur noch dieser Satz steht da")

        _loeschen(datenbank)

        destilled_by = _destilled_by(datenbank, einwurf)
        assert destilled_by.startswith("ehemalige-person-")
        # Kein Codepfad zeigt einen Namen zu destilled_by, also keine Zeile in users.
        assert _anzeigenamen(datenbank, [destilled_by]) == {}

    def test_zwei_geloeschte_personen_am_selben_einwurf(self, datenbank, einwuerfe):
        """Der eindeutige Index (Einwurf, Person) laesst keinen gemeinsamen Platzhalter zu."""
        with datenbank.get_session() as s:
            _satz(s, einwuerfe.fremd, DRITTE, "Ein dritter Satz")

        _loeschen(datenbank, PERSON)
        _loeschen(datenbank, DRITTE)

        saetze = _saetze(datenbank, einwuerfe.fremd)
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


@pytest.fixture
def spuren(datenbank, einwuerfe):
    """
    Was sonst an der Kennung haengt: Stimme, Meldung samt Sitzung und deren
    Nutzung, eine bearbeitete Meldung, eine Verknuepfung auf den Satz der Person.
    """
    beitrag = uuid.uuid4()
    with datenbank.get_session() as s:
        s.execute(
            text(
                "INSERT INTO votes (user_id, content_id, vote_type)"
                " VALUES (:uid, :beitrag, 'like')"
            ),
            {"uid": PERSON, "beitrag": beitrag},
        )
        s.add(GeseheneNutzung(user_id=PERSON, nutzung=3))
        # Muster-Hinweise (#352): einer mit der Person, einer ohne sie.
        for a, b in [(ANDERE, PERSON), (ANDERE, DRITTE)]:
            s.add(
                MusterHinweisZeile(
                    konto_a=a,
                    konto_b=b,
                    tage=1,
                    erster_tag=date(2026, 10, 26),
                    letzter_tag=date(2026, 10, 26),
                )
            )
        s.add(UsageTracking(content_id=beitrag))
        s.flush()
        s.add(UsageEvent(content_id=beitrag, session_id="sitzung-der-person"))
        s.add(UsageEvent(content_id=beitrag, session_id="sitzung-anderer"))
        s.add(
            ContentReport(
                content_id=beitrag,
                content_type="commentary",
                reported_by_user_id=PERSON,
                reported_by_session_id="sitzung-der-person",
                reason="spam",
            )
        )
        bearbeitet = ContentReport(
            content_id=beitrag,
            content_type="commentary",
            reported_by_user_id=ANDERE,
            reason="spam",
            reviewed_by=PERSON,
        )
        s.add(bearbeitet)
        satz = (
            s.query(RawInputDraft)
            .filter_by(raw_input_id=einwuerfe.fremd, user_id=PERSON)
            .one()
        )
        link = RawInputContentLink(
            raw_input_id=einwuerfe.fremd,
            content_id=beitrag,
            created_by=PERSON,
            draft_id=satz.id,
        )
        s.add(link)
        # Eine Sperre am Beitrag der Person mit ihrem Widerspruch, eine von ihr
        # gesperrte und geprueft (#448).
        eigene_sperre = Sperre(
            content_id=uuid.uuid4(),
            sperrgrund="unterstellung",
            begruendung="Unterstellt Bosheit.",
            gesperrt_von=ANDERE,
            autor=PERSON,
            widerspruch="Das ist belegt.",
        )
        fremde_sperre = Sperre(
            content_id=beitrag,
            sperrgrund="ohne_bezug",
            begruendung="Werbung",
            gesperrt_von=PERSON,
            autor=ANDERE,
            geprueft_von=PERSON,
        )
        s.add_all([eigene_sperre, fremde_sperre])
        s.flush()
        return SimpleNamespace(
            bearbeitet=bearbeitet.id,
            link=link.id,
            satz=satz.id,
            eigene_sperre=eigene_sperre.id,
            fremde_sperre=fremde_sperre.id,
        )


class TestLoeschkommando:
    def test_keine_kennung_mehr_in_postgresql(self, datenbank, spuren):
        _loeschen(datenbank)

        assert _kennung_irgendwo(datenbank, PERSON) == []

    def test_fremdes_bleibt_ohne_kennung(self, datenbank, spuren):
        _loeschen(datenbank)

        with datenbank.get_session() as s:
            meldungen = s.query(ContentReport).all()
            assert [(m.id, m.reviewed_by) for m in meldungen] == [
                (spuren.bearbeitet, None)
            ]
            link = s.get(RawInputContentLink, spuren.link)
            assert (link.created_by, link.draft_id) == (None, spuren.satz)
            assert s.get(RawInputDraft, spuren.satz).sentence == SATZ_DER_PERSON

    def test_muster_hinweise_ohne_die_person_bleiben(self, datenbank, spuren):
        _loeschen(datenbank)

        with datenbank.get_session() as s:
            assert [(h.konto_a, h.konto_b) for h in s.query(MusterHinweisZeile)] == [
                (ANDERE, DRITTE)
            ]

    def test_sperren_bleiben_ohne_kennung_und_ohne_widerspruch(self, datenbank, spuren):
        _loeschen(datenbank)

        with datenbank.get_session() as s:
            eigene = s.get(Sperre, spuren.eigene_sperre)
            assert (eigene.autor, eigene.widerspruch) == (None, None)
            assert eigene.gesperrt_von == ANDERE
            assert eigene.begruendung == "Unterstellt Bosheit."
            fremde = s.get(Sperre, spuren.fremde_sperre)
            assert (fremde.gesperrt_von, fremde.geprueft_von) == (None, None)
            assert fremde.autor == ANDERE

    def test_nutzung_der_sitzung_weg(self, datenbank, spuren):
        _loeschen(datenbank)

        with datenbank.get_session() as s:
            sitzungen = [e.session_id for e in s.query(UsageEvent)]
        assert sitzungen == ["sitzung-anderer"]

    def test_eigene_einwuerfe_samt_saetzen_weg(self, datenbank, einwuerfe):
        _loeschen(datenbank)

        assert RawInputRepository(datenbank).get_by_id(einwuerfe.eigen) is None
        assert _saetze(datenbank, einwuerfe.eigen) == {}

    def test_zweiter_lauf_aendert_nichts(self, datenbank, einwuerfe):
        _loeschen(datenbank)
        vorher = _saetze(datenbank, einwuerfe.fremd)

        _loeschen(datenbank)

        assert _saetze(datenbank, einwuerfe.fremd) == vorher
