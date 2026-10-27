"""
Die Migrationen (mvp/backend/postgres-app/migrations) und das Init-Skript
(mvp/backend/postgres-app/init.sql) gegen ein echtes PostgreSQL.

Prueft die README-Regeln, die der Unit-Test test_migrationskonvention.py ohne
Datenbank nicht pruefen kann: Jedes Skript laeuft zweimal fehlerfrei auf einer
Datenbank im aktuellen Schema, und danach gleicht das Schema dem, was ``create_all``
aus den Modellen anlegt. Dasselbe gilt fuer eine Datenbank, die wie Test und
Produktion aus dem Init-Skript entstanden ist: im heutigen Stand, vor #285 und im
aeltesten Stand der oeffentlichen Historie, vor der Datensparsamkeit.

Verglichen werden Spalten (Typ, Laenge, Nullbarkeit, Default), Indizes, Constraints
samt Fremdschluesseln, Sequenzen (Typ), Trigger und Funktionen. ``create_all`` legt
keine Trigger oder Funktionen an; jeder Trigger im Init-Skript oder in einer
Migration ist deshalb eine Abweichung.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import text

from infrastructure.database import migrationen
from infrastructure.database.models import Base
from tests.integration import postgres
from tests.integration.postgres import Datenbank

pytestmark = pytest.mark.integration

# Laeuft nur einmal, auf dem Schema davor: benennt user_agent um, das es seither
# nicht mehr gibt. Steht in der README unter "Erneut anwenden". Das zweite Skript
# dort (search-events-pseudonymisieren) laeuft mit: Sein TRUNCATE verliert auf den
# leeren Tabellen hier nichts, das Schema bleibt pruefbar.
NUR_EINMAL = {"2026-08-25-usage-events-datensparsamkeit.sql"}

SKRIPTE = postgres.migrationen()
WIEDERHOLBAR = [s for s in SKRIPTE if s.name not in NUR_EINMAL]
ANGELEGT = re.compile(r"CREATE TABLE IF NOT EXISTS (\w+)", re.IGNORECASE)
INHALT = {"id": "6f1c1e9e-0000-4000-8000-000000000285"}

# Fruehere Staende des Init-Skripts, aus denen Test- und Produktionsdatenbanken
# entstanden sind, ohne GRANTs. Beide wichen vom Modell ab (Indizes, Trigger, Typ
# von usage_events.id); die Migration 2026-10-26-init-angleichen.sql gleicht das an.
# Der aeltere hat zudem noch die Spalten, die die Datensparsamkeit entfernt.
INIT_VOR_285 = Path(__file__).with_name("init_vor_285.sql")
INIT_VOR_DATENSPARSAMKEIT = Path(__file__).with_name("init_vor_datensparsamkeit.sql")


def _schema_der(db: Datenbank) -> dict:
    """Spalten, Indizes, Constraints, Sequenzen, Trigger und Funktionen im Schema."""
    abfragen = {
        "spalten": """
            SELECT table_name, column_name, data_type, udt_name,
                   character_maximum_length, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = current_schema()
        """,
        "indizes": """
            SELECT tablename, indexname, indexdef
            FROM pg_indexes WHERE schemaname = current_schema()
        """,
        "constraints": """
            SELECT cl.relname, co.conname, pg_get_constraintdef(co.oid)
            FROM pg_constraint co JOIN pg_class cl ON cl.oid = co.conrelid
            WHERE co.connamespace = current_schema()::regnamespace
        """,
        "sequenzen": """
            SELECT sequence_name, data_type
            FROM information_schema.sequences
            WHERE sequence_schema = current_schema()
        """,
        "trigger": """
            SELECT event_object_table, trigger_name, action_timing,
                   event_manipulation, action_statement
            FROM information_schema.triggers
            WHERE trigger_schema = current_schema()
        """,
        "funktionen": """
            SELECT proname FROM pg_proc
            WHERE pronamespace = current_schema()::regnamespace
        """,
    }
    with db.engine.connect() as c:
        return {
            art: sorted(
                tuple(_normalisiert(wert, db.schema) for wert in zeile)
                for zeile in c.execute(text(abfrage))
            )
            for art, abfrage in abfragen.items()
        }


def _normalisiert(wert, schema: str) -> str:
    """
    Den Schemanamen weglassen und CURRENT_TIMESTAMP als now() lesen: Fuer
    timestamptz ist das in PostgreSQL dieselbe Funktion, die Skripte schreiben
    die eine, func.now() im Modell die andere.
    """
    return str(wert).replace(f"{schema}.", "").replace("CURRENT_TIMESTAMP", "now()")


def _abweichungen(ist: dict, modell: dict) -> dict:
    """Je Art, was nur nach den Migrationen und was nur im Modell steht."""
    abweichungen = {}
    for art in modell:
        nur_ist = sorted(set(ist[art]) - set(modell[art]))
        nur_modell = sorted(set(modell[art]) - set(ist[art]))
        if nur_ist or nur_modell:
            abweichungen[art] = {"nur_migriert": nur_ist, "nur_modell": nur_modell}
    return abweichungen


@pytest.fixture
def modell_schema(postgres_url):
    with postgres.schema(postgres_url, "itest_modell") as db:
        Base.metadata.create_all(db.engine)
        yield _schema_der(db)


@pytest.fixture
def aktuelle_datenbank(wegwerf_schema):
    Base.metadata.create_all(wegwerf_schema.engine)
    return wegwerf_schema


def _aus_init_skript(db: Datenbank, skript: Path) -> Datenbank:
    """
    Wie eine Bestandsdatenbank entstanden ist: Das Init-Skript laeuft bei leerem
    Volume, beim ersten Start legt der Dienst mit create_all die uebrigen Tabellen an.
    """
    postgres.init_skript_anwenden(db, skript)
    Base.metadata.create_all(db.engine)
    return db


def _kette(db: Datenbank, mit_einmaligen: bool) -> None:
    """
    Alle Migrationen in der Reihenfolge der README, die wiederholbaren zweimal. Die
    nur einmal lauffaehigen nur, wenn die Datenbank sie noch braucht.
    """
    for skript in SKRIPTE:
        if skript.name in NUR_EINMAL:
            if mit_einmaligen:
                postgres.migration(db, skript)
        else:
            postgres.migration(db, skript)
            postgres.migration(db, skript)


def test_es_gibt_migrationen():
    """Ohne Skripte waere der parametrisierte Test still leer."""
    assert len(SKRIPTE) > 1
    assert NUR_EINMAL <= {s.name for s in SKRIPTE}


def test_ausnahmen_stehen_in_der_readme():
    readme = (postgres.MIGRATIONEN / "README.md").read_text(encoding="utf-8")
    abschnitt = readme.split("### Erneut anwenden", 1)[1].split("\n## ", 1)[0]
    for name in NUR_EINMAL | migrationen.NICHT_WIEDERHOLBAR.keys():
        assert f"`{name}`" in abschnitt


@pytest.mark.parametrize(
    "skript",
    WIEDERHOLBAR,
    ids=lambda s: s.stem,
)
def test_zweimal_angewendet_bleibt_das_schema_des_modells(
    skript, aktuelle_datenbank, modell_schema
):
    postgres.migration(aktuelle_datenbank, skript)
    postgres.migration(aktuelle_datenbank, skript)

    assert _abweichungen(_schema_der(aktuelle_datenbank), modell_schema) == {}


def test_kette_legt_tabellen_an_wie_das_modell(aktuelle_datenbank, modell_schema):
    """
    Ohne die Tabellen, die Migrationen selbst anlegen, ergibt die ganze Kette in
    der Reihenfolge der README wieder das Modell: Was ein Skript anlegt und spaeter
    eines aendert, entspricht create_all, nicht nur ein Lauf auf fertigem Schema.
    """
    tabellen = {
        name
        for skript in SKRIPTE
        for name in ANGELEGT.findall(skript.read_text(encoding="utf-8"))
    }
    assert tabellen, "Kein Skript legt eine Tabelle an?"
    with aktuelle_datenbank.engine.begin() as c:
        for tabelle in tabellen:
            c.execute(text(f"DROP TABLE {tabelle} CASCADE"))

    for skript in WIEDERHOLBAR:
        postgres.migration(aktuelle_datenbank, skript)
        postgres.migration(aktuelle_datenbank, skript)

    assert _abweichungen(_schema_der(aktuelle_datenbank), modell_schema) == {}


def test_vergleich_sieht_einen_anderen_default(aktuelle_datenbank, modell_schema):
    """Gegenprobe: Der Vergleich wuerde den alten Default von search_events zeigen."""
    with aktuelle_datenbank.engine.begin() as c:
        c.execute(text(postgres.SUCHEREIGNIS_DEFAULT_VOR_256))

    assert _abweichungen(_schema_der(aktuelle_datenbank), modell_schema) != {}


def test_init_skript_legt_das_schema_des_modells_an(wegwerf_schema, modell_schema):
    """Eine neue Datenbank hat ohne jede Migration das Schema des Modells."""
    db = _aus_init_skript(wegwerf_schema, postgres.INIT_SKRIPT)

    assert _abweichungen(_schema_der(db), modell_schema) == {}


@pytest.mark.parametrize(
    "init, mit_einmaligen",
    [
        (postgres.INIT_SKRIPT, False),
        (INIT_VOR_285, False),
        (INIT_VOR_DATENSPARSAMKEIT, True),
    ],
    ids=["init", "init_vor_285", "init_vor_datensparsamkeit"],
)
def test_kette_ab_init_skript_ergibt_das_modell(
    init, mit_einmaligen, wegwerf_schema, modell_schema
):
    """
    Eine Bestandsdatenbank aus dem Init-Skript hat nach der Kette, je
    wiederholbarem Skript zweimal, das Schema des Modells, Trigger eingeschlossen.
    """
    db = _aus_init_skript(wegwerf_schema, init)

    _kette(db, mit_einmaligen)

    assert _abweichungen(_schema_der(db), modell_schema) == {}


def test_kette_ab_aeltestem_init_skript_behaelt_die_nutzungen(wegwerf_schema):
    """
    Der Typwechsel von usage_events.id laesst Zeilen, IDs und den Stand der Sequenz
    unberuehrt; die naechste Nutzung bekommt die naechste ID.
    """
    db = _aus_init_skript(wegwerf_schema, INIT_VOR_DATENSPARSAMKEIT)
    with db.engine.begin() as c:
        c.execute(text("INSERT INTO usage_tracking (content_id) VALUES (:id)"), INHALT)
        c.execute(
            text("INSERT INTO usage_events (content_id) VALUES (:id), (:id)"), INHALT
        )
        vorher = c.execute(text("SELECT id FROM usage_events ORDER BY id")).all()

    _kette(db, mit_einmaligen=True)

    with db.engine.begin() as c:
        nachher = c.execute(text("SELECT id FROM usage_events ORDER BY id")).all()
        c.execute(text("INSERT INTO usage_events (content_id) VALUES (:id)"), INHALT)
        neu = c.execute(text("SELECT max(id) FROM usage_events")).scalar_one()
    assert nachher == vorher
    assert neu == vorher[-1][0] + 1


def test_vergleich_sieht_das_init_skript_vor_285(wegwerf_schema, modell_schema):
    """Gegenprobe: Ohne Migrationen weicht eine Datenbank von vor #285 ab, auch im Trigger."""
    db = _aus_init_skript(wegwerf_schema, INIT_VOR_285)

    abweichungen = _abweichungen(_schema_der(db), modell_schema)

    assert {"indizes", "trigger", "funktionen"} <= abweichungen.keys()


# --- Automatisches Einspielen (#293) ------------------------------------------


def test_einspielen_auf_neuer_datenbank_ergibt_das_modell(
    aktuelle_datenbank, modell_schema
):
    """
    Wie bei run-local.sh wipe: init.sql und create_all haben das Schema schon
    angelegt. Die wiederholbaren Skripte laufen trotzdem und landen im Protokoll,
    die drei nicht wiederholbaren erkennt der Lauf an ihrer Wirkung.
    """
    eingespielt = migrationen.einspielen(
        aktuelle_datenbank.engine, postgres.MIGRATIONEN
    )

    assert eingespielt == [
        s.name for s in SKRIPTE if s.name not in migrationen.NICHT_WIEDERHOLBAR
    ]
    assert migrationen.protokoll(aktuelle_datenbank.engine) == {
        s.name: (
            migrationen.ERKANNT
            if s.name in migrationen.NICHT_WIEDERHOLBAR
            else migrationen.EINGESPIELT
        )
        for s in SKRIPTE
    }
    assert _abweichungen(_schema_der(aktuelle_datenbank), modell_schema) == {}


@pytest.mark.parametrize(
    "init",
    [postgres.INIT_SKRIPT, INIT_VOR_285, INIT_VOR_DATENSPARSAMKEIT],
    ids=["init", "init_vor_285", "init_vor_datensparsamkeit"],
)
def test_einspielen_ab_init_skript_ergibt_das_modell(
    init, wegwerf_schema, modell_schema
):
    """Die Kettentests fuer den automatischen Ablauf, zweimal hintereinander."""
    db = _aus_init_skript(wegwerf_schema, init)

    migrationen.einspielen(db.engine, postgres.MIGRATIONEN)

    assert migrationen.einspielen(db.engine, postgres.MIGRATIONEN) == []
    assert _abweichungen(_schema_der(db), modell_schema) == {}


def test_einspielen_ohne_tabellen_der_skripte_ergibt_das_modell(
    aktuelle_datenbank, modell_schema
):
    """Wie test_kette_legt_tabellen_an_wie_das_modell, nur ueber den Ablauf."""
    tabellen = {
        name
        for skript in SKRIPTE
        for name in ANGELEGT.findall(skript.read_text(encoding="utf-8"))
    }
    with aktuelle_datenbank.engine.begin() as c:
        for tabelle in tabellen:
            c.execute(text(f"DROP TABLE {tabelle} CASCADE"))

    migrationen.einspielen(aktuelle_datenbank.engine, postgres.MIGRATIONEN)

    assert _abweichungen(_schema_der(aktuelle_datenbank), modell_schema) == {}


def test_einspielen_spielt_datensparsamkeit_nur_auf_altem_stand_ein(wegwerf_schema):
    db = _aus_init_skript(wegwerf_schema, INIT_VOR_DATENSPARSAMKEIT)

    eingespielt = migrationen.einspielen(db.engine, postgres.MIGRATIONEN)

    assert "2026-08-25-usage-events-datensparsamkeit.sql" in eingespielt
    assert (
        migrationen.protokoll(db.engine)["2026-08-25-usage-events-datensparsamkeit.sql"]
        == migrationen.EINGESPIELT
    )


def test_einspielen_leert_eingespielte_suchereignisse_nicht(aktuelle_datenbank):
    """
    Von Hand eingespielt, noch ohne Protokoll: Das TRUNCATE der Pseudonymisierung
    darf die seither erfassten Suchereignisse nicht treffen.
    """
    with aktuelle_datenbank.engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO search_events (actor_hash, results_count) VALUES ('a', 0)"
            )
        )

    migrationen.einspielen(aktuelle_datenbank.engine, postgres.MIGRATIONEN)

    with aktuelle_datenbank.engine.begin() as c:
        assert c.execute(text("SELECT count(*) FROM search_events")).scalar_one() == 1


def test_einspielen_pseudonymisiert_alte_suchereignisse(aktuelle_datenbank):
    """Gegenstueck: Ohne actor_hash (Stand vor dem 19.08.) laeuft das Skript."""
    with aktuelle_datenbank.engine.begin() as c:
        c.execute(text("ALTER TABLE search_events DROP COLUMN actor_hash"))
        c.execute(text("ALTER TABLE search_events ADD COLUMN query_text TEXT"))
        c.execute(
            text(
                "INSERT INTO search_events (query_text, results_count) "
                "VALUES ('Waermepumpe', 0)"
            )
        )

    eingespielt = migrationen.einspielen(
        aktuelle_datenbank.engine, postgres.MIGRATIONEN
    )

    assert "2026-08-19-search-events-pseudonymisieren.sql" in eingespielt
    with aktuelle_datenbank.engine.begin() as c:
        assert c.execute(text("SELECT count(*) FROM search_events")).scalar_one() == 0
        spalten = c.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = 'search_events'"
            )
        ).scalars()
        assert "actor_hash" in set(spalten)


def test_einspielen_verknuepft_beitraege_nicht_neu(aktuelle_datenbank):
    """
    Von Hand eingespielt: Der Nachtrag in fangkorb-v2 haengte einen Beitrag ohne
    Satz an einen spaeter geschriebenen Satz derselben Person.
    """
    with aktuelle_datenbank.engine.begin() as c:
        einwurf = c.execute(
            text("INSERT INTO raw_inputs (content) VALUES ('Einwurf') RETURNING id")
        ).scalar_one()
        parameter = {"einwurf": einwurf, "beitrag": INHALT["id"], "person": "u-1"}
        c.execute(
            text(
                "INSERT INTO raw_input_content_links "
                "(raw_input_id, content_id, created_by) "
                "VALUES (:einwurf, :beitrag, :person)"
            ),
            parameter,
        )
        c.execute(
            text(
                "INSERT INTO raw_input_drafts (raw_input_id, user_id, sentence) "
                "VALUES (:einwurf, :person, 'Spaeter geschriebener Satz')"
            ),
            parameter,
        )

    migrationen.einspielen(aktuelle_datenbank.engine, postgres.MIGRATIONEN)

    assert (
        migrationen.protokoll(aktuelle_datenbank.engine)["2026-09-13-fangkorb-v2.sql"]
        == migrationen.ERKANNT
    )
    with aktuelle_datenbank.engine.begin() as c:
        assert (
            c.execute(text("SELECT draft_id FROM raw_input_content_links")).scalar_one()
            is None
        )


def test_einspielen_bei_belegter_sperre_fehlgeschlagen_und_spaeter_wiederholt(
    aktuelle_datenbank,
):
    """
    2026-10-26-init-angleichen.sql wartet 5 s auf die Sperre der Nutzungstabellen
    und bricht dann ab. Der Lauf vermerkt das und wirft; der naechste holt es nach.
    """
    skript = "2026-10-26-init-angleichen.sql"
    with aktuelle_datenbank.engine.connect() as sperre:
        sperre.execute(text("LOCK TABLE usage_tracking IN ACCESS SHARE MODE"))
        with pytest.raises(migrationen.MigrationFehlgeschlagen, match=skript):
            migrationen.einspielen(aktuelle_datenbank.engine, postgres.MIGRATIONEN)
        assert migrationen.protokoll(aktuelle_datenbank.engine)[skript] == (
            migrationen.FEHLGESCHLAGEN
        )
        sperre.rollback()

    eingespielt = migrationen.einspielen(
        aktuelle_datenbank.engine, postgres.MIGRATIONEN
    )

    assert eingespielt[0] == skript
    assert set(migrationen.protokoll(aktuelle_datenbank.engine).values()) <= {
        migrationen.EINGESPIELT,
        migrationen.ERKANNT,
    }


def _skript(sql: str, nachlauf: str = "") -> str:
    return f"-- Test\n-- Anwenden: siehe README.md in diesem Verzeichnis.\n\nBEGIN;\n{sql}\nCOMMIT;\n{nachlauf}\n"


def test_einspielen_skript_ohne_eigene_grenze_wartet_nicht_endlos(
    aktuelle_datenbank, tmp_path, monkeypatch
):
    """
    Ein Skript ohne SET LOCAL lock_timeout (wie das aus #275) bricht an einer
    belegten Sperre nach WARTEN_AUF_SPERRE ab, statt den Start anzuhalten.
    """
    monkeypatch.setattr(migrationen, "WARTEN_AUF_SPERRE", "1s")
    name = "2026-10-27-ohne-grenze.sql"
    (tmp_path / name).write_text(
        _skript("ALTER TABLE search_events ADD COLUMN IF NOT EXISTS itest INT;")
    )
    with aktuelle_datenbank.engine.connect() as sperre:
        sperre.execute(text("LOCK TABLE search_events IN ACCESS SHARE MODE"))
        with pytest.raises(migrationen.MigrationFehlgeschlagen, match="lock timeout"):
            migrationen.einspielen(aktuelle_datenbank.engine, tmp_path)
        sperre.rollback()

    assert migrationen.protokoll(aktuelle_datenbank.engine) == {
        name: migrationen.FEHLGESCHLAGEN
    }
    assert migrationen.einspielen(aktuelle_datenbank.engine, tmp_path) == [name]


def test_einspielen_vacuum_bei_belegter_sperre_holt_der_naechste_start_nach(
    aktuelle_datenbank, tmp_path, monkeypatch
):
    monkeypatch.setattr(migrationen, "WARTEN_AUF_SPERRE", "1s")
    name = "2026-10-27-vacuum-gesperrt.sql"
    (tmp_path / name).write_text(_skript("SELECT 1;", "VACUUM FULL search_events;"))
    with aktuelle_datenbank.engine.connect() as sperre:
        sperre.execute(text("LOCK TABLE search_events IN ACCESS SHARE MODE"))
        assert migrationen.einspielen(aktuelle_datenbank.engine, tmp_path) == [name]
        sperre.rollback()
    assert migrationen.protokoll(aktuelle_datenbank.engine)[name] == (
        migrationen.NACHLAUF_OFFEN
    )

    assert migrationen.einspielen(aktuelle_datenbank.engine, tmp_path) == []
    assert migrationen.protokoll(aktuelle_datenbank.engine)[name] == (
        migrationen.EINGESPIELT
    )


def test_einspielen_nimmt_neue_datei_ohne_codeaenderung_mit(
    aktuelle_datenbank, tmp_path
):
    (tmp_path / "2026-10-27-a.sql").write_text(
        _skript("CREATE TABLE IF NOT EXISTS itest_a (n INT);")
    )
    assert migrationen.einspielen(aktuelle_datenbank.engine, tmp_path) == [
        "2026-10-27-a.sql"
    ]

    (tmp_path / "2026-10-28-b.sql").write_text(
        _skript("INSERT INTO itest_a VALUES (1);")
    )

    assert migrationen.einspielen(aktuelle_datenbank.engine, tmp_path) == [
        "2026-10-28-b.sql"
    ]
    with aktuelle_datenbank.engine.begin() as c:
        assert c.execute(text("SELECT count(*) FROM itest_a")).scalar_one() == 1


def test_einspielen_holt_nur_den_gescheiterten_nachlauf_nach(
    aktuelle_datenbank, tmp_path
):
    """Scheitert das VACUUM nach dem COMMIT, laeuft beim naechsten Mal nur das VACUUM."""
    name = "2026-10-27-mit-vacuum.sql"
    (tmp_path / name).write_text(
        _skript(
            "CREATE TABLE IF NOT EXISTS itest_zaehler (n INT);\n"
            "INSERT INTO itest_zaehler VALUES (1);",
            "VACUUM FULL itest_spaeter;",
        )
    )

    assert migrationen.einspielen(aktuelle_datenbank.engine, tmp_path) == [name]
    assert migrationen.protokoll(aktuelle_datenbank.engine)[name] == (
        migrationen.NACHLAUF_OFFEN
    )

    with aktuelle_datenbank.engine.begin() as c:
        c.execute(text("CREATE TABLE itest_spaeter (n INT)"))
    assert migrationen.einspielen(aktuelle_datenbank.engine, tmp_path) == []

    assert migrationen.protokoll(aktuelle_datenbank.engine)[name] == (
        migrationen.EINGESPIELT
    )
    with aktuelle_datenbank.engine.begin() as c:
        assert c.execute(text("SELECT count(*) FROM itest_zaehler")).scalar_one() == 1


def test_einspielen_rollt_fehlgeschlagene_migration_ganz_zurueck(
    aktuelle_datenbank, tmp_path
):
    name = "2026-10-27-kaputt.sql"
    (tmp_path / name).write_text(
        _skript("CREATE TABLE itest_halb (n INT);\nSELECT * FROM itest_gibt_es_nicht;")
    )

    with pytest.raises(migrationen.MigrationFehlgeschlagen):
        migrationen.einspielen(aktuelle_datenbank.engine, tmp_path)

    with aktuelle_datenbank.engine.begin() as c:
        assert c.execute(text("SELECT to_regclass('itest_halb')")).scalar() is None
    assert migrationen.protokoll(aktuelle_datenbank.engine) == {
        name: migrationen.FEHLGESCHLAGEN
    }


def test_einspielen_zwei_gleichzeitige_starts_spielen_einmal_ein(
    aktuelle_datenbank, tmp_path
):
    """Die Advisory-Sperre laesst den zweiten Start warten; er findet das Skript fertig."""
    name = "2026-10-27-langsam.sql"
    (tmp_path / name).write_text(
        _skript(
            "CREATE TABLE IF NOT EXISTS itest_zaehler (n INT);\n"
            "INSERT INTO itest_zaehler VALUES (1);\nSELECT pg_sleep(1);"
        )
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        laeufe = [
            pool.submit(migrationen.einspielen, aktuelle_datenbank.engine, tmp_path)
            for _ in range(2)
        ]
        ergebnisse = sorted(lauf.result() for lauf in laeufe)

    assert ergebnisse == [[], [name]]
    with aktuelle_datenbank.engine.begin() as c:
        assert c.execute(text("SELECT count(*) FROM itest_zaehler")).scalar_one() == 1
