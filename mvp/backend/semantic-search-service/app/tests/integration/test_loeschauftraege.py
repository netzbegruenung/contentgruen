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
from sqlalchemy import text
from infrastructure.database.models import (
    Art9EinwilligungZeile,
    Art9OhneEinwilligungZeile,
    AusformuliertIn,
    Einwurf,
    LoeschauftragZeile,
    Satz,
    Sperre,
    User,
)
from repositories.art9_einwilligung_repository import Art9EinwilligungRepository
from repositories.einwurf_repository import EinwurfRepository
from repositories.loeschauftrag_repository import (
    FRIST_TAGE,
    LoeschauftragRepository,
    StandGeaendert,
)
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
    _einwurf,
    _satz,
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
        dienst.einwilligen(PERSON, "2026-11-13")

        dienst.widerrufen(PERSON)

        (auftrag,) = auftraege.offene()
        assert auftrag.user_id == PERSON
        assert auftrag.frist - auftrag.angelegt_am == timedelta(days=FRIST_TAGE)
        assert auftrag.erledigt_am is None

    def test_zweiter_widerruf_kein_zweiter_offener_auftrag(
        self, dienst, auftraege, datenbank
    ):
        dienst.einwilligen(PERSON, "2026-11-13")
        dienst.widerrufen(PERSON)
        dienst.einwilligen(PERSON, "2026-11-13")

        dienst.widerrufen(PERSON)

        assert _zeilen(datenbank) == [(PERSON, False)]

    def test_nach_erledigtem_auftrag_neuer_widerruf_neuer_auftrag(
        self, dienst, auftraege, datenbank, einwuerfe
    ):
        dienst.einwilligen(PERSON, "2026-11-13")
        dienst.widerrufen(PERSON)
        (erster,) = auftraege.offene()
        auftraege.ausfuehren(erster)
        dienst.einwilligen(PERSON, "2026-11-13")

        dienst.widerrufen(PERSON)

        assert _zeilen(datenbank) == [(PERSON, True), (PERSON, False)]

    def test_widerruf_ohne_geltende_einwilligung_legt_keinen_auftrag_an(
        self, dienst, datenbank
    ):
        dienst.widerrufen(PERSON)

        assert _zeilen(datenbank) == []

    def test_wiederholter_widerruf_nach_erledigtem_auftrag_legt_keinen_neuen_an(
        self, dienst, auftraege, datenbank, einwuerfe
    ):
        dienst.einwilligen(PERSON, "2026-11-13")
        dienst.widerrufen(PERSON)
        (erster,) = auftraege.offene()
        auftraege.ausfuehren(erster)

        dienst.widerrufen(PERSON)

        assert _zeilen(datenbank) == [(PERSON, True)]

    def test_liste_zeigt_eine_neue_einwilligung_nach_dem_widerruf(
        self, dienst, auftraege
    ):
        dienst.einwilligen(PERSON, "2026-11-13")
        dienst.widerrufen(PERSON)
        (vorher,) = auftraege.offene()
        assert vorher.neu_eingewilligt_am is None

        dienst.einwilligen(PERSON, "2026-11-13")

        (nachher,) = auftraege.offene()
        assert nachher.neu_eingewilligt_am is not None
        assert nachher.neu_eingewilligt_am > nachher.angelegt_am

    def test_scheitert_der_auftrag_gilt_der_widerruf_nicht(self, datenbank):
        """Eine Transaktion wie beim Loeschen der Stimmen."""
        from unittest.mock import MagicMock

        kaputt = MagicMock()
        kaputt.anlegen.side_effect = RuntimeError("Datenbank weg")
        stimmen = VoteRepository(datenbank)
        dienst = Art9EinwilligungService(
            Art9EinwilligungRepository(datenbank), stimmen, kaputt
        )
        dienst.einwilligen(PERSON, "2026-11-13")

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

    def test_vermerk_ohne_einwilligung_geht_mit(
        self, datenbank, einwuerfe, auftraege, auftrag
    ):
        """UX-Review B2: Der Vermerk am Konto geht mit dem Loeschablauf (PR #670)."""
        Art9EinwilligungRepository(datenbank).ohne_merken(PERSON, "2026-11-13")

        auftraege.ausfuehren(auftrag)

        assert Art9EinwilligungRepository(datenbank).ohne_lesen(PERSON) is None

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

        auftraege.ausfuehren(auftraege.laden(auftrag.id))

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


WIDERRUF = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
NEU = WIDERRUF + timedelta(hours=1)


def _einwilligung(datenbank, wortlaut, eingewilligt, widerrufen=None):
    with datenbank.get_session() as s:
        s.add(
            Art9EinwilligungZeile(
                user_id=PERSON,
                wortlaut=wortlaut,
                eingewilligt_am=eingewilligt,
                widerrufen_am=widerrufen,
            )
        )


def _zeitpunkt(datenbank, einwurf, wann):
    """Einwurf und Saetze daran auf einen festen Zeitpunkt setzen."""
    with datenbank.get_session() as s:
        s.query(Einwurf).filter_by(id=einwurf).update({"created_at": wann})
        s.query(Satz).filter_by(raw_input_id=einwurf).update({"updated_at": wann})


class TestObergrenze:
    """
    Neue Einwilligung vor der Ausfuehrung (Entscheidung Maintainer, 13.11.2026): Was ab
    der fruehesten Einwilligung zum geltenden Wortlaut nach dem juengsten Widerruf
    angelegt ist, bleibt. Ohne sie erfasst der Auftrag alles, auch Nachzuegler.
    """

    @pytest.fixture
    def dienst(self, datenbank, auftraege):
        return Art9EinwilligungService(
            Art9EinwilligungRepository(datenbank), VoteRepository(datenbank), auftraege
        )

    def _auftrag(self, auftraege):
        """Ein offener Auftrag, angelegt zum Widerruf wie in Art9EinwilligungService."""
        with auftraege.db.get_session() as s:
            s.add(
                LoeschauftragZeile(
                    id=uuid.uuid4(),
                    user_id=PERSON,
                    angelegt_am=WIDERRUF,
                    frist=WIDERRUF + timedelta(days=FRIST_TAGE),
                )
            )
        (offen,) = auftraege.offene()
        return auftraege.laden(offen.id)

    def test_ab_der_neuen_einwilligung_bleibt_alles_genau_an_der_grenze(
        self, datenbank, einwuerfe, auftraege
    ):
        _einwilligung(datenbank, "2026-11-13", WIDERRUF - timedelta(days=1), WIDERRUF)
        _einwilligung(datenbank, "2026-11-13", NEU)
        knapp_davor = NEU - timedelta(microseconds=1)
        _zeitpunkt(datenbank, einwuerfe.eigen, knapp_davor)
        _zeitpunkt(datenbank, einwuerfe.fremd, knapp_davor)
        spaeter_beitrag = uuid.uuid4()
        with datenbank.get_session() as s:
            neu_eigen = _einwurf(s, von=PERSON)
            neu_fremd = _einwurf(s, von=ANDERE, destilled_by=PERSON)
            _satz(s, neu_fremd, PERSON, "Ein Satz nach der neuen Einwilligung")
            link = AusformuliertIn(
                raw_input_id=neu_fremd,
                content_id=spaeter_beitrag,
                created_by=PERSON,
                created_at=NEU,
            )
            sperre = Sperre(
                content_id=spaeter_beitrag,
                sperrgrund="unterstellung",
                begruendung="Unterstellt Bosheit.",
                gesperrt_von=ANDERE,
                autor=PERSON,
            )
            s.add_all([link, sperre])
            s.flush()
            link_id, sperre_id = link.id, sperre.id
        _zeitpunkt(datenbank, neu_eigen, NEU)
        _zeitpunkt(datenbank, neu_fremd, NEU)
        auftrag = self._auftrag(auftraege)
        assert (auftrag.widerrufen_am, auftrag.obergrenze) == (WIDERRUF, NEU)

        bericht = auftraege.ausfuehren(
            auftrag, beitraege_behalten=[str(spaeter_beitrag)]
        )

        # Knapp vor der neuen Einwilligung: geht wie sonst.
        assert (bericht.einwuerfe, bericht.saetze) == (1, 1)
        assert EinwurfRepository(datenbank).get_by_id(einwuerfe.eigen) is None
        assert _saetze(datenbank, einwuerfe.fremd)[SATZ_DER_PERSON] != PERSON
        # Genau ab der neuen Einwilligung: bleibt an der Person.
        assert EinwurfRepository(datenbank).get_by_id(neu_eigen) is not None
        assert _saetze(datenbank, neu_fremd) == {
            "Ein Satz nach der neuen Einwilligung": PERSON
        }
        assert _destilled_by(datenbank, neu_fremd) == PERSON
        with datenbank.get_session() as s:
            assert s.get(AusformuliertIn, link_id).created_by == PERSON
            assert s.get(Sperre, sperre_id).autor == PERSON

    def test_nachzuegler_ohne_neue_einwilligung_gehen_mit(
        self, datenbank, einwuerfe, auftraege
    ):
        """Gespeichert nach dem Widerruf (vorher geprueft): ohne neue Einwilligung erfasst."""
        _einwilligung(datenbank, "2026-11-13", WIDERRUF - timedelta(days=1), WIDERRUF)
        _zeitpunkt(datenbank, einwuerfe.eigen, WIDERRUF + timedelta(seconds=1))
        _zeitpunkt(datenbank, einwuerfe.fremd, WIDERRUF + timedelta(seconds=1))
        auftrag = self._auftrag(auftraege)
        assert auftrag.obergrenze is None

        bericht = auftraege.ausfuehren(auftrag)

        assert (bericht.einwuerfe, bericht.saetze) == (1, 1)
        assert EinwurfRepository(datenbank).get_by_id(einwuerfe.eigen) is None
        assert _saetze(datenbank, einwuerfe.fremd)[SATZ_DER_PERSON] != PERSON

    def test_neue_einwilligung_zu_frueherem_wortlaut_ist_die_obergrenze(
        self, datenbank, auftraege
    ):
        """
        Vor dem Deploy widerrufen und zu 2026-11-12 neu eingewilligt: Die Einwilligung
        galt, als sie gegeben wurde; ein spaeterer Pflicht-Wortlaut kippt die Zusage
        nicht.
        """
        _einwilligung(datenbank, "2026-11-12", WIDERRUF - timedelta(days=1), WIDERRUF)
        _einwilligung(datenbank, "2026-11-12", NEU)

        assert self._auftrag(auftraege).obergrenze == NEU

    def test_ohne_widerrufszeile_keine_obergrenze(self, datenbank, auftraege):
        """Fehlt der Widerruf (etwa nach einer Umstellung), erfasst der Auftrag alles."""
        _einwilligung(datenbank, "2026-11-13", NEU)

        auftrag = self._auftrag(auftraege)

        assert (auftrag.widerrufen_am, auftrag.obergrenze) == (None, None)

    def test_einwilligung_vor_dem_anlegen_ist_keine_obergrenze(
        self, datenbank, auftraege
    ):
        """Die Suche beginnt fruehestens beim Anlegen des Auftrags."""
        _einwilligung(datenbank, "2026-11-13", WIDERRUF - timedelta(days=1), WIDERRUF)
        _einwilligung(datenbank, "2026-11-13", NEU)
        with datenbank.get_session() as s:
            s.add(
                LoeschauftragZeile(
                    id=uuid.uuid4(),
                    user_id=PERSON,
                    angelegt_am=NEU + timedelta(hours=1),
                    frist=NEU + timedelta(days=8),
                )
            )
        (offen,) = auftraege.offene()

        assert offen.obergrenze is None

    def test_einwilligung_vor_dem_juengsten_widerruf_ist_keine_obergrenze(
        self, dienst, auftraege
    ):
        """Zweimal widerrufen: Die Einwilligung dazwischen schuetzt nichts."""
        dienst.einwilligen(PERSON, "2026-11-13")
        dienst.widerrufen(PERSON)
        dienst.einwilligen(PERSON, "2026-11-13")
        dienst.widerrufen(PERSON)
        (offen,) = auftraege.offene()

        auftrag = auftraege.laden(offen.id)

        assert auftrag.obergrenze is None
        assert auftrag.neu_eingewilligt_am is None
        assert auftrag.widerrufen_am > auftrag.angelegt_am

    def test_liste_zeigt_juengsten_widerruf_und_die_neue_einwilligung(
        self, dienst, auftraege
    ):
        dienst.einwilligen(PERSON, "2026-11-13")
        dienst.widerrufen(PERSON)
        (vorher,) = auftraege.offene()
        assert vorher.widerrufen_am == vorher.angelegt_am

        dienst.einwilligen(PERSON, "2026-11-13")

        (nachher,) = auftraege.offene()
        assert nachher.neu_eingewilligt_am == nachher.obergrenze
        assert nachher.obergrenze > nachher.widerrufen_am


class TestStandWaehrendDerAusfuehrung:
    @pytest.fixture
    def dienst(self, datenbank, auftraege):
        return Art9EinwilligungService(
            Art9EinwilligungRepository(datenbank), VoteRepository(datenbank), auftraege
        )

    @pytest.fixture
    def geladen(self, dienst, auftraege, einwuerfe):
        dienst.einwilligen(PERSON, "2026-11-13")
        dienst.widerrufen(PERSON)
        (offen,) = auftraege.offene()
        return auftraege.laden(offen.id)

    def test_widerruf_zwischen_laden_und_ausfuehren(
        self, dienst, auftraege, datenbank, einwuerfe, geladen
    ):
        """Neue Einwilligung und erneuter Widerruf: nicht erledigen, neu laden."""
        dienst.einwilligen(PERSON, "2026-11-13")
        dienst.widerrufen(PERSON)

        with pytest.raises(StandGeaendert):
            auftraege.ausfuehren(geladen)

        assert [a.id for a in auftraege.offene()] == [geladen.id]
        assert EinwurfRepository(datenbank).get_by_id(einwuerfe.eigen) is not None
        bericht = auftraege.ausfuehren(auftraege.laden(geladen.id))
        assert bericht.einwuerfe == 1
        assert auftraege.offene() == []

    def test_neue_einwilligung_zwischen_laden_und_ausfuehren(
        self, dienst, auftraege, geladen
    ):
        dienst.einwilligen(PERSON, "2026-11-13")

        with pytest.raises(StandGeaendert):
            auftraege.ausfuehren(geladen)

        assert [a.id for a in auftraege.offene()] == [geladen.id]


class TestSperren:
    """
    Zwei Verbindungen: Widerruf und Ausfuehrung sperren beide die Zeile des offenen
    Auftrags (FOR UPDATE), damit kein Widerruf waehrend der Ausfuehrung verloren geht.
    Ohne die Sperren werden diese Tests rot.
    """

    @pytest.fixture
    def dienst(self, datenbank, auftraege):
        return Art9EinwilligungService(
            Art9EinwilligungRepository(datenbank), VoteRepository(datenbank), auftraege
        )

    @pytest.fixture
    def neu_eingewilligt(self, dienst, auftraege, einwuerfe):
        """Widerrufen (offener Auftrag) und neu eingewilligt: ein zweiter Widerruf zaehlt."""
        dienst.einwilligen(PERSON, "2026-11-13")
        dienst.widerrufen(PERSON)
        dienst.einwilligen(PERSON, "2026-11-13")
        (offen,) = auftraege.offene()
        return auftraege.laden(offen.id)

    @staticmethod
    def _im_thread(ziel):
        import threading

        ergebnis = {}

        def lauf():
            try:
                ergebnis["wert"] = ziel()
            except Exception as e:  # noqa: BLE001 (der Test prueft den Fehler)
                ergebnis["fehler"] = e

        faden = threading.Thread(target=lauf, daemon=True)
        faden.start()
        return faden, ergebnis

    def test_widerruf_wartet_auf_die_ausfuehrung_und_legt_dann_einen_neuen_an(
        self, datenbank, dienst, auftraege, neu_eingewilligt
    ):
        a = datenbank.sessions()
        try:
            # A wie ausfuehren: Zeile sperren ...
            a.execute(
                text("SELECT id FROM loeschauftraege WHERE id = :id FOR UPDATE"),
                {"id": neu_eingewilligt.id},
            )
            faden, ergebnis = self._im_thread(lambda: dienst.widerrufen(PERSON))
            faden.join(timeout=1.5)
            assert faden.is_alive(), "der Widerruf wartet nicht auf die Sperre"
            # ... und erledigen
            a.execute(
                text("UPDATE loeschauftraege SET erledigt_am = now() WHERE id = :id"),
                {"id": neu_eingewilligt.id},
            )
            a.commit()
        finally:
            a.close()
        faden.join(timeout=10)

        assert not faden.is_alive()
        assert "fehler" not in ergebnis
        (neu,) = auftraege.offene()
        assert neu.id != neu_eingewilligt.id
        assert auftraege.laden(neu_eingewilligt.id).erledigt_am is not None

    def test_ausfuehren_wartet_auf_den_widerruf_und_bricht_dann_ab(
        self, datenbank, auftraege, neu_eingewilligt
    ):
        b = datenbank.sessions()
        try:
            # B wie der Widerruf: Vermerk und anlegen (sperrt den offenen Auftrag)
            b.execute(
                text(
                    "UPDATE art9_einwilligungen SET widerrufen_am = now()"
                    " WHERE user_id = :p AND widerrufen_am IS NULL"
                ),
                {"p": PERSON},
            )
            auftraege.anlegen(PERSON, session=b)
            faden, ergebnis = self._im_thread(
                lambda: auftraege.ausfuehren(neu_eingewilligt)
            )
            faden.join(timeout=1.5)
            assert faden.is_alive(), "die Ausfuehrung wartet nicht auf die Sperre"
            b.commit()
        finally:
            b.close()
        faden.join(timeout=10)

        assert not faden.is_alive()
        assert isinstance(ergebnis.get("fehler"), StandGeaendert)
        assert [a.id for a in auftraege.offene()] == [neu_eingewilligt.id]


class TestFrist:
    def test_ueberfaellige_zaehlen_nur_offene_mit_vergangener_frist(
        self, datenbank, auftraege
    ):
        jetzt = datetime.now(timezone.utc)
        alt = jetzt - timedelta(days=10)
        with datenbank.get_session() as s:
            s.add_all(
                [
                    LoeschauftragZeile(user_id="a", angelegt_am=alt, frist=alt),
                    LoeschauftragZeile(
                        user_id="b", angelegt_am=alt, frist=alt, erledigt_am=jetzt
                    ),
                    LoeschauftragZeile(
                        user_id="c", angelegt_am=jetzt, frist=jetzt + timedelta(days=7)
                    ),
                ]
            )

        assert auftraege.ueberfaellige_zaehlen(jetzt) == 1

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
    Jede Person mit einem frueheren Widerruf bekommt einen offenen Auftrag, angelegt
    zum juengsten Widerruf, auch wenn sie seither neu eingewilligt hat (Entscheidung
    Maintainer, 13.11.2026); was nach der neuen Einwilligung gespeichert wurde,
    schuetzt die Obergrenze. Wer nie widerrufen hat, bekommt keinen. Ein
    zweiter Lauf legt nichts an.
    """
    with postgres.schema(postgres_url, "itest_loeschauftraege") as db:
        Art9EinwilligungZeile.__table__.create(db.engine)
        LoeschauftragZeile.__table__.create(db.engine)
        frueher = datetime(2026, 11, 12, tzinfo=timezone.utc)
        spaeter = frueher + timedelta(hours=5)

        def zeile(person, wortlaut, eingewilligt, widerrufen=None):
            return Art9EinwilligungZeile(
                user_id=person,
                wortlaut=wortlaut,
                eingewilligt_am=eingewilligt,
                widerrufen_am=widerrufen,
            )

        tag_davor = frueher - timedelta(days=1)
        # Ein offener Auftrag, den ein Widerruf schon angelegt hat: kein zweiter
        with db.get_session() as s:
            s.add_all(
                [
                    zeile("widerrufen", "2026-11-12", tag_davor, frueher),
                    zeile("eingewilligt", "2026-11-12", tag_davor),
                    # widerrufen, neu eingewilligt zum vorigen Wortlaut
                    zeile("neu-alt", "2026-11-12", tag_davor, frueher),
                    zeile("neu-alt", "2026-11-12", frueher + timedelta(hours=1)),
                    # zweimal widerrufen, danach wieder zu 2026-11-12 eingewilligt
                    zeile("zweimal", "2026-11-10", tag_davor, frueher),
                    zeile(
                        "zweimal", "2026-11-12", frueher + timedelta(hours=1), spaeter
                    ),
                    zeile("zweimal", "2026-11-12", spaeter + timedelta(hours=1)),
                    zeile("schon-offen", "2026-11-12", tag_davor, frueher),
                    LoeschauftragZeile(
                        id=uuid.uuid4(),
                        user_id="schon-offen",
                        angelegt_am=frueher,
                        frist=frueher + timedelta(days=FRIST_TAGE),
                    ),
                ]
            )

        postgres.migration(db, MIGRATION)
        postgres.migration(db, MIGRATION)

        auftraege = {a.user_id: a for a in LoeschauftragRepository(db).offene()}
        assert set(auftraege) == {"widerrufen", "neu-alt", "zweimal", "schon-offen"}
        assert auftraege["schon-offen"].frist == frueher + timedelta(days=FRIST_TAGE)
        # "Widerrufen am" ist der juengste echte Widerruf; die Frist zaehlt ab jetzt,
        # sonst waere der Auftrag sofort ueberfaellig.
        assert auftraege["widerrufen"].angelegt_am == frueher
        assert auftraege["zweimal"].angelegt_am == spaeter
        assert auftraege["zweimal"].widerrufen_am == spaeter
        for person, auftrag in auftraege.items():
            if person == "schon-offen":
                continue
            assert auftrag.frist > datetime.now(timezone.utc) + timedelta(
                days=FRIST_TAGE - 1
            )
        # Obergrenze: die erste Einwilligung nach dem juengsten Widerruf, gleich zu
        # welchem Wortlaut; die zwischen zwei Widerrufen zaehlt nicht.
        assert auftraege["widerrufen"].obergrenze is None
        assert auftraege["neu-alt"].obergrenze == frueher + timedelta(hours=1)
        assert auftraege["zweimal"].obergrenze == spaeter + timedelta(hours=1)
