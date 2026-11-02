"""
Kennungen auf den Realm von Gut gesagt umstellen (#487), PostgreSQL-Teil, gegen ein
echtes PostgreSQL.

Die Daten sind dieselben wie beim Loeschkommando (test_loeschkommando.py): eine
Person mit einer Spur in jeder Spalte, die eine Kennung traegt. Was dort geloescht
wird, wird hier auf die neue Kennung umgeschrieben.
"""

import uuid

import pytest
from sqlalchemy import text

from infrastructure.database.models import GeseheneNutzung, RawInputDraft, User
from services.wartung.kennungen_umstellen import (
    kennungen_in_postgres,
    postgres_umschreiben,
)
from tests.integration.test_loeschkommando import (  # noqa: F401 (Fixtures)
    ANDERE,
    PERSON,
    _kennung_irgendwo,
    _satz,
    datenbank,
    einwuerfe,
    spuren,
)

pytestmark = pytest.mark.integration

NEU = "neu-im-realm-gutgesagt"

# Je Spalte genau eine Spur der Person (Fixture spuren).
JE_SPALTE_EINE = {
    "users.user_id": 1,
    "gesehene_nutzung.user_id": 1,
    "votes.user_id": 1,
    "raw_inputs.submitted_by": 1,
    "raw_inputs.destilled_by": 1,
    "raw_input_drafts.user_id": 1,
    "raw_input_content_links.created_by": 1,
    "content_reports.reported_by_user_id": 1,
    "content_reports.reviewed_by": 1,
    "sperren.autor": 1,
    "sperren.gesperrt_von": 1,
    "sperren.geprueft_von": 1,
}


def _umschreiben(datenbank, zuordnung=None, ausfuehren=True):
    with datenbank.engine.connect() as verbindung:
        return postgres_umschreiben(
            verbindung, zuordnung or {PERSON: NEU}, ausfuehren=ausfuehren
        )


def _stimmen(datenbank, kennung):
    with datenbank.engine.connect() as c:
        return c.execute(
            text("SELECT content_id, vote_type FROM votes WHERE user_id = :k"),
            {"k": kennung},
        ).all()


class TestPostgresUmschreiben:
    def test_keine_alte_kennung_mehr_und_jede_spur_an_der_neuen(
        self, datenbank, spuren
    ):
        bericht = _umschreiben(datenbank)

        assert _kennung_irgendwo(datenbank, PERSON) == []
        assert sorted(_kennung_irgendwo(datenbank, NEU)) == sorted(JE_SPALTE_EINE)
        assert bericht.geaendert == JE_SPALTE_EINE
        assert bericht.stehen_geblieben == 0

    def test_trockenlauf_zaehlt_gleich_und_aendert_nichts(self, datenbank, spuren):
        bericht = _umschreiben(datenbank, ausfuehren=False)

        assert bericht.geaendert == JE_SPALTE_EINE
        assert sorted(_kennung_irgendwo(datenbank, PERSON)) == sorted(JE_SPALTE_EINE)
        assert _kennung_irgendwo(datenbank, NEU) == []

    def test_zweiter_lauf_zaehlt_null(self, datenbank, spuren):
        _umschreiben(datenbank)

        bericht = _umschreiben(datenbank)

        assert set(bericht.geaendert.values()) == {0}

    def test_fremde_kennungen_bleiben(self, datenbank, spuren):
        vorher = sorted(_kennung_irgendwo(datenbank, ANDERE))

        _umschreiben(datenbank)

        assert sorted(_kennung_irgendwo(datenbank, ANDERE)) == vorher

    def test_anzeigename_und_stimme_der_neuen_kennung_gewinnen(self, datenbank, spuren):
        """Hat die neue Kennung schon eine Zeile, bleibt ihre; die alte geht."""
        beitrag = uuid.uuid4()
        with datenbank.get_session() as s:
            s.add(User(user_id=NEU, anzeigename="Anna im Realm"))
            s.add(GeseheneNutzung(user_id=NEU, nutzung=7))
            for kennung, art in ((PERSON, "like"), (NEU, "dislike")):
                s.execute(
                    text(
                        "INSERT INTO votes (user_id, content_id, vote_type)"
                        " VALUES (:k, :b, :art)"
                    ),
                    {"k": kennung, "b": beitrag, "art": art},
                )

        _umschreiben(datenbank)

        with datenbank.get_session() as s:
            assert s.get(User, NEU).anzeigename == "Anna im Realm"
            assert s.get(GeseheneNutzung, NEU).nutzung == 7
        stimmen = _stimmen(datenbank, NEU)
        assert (beitrag, "dislike") in stimmen
        assert len(stimmen) == 2  # die eine aus spuren dazu
        assert _kennung_irgendwo(datenbank, PERSON) == []

    def test_satz_beider_kennungen_am_selben_einwurf_bleibt_stehen(
        self, datenbank, einwuerfe
    ):
        """Zwei Saetze derselben Person an einem Einwurf laesst der Index nicht zu."""
        with datenbank.get_session() as s:
            _satz(s, einwuerfe.fremd, NEU, "Schon im Realm geschrieben")

        bericht = _umschreiben(datenbank)

        assert bericht.stehen_geblieben == 1
        assert bericht.geaendert["raw_input_drafts.user_id"] == 0
        with datenbank.get_session() as s:
            saetze = s.query(RawInputDraft).filter_by(raw_input_id=einwuerfe.fremd)
            assert {d.user_id for d in saetze} == {PERSON, NEU, ANDERE}


class TestKennungenInPostgres:
    def test_findet_jede_kennung_ausser_platzhaltern(self, datenbank, spuren):
        with datenbank.get_session() as s:
            s.add(User(user_id="ehemalige-person-123", anzeigename="ehemalige Person"))

        with datenbank.engine.connect() as verbindung:
            assert kennungen_in_postgres(verbindung) == {PERSON, ANDERE}
