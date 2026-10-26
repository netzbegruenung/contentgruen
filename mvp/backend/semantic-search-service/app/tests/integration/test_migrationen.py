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
from pathlib import Path

import pytest
from sqlalchemy import text

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
    for name in NUR_EINMAL:
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
