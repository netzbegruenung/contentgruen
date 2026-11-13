"""
Loeschauftraege nach dem Widerruf der Art.-9-Einwilligung (DSFA R9b) gegen ein
echtes PostgreSQL: Anlegen im Widerruf, hoechstens ein offener je Person, der
PostgreSQL-Teil des Loeschablaufs, die Frist erledigter Auftraege und die Migration.

Daten wie beim Loeschkommando (test_loeschkommando.py): Was dort mit dem Konto geht,
verliert hier nur bei Einwuerfen und Saetzen den Personenbezug; Konto, Anzeigename
und Einwilligung bleiben.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from infrastructure.database.models import (
    Art9EinwilligungZeile,
    AusformuliertIn,
    LoeschauftragZeile,
    Satz,
    Sperre,
    User,
)
from repositories.art9_einwilligung_repository import Art9EinwilligungRepository
from repositories.einwurf_repository import EinwurfRepository
from repositories.loeschauftrag_repository import FRIST_TAGE, LoeschauftragRepository
from repositories.vote_repository import VoteRepository
from services.art9_einwilligung_service import Art9EinwilligungService
from tests.integration import postgres
from tests.integration.test_loeschkommando import (  # noqa: F401 (Fixtures)
    ANDERE,
    PERSON,
    SATZ_DER_ANDEREN,
    SATZ_DER_PERSON,
    _anzeigenamen,
    _destilled_by,
    _saetze,
    datenbank,
    einwuerfe,
)

MIGRATION = postgres.MIGRATIONEN / "2026-11-13-loeschauftraege.sql"

pytestmark = pytest.mark.integration


@pytest.fixture
def auftraege(datenbank):
    return LoeschauftragRepository(datenbank)


def _zeilen(datenbank):
    with datenbank.get_session() as s:
        return [
            (z.user_id, z.erledigt_am is not None)
            for z in s.query(LoeschauftragZeile).order_by(
                LoeschauftragZeile.angelegt_am
            )
        ]


class TestWiderruf:
    @pytest.fixture
    def dienst(self, datenbank, auftraege):
        return Art9EinwilligungService(
            Art9EinwilligungRepository(datenbank), VoteRepository(datenbank), auftraege
        )

    def test_widerruf_legt_einen_auftrag_mit_frist_an(self, dienst, auftraege):
        dienst.einwilligen(PERSON, "2026-11-12")

        dienst.widerrufen(PERSON)

        (auftrag,) = auftraege.offene()
        assert auftrag.user_id == PERSON
        assert auftrag.frist - auftrag.angelegt_am == timedelta(days=FRIST_TAGE)
        assert auftrag.erledigt_am is None

    def test_zweiter_widerruf_kein_zweiter_offener_auftrag(
        self, dienst, auftraege, datenbank
    ):
        dienst.einwilligen(PERSON, "2026-11-12")
        dienst.widerrufen(PERSON)
        dienst.einwilligen(PERSON, "2026-11-12")

        dienst.widerrufen(PERSON)

        assert _zeilen(datenbank) == [(PERSON, False)]

    def test_nach_erledigtem_auftrag_neuer_widerruf_neuer_auftrag(
        self, dienst, auftraege, datenbank, einwuerfe
    ):
        dienst.einwilligen(PERSON, "2026-11-12")
        dienst.widerrufen(PERSON)
        (erster,) = auftraege.offene()
        auftraege.ausfuehren(erster)
        dienst.einwilligen(PERSON, "2026-11-12")

        dienst.widerrufen(PERSON)

        assert _zeilen(datenbank) == [(PERSON, True), (PERSON, False)]

    def test_scheitert_der_auftrag_gilt_der_widerruf_nicht(self, datenbank):
        """Eine Transaktion wie beim Loeschen der Stimmen."""
        from unittest.mock import MagicMock

        kaputt = MagicMock()
        kaputt.anlegen.side_effect = RuntimeError("Datenbank weg")
        stimmen = VoteRepository(datenbank)
        dienst = Art9EinwilligungService(
            Art9EinwilligungRepository(datenbank), stimmen, kaputt
        )
        dienst.einwilligen(PERSON, "2026-11-12")

        with pytest.raises(RuntimeError):
            dienst.widerrufen(PERSON)

        assert dienst.eingewilligt(PERSON)


class TestAusfuehren:
    @pytest.fixture
    def auftrag(self, auftraege):
        auftraege.anlegen(PERSON)
        (auftrag,) = auftraege.offene()
        return auftrag

    def test_eigene_einwuerfe_weg_fremde_saetze_mit_platzhalter(
        self, datenbank, einwuerfe, auftraege, auftrag
    ):
        bericht = auftraege.ausfuehren(auftrag)

        assert (bericht.einwuerfe, bericht.saetze) == (1, 1)
        assert EinwurfRepository(datenbank).get_by_id(einwuerfe.eigen) is None
        saetze = _saetze(datenbank, einwuerfe.fremd)
        assert set(saetze) == {SATZ_DER_PERSON, SATZ_DER_ANDEREN}
        assert saetze[SATZ_DER_ANDEREN] == ANDERE
        platzhalter = saetze[SATZ_DER_PERSON]
        assert platzhalter.startswith("ehemalige-person-")
        assert _anzeigenamen(datenbank, [platzhalter]) == {
            platzhalter: "ehemalige Person"
        }
        assert _destilled_by(datenbank, einwuerfe.fremd) == platzhalter

    def test_konto_name_und_einwilligung_bleiben(
        self, datenbank, einwuerfe, auftraege, auftrag
    ):
        with datenbank.get_session() as s:
            s.add(
                Art9EinwilligungZeile(
                    user_id=PERSON,
                    wortlaut="2026-11-12",
                    eingewilligt_am=datetime.now(timezone.utc),
                    widerrufen_am=datetime.now(timezone.utc),
                )
            )

        auftraege.ausfuehren(auftrag)

        assert _anzeigenamen(datenbank, [PERSON]) == {PERSON: "Anna B."}
        assert Art9EinwilligungRepository(datenbank).lesen(PERSON) is not None

    def test_verknuepfung_und_sperre_ohne_kennung(
        self, datenbank, einwuerfe, auftraege, auftrag
    ):
        beitrag = uuid.uuid4()
        with datenbank.get_session() as s:
            satz = (
                s.query(Satz)
                .filter_by(raw_input_id=einwuerfe.fremd, user_id=PERSON)
                .one()
            )
            link = AusformuliertIn(
                raw_input_id=einwuerfe.fremd,
                content_id=beitrag,
                created_by=PERSON,
                draft_id=satz.id,
            )
            sperre = Sperre(
                content_id=beitrag,
                sperrgrund="unterstellung",
                begruendung="Unterstellt Bosheit.",
                gesperrt_von=ANDERE,
                autor=PERSON,
                widerspruch="Das ist belegt.",
            )
            s.add_all([link, sperre])
            s.flush()
            link_id, sperre_id = link.id, sperre.id

        auftraege.ausfuehren(auftrag)

        with datenbank.get_session() as s:
            assert s.get(AusformuliertIn, link_id).created_by is None
            sperre = s.get(Sperre, sperre_id)
            assert (sperre.autor, sperre.widerspruch) == (None, None)
            assert sperre.gesperrt_von == ANDERE

    def test_auftrag_erledigt_und_zweiter_lauf_aendert_nichts(
        self, datenbank, einwuerfe, auftraege, auftrag
    ):
        auftraege.ausfuehren(auftrag)
        vorher = _saetze(datenbank, einwuerfe.fremd)

        bericht = auftraege.ausfuehren(auftrag)

        assert (bericht.einwuerfe, bericht.saetze) == (0, 0)
        assert _saetze(datenbank, einwuerfe.fremd) == vorher
        assert auftraege.offene() == []
        assert auftraege.laden(auftrag.id).erledigt_am is not None

    def test_scheitert_ein_schritt_bleibt_alles_und_der_auftrag_offen(
        self, datenbank, einwuerfe, auftraege, auftrag
    ):
        # Ein Platzhalter, den der Lauf nicht anlegen kann, weil es die Kennung in users
        # schon gibt: Die Transaktion scheitert nach dem Loeschen der Einwuerfe.
        from unittest.mock import patch

        with datenbank.get_session() as s:
            s.add(User(user_id="ehemalige-person-fest", anzeigename="x"))
        with patch(
            "repositories.loeschauftrag_repository._platzhalter",
            return_value="ehemalige-person-fest",
        ):
            with pytest.raises(Exception):
                auftraege.ausfuehren(auftrag)

        assert EinwurfRepository(datenbank).get_by_id(einwuerfe.eigen) is not None
        assert _saetze(datenbank, einwuerfe.fremd)[SATZ_DER_PERSON] == PERSON
        assert [a.id for a in auftraege.offene()] == [auftrag.id]


class TestFrist:
    def test_erledigte_vor_der_grenze_gehen_offene_bleiben(self, datenbank, auftraege):
        alt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        with datenbank.get_session() as s:
            s.add_all(
                [
                    LoeschauftragZeile(
                        user_id="erledigt-alt",
                        angelegt_am=alt,
                        frist=alt,
                        erledigt_am=alt,
                    ),
                    LoeschauftragZeile(
                        user_id="erledigt-neu",
                        angelegt_am=alt,
                        frist=alt,
                        erledigt_am=datetime.now(timezone.utc),
                    ),
                    LoeschauftragZeile(user_id="offen-alt", angelegt_am=alt, frist=alt),
                ]
            )

        geloescht = auftraege.erledigte_loeschen_vor(
            datetime(2026, 1, 1, tzinfo=timezone.utc)
        )

        assert geloescht == 1
        assert sorted(u for u, _ in _zeilen(datenbank)) == ["erledigt-neu", "offen-alt"]


def test_migration_legt_auftraege_fuer_fruehere_widerrufe_an(postgres_url):
    """
    Wer vor diesem Stand widerrufen hat, bekommt einen offenen Auftrag; wer seither neu
    eingewilligt hat, nicht. Ein zweiter Lauf legt nichts an.
    """
    with postgres.schema(postgres_url, "itest_loeschauftraege") as db:
        Art9EinwilligungZeile.__table__.create(db.engine)
        frueher = datetime(2026, 11, 12, tzinfo=timezone.utc)
        with db.get_session() as s:
            for person, widerrufen in [
                ("widerrufen", frueher),
                ("eingewilligt", None),
            ]:
                s.add(
                    Art9EinwilligungZeile(
                        user_id=person,
                        wortlaut="2026-11-12",
                        eingewilligt_am=frueher - timedelta(days=1),
                        widerrufen_am=widerrufen,
                    )
                )
            # Widerrufen und danach neu eingewilligt
            s.add(
                Art9EinwilligungZeile(
                    user_id="neu-eingewilligt",
                    wortlaut="2026-11-12",
                    eingewilligt_am=frueher - timedelta(days=1),
                    widerrufen_am=frueher,
                )
            )
            s.add(
                Art9EinwilligungZeile(
                    user_id="neu-eingewilligt",
                    wortlaut="2026-11-12",
                    eingewilligt_am=frueher + timedelta(hours=1),
                )
            )

        postgres.migration(db, MIGRATION)
        postgres.migration(db, MIGRATION)

        (auftrag,) = LoeschauftragRepository(db).offene()
        assert auftrag.user_id == "widerrufen"
        assert auftrag.frist - auftrag.angelegt_am == timedelta(days=FRIST_TAGE)
