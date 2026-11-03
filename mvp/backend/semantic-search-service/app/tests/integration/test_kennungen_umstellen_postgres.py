"""
Kennungen auf den Realm von Gut gesagt umstellen (#487), PostgreSQL-Teil, gegen ein
echtes PostgreSQL.

Die Daten sind dieselben wie beim Loeschkommando (test_loeschkommando.py): eine
Person mit einer Spur in jeder Spalte, die eine Kennung traegt. Was dort geloescht
wird, wird hier auf die neue Kennung umgeschrieben.
"""

import uuid

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sqlalchemy import text

from infrastructure.database.models import GeseheneNutzung, Satz, User
from domain.interfaces.konten_im_realm import (
    BetaZugang,
    KontenMitPasswort,
    VerknuepfteKonten,
)
from services.wartung.kennungen_umstellen import (
    kennungen_in_postgres,
    postgres_umschreiben,
    umstellen,
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
ANDERE_NEU = "andere-neu-im-realm"
COLLECTION = "beitraege"

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
            saetze = s.query(Satz).filter_by(raw_input_id=einwuerfe.fremd)
            assert {d.user_id for d in saetze} == {PERSON, NEU, ANDERE}

    def test_anzeigename_der_alten_bleibt_solange_ihr_satz_stehen_bleibt(
        self, datenbank, einwuerfe
    ):
        """Ohne die Zeile in users zeigte der Fangkorb am stehen gebliebenen Satz keinen Namen."""
        with datenbank.get_session() as s:
            _satz(s, einwuerfe.fremd, NEU, "Schon im Realm geschrieben")
            s.add(User(user_id=NEU, anzeigename="Anna im Realm"))

        bericht = _umschreiben(datenbank)
        zweiter = _umschreiben(datenbank)

        with datenbank.get_session() as s:
            assert s.get(User, PERSON).anzeigename == "Anna B."
            assert s.get(User, NEU).anzeigename == "Anna im Realm"
        assert bericht.geaendert["users.user_id"] == 0
        assert zweiter.geaendert["users.user_id"] == 0


class Realm:
    """Attrappe des Realms: verknuepfte Konten, legt auf Wunsch eins an."""

    def __init__(self, verknuepft, adressen=None):
        self.verknuepft = dict(verknuepft)
        self.angelegt_fuer = []
        # Mail-Adresse -> Konto im Realm (Beta-Zugaenge, #488)
        self.adressen = dict(adressen or {})
        self.mit_passwort_fuer = []
        # Adressen, deren Konto Keycloak abweist (400)
        self.abweisen = set()

    def kennungen_zuordnen(self, identity_provider, kennungen):
        assert identity_provider == "netzbegruenung"
        return {k: self.verknuepft[k] for k in kennungen if k in self.verknuepft}

    def konten_verknuepft_anlegen(self, identity_provider, konten):
        self.angelegt_fuer.extend(konten)
        ergebnis = VerknuepfteKonten()
        for kennung in konten:
            ergebnis.angelegt[kennung] = self.verknuepft[kennung] = f"{kennung}-neu"
        return ergebnis

    def konten_nach_adresse(self, adressen):
        return {
            a.lower(): self.adressen[a.lower()]
            for a in adressen
            if a.lower() in self.adressen
        }

    def konten_mit_passwort_anlegen(self, zugaenge):
        self.mit_passwort_fuer.extend(zugaenge)
        ergebnis = KontenMitPasswort()
        for kennung, zugang in zugaenge.items():
            if zugang.email in self.abweisen:
                ergebnis.abgewiesen.append(kennung)
                continue
            ergebnis.angelegt[kennung] = self.adressen[zugang.email] = f"{kennung}-neu"
        return ergebnis


@pytest.fixture
def qdrant():
    client = QdrantClient(":memory:")
    client.create_collection(
        COLLECTION, vectors_config=VectorParams(size=2, distance=Distance.COSINE)
    )
    payload = {"original_author": PERSON, "last_modified_by": PERSON}
    client.upsert(COLLECTION, [PointStruct(id=1, vector=[1.0, 0.0], payload=payload)])
    return client


def _umstellen(datenbank, qdrant, realm, **kwargs):
    with datenbank.engine.connect() as verbindung:
        return umstellen(
            verbindung, qdrant, COLLECTION, realm, "netzbegruenung", **kwargs
        )


class TestUmstellen:
    def test_trockenlauf_zaehlt_je_tabelle_und_collection(
        self, datenbank, spuren, qdrant
    ):
        ergebnis = _umstellen(datenbank, qdrant, Realm({PERSON: NEU}))

        assert ergebnis.postgres.geaendert == JE_SPALTE_EINE
        assert ergebnis.qdrant == {COLLECTION: 1}
        assert ergebnis.ohne_konto == [ANDERE]
        assert _kennung_irgendwo(datenbank, NEU) == []

    def test_lauf_schreibt_ueberall_und_der_zweite_findet_nichts(
        self, datenbank, spuren, qdrant
    ):
        realm = Realm({PERSON: NEU, ANDERE: ANDERE_NEU})
        _umstellen(datenbank, qdrant, realm, ausfuehren=True)

        zweiter = _umstellen(datenbank, qdrant, realm, ausfuehren=True)

        assert _kennung_irgendwo(datenbank, PERSON) == []
        payload = qdrant.retrieve(COLLECTION, [1], with_payload=True)[0].payload
        assert payload["original_author"] == NEU
        assert set(zweiter.postgres.geaendert.values()) == {0}
        assert zweiter.qdrant == {COLLECTION: 0}
        assert zweiter.zuordnung == {}

    def test_listen_aus_der_konfiguration_bekommen_die_neuen_kennungen(
        self, datenbank, spuren, qdrant
    ):
        ergebnis = _umstellen(
            datenbank,
            qdrant,
            Realm({PERSON: NEU, "nur-admin": "nur-admin-neu"}),
            listen={"ADMIN_USER_IDS": ["user-001", PERSON, "nur-admin"]},
        )

        assert ergebnis.listen == {"ADMIN_USER_IDS": ["user-001", NEU, "nur-admin-neu"]}

    def test_konten_werden_nur_beim_lauf_und_nur_fuer_fehlende_angelegt(
        self, datenbank, spuren, qdrant
    ):
        realm = Realm({PERSON: NEU})
        mails = {PERSON: "anna@example.org", ANDERE: "ben@example.org"}

        trocken = _umstellen(datenbank, qdrant, realm, anzulegen=mails)
        assert realm.angelegt_fuer == []
        assert trocken.anzulegen == [ANDERE]

        lauf = _umstellen(datenbank, qdrant, realm, anzulegen=mails, ausfuehren=True)
        assert realm.angelegt_fuer == [ANDERE]
        assert lauf.zuordnung == {PERSON: NEU, ANDERE: f"{ANDERE}-neu"}
        assert lauf.ohne_konto == []

    def test_beta_zugaenge_ziehen_ueber_die_adresse_um(self, datenbank, spuren, qdrant):
        """#488: ANDERE ist ein Beta-Zugang ohne Konto, PERSON hat schon eins."""
        realm = Realm({}, adressen={"anna@example.org": NEU})
        beta = {
            PERSON: BetaZugang("anna@example.org", "Anna Beispiel"),
            ANDERE: BetaZugang("ben@example.org", "Ben Beispiel"),
        }

        trocken = _umstellen(datenbank, qdrant, realm, beta_zugaenge=beta)
        assert realm.mit_passwort_fuer == []
        assert trocken.zuordnung == {PERSON: NEU}
        assert trocken.beta_anzulegen == [ANDERE]

        lauf = _umstellen(datenbank, qdrant, realm, beta_zugaenge=beta, ausfuehren=True)
        assert realm.mit_passwort_fuer == [ANDERE]
        assert lauf.zuordnung == {PERSON: NEU, ANDERE: f"{ANDERE}-neu"}
        assert lauf.beta_anzulegen == []
        assert _kennung_irgendwo(datenbank, PERSON) == []
        assert _kennung_irgendwo(datenbank, ANDERE) == []

        zweiter = _umstellen(
            datenbank, qdrant, realm, beta_zugaenge=beta, ausfuehren=True
        )
        assert realm.mit_passwort_fuer == [ANDERE]
        assert set(zweiter.postgres.geaendert.values()) == {0}

    def test_beta_zugang_mit_adresse_eines_anderen_kontos_bleibt_und_wird_genannt(
        self, datenbank, spuren, qdrant
    ):
        """
        Dieselbe Adresse wie ein Mitglied mit verknuepftem Konto: Zwei alte Kennungen
        auf eine neue liessen den Lauf erst nach dem Anlegen abbrechen.
        """
        realm = Realm({PERSON: NEU}, adressen={"anna@example.org": NEU})
        beta = {ANDERE: BetaZugang("anna@example.org", "Anna Beispiel")}

        lauf = _umstellen(datenbank, qdrant, realm, beta_zugaenge=beta, ausfuehren=True)

        assert lauf.zuordnung == {PERSON: NEU}
        assert lauf.beta_vergeben == [ANDERE]
        assert lauf.beta_anzulegen == []
        assert realm.mit_passwort_fuer == []

    def test_zwei_beta_zugaenge_mit_derselben_adresse(self, datenbank, spuren, qdrant):
        realm = Realm({}, adressen={"anna@example.org": NEU})
        beta = {
            PERSON: BetaZugang("anna@example.org", "Anna Beispiel"),
            ANDERE: BetaZugang("Anna@example.org", "Anna Beispiel"),
        }

        lauf = _umstellen(datenbank, qdrant, realm, beta_zugaenge=beta)

        # Der erste in der Sortierung bekommt das Konto, der zweite wird genannt.
        assert lauf.zuordnung == {ANDERE: NEU}
        assert lauf.beta_vergeben == [PERSON]

    def test_beta_zugang_ohne_spuren_bekommt_trotzdem_ein_konto(
        self, datenbank, spuren, qdrant
    ):
        realm = Realm({})
        beta = {"user-009": BetaZugang("kim@example.org", "Kim Neu")}

        lauf = _umstellen(datenbank, qdrant, realm, beta_zugaenge=beta, ausfuehren=True)

        assert realm.mit_passwort_fuer == ["user-009"]
        assert lauf.zuordnung["user-009"] == "user-009-neu"

    def test_admins_unter_den_beta_zugaengen_mit_neuer_kennung(
        self, datenbank, spuren, qdrant
    ):
        realm = Realm({}, adressen={"anna@example.org": NEU})
        beta = {
            PERSON: BetaZugang("anna@example.org", "Anna Beispiel", admin=True),
            ANDERE: BetaZugang("ben@example.org", "Ben Beispiel"),
        }

        ergebnis = _umstellen(datenbank, qdrant, realm, beta_zugaenge=beta)

        assert ergebnis.beta_admins == [NEU]

    def test_admin_schon_ueber_den_identity_provider_zugeordnet_wird_genannt(
        self, datenbank, spuren, qdrant
    ):
        """isAdmin gibt es im Realm nicht: Ohne Nennung verloere er die Admin-Rechte."""
        realm = Realm({PERSON: NEU})
        beta = {PERSON: BetaZugang("anna@example.org", "Anna Beispiel", admin=True)}

        ergebnis = _umstellen(datenbank, qdrant, realm, beta_zugaenge=beta)

        assert ergebnis.beta_admins == [NEU]

    def test_trockenlauf_zeigt_den_konflikt_mit_anzulegenden_konten(
        self, datenbank, spuren, qdrant
    ):
        """Wie der Lauf: Das Konto aus --konten-anlegen entsteht vor dem Beta-Zugang."""
        beta = {"user-009": BetaZugang("Ben@example.org", "Ben Beispiel")}
        mails = {ANDERE: "ben@example.org"}

        trocken = _umstellen(
            datenbank, qdrant, Realm({}), anzulegen=mails, beta_zugaenge=beta
        )
        realm = Realm({})
        realm.adressen["ben@example.org"] = f"{ANDERE}-neu"
        lauf = _umstellen(
            datenbank,
            qdrant,
            realm,
            anzulegen=mails,
            beta_zugaenge=beta,
            ausfuehren=True,
        )

        assert trocken.beta_vergeben == lauf.beta_vergeben == ["user-009"]
        assert trocken.beta_anzulegen == lauf.beta_anzulegen == []

    def test_beta_zugaenge_stehen_nicht_zusaetzlich_unter_ohne_konto(
        self, datenbank, spuren, qdrant
    ):
        beta = {ANDERE: BetaZugang("ben@example.org", "Ben Beispiel")}

        trocken = _umstellen(datenbank, qdrant, Realm({}), beta_zugaenge=beta)

        assert trocken.beta_anzulegen == [ANDERE]
        assert ANDERE not in trocken.ohne_konto

    def test_abgewiesener_beta_zugang_haelt_die_anderen_nicht_auf(
        self, datenbank, spuren, qdrant
    ):
        realm = Realm({})
        realm.abweisen = {"kaputt@example"}
        beta = {
            PERSON: BetaZugang("kaputt@example", "Anna Beispiel"),
            ANDERE: BetaZugang("ben@example.org", "Ben Beispiel"),
        }

        lauf = _umstellen(datenbank, qdrant, realm, beta_zugaenge=beta, ausfuehren=True)

        assert lauf.beta_abgewiesen == [PERSON]
        assert lauf.beta_anzulegen == []
        assert lauf.zuordnung == {ANDERE: f"{ANDERE}-neu"}
        assert _kennung_irgendwo(datenbank, ANDERE) == []

    def test_geloeschter_beta_zugang_bekommt_kein_konto(
        self, datenbank, spuren, qdrant
    ):
        realm = Realm({})
        beta = {ANDERE: BetaZugang("ben@example.org", "Ben Beispiel")}

        ergebnis = _umstellen(
            datenbank,
            qdrant,
            realm,
            beta_zugaenge=beta,
            loeschliste=[ANDERE],
            ausfuehren=True,
        )

        assert realm.mit_passwort_fuer == []
        assert ANDERE not in ergebnis.zuordnung

    def test_unstimmige_zuordnung_bricht_ab_bevor_ein_konto_entsteht(
        self, datenbank, spuren, qdrant
    ):
        """Erst alles pruefen, dann Konten anlegen und Mails schicken."""
        realm = Realm({PERSON: NEU, "noch-wer": NEU})
        beta = {ANDERE: BetaZugang("ben@example.org", "Ben Beispiel")}

        with pytest.raises(ValueError):
            _umstellen(
                datenbank,
                qdrant,
                realm,
                listen={"ADMIN_USER_IDS": ["noch-wer"]},
                anzulegen={ANDERE: "ben@example.org"},
                beta_zugaenge=beta,
                ausfuehren=True,
            )

        assert realm.angelegt_fuer == []
        assert realm.mit_passwort_fuer == []

    def test_loeschliste_behaelt_die_alte_und_bekommt_die_neue_dazu(
        self, datenbank, spuren, qdrant
    ):
        """Ein Cookie mit der alten Kennung gilt bis zu 14 Tage; die BFF muss es abweisen."""
        realm = Realm({PERSON: NEU})

        ergebnis = _umstellen(
            datenbank,
            qdrant,
            realm,
            loeschliste=[PERSON, "geloescht-ohne-konto"],
            anzulegen={"geloescht-ohne-konto": "weg@example.org"},
            ausfuehren=True,
        )

        assert ergebnis.loeschliste == [PERSON, "geloescht-ohne-konto", NEU]
        # Fuer Geloeschte kein Konto, und sie stehen nicht unter "ohne Konto".
        assert realm.angelegt_fuer == []
        assert "geloescht-ohne-konto" not in ergebnis.ohne_konto

    def test_zweiter_lauf_ergaenzt_die_loeschliste_nicht_doppelt(
        self, datenbank, spuren, qdrant
    ):
        realm = Realm({PERSON: NEU})
        erster = _umstellen(
            datenbank, qdrant, realm, loeschliste=[PERSON], ausfuehren=True
        )

        zweiter = _umstellen(
            datenbank, qdrant, realm, loeschliste=erster.loeschliste, ausfuehren=True
        )

        assert zweiter.loeschliste == [PERSON, NEU]


class TestKennungenInPostgres:
    def test_findet_jede_kennung_ausser_platzhaltern(self, datenbank, spuren):
        with datenbank.get_session() as s:
            s.add(User(user_id="ehemalige-person-123", anzeigename="ehemalige Person"))

        with datenbank.engine.connect() as verbindung:
            assert kennungen_in_postgres(verbindung) == {PERSON, ANDERE}
