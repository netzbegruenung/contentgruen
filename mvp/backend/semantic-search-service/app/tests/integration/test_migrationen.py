"""
Die Migrationen (mvp/backend/postgres-app/migrations) gegen ein echtes PostgreSQL.

Prueft die beiden README-Regeln, die der Unit-Test test_migrationskonvention.py
ohne Datenbank nicht pruefen kann: Jedes Skript laeuft zweimal fehlerfrei auf einer
Datenbank im aktuellen Schema, und danach ist das Schema genau das, was
``create_all`` aus den Modellen anlegt (Spalten, Defaults, Indizes, Constraints).
"""

import re

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


def _schema_der(db: Datenbank) -> dict:
    """Tabellen, Spalten, Indizes und Constraints im Schema, ohne dessen Namen."""
    abfragen = {
        "spalten": """
            SELECT table_name, column_name, data_type, character_maximum_length,
                   is_nullable, column_default
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
        c.execute(
            text("ALTER TABLE search_events ALTER COLUMN timestamp SET DEFAULT now()")
        )

    assert _abweichungen(_schema_der(aktuelle_datenbank), modell_schema) != {}
