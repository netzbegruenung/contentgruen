"""
Woraus Punkte entstehen (#352), gegen ein echtes PostgreSQL: Zustimmung anderer und
ausformulierte Einwuerfe. Wegwerf-Schema aus der Fixture ``datenbank`` von
``test_loeschkommando.py``.
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text

from infrastructure.database.models import RawInput, RawInputContentLink, Sperre
from repositories.punkte_repository import PunkteRepository
from repositories.vote_repository import VoteRepository
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

pytestmark = pytest.mark.integration

SPAETER = datetime(2026, 11, 30, tzinfo=timezone.utc)


def _stimme(datenbank, von: str, beitrag: uuid.UUID, art: str) -> None:  # noqa: F811
    with datenbank.get_session() as s:
        s.execute(
            text(
                "INSERT INTO votes (user_id, content_id, vote_type)"
                " VALUES (:u, :c, :a)"
            ),
            {"u": von, "c": str(beitrag), "a": art},
        )


def _einwurf(
    datenbank, von: str, verknuepft_am: list, gesperrt: bool = False  # noqa: F811
) -> None:
    with datenbank.get_session() as s:
        einwurf = RawInput(content="Fundstueck", submitted_by=von, status="done")
        s.add(einwurf)
        s.flush()
        for am in verknuepft_am:
            beitrag = uuid.uuid4()
            s.add(
                RawInputContentLink(
                    raw_input_id=einwurf.id,
                    content_id=beitrag,
                    created_by="ausformuliererin",
                    created_at=am,
                )
            )
            if gesperrt:
                s.add(
                    Sperre(
                        content_id=beitrag,
                        sperrgrund="ohne_bezug",
                        begruendung="Werbung",
                    )
                )


class TestPunkteQuellen:
    def test_zustimmungen_nur_likes_ohne_ausgenommene(self, datenbank):  # noqa: F811
        repo = PunkteRepository(datenbank)
        eins, zwei, fremd = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        _stimme(datenbank, "bo-2", eins, "like")
        _stimme(datenbank, "ali-3", eins, "like")
        _stimme(datenbank, "bo-2", zwei, "like")
        _stimme(datenbank, "ali-3", zwei, "dislike")
        _stimme(datenbank, "kim-1", zwei, "like")
        _stimme(datenbank, "start-9", zwei, "like")
        _stimme(datenbank, "bo-2", fremd, "like")

        assert repo.zustimmungen([eins, zwei], {"kim-1", "start-9"}) == 3
        assert repo.zustimmungen([], {"kim-1"}) == 0

    def test_einwuerfe_ausformuliert_je_tag_der_ersten_verknuepfung(
        self, datenbank  # noqa: F811
    ):
        repo = PunkteRepository(datenbank)
        montag = datetime(2026, 10, 26, 9, tzinfo=timezone.utc)
        dienstag = datetime(2026, 10, 27, 9, tzinfo=timezone.utc)
        _einwurf(datenbank, "kim-1", [montag, dienstag])
        _einwurf(datenbank, "kim-1", [dienstag])
        _einwurf(datenbank, "kim-1", [])
        _einwurf(datenbank, "bo-2", [montag])

        assert repo.einwuerfe_ausformuliert_je_tag("kim-1", bis=SPAETER) == {
            date(2026, 10, 26): 1,
            date(2026, 10, 27): 1,
        }

    def test_einwuerfe_ausformuliert_je_tag_erst_nach_der_wartezeit(
        self, datenbank  # noqa: F811
    ):
        repo = PunkteRepository(datenbank)
        _einwurf(datenbank, "kim-1", [datetime(2026, 10, 26, 9, tzinfo=timezone.utc)])

        bis_sonntag = datetime(2026, 10, 25, 23, tzinfo=timezone.utc)
        assert repo.einwuerfe_ausformuliert_je_tag("kim-1", bis=bis_sonntag) == {}

    def test_einwuerfe_ausformuliert_je_tag_ohne_gesperrten_beitrag(
        self, datenbank  # noqa: F811
    ):
        repo = PunkteRepository(datenbank)
        montag = datetime(2026, 10, 26, 9, tzinfo=timezone.utc)
        _einwurf(datenbank, "kim-1", [montag], gesperrt=True)

        assert repo.einwuerfe_ausformuliert_je_tag("kim-1", bis=SPAETER) == {}


class TestStimmenVonStartkonten:
    def test_get_vote_counts_ohne_ausgenommene(self, datenbank):  # noqa: F811
        beitrag = uuid.uuid4()
        _stimme(datenbank, "bo-2", beitrag, "like")
        _stimme(datenbank, "start-9", beitrag, "like")
        _stimme(datenbank, "start-8", beitrag, "dislike")
        repo = VoteRepository(datenbank)

        assert repo.get_vote_counts(beitrag) == {"likes": 2, "dislikes": 1}
        assert repo.get_vote_counts(beitrag, {"start-9", "start-8"}) == {
            "likes": 1,
            "dislikes": 0,
        }
