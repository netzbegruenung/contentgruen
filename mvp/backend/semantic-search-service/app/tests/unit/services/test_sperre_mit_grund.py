"""
Sperren mit Sperrgrund, Sperrnachricht und Widerspruch (#448).

Wer sperrt, gibt einen Sperrgrund aus der Liste und eine Begruendung an; ohne beides
gibt es keine Sperre. Die Sperre merkt sich den Autor des Beitrags: Nur er sieht die
Sperrnachricht und darf widersprechen. Ein Widerspruch landet bei den Admins, die die
Sperre bestaetigen oder entsperren. Das Repository ist gemockt; was es in PostgreSQL
tut, pruefen tests/integration/test_sperren_postgres.py.
"""

import re
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from domain.models.sperrgrund import SPERRGRUENDE
from repositories.implementations.qdrant.moderation_repository import (
    QdrantModerationRepository,
)
from repositories.sperre_repository import SperreRepository, Widerspruchsergebnis
from services.moderation_service import ModerationService, SperreUngueltig
from tests.conftest import create_base_content_fields

CONTENT_ID = str(uuid.uuid4())

FRONTEND_SPERRGRUENDE = (
    Path(__file__).resolve().parents[6]
    / "frontend/gutgesagt-frontend/src/app/shared/sperrgruende.ts"
)


def _beitrag(**felder) -> dict:
    return {
        **create_base_content_fields(),
        "id": CONTENT_ID,
        "title": "Tempolimit rettet Leben",
        "text": "Gemeldeter Kommentar",
        "status": "visible",
        "original_author": "autorin-1",
        **felder,
    }


@pytest.fixture
def speicher(test_embeddings_manager):
    test_embeddings_manager.add_test_data("commentary", [_beitrag()])
    return test_embeddings_manager


@pytest.fixture
def sperre_repo():
    return MagicMock(spec=SperreRepository)


@pytest.fixture
def service(speicher, sperre_repo):
    report_repo = MagicMock()
    report_repo.update_reports_by_content_id = MagicMock(return_value=1)
    return ModerationService(
        report_repo=report_repo,
        moderation_repo=QdrantModerationRepository(embeddings_manager=speicher),
        vote_repo=MagicMock(),
        raw_input_repo=MagicMock(),
        sperre_repo=sperre_repo,
    )


def _sperre(**felder) -> SimpleNamespace:
    werte = dict(
        id=uuid.uuid4(),
        content_id=uuid.UUID(CONTENT_ID),
        sperrgrund="unterstellung",
        begruendung="Unterstellt der Gegenseite Bosheit.",
        gesperrt_am=None,
        autor="autorin-1",
        widerspruch=None,
        widerspruch_am=None,
        pruefung=None,
        pruefung_begruendung=None,
        geprueft_am=None,
    )
    werte.update(felder)
    return SimpleNamespace(**werte)


@pytest.mark.unit
class TestSperrgruende:
    @pytest.mark.skipif(
        not FRONTEND_SPERRGRUENDE.exists(), reason="Frontend nicht im Checkout"
    )
    def test_sperrgruende_gleich_wie_im_frontend(self):
        quelltext = FRONTEND_SPERRGRUENDE.read_text(encoding="utf-8")
        werte = re.findall(r"value: '([^']+)'", quelltext)

        assert sorted(werte) == sorted(SPERRGRUENDE)


@pytest.mark.unit
@pytest.mark.asyncio
class TestSperrenVerlangtGrund:
    async def test_sperren_speichert_grund_begruendung_und_autor(
        self, service, sperre_repo, speicher
    ):
        assert await service.sperren(
            CONTENT_ID,
            gesperrt_von="admin-1",
            sperrgrund="unterstellung",
            begruendung="  Unterstellt der Gegenseite Bosheit. ",
        )

        assert speicher.get_data()[CONTENT_ID]["status"] == "blocked"
        kwargs = sperre_repo.anlegen.call_args.kwargs
        assert kwargs["content_id"] == uuid.UUID(CONTENT_ID)
        assert kwargs["sperrgrund"] == "unterstellung"
        assert kwargs["begruendung"] == "Unterstellt der Gegenseite Bosheit."
        assert kwargs["gesperrt_von"] == "admin-1"
        assert kwargs["autor"] == "autorin-1"

    @pytest.mark.parametrize(
        "grund,begruendung",
        [
            ("", "Begruendung"),
            ("fake_news", "Begruendung"),
            ("unterstellung", ""),
            ("unterstellung", "   "),
        ],
    )
    async def test_sperren_ohne_grund_ist_nicht_moeglich(
        self, service, sperre_repo, speicher, grund, begruendung
    ):
        with pytest.raises(SperreUngueltig):
            await service.sperren(
                CONTENT_ID,
                gesperrt_von="admin-1",
                sperrgrund=grund,
                begruendung=begruendung,
            )

        assert speicher.get_data()[CONTENT_ID]["status"] == "visible"
        sperre_repo.anlegen.assert_not_called()

    @pytest.mark.parametrize("autor", [None, "", "ehemalige-person"])
    async def test_sperren_ohne_kontakt_merkt_keinen_autor(
        self, test_embeddings_manager, sperre_repo, autor
    ):
        test_embeddings_manager.add_test_data(
            "commentary", [_beitrag(original_author=autor)]
        )
        service = ModerationService(
            report_repo=MagicMock(),
            moderation_repo=QdrantModerationRepository(
                embeddings_manager=test_embeddings_manager
            ),
            sperre_repo=sperre_repo,
        )

        await service.sperren(
            CONTENT_ID, "admin-1", sperrgrund="ohne_bezug", begruendung="Werbung"
        )

        assert sperre_repo.anlegen.call_args.kwargs["autor"] is None

    async def test_entsperren_hebt_die_sperre_auf(self, service, sperre_repo):
        await service.sperren(
            CONTENT_ID, "admin-1", sperrgrund="ohne_bezug", begruendung="Werbung"
        )

        assert await service.entsperren(CONTENT_ID, entsperrt_von="admin-2")

        args = sperre_repo.aufheben.call_args
        assert args.args[0] == uuid.UUID(CONTENT_ID)
        assert args.args[1] == "admin-2"


@pytest.mark.unit
@pytest.mark.asyncio
class TestSperrnachricht:
    async def test_meine_sperren_nennen_entscheidung_grund_und_beitrag(
        self, service, sperre_repo
    ):
        sperre = _sperre()
        sperre_repo.aktive_fuer_autor.return_value = [sperre]

        [nachricht] = await service.meine_sperren("autorin-1")

        sperre_repo.aktive_fuer_autor.assert_called_once_with("autorin-1")
        assert nachricht["id"] == str(sperre.id)
        assert nachricht["content_id"] == CONTENT_ID
        assert nachricht["content_type"] == "commentary"
        assert nachricht["titel"] == "Tempolimit rettet Leben"
        assert nachricht["sperrgrund"] == "unterstellung"
        assert nachricht["begruendung"] == "Unterstellt der Gegenseite Bosheit."
        assert nachricht["widerspruch_am"] is None
        assert nachricht["pruefung"] is None
        # Wer gesperrt hat, erfaehrt der Autor nicht.
        assert "gesperrt_von" not in nachricht

    async def test_meine_sperren_ohne_beitrag_ohne_titel(self, service, sperre_repo):
        sperre_repo.aktive_fuer_autor.return_value = [_sperre(content_id=uuid.uuid4())]

        [nachricht] = await service.meine_sperren("autorin-1")

        assert nachricht["titel"] is None
        assert nachricht["content_type"] is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestWiderspruch:
    async def test_widersprechen_traegt_text_ein(self, service, sperre_repo):
        sperre_id = uuid.uuid4()
        sperre_repo.widersprechen.return_value = Widerspruchsergebnis.ANGENOMMEN

        ergebnis = await service.widersprechen(
            str(sperre_id), "autorin-1", "  Das ist belegt. "
        )

        assert ergebnis is Widerspruchsergebnis.ANGENOMMEN
        args = sperre_repo.widersprechen.call_args.args
        assert args[:3] == (sperre_id, "autorin-1", "Das ist belegt.")

    async def test_widersprechen_ohne_text_ist_formlos_moeglich(
        self, service, sperre_repo
    ):
        sperre_repo.widersprechen.return_value = Widerspruchsergebnis.ANGENOMMEN

        await service.widersprechen(str(uuid.uuid4()), "autorin-1", "  ")

        assert sperre_repo.widersprechen.call_args.args[2] is None

    async def test_widersprechen_ungueltige_kennung(self, service, sperre_repo):
        ergebnis = await service.widersprechen("keine-uuid", "autorin-1", None)

        assert ergebnis is Widerspruchsergebnis.NICHT_GEFUNDEN
        sperre_repo.widersprechen.assert_not_called()

    async def test_sperre_bestaetigen_verlangt_begruendung(self, service, sperre_repo):
        with pytest.raises(SperreUngueltig):
            await service.sperre_bestaetigen(str(uuid.uuid4()), "admin-1", " ")

        sperre_repo.sperre_bestaetigen.assert_not_called()

    async def test_sperre_bestaetigen(self, service, sperre_repo):
        sperre_id = uuid.uuid4()
        sperre_repo.sperre_bestaetigen.return_value = True

        assert await service.sperre_bestaetigen(
            str(sperre_id), "admin-1", "Bleibt eine Unterstellung."
        )

        args = sperre_repo.sperre_bestaetigen.call_args.args
        assert args[:3] == (sperre_id, "admin-1", "Bleibt eine Unterstellung.")


@pytest.mark.unit
@pytest.mark.asyncio
class TestGesperrteFuerAdmins:
    async def test_gesperrte_tragen_ihre_sperre_und_offenen_widerspruch(
        self, service, sperre_repo
    ):
        await service.sperren(
            CONTENT_ID, "admin-1", sperrgrund="unterstellung", begruendung="x"
        )
        sperre = _sperre(widerspruch="Belegt.", widerspruch_am="2026-10-29")
        sperre_repo.aktive_je_beitrag.return_value = {sperre.content_id: sperre}

        [beitrag] = await service.gesperrte_beitraege()

        assert beitrag["sperre"]["sperrgrund"] == "unterstellung"
        assert beitrag["sperre"]["widerspruch"] == "Belegt."
        assert beitrag["sperre"]["widerspruch_offen"] is True
        assert beitrag["sperre"]["ohne_kontaktdaten"] is False

    async def test_gesperrte_ohne_autor_vermerken_keine_kontaktdaten(
        self, service, sperre_repo
    ):
        await service.sperren(
            CONTENT_ID, "admin-1", sperrgrund="unterstellung", begruendung="x"
        )
        sperre = _sperre(autor=None)
        sperre_repo.aktive_je_beitrag.return_value = {sperre.content_id: sperre}

        [beitrag] = await service.gesperrte_beitraege()

        assert beitrag["sperre"]["ohne_kontaktdaten"] is True
        assert beitrag["sperre"]["widerspruch_offen"] is False

    async def test_gesperrte_aus_der_zeit_vor_448_ohne_sperre(
        self, service, sperre_repo
    ):
        await service.sperren(
            CONTENT_ID, "admin-1", sperrgrund="unterstellung", begruendung="x"
        )
        sperre_repo.aktive_je_beitrag.return_value = {}

        [beitrag] = await service.gesperrte_beitraege()

        assert beitrag["sperre"] is None
