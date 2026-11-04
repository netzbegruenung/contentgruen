"""
Der Autor aendert seinen Beitrag: Titel, Text und Herkunft (BeitragAendernService, #299).

Gegen den Speicher-Modus: Was der Service schreibt, liest der naechste Leser ueber das
Repository. Dass die Suche den neuen Text findet, zeigt der Integrationstest gegen
echtes Qdrant (tests/integration/test_autor_aendert.py).
"""

import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from core.fehler import Validierungsfehler
from domain.models.content_status import AUSGEBLENDET, ContentStatus
from repositories.aggregated.content_repository import ContentRepository
from services.content.beitrag_aendern_service import (
    AenderErgebnis,
    Aenderung,
    BeitragAendernService,
    HerkunftAngabe,
)
from tests.conftest import create_base_content_fields

BEITRAG_ID = str(uuid.uuid4())
AUTOR = "autor-1"
HERKUNFT_ID = uuid.uuid4()

AENDERUNG = Aenderung(
    titel="Wärmepumpe spart auch im Altbau Geld",
    text="Mit Flächenheizung und gedämmtem Dach rechnet sie sich nach wenigen Jahren.",
    herkuenfte=[HerkunftAngabe("https://example.org/studie", "Feldtest 2025")],
)


def _beitrag(content_type="commentary", **felder):
    return {
        **create_base_content_fields(original_author=AUTOR, last_modified_by=AUTOR),
        "id": BEITRAG_ID,
        "title": "Wärmepumpe lohnt sich auch im Altbau",
        "text": "Alter Text",
        "references": [],
        "references_count": 0,
        "status": ContentStatus.VISIBLE.value,
        **felder,
        "content_type": content_type,
    }


@pytest.fixture
def speicher(test_embeddings_manager):
    return test_embeddings_manager


@pytest.fixture
def herkunft_id():
    return AsyncMock(return_value=HERKUNFT_ID)


@pytest.fixture
def offene_meldung():
    return Mock(return_value=False)


@pytest.fixture
def service(test_settings, speicher, herkunft_id, offene_meldung):
    return BeitragAendernService(
        ContentRepository(test_settings, speicher), herkunft_id, offene_meldung
    )


def _gespeichert(speicher) -> dict:
    return speicher.get_data()[BEITRAG_ID]


@pytest.mark.unit
@pytest.mark.asyncio
class TestBeitragAendern:
    @pytest.mark.parametrize("typ", ["commentary", "generic_text"])
    async def test_aendern_autor_schreibt_titel_text_und_herkunft(
        self, service, speicher, herkunft_id, typ
    ):
        speicher.add_test_data(typ, [_beitrag(typ)])

        ergebnis = await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, AENDERUNG)

        assert ergebnis is AenderErgebnis.GEAENDERT
        gespeichert = _gespeichert(speicher)
        assert gespeichert["title"] == AENDERUNG.titel
        assert gespeichert["text"] == AENDERUNG.text
        assert [r["reference_id"] for r in gespeichert["references"]] == [
            str(HERKUNFT_ID)
        ]
        assert gespeichert["references"][0]["description"] == "Feldtest 2025"
        assert gespeichert["references_count"] == 1
        herkunft_id.assert_awaited_once_with(
            "https://example.org/studie", "Feldtest 2025", AUTOR
        )

    async def test_aendern_berechnet_den_vektor_aus_dem_neuen_text(
        self, service, speicher
    ):
        speicher.add_test_data("commentary", [_beitrag()])

        await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, AENDERUNG)

        assert speicher.vektor_texte[BEITRAG_ID] == AENDERUNG.text
        # Auch die Normalform der Dublettenpruefung folgt dem neuen Text.
        assert _gespeichert(speicher)["text_normalisiert"] != "alter text"

    async def test_aendern_schreibt_den_aenderungsverlauf_fort(self, service, speicher):
        frueher = {"editor": AUTOR, "timestamp": "2026-10-01T10:00:00+00:00"}
        speicher.add_test_data("commentary", [_beitrag(edit_history=[frueher])])

        await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, AENDERUNG)

        gespeichert = _gespeichert(speicher)
        verlauf = gespeichert["edit_history"]
        assert len(verlauf) == 2
        assert verlauf[0]["timestamp"].startswith("2026-10-01")
        assert verlauf[1]["editor"] == AUTOR
        assert verlauf[1]["action"] == "edit"
        assert gespeichert["last_modified_by"] == AUTOR
        assert gespeichert["last_modified"] == verlauf[1]["timestamp"]

    async def test_aendern_speichert_den_gezeigten_cc0_wortlaut(
        self, service, speicher
    ):
        speicher.add_test_data("commentary", [_beitrag(cc0_wortlaut=None)])
        mit_hinweis = Aenderung(
            AENDERUNG.titel, AENDERUNG.text, [], cc0_wortlaut="2026-11-02-formular"
        )

        await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, mit_hinweis)

        assert _gespeichert(speicher)["cc0_wortlaut"] == "2026-11-02-formular"

    async def test_inhalt_aendern_gesperrt_bekommt_keinen_neuen_vektor(
        self, test_settings, speicher
    ):
        """Sperrt ein Admin zwischen Lesen und Schreiben: Text und Vektor bleiben."""
        speicher.add_test_data(
            "commentary", [_beitrag(status=ContentStatus.BLOCKED.value)]
        )

        await ContentRepository(test_settings, speicher).inhalt_aendern(
            uuid.UUID(BEITRAG_ID),
            "commentary",
            {"text": "Neuer Text"},
            nicht_aus=AUSGEBLENDET,
        )

        assert _gespeichert(speicher)["text"] == "Alter Text"
        assert BEITRAG_ID not in speicher.vektor_texte

    async def test_aendern_andere_person_aendert_nichts(
        self, service, speicher, herkunft_id
    ):
        speicher.add_test_data("commentary", [_beitrag()])

        ergebnis = await service.aendern(uuid.UUID(BEITRAG_ID), "andere", AENDERUNG)

        assert ergebnis is AenderErgebnis.NICHT_AUTOR
        assert _gespeichert(speicher)["text"] == "Alter Text"
        herkunft_id.assert_not_awaited()

    async def test_aendern_mit_offener_meldung_aendert_nichts(
        self, service, speicher, herkunft_id, offene_meldung
    ):
        """Der Admin soll den gemeldeten Wortlaut sehen, nicht einen neuen."""
        speicher.add_test_data("commentary", [_beitrag()])
        offene_meldung.return_value = True

        ergebnis = await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, AENDERUNG)

        assert ergebnis is AenderErgebnis.MELDUNG_OFFEN
        offene_meldung.assert_called_once_with(uuid.UUID(BEITRAG_ID))
        assert _gespeichert(speicher)["text"] == "Alter Text"
        herkunft_id.assert_not_awaited()

    async def test_aendern_andere_person_verraet_keine_meldung(
        self, service, speicher, offene_meldung
    ):
        speicher.add_test_data("commentary", [_beitrag()])
        offene_meldung.return_value = True

        ergebnis = await service.aendern(uuid.UUID(BEITRAG_ID), "andere", AENDERUNG)

        assert ergebnis is AenderErgebnis.NICHT_AUTOR

    @pytest.mark.parametrize(
        "status", [ContentStatus.BLOCKED.value, ContentStatus.DELETED.value]
    )
    async def test_aendern_gesperrt_oder_geloescht_ist_nicht_da(
        self, service, speicher, status
    ):
        speicher.add_test_data("commentary", [_beitrag(status=status)])

        ergebnis = await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, AENDERUNG)

        assert ergebnis is AenderErgebnis.NICHT_DA
        assert _gespeichert(speicher)["text"] == "Alter Text"

    async def test_aendern_aussage_ist_kein_beitrag(self, service, speicher):
        speicher.add_test_data("statement", [_beitrag("statement")])

        ergebnis = await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, AENDERUNG)

        assert ergebnis is AenderErgebnis.NICHT_DA

    async def test_aendern_unbekannte_id_ist_nicht_da(self, service):
        ergebnis = await service.aendern(uuid.uuid4(), AUTOR, AENDERUNG)

        assert ergebnis is AenderErgebnis.NICHT_DA

    @pytest.mark.parametrize("typ", ["post", "image"])
    async def test_aendern_post_und_bild_sind_nicht_aenderbar(
        self, service, speicher, typ
    ):
        speicher.add_test_data(typ, [_beitrag(typ)])

        ergebnis = await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, AENDERUNG)

        assert ergebnis is AenderErgebnis.NICHT_AENDERBAR
        assert _gespeichert(speicher)["text"] == "Alter Text"

    @pytest.mark.parametrize(
        "typ, zeichen", [("commentary", 501), ("generic_text", 2001)]
    )
    async def test_aendern_zu_langer_text_wie_beim_anlegen(
        self, service, speicher, typ, zeichen
    ):
        speicher.add_test_data(typ, [_beitrag(typ)])
        zu_lang = Aenderung(AENDERUNG.titel, "x" * zeichen, [])

        with pytest.raises(Validierungsfehler):
            await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, zu_lang)

        assert _gespeichert(speicher)["text"] == "Alter Text"

    async def test_aendern_ohne_herkunft_entfernt_sie(self, service, speicher):
        verknuepft = {
            "reference_id": str(uuid.uuid4()),
            "created": "2026-10-01T10:00:00+00:00",
        }
        speicher.add_test_data(
            "commentary", [_beitrag(references=[verknuepft], references_count=1)]
        )

        await service.aendern(
            uuid.UUID(BEITRAG_ID), AUTOR, Aenderung(AENDERUNG.titel, "Neu", [])
        )

        assert _gespeichert(speicher)["references"] == []
        assert _gespeichert(speicher)["references_count"] == 0
