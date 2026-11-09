"""
Kontext der Beitragsseite (#603): welche Aussage, welche weiteren Antworten.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.models.content_type import ContentType
from domain.models.statement import (
    AntwortKurz,
    StatementDbEntry,
    StatementReplysuggestion,
)
from services.beitrag_kontext import (
    WEITERE_ANTWORTEN_HOECHSTENS,
    aussage_waehlen,
    kontext_laden,
)
from tests.conftest import create_base_content_fields

BEITRAG = uuid.uuid4()


def _vorschlag(beitrag_id, relevanz=1.0):
    return StatementReplysuggestion(
        id=beitrag_id,
        content_type=ContentType.COMMENTARY,
        relevance=relevanz,
        created="2026-11-01T12:00:00Z",
        updated="2026-11-01T12:00:00Z",
        number_of_usages=0,
    )


def _aussage(*vorschlaege, created="2026-11-01T12:00:00Z", text="Aussage"):
    felder = create_base_content_fields()
    felder["created"] = created
    return StatementDbEntry(
        **felder,
        id=uuid.uuid4(),
        text=text,
        replysuggestions=list(vorschlaege),
        replysuggestions_count=len(vorschlaege),
    )


def _dienst(aussagen, sichtbar=None):
    dienst = MagicMock()
    dienst.zu_antwort = AsyncMock(return_value=aussagen)
    dienst.sichtbare_antworten = AsyncMock(
        side_effect=lambda ids: [
            AntwortKurz(id=i, content_type=ContentType.COMMENTARY, titel="T")
            for i in ids
            if sichtbar is None or i in sichtbar
        ]
    )
    return dienst


@pytest.mark.unit
class TestAussageWaehlen:
    def test_ohne_aussage_none(self):
        assert aussage_waehlen([], BEITRAG) is None

    def test_die_mit_der_hoechsten_relevanz_des_beitrags(self):
        schwach = _aussage(_vorschlag(BEITRAG, 0.5))
        stark = _aussage(_vorschlag(BEITRAG, 0.9))

        assert aussage_waehlen([schwach, stark], BEITRAG) is stark

    def test_bei_gleichstand_die_aeltere(self):
        neu = _aussage(_vorschlag(BEITRAG), created="2026-11-05T12:00:00Z")
        alt = _aussage(_vorschlag(BEITRAG), created="2026-10-01T12:00:00Z")

        assert aussage_waehlen([neu, alt], BEITRAG) is alt


@pytest.mark.unit
@pytest.mark.asyncio
class TestKontextLaden:
    async def test_ohne_aussage_leer_und_ohne_zweiten_abruf(self):
        dienst = _dienst([])

        kontext = await kontext_laden(BEITRAG, dienst)

        assert kontext.aussage is None
        assert kontext.weitere_antworten == []
        dienst.sichtbare_antworten.assert_not_awaited()

    async def test_weitere_ohne_den_beitrag_nach_relevanz(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        aussage = _aussage(
            _vorschlag(a, 0.3), _vorschlag(BEITRAG, 1.0), _vorschlag(b, 0.8)
        )

        kontext = await kontext_laden(BEITRAG, _dienst([aussage]))

        assert kontext.aussage.id == aussage.id
        assert kontext.aussage.text == "Aussage"
        assert [w.id for w in kontext.weitere_antworten] == [b, a]

    async def test_gesperrte_fallen_weg(self):
        # sichtbare_antworten laesst gesperrte und geloeschte weg.
        a, b = uuid.uuid4(), uuid.uuid4()
        aussage = _aussage(_vorschlag(BEITRAG), _vorschlag(a), _vorschlag(b))

        kontext = await kontext_laden(BEITRAG, _dienst([aussage], sichtbar={b}))

        assert [w.id for w in kontext.weitere_antworten] == [b]

    async def test_hoechstens_fuenf_weitere(self):
        andere = [uuid.uuid4() for _ in range(WEITERE_ANTWORTEN_HOECHSTENS + 3)]
        aussage = _aussage(_vorschlag(BEITRAG), *(_vorschlag(i) for i in andere))

        kontext = await kontext_laden(BEITRAG, _dienst([aussage]))

        assert len(kontext.weitere_antworten) == WEITERE_ANTWORTEN_HOECHSTENS

    async def test_als_json(self):
        a = uuid.uuid4()
        aussage = _aussage(_vorschlag(BEITRAG), _vorschlag(a), text="Wind tötet Vögel")

        body = (await kontext_laden(BEITRAG, _dienst([aussage]))).als_json()

        assert body == {
            "aussage": {"id": str(aussage.id), "text": "Wind tötet Vögel"},
            "weitere_antworten": [
                {"id": str(a), "content_type": "commentary", "titel": "T"}
            ],
        }
