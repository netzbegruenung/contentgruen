"""
Art.-9-Einwilligung (#489): Stand lesen, einwilligen, widerrufen
(GET/POST/DELETE /api/v1/art9-einwilligung) und die Sperre der Endpunkte, die
ohne Einwilligung nichts speichern duerfen (``require_art9_einwilligung``).

Die Datenbank ersetzt ``art9_einwilligung_ohne_datenbank`` (tests/conftest.py).
"""

import datetime
import re

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from api.v1.art9_einwilligung import router as art9_router
from dependencies import ART9_EINWILLIGUNG_FEHLT, require_art9_einwilligung
from domain.art9_einwilligung import (
    AKTUELLER_WORTLAUT,
    GELTENDE_WORTLAUTE,
    WORTLAUTE,
    WORTLAUT_KENNUNG_MAX,
    geltender_wortlaut,
)
from repositories.art9_einwilligung_repository import Art9Einwilligung

pytestmark = [pytest.mark.unit, pytest.mark.api]

BASIS = "/api/v1/art9-einwilligung"
PERSON = {"X-User": "user-001"}
AM = datetime.datetime(2026, 11, 5, 9, 30, tzinfo=datetime.timezone.utc)
SPAETER = datetime.datetime(2026, 11, 6, 9, 30, tzinfo=datetime.timezone.utc)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(art9_router, prefix=BASIS)
    return TestClient(app)


@pytest.fixture
def repository(art9_einwilligung_ohne_datenbank):
    return art9_einwilligung_ohne_datenbank


@pytest.fixture
def stimmen(repository, monkeypatch):
    """Die Stimmen der Person, die der Widerruf loescht; ersetzt die Datenbank."""
    from unittest.mock import MagicMock

    import services.art9_einwilligung_service as modul

    ersatz = MagicMock()
    ersatz.loeschen_fuer_person.return_value = 3
    monkeypatch.setattr(
        modul, "_service", modul.Art9EinwilligungService(repository, ersatz)
    )
    return ersatz


@pytest.fixture
def loeschauftraege(repository, stimmen, monkeypatch):
    """Der Loeschauftrag, den der Widerruf anlegt (DSFA R9b); ersetzt die Datenbank."""
    from unittest.mock import MagicMock

    import services.art9_einwilligung_service as modul

    ersatz = MagicMock()
    monkeypatch.setattr(
        modul,
        "_service",
        modul.Art9EinwilligungService(repository, stimmen, ersatz),
    )
    return ersatz


class TestStand:
    def test_get_ohne_anmeldung_401(self, client):
        assert client.get(BASIS).status_code == 401
        assert client.get(BASIS, headers={"X-User": "anonymous"}).status_code == 401

    def test_get_ohne_zeile_nicht_eingewilligt_mit_aktuellem_wortlaut(
        self, client, repository
    ):
        repository.lesen.return_value = None

        antwort = client.get(BASIS, headers=PERSON)

        assert antwort.status_code == 200
        assert antwort.json() == {
            "eingewilligt": False,
            "wortlaut": None,
            "eingewilligt_am": None,
            "widerrufen_am": None,
            "aktueller_wortlaut": {
                "kennung": AKTUELLER_WORTLAUT,
                "text": WORTLAUTE[AKTUELLER_WORTLAUT],
            },
        }
        repository.lesen.assert_called_once_with("user-001")

    def test_get_eingewilligt_mit_zeitpunkt_und_wortlaut(self, client, repository):
        repository.lesen.return_value = Art9Einwilligung("2026-11-13", AM, None)

        stand = client.get(BASIS, headers=PERSON).json()

        assert stand["eingewilligt"] is True
        assert stand["wortlaut"] == "2026-11-13"
        assert stand["eingewilligt_am"].startswith("2026-11-05T09:30")

    @pytest.mark.parametrize(
        "frueher", ["2026-11-05", "2026-11-05-b", "2026-11-10", "2026-11-12"]
    )
    def test_einwilligung_zu_frueherem_wortlaut_fragt_neu(
        self, client, repository, frueher
    ):
        """
        2026-11-13 (Entscheidung Maintainer, 13.11.2026): Die Folgen des Widerrufs gehen
        weiter, deshalb zaehlt nur eine Einwilligung zu ihm. Wer einem frueheren
        Wortlaut zugestimmt hat, ist nicht eingewilligt, ohne widerrufen zu haben; das
        Frontend fragt neu.
        """
        repository.lesen.return_value = Art9Einwilligung(frueher, AM, None)

        stand = client.get(BASIS, headers=PERSON).json()

        assert stand["eingewilligt"] is False
        assert stand["wortlaut"] == frueher
        assert stand["widerrufen_am"] is None
        assert stand["aktueller_wortlaut"]["kennung"] == "2026-11-13"

    def test_get_widerrufen_nicht_eingewilligt_wortlaut_bleibt(
        self, client, repository
    ):
        repository.lesen.return_value = Art9Einwilligung("2026-11-05", AM, SPAETER)

        stand = client.get(BASIS, headers=PERSON).json()

        assert stand["eingewilligt"] is False
        assert stand["wortlaut"] == "2026-11-05"
        assert stand["widerrufen_am"].startswith("2026-11-06T09:30")


class TestWortlaute:
    def test_aktueller_wortlaut_nennt_punkte_und_muster_hinweise(self):
        """Wortlaut vom 12.11.2026: die Zwecke aus DSFA Abschnitt 4 wie 2026-11-05-b."""
        text = WORTLAUTE[AKTUELLER_WORTLAUT]

        assert AKTUELLER_WORTLAUT == "2026-11-13"
        assert (
            "ein Punktestand, ein Level, Quests und Meilenstein-Abzeichen, die nur ich "
            "sehe, solange ich nicht gesondert zustimme, sie anderen Angemeldeten zu zeigen"
        ) in text
        assert "neue Aktionen, die ein höheres Level freischaltet" in text
        assert "wenn zwei Konten sich auffällig oft gegenseitig nutzen" in text

    def test_aktueller_wortlaut_nennt_den_menuepunkt_datenschutz_einstellungen(self):
        """Der Widerrufsweg heisst wie der Menuepunkt (#644)."""
        assert (
            "im Profilmenü unter „Datenschutz-Einstellungen“ widerrufen"
            in WORTLAUTE[AKTUELLER_WORTLAUT]
        )

    def test_neuer_wortlaut_aendert_nur_den_namen_des_widerrufswegs(self):
        """
        Redaktionell (#644): 2026-11-10 ist 2026-11-05-b bis auf den Namen des
        Menuepunkts. Deshalb fragt die App niemanden neu; aendert sich mehr, gilt das
        nicht mehr (docs/ART9_EINWILLIGUNG.md, „Wortlaut ändern“).
        """
        vorher = WORTLAUTE["2026-11-05-b"].replace(
            "„Einwilligung“", "„Datenschutz-Einstellungen“"
        )
        assert WORTLAUTE["2026-11-10"] == vorher

    def test_wortlaut_vom_12_11_aendert_nur_die_folgen_des_widerrufs(self):
        """
        Juristische Vorpruefung vom 12.11.2026: Der Widerruf loescht die Bewertungen
        (Art9EinwilligungService.widerrufen). Sonst wortgleich mit 2026-11-10, also
        keine neuen Zwecke; der Wortlaut verspricht nicht mehr, als der Code tut.
        """
        vorher = WORTLAUTE["2026-11-10"].replace(
            "Danach kann ich nichts mehr beitragen oder bewerten; was ich schon "
            "gespeichert habe, bleibt,",
            "Danach kann ich nichts mehr beitragen oder bewerten, und meine "
            "Bewertungen werden gelöscht. Was ich sonst gespeichert habe, bleibt,",
        )
        assert WORTLAUTE["2026-11-12"] == vorher
        assert "meine Bewertungen werden gelöscht" in WORTLAUTE[AKTUELLER_WORTLAUT]

    def test_wortlaut_vom_13_11_aendert_nur_die_folgen_des_widerrufs(self):
        """
        Loeschauftrag nach dem Widerruf (Entscheidung Maintainer, 13.11.2026): Sonst
        wortgleich mit 2026-11-12; die neuen Folgen stehen im Text.
        """
        vorher = WORTLAUTE["2026-11-12"].replace(
            "Was ich sonst gespeichert habe, bleibt, bis ich es lösche oder mein "
            "Konto löschen lasse. ",
            "Innerhalb von sieben Tagen werden auch meine Beiträge, Einwürfe und "
            "Sätze von mir gelöst: Meine Beiträge bleiben stehen und zeigen "
            "„ehemalige Person“ statt meines Namens, meine Einwürfe werden gelöscht, "
            "und meine Sätze an Einwürfen anderer bleiben ohne meinen Namen. Was ich "
            "nach einer neuen Einwilligung beitrage, bleibt davon unberührt. Mein "
            "Konto bleibt. ",
        )
        assert WORTLAUTE["2026-11-13"] == vorher
        assert AKTUELLER_WORTLAUT == "2026-11-13"

    def test_nur_der_aktuelle_wortlaut_zaehlt(self):
        """Fruehere Einwilligungen zaehlen nicht (GELTENDE_WORTLAUTE, 13.11.2026)."""
        assert GELTENDE_WORTLAUTE == {AKTUELLER_WORTLAUT}
        assert all(k in WORTLAUTE for k in GELTENDE_WORTLAUTE)
        assert not geltender_wortlaut("2026-11-12")
        assert Art9Einwilligung(AKTUELLER_WORTLAUT, AM, None).zaehlt
        assert not Art9Einwilligung("2026-11-12", AM, None).zaehlt
        assert not Art9Einwilligung(AKTUELLER_WORTLAUT, AM, SPAETER).zaehlt

    def test_frueherer_wortlaut_bleibt_bekannt(self):
        """Eine gespeicherte Kennung behaelt ihren Text (docs/ART9_EINWILLIGUNG.md)."""
        assert "2026-11-05" in WORTLAUTE
        assert "Punktestand" not in WORTLAUTE["2026-11-05"]
        assert "„Einwilligung“" in WORTLAUTE["2026-11-05-b"]

    def test_kennungen_passen_in_die_spalte(self):
        assert all(len(kennung) <= WORTLAUT_KENNUNG_MAX for kennung in WORTLAUTE)

    def test_kennungen_passen_auf_das_muster_des_frontends(self):
        """
        Das Frontend liest mit ``wortlautDatum``
        (mvp/frontend/gutgesagt-frontend/src/app/services/art9-einwilligung.service.ts)
        das fuehrende ``JJJJ-MM-TT`` als Stand-Datum fuer die DatePipe; ohne
        ``wortlautDatum`` liess das Suffix von ``2026-11-05-b`` sie abstuerzen
        (#560, #569). Das Datum muss deshalb ein echtes Kalenderdatum sein.
        """
        muster = re.compile(r"^\d{4}-\d{2}-\d{2}(-[a-z])?$")

        assert [k for k in WORTLAUTE if not muster.fullmatch(k)] == []
        for kennung in WORTLAUTE:
            datetime.date.fromisoformat(kennung[:10])
        assert AKTUELLER_WORTLAUT in WORTLAUTE


class TestEinwilligen:
    def test_post_bekannter_wortlaut_speichert_kennung(self, client, repository):
        antwort = client.post(
            BASIS, headers=PERSON, json={"wortlaut": AKTUELLER_WORTLAUT}
        )

        assert antwort.status_code == 204
        repository.einwilligen.assert_called_once_with("user-001", AKTUELLER_WORTLAUT)

    def test_post_unbekannter_wortlaut_422_ohne_speichern(self, client, repository):
        antwort = client.post(BASIS, headers=PERSON, json={"wortlaut": "2099-01-01"})

        assert antwort.status_code == 422
        repository.einwilligen.assert_not_called()

    @pytest.mark.parametrize("frueher", ["2026-11-05-b", "2026-11-12"])
    def test_post_frueherer_wortlaut_400_ohne_speichern(
        self, client, repository, frueher
    ):
        """Nur GELTENDE_WORTLAUTE: eine Einwilligung zu einem frueheren zaehlte nicht."""
        antwort = client.post(BASIS, headers=PERSON, json={"wortlaut": frueher})

        assert antwort.status_code == 400
        repository.einwilligen.assert_not_called()

    def test_post_ohne_anmeldung_401(self, client, repository):
        antwort = client.post(BASIS, json={"wortlaut": AKTUELLER_WORTLAUT})

        assert antwort.status_code == 401
        repository.einwilligen.assert_not_called()


class TestWiderrufen:
    def test_delete_widerruft(self, client, repository):
        antwort = client.delete(BASIS, headers=PERSON)

        assert antwort.status_code == 204
        repository.widerrufen.assert_called_once()
        assert repository.widerrufen.call_args.args == ("user-001",)

    def test_delete_nimmt_das_sichtbare_abzeichen_sofort_weg(
        self, client, repository, monkeypatch
    ):
        """Ohne Einwilligung keine Meilensteine, also auch kein Abzeichen (#351)."""
        from unittest.mock import Mock

        from services import abzeichen_service

        dienst = Mock()
        monkeypatch.setattr(abzeichen_service, "_service", dienst)

        assert client.delete(BASIS, headers=PERSON).status_code == 204
        dienst.zuruecknehmen.assert_called_once_with("user-001")

    def test_delete_ohne_anmeldung_401(self, client, repository, stimmen):
        assert client.delete(BASIS).status_code == 401
        repository.widerrufen.assert_not_called()
        stimmen.loeschen_fuer_person.assert_not_called()

    def test_delete_loescht_die_stimmen_in_der_transaktion_des_widerrufs(
        self, client, repository, stimmen
    ):
        """
        Nach dem Widerruf fehlt die Rechtsgrundlage (Art. 17 Abs. 1 lit. b DSGVO).
        Geloescht wird in der Sitzung des Vermerks; ob ein Fehler beide zuruecknimmt,
        prueft tests/integration/test_art9_einwilligung.py gegen PostgreSQL.
        """
        sitzung = object()
        repository.widerrufen.side_effect = lambda user_id, im_selben_zug=None: (
            im_selben_zug(sitzung, True)
        )

        assert client.delete(BASIS, headers=PERSON).status_code == 204
        stimmen.loeschen_fuer_person.assert_called_once_with(
            "user-001", session=sitzung
        )

    def test_delete_legt_den_loeschauftrag_in_der_transaktion_des_widerrufs_an(
        self, client, repository, stimmen, loeschauftraege
    ):
        """
        Beitraege, Einwuerfe und Saetze verlieren den Personenbezug, sobald ein Admin
        den Auftrag ausfuehrt; angelegt wird er in der Sitzung des Vermerks.
        """
        sitzung = object()
        repository.widerrufen.side_effect = lambda user_id, im_selben_zug=None: (
            im_selben_zug(sitzung, True)
        )

        assert client.delete(BASIS, headers=PERSON).status_code == 204
        loeschauftraege.anlegen.assert_called_once_with("user-001", session=sitzung)
        stimmen.loeschen_fuer_person.assert_called_once_with(
            "user-001", session=sitzung
        )

    def test_delete_ohne_geltende_einwilligung_kein_auftrag(
        self, client, repository, stimmen, loeschauftraege
    ):
        """Nichts widerrufen (nie eingewilligt oder schon widerrufen): kein Auftrag."""
        repository.widerrufen.side_effect = lambda user_id, im_selben_zug=None: (
            im_selben_zug(object(), False)
        )

        assert client.delete(BASIS, headers=PERSON).status_code == 204
        loeschauftraege.anlegen.assert_not_called()

    def test_delete_fehler_beim_auftrag_gibt_500(
        self, client, repository, stimmen, loeschauftraege
    ):
        repository.widerrufen.side_effect = lambda user_id, im_selben_zug=None: (
            im_selben_zug(object(), True)
        )
        loeschauftraege.anlegen.side_effect = RuntimeError("Datenbank weg")

        antwort = TestClient(client.app, raise_server_exceptions=False).delete(
            BASIS, headers=PERSON
        )

        assert antwort.status_code == 500

    def test_delete_fehler_beim_loeschen_gibt_500(self, client, repository, stimmen):
        repository.widerrufen.side_effect = lambda user_id, im_selben_zug=None: (
            im_selben_zug(object(), True)
        )
        stimmen.loeschen_fuer_person.side_effect = RuntimeError("Datenbank weg")

        antwort = TestClient(client.app, raise_server_exceptions=False).delete(
            BASIS, headers=PERSON
        )

        assert antwort.status_code == 500

    def test_abzeichen_trotz_loeschfehler_zurueckgenommen(
        self, client, repository, stimmen, monkeypatch
    ):
        from unittest.mock import Mock

        from services import abzeichen_service

        dienst = Mock()
        monkeypatch.setattr(abzeichen_service, "_service", dienst)
        repository.widerrufen.side_effect = RuntimeError("Datenbank weg")

        antwort = TestClient(client.app, raise_server_exceptions=False).delete(
            BASIS, headers=PERSON
        )

        assert antwort.status_code == 500
        dienst.zuruecknehmen.assert_called_once_with("user-001")

    def test_widerruf_trotz_abzeichenfehler_vermerkt(
        self, client, repository, stimmen, monkeypatch
    ):
        from unittest.mock import Mock

        from services import abzeichen_service

        dienst = Mock()
        dienst.zuruecknehmen.side_effect = RuntimeError("weg")
        monkeypatch.setattr(abzeichen_service, "_service", dienst)

        antwort = TestClient(client.app, raise_server_exceptions=False).delete(
            BASIS, headers=PERSON
        )

        assert antwort.status_code == 500
        repository.widerrufen.assert_called_once()


@pytest.fixture
def gesperrt_client():
    app = FastAPI()

    @app.post("/speichern", dependencies=[Depends(require_art9_einwilligung)])
    def speichern():
        return {"ok": True}

    app.include_router(art9_router, prefix=BASIS)
    return TestClient(app)


class TestSperre:
    def test_eingewilligt_kommt_durch(self, gesperrt_client):
        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 200

    def test_ohne_einwilligung_403_mit_kennzeichen(self, gesperrt_client, repository):
        repository.lesen.return_value = None

        antwort = gesperrt_client.post("/speichern", headers=PERSON)

        assert antwort.status_code == 403
        assert antwort.json() == {"detail": ART9_EINWILLIGUNG_FEHLT}

    def test_widerrufen_403(self, gesperrt_client, repository):
        repository.lesen.return_value = Art9Einwilligung("2026-11-05", AM, SPAETER)

        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 403

    def test_ohne_anmeldung_entscheidet_der_endpunkt(self, gesperrt_client, repository):
        repository.lesen.return_value = None

        assert gesperrt_client.post("/speichern").status_code == 200
        assert (
            gesperrt_client.post(
                "/speichern", headers={"X-User": "anonymous"}
            ).status_code
            == 200
        )
        repository.lesen.assert_not_called()

    def test_nach_widerruf_sofort_gesperrt(self, gesperrt_client, repository):
        # Kein Merken im Prozess: Jede Pruefung fragt die Datenbank.
        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 200

        gesperrt_client.delete(BASIS, headers=PERSON)
        repository.lesen.return_value = Art9Einwilligung("2026-11-05", AM, SPAETER)

        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 403

    def test_nach_einwilligen_sofort_frei(self, gesperrt_client, repository):
        repository.lesen.return_value = None
        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 403

        gesperrt_client.post(
            BASIS, headers=PERSON, json={"wortlaut": AKTUELLER_WORTLAUT}
        )
        repository.lesen.return_value = Art9Einwilligung(
            AKTUELLER_WORTLAUT, SPAETER, None
        )

        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 200

    def test_frueherer_wortlaut_gesperrt(self, gesperrt_client, repository):
        """Nicht widerrufen, aber zu 2026-11-12: gesperrt, bis die Person neu einwilligt."""
        repository.lesen.return_value = Art9Einwilligung("2026-11-12", AM, None)

        antwort = gesperrt_client.post("/speichern", headers=PERSON)

        assert antwort.status_code == 403
        assert antwort.json() == {"detail": ART9_EINWILLIGUNG_FEHLT}

    def test_datenbankfehler_500_ohne_durchlassen(self, gesperrt_client, repository):
        repository.lesen.side_effect = RuntimeError("weg")

        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 500


# Was ohne Art.-9-Einwilligung gesperrt ist: alles, was mit Personenbezug etwas
# speichert, aus dem sich auf die politische Meinung schliessen laesst. Kommt ein
# solcher Endpunkt dazu, gehoert er hierher und an ihn die Sperre.
# PATCH /api/v1/rawinput/{einwurf_id}/status prueft selbst, nur beim Ausformulieren
# (Verwerfen bleibt offen); die Tests dazu stehen in test_einwurf.py
# (TestStatuswechsel).
GESPERRT = {
    ("POST", "/api/v1/commentary/addCommentary"),
    ("POST", "/api/v1/generic_text/addGenericText"),
    ("POST", "/api/v1/post/addPost"),
    ("POST", "/api/v1/image/addImage"),
    ("POST", "/api/v1/statement/addStatement"),
    ("POST", "/api/v1/statement/vorab"),
    ("POST", "/api/v1/reference/add"),
    ("PUT", "/api/v1/content/{beitrag_id}"),
    ("POST", "/api/v1/rawinput/addRawInput"),
    ("PUT", "/api/v1/rawinput/{einwurf_id}/draft"),
    ("PUT", "/api/v1/voting/content/{content_id}/like"),
    ("PUT", "/api/v1/voting/content/{content_id}/dislike"),
    # "Ja, gepostet" (#643): oeffentlich gekontert zu haben verraet die politische
    # Meinung; GET mit, damit das Frontend den Knopf nur mit Einwilligung zeigt.
    ("GET", "/api/v1/usage/users/me/gepostet"),
    ("POST", "/api/v1/usage/users/me/gepostet"),
}


# Schreibende Endpunkte, die ohne Art.-9-Einwilligung offen bleiben: lesen und
# suchen per POST, ohne Personenbezug, nur fuer Admins, Zuruecknehmen und Melden.
# Ein neuer schreibender Endpunkt gehoert in GESPERRT (mit Sperre) oder hierher.
OFFEN = {
    # Zustimmung zur Sichtbarkeit der Abzeichen (#351): Ein Nein ist Zuruecknehmen,
    # ein Ja zeigt ohne Einwilligung nichts (keine Meilensteine).
    ("PUT", "/api/v1/usage/users/me/abzeichen-sichtbarkeit"),
    # Die Einwilligung selbst
    ("POST", "/api/v1/art9-einwilligung"),
    # Suchen und Lesen per POST
    ("POST", "/api/v1/search/searchByText"),
    ("POST", "/api/v1/post/searchPost"),
    ("POST", "/api/v1/reference/search"),
    ("POST", "/api/v1/statement/searchStatements"),
    ("POST", "/api/v1/statement/aehnliche"),  # "Nicht dabei?", nur lesend (#642)
    ("POST", "/api/v1/statement/getStatementsOfTopic"),
    ("POST", "/api/v1/statement/getStatementsOfCategory"),
    ("POST", "/api/v1/rawinput/gleicherLink"),
    ("POST", "/api/v1/voting/votes/batch"),
    # Ohne gespeicherten Personenbezug (Werkzeuge, Zaehler, Zuordnungen)
    ("POST", "/api/v1/gegenlesen"),
    ("POST", "/api/v1/kuerzungsvorschlag"),
    ("POST", "/api/v1/spracherkennung"),
    ("POST", "/api/v1/usage/content/{content_id}/usage"),
    ("POST", "/api/v1/usage/users/me/besuch"),
    ("POST", "/api/v1/statement/addReplysuggestionToStatement"),
    ("PUT", "/api/v1/statement/themen/zuordnen"),
    ("POST", "/api/v1/feedback/senden"),
    # Ausformulieren prueft selbst, Verwerfen bleibt offen (test_einwurf.py)
    ("PATCH", "/api/v1/rawinput/{einwurf_id}/status"),
    # Melden, Widerspruch, Angaben der Meldenden
    ("POST", "/api/v1/moderation/report"),
    ("POST", "/api/v1/moderation/melder/meldungen"),
    ("POST", "/api/v1/moderation/melder/angaben-loeschen"),
    # Loeschauftrag ausfuehren (Admin, nach dem Widerruf einer anderen Person)
    ("POST", "/api/v1/moderation/loeschauftraege/{auftrag_id}/ausfuehren"),
    ("POST", "/api/v1/sperren/{sperre_id}/widerspruch"),
    # Einladungen (vor dem Konto) und Admin-Endpunkte
    ("POST", "/api/v1/einladungen"),
    ("PATCH", "/api/v1/einladungen/{einladung_id}"),
    ("POST", "/api/v1/einladungen/pruefen"),
    ("POST", "/api/v1/einladungen/einloesen"),
    ("PATCH", "/api/v1/feedback/{feedback_id}"),
    ("PUT", "/api/v1/moderation/content/{content_id}/sperren"),
    ("PUT", "/api/v1/moderation/content/{content_id}/entsperren"),
    ("PUT", "/api/v1/moderation/reports/{report_id}/dismiss"),
    ("PUT", "/api/v1/moderation/sperren/{sperre_id}/bestaetigen"),
    ("PUT", "/api/v1/moderation/suchanfragen/{statement_id}/freigeben"),
    ("PUT", "/api/v1/moderation/suchanfragen/{statement_id}/ablehnen"),
    ("POST", "/api/v1/usage/cleanup/run"),
    # Seeding: am BFF gesperrt (EndpointPolicy.Blocked)
    ("POST", "/api/v1/seeding/start"),
    ("POST", "/api/v1/seeding/reset"),
    ("POST", "/api/v1/seeding/resume"),
    ("POST", "/api/v1/seeding/stop"),
}


def _gesperrte_routen():
    from main import app

    gesperrt = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if any(
            d.call is require_art9_einwilligung for d in route.dependant.dependencies
        ):
            gesperrt |= {(methode, route.path) for methode in route.methods}
    return gesperrt


def test_app_sperrt_genau_die_endpunkte_mit_art9_daten():
    assert _gesperrte_routen() == GESPERRT


def test_app_loeschen_bleibt_ohne_einwilligung_offen():
    gesperrt = _gesperrte_routen()

    assert not [eintrag for eintrag in gesperrt if eintrag[0] == "DELETE"]


def test_jeder_schreibende_endpunkt_ist_entschieden():
    """Ein neuer POST/PUT/PATCH-Endpunkt faellt hier auf, bis er in GESPERRT oder OFFEN steht."""
    from main import app

    schreibend = {
        (methode, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for methode in route.methods & {"POST", "PUT", "PATCH"}
    }

    # GESPERRT nennt auch lesende Endpunkte mit Sperre (GET gepostet, #643).
    assert schreibend == {e for e in GESPERRT | OFFEN if e[0] != "GET"}
    assert not GESPERRT & OFFEN
