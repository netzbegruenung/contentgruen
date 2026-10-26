"""
Konvention fuer die SQL-Migrationen in mvp/backend/postgres-app/migrations/.

Die Regeln stehen in der README.md dort ("Konvention fuer neue Migrationen"):

- Dateiname ``JJJJ-MM-TT-<thema>.sql``.
- Der Kopf (fuehrender SQL-Kommentar) endet mit dem Verweis auf die README und
  enthaelt keinen eigenen Befehl zum Anwenden. Der Befehl steht nur in der
  README, damit eine Umbenennung (Container, Datenbank, Pfad) nur sie aendert.
- Das SQL laeuft in ``BEGIN; ... COMMIT;``. Danach steht hoechstens, was nicht
  in einer Transaktion laufen darf (``VACUUM``).

``verstoesse`` prueft einen Dateiinhalt; die Tests mit absichtlichen
Verstoessen belegen, dass jede Regel einen Fehler meldet.
"""

import re
from pathlib import Path

import pytest

REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
MIGRATIONEN = REPO_WURZEL / "mvp" / "backend" / "postgres-app" / "migrations"

VERWEIS = "-- Anwenden: siehe README.md in diesem Verzeichnis."
DATEINAME = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*\.sql$")
# Woran man einen kopierten Befehl zum Anwenden erkennt.
BEFEHL = re.compile(r"\bpsql\b|\bdocker\b|docker-compose|ON_ERROR_STOP", re.I)
NACH_COMMIT_ERLAUBT = re.compile(r"^VACUUM\b", re.I)


def _kopf_und_rumpf(inhalt: str) -> tuple[list[str], list[str]]:
    """Trennt den fuehrenden Kommentarblock vom Rest der Datei."""
    zeilen = inhalt.splitlines()
    kopf: list[str] = []
    for i, zeile in enumerate(zeilen):
        if zeile.startswith("--"):
            kopf.append(zeile.rstrip())
        elif zeile.strip():
            return kopf, zeilen[i:]
        elif kopf:
            # Leerzeile beendet den Kopf.
            return kopf, zeilen[i:]
    return kopf, []


def _anweisungen(zeilen: list[str]) -> list[str]:
    """SQL ohne Kommentarzeilen, an ``;`` zerlegt (reicht fuer diese Skripte)."""
    sql = "\n".join(z for z in zeilen if not z.lstrip().startswith("--"))
    return [a.strip() for a in sql.split(";") if a.strip()]


def verstoesse(dateiname: str, inhalt: str) -> list[str]:
    """Alle Abweichungen einer Migrationsdatei von der Konvention."""
    fehler: list[str] = []
    if not DATEINAME.match(dateiname):
        fehler.append("Dateiname folgt nicht JJJJ-MM-TT-<thema>.sql")

    kopf, rumpf = _kopf_und_rumpf(inhalt)
    if not kopf:
        fehler.append("kein Kopf (fuehrender SQL-Kommentar)")
    elif kopf[-1] != VERWEIS:
        fehler.append(f"letzte Kopfzeile ist nicht {VERWEIS!r}")
    for zeile in kopf:
        if BEFEHL.search(zeile):
            fehler.append(f"Kopf enthaelt einen Befehl zum Anwenden: {zeile!r}")

    anweisungen = _anweisungen(rumpf)
    gross = [a.upper() for a in anweisungen]
    if not gross or gross[0] != "BEGIN":
        fehler.append("erste Anweisung ist nicht BEGIN;")
    if "COMMIT" not in gross:
        fehler.append("kein COMMIT;")
    else:
        nach_commit = anweisungen[gross.index("COMMIT") + 1 :]
        for anweisung in nach_commit:
            if not NACH_COMMIT_ERLAUBT.match(anweisung):
                erste_zeile = anweisung.splitlines()[0]
                fehler.append(f"nach COMMIT steht mehr als VACUUM: {erste_zeile!r}")
    return fehler


def _migrationsdateien() -> list[Path]:
    return sorted(MIGRATIONEN.glob("*.sql"))


GUTE_MIGRATION = f"""-- Beispiel: neue Spalte
--
-- Neue Datenbanken brauchen dieses Skript nicht.
--
{VERWEIS}

BEGIN;

ALTER TABLE beispiel ADD COLUMN IF NOT EXISTS neu TEXT;

COMMIT;
"""


@pytest.mark.unit
class TestMigrationsdateien:
    def test_verzeichnis_hat_migrationen(self):
        # Ohne Dateien liefe die Parametrisierung unten leer und waere gruen.
        assert _migrationsdateien(), f"keine Migrationen unter {MIGRATIONEN}"

    @pytest.mark.parametrize("datei", _migrationsdateien(), ids=lambda p: p.name)
    def test_migration_folgt_konvention(self, datei: Path):
        assert verstoesse(datei.name, datei.read_text(encoding="utf-8")) == []


@pytest.mark.unit
class TestVerstoesse:
    """Absichtliche Verstoesse: jede Regel muss anschlagen."""

    def test_verstoesse_gute_migration_keine(self):
        assert verstoesse("2026-10-26-beispiel.sql", GUTE_MIGRATION) == []

    def test_verstoesse_vacuum_nach_commit_erlaubt(self):
        inhalt = GUTE_MIGRATION + "\n-- Platz zurueckgeben\nVACUUM FULL beispiel;\n"
        assert verstoesse("2026-10-26-beispiel.sql", inhalt) == []

    @pytest.mark.parametrize(
        "dateiname",
        ["beispiel.sql", "2026-10-26_beispiel.sql", "2026-10-26-Beispiel.sql"],
    )
    def test_verstoesse_falscher_dateiname(self, dateiname: str):
        assert verstoesse(dateiname, GUTE_MIGRATION) != []

    def test_verstoesse_ohne_kopf(self):
        inhalt = GUTE_MIGRATION.split("\n\n", 1)[1]
        assert verstoesse("2026-10-26-beispiel.sql", inhalt) != []

    def test_verstoesse_ohne_verweis(self):
        inhalt = GUTE_MIGRATION.replace(VERWEIS, "-- Fertig.")
        assert verstoesse("2026-10-26-beispiel.sql", inhalt) != []

    def test_verstoesse_verweis_nicht_letzte_kopfzeile(self):
        inhalt = GUTE_MIGRATION.replace(VERWEIS, VERWEIS + "\n-- Noch ein Satz.")
        assert verstoesse("2026-10-26-beispiel.sql", inhalt) != []

    @pytest.mark.parametrize(
        "befehl",
        [
            "--   docker exec -i gutgesagt-app-postgres psql -U app_user -d gutgesagt_app",
            "--   psql -v ON_ERROR_STOP=1 -f 2026-10-26-beispiel.sql",
            "--   docker compose exec app-postgres psql < datei.sql",
        ],
    )
    def test_verstoesse_befehl_im_kopf(self, befehl: str):
        inhalt = GUTE_MIGRATION.replace(VERWEIS, befehl + "\n" + VERWEIS)
        assert any("Befehl" in f for f in verstoesse("2026-10-26-b.sql", inhalt))

    def test_verstoesse_ohne_begin(self):
        inhalt = GUTE_MIGRATION.replace("BEGIN;\n", "")
        assert verstoesse("2026-10-26-beispiel.sql", inhalt) != []

    def test_verstoesse_ohne_commit(self):
        inhalt = GUTE_MIGRATION.replace("COMMIT;\n", "")
        assert verstoesse("2026-10-26-beispiel.sql", inhalt) != []

    def test_verstoesse_aenderung_nach_commit(self):
        inhalt = GUTE_MIGRATION + "DROP TABLE alt;\n"
        assert verstoesse("2026-10-26-beispiel.sql", inhalt) != []
