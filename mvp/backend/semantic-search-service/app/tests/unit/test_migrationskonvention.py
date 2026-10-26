"""
Konvention fuer die SQL-Migrationen in mvp/backend/postgres-app/migrations/.

Die Regeln stehen in der README.md dort ("Konvention fuer neue Migrationen"):

- Dateiname ``JJJJ-MM-TT-<thema>.sql`` mit gueltigem Datum.
- Der Kopf (fuehrender SQL-Kommentar) endet mit dem Verweis auf die README.
  Keine Kommentarzeile der Datei enthaelt einen eigenen Befehl zum Anwenden:
  Der Befehl steht nur in der README, damit eine Umbenennung (Container,
  Datenbank, Pfad) nur sie aendert.
- Das SQL laeuft in ``BEGIN; ... COMMIT;``. Danach steht hoechstens, was nicht
  in einer Transaktion laufen darf; bisher ist das nur ``VACUUM``.

``verstoesse`` prueft einen Dateiinhalt; die Tests mit absichtlichen
Verstoessen belegen, dass jede Regel ihren Fehler meldet. Die Zerlegung an
``;`` traegt, solange die Skripte keine Strings mit Semikolon und keine
$$-Bloecke haben.
"""

import re
from datetime import date
from pathlib import Path

import pytest

REPO_WURZEL = next((p for p in Path(__file__).parents if (p / "mvp").is_dir()), None)
MIGRATIONEN = (
    REPO_WURZEL / "mvp" / "backend" / "postgres-app" / "migrations"
    if REPO_WURZEL
    else None
)

VERWEIS = "-- Anwenden: siehe README.md in diesem Verzeichnis."
DATEINAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-[a-z0-9]+(-[a-z0-9]+)*\.sql$")
# Woran man einen kopierten Befehl zum Anwenden erkennt.
BEFEHL = re.compile(
    r"\bpsql\b|\bdocker(\s+compose|-compose)?\s+exec\b|ON_ERROR_STOP|^--\s*\\i\s",
    re.I,
)
NACH_COMMIT_ERLAUBT = re.compile(r"^VACUUM\b", re.I)


def _kopf_und_rumpf(inhalt: str) -> tuple[list[str], list[str]]:
    """Trennt den fuehrenden Kommentarblock (bis zur ersten Leerzeile) vom Rest."""
    zeilen = inhalt.splitlines()
    kopf: list[str] = []
    for i, zeile in enumerate(zeilen):
        if zeile.startswith("--"):
            kopf.append(zeile.rstrip())
        elif zeile.strip() or kopf:
            return kopf, zeilen[i:]
    return kopf, []


def _anweisungen(zeilen: list[str]) -> list[str]:
    """SQL ohne Kommentarzeilen, an ``;`` zerlegt."""
    sql = "\n".join(z for z in zeilen if not z.lstrip().startswith("--"))
    return [a.strip() for a in sql.split(";") if a.strip()]


def _datum_gueltig(text: str) -> bool:
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def verstoesse(dateiname: str, inhalt: str) -> list[str]:
    """Alle Abweichungen einer Migrationsdatei von der Konvention."""
    fehler: list[str] = []
    treffer = DATEINAME.match(dateiname)
    if not treffer or not _datum_gueltig(treffer.group(1)):
        fehler.append("Dateiname folgt nicht JJJJ-MM-TT-<thema>.sql")

    kopf, rumpf = _kopf_und_rumpf(inhalt)
    if not kopf:
        fehler.append("kein Kopf (fuehrender SQL-Kommentar)")
    elif kopf[-1] != VERWEIS:
        fehler.append(f"letzte Kopfzeile ist nicht {VERWEIS!r}")
    for zeile in inhalt.splitlines():
        if zeile.lstrip().startswith("--") and BEFEHL.search(zeile.lstrip()):
            fehler.append(f"Befehl zum Anwenden im Kommentar: {zeile!r}")

    anweisungen = _anweisungen(rumpf)
    gross = [a.upper() for a in anweisungen]
    if not gross or gross[0] != "BEGIN":
        fehler.append("erste Anweisung ist nicht BEGIN;")
    if "COMMIT" not in gross:
        fehler.append("kein COMMIT;")
    else:
        for anweisung in anweisungen[gross.index("COMMIT") + 1 :]:
            if not NACH_COMMIT_ERLAUBT.match(anweisung):
                erste_zeile = anweisung.splitlines()[0]
                fehler.append(f"nach COMMIT steht mehr als VACUUM: {erste_zeile!r}")
    return fehler


def _migrationsdateien() -> list[Path]:
    return sorted(MIGRATIONEN.glob("*.sql")) if MIGRATIONEN else []


DATEI = "2026-10-26-beispiel.sql"
GUTE_MIGRATION = f"""-- Beispiel: neue Spalte
--
-- Neue Datenbanken brauchen dieses Skript nicht.
--
{VERWEIS}

BEGIN;

ALTER TABLE beispiel ADD COLUMN IF NOT EXISTS neu TEXT;

COMMIT;
"""


def _meldet(inhalt: str, stichwort: str, dateiname: str = DATEI) -> bool:
    """Ob genau die Regel mit diesem Stichwort anschlaegt."""
    return any(stichwort in f for f in verstoesse(dateiname, inhalt))


@pytest.mark.unit
class TestMigrationsdateien:
    def test_migrationsdateien_verzeichnis_nicht_leer(self):
        # Ohne Dateien liefe die Parametrisierung unten leer und waere gruen.
        assert _migrationsdateien(), (
            "keine Migrationen gefunden: Test muss im Repo-Checkout laufen "
            "(mvp/backend/postgres-app/migrations/)"
        )

    @pytest.mark.parametrize("datei", _migrationsdateien(), ids=lambda p: p.name)
    def test_migrationsdateien_folgen_konvention(self, datei: Path):
        assert verstoesse(datei.name, datei.read_text(encoding="utf-8")) == []


@pytest.mark.unit
class TestVerstoesse:
    """Absichtliche Verstoesse: jede Regel muss ihren Fehler melden."""

    def test_verstoesse_gute_migration_keine(self):
        assert verstoesse(DATEI, GUTE_MIGRATION) == []

    def test_verstoesse_vacuum_nach_commit_erlaubt(self):
        inhalt = GUTE_MIGRATION + "\n-- Platz zurueckgeben\nVACUUM FULL beispiel;\n"
        assert verstoesse(DATEI, inhalt) == []

    def test_verstoesse_docker_im_fliesstext_erlaubt(self):
        inhalt = GUTE_MIGRATION.replace(
            VERWEIS, "-- Der Dienst im Docker-Container legt sie an.\n" + VERWEIS
        )
        assert verstoesse(DATEI, inhalt) == []

    @pytest.mark.parametrize(
        "dateiname",
        [
            "beispiel.sql",
            "2026-10-26_beispiel.sql",
            "2026-10-26-Beispiel.sql",
            "2026-13-45-beispiel.sql",
        ],
    )
    def test_verstoesse_falscher_dateiname(self, dateiname: str):
        assert _meldet(GUTE_MIGRATION, "Dateiname", dateiname)

    def test_verstoesse_ohne_kopf(self):
        inhalt = GUTE_MIGRATION.split("\n\n", 1)[1]
        assert _meldet(inhalt, "kein Kopf")

    def test_verstoesse_ohne_verweis(self):
        inhalt = GUTE_MIGRATION.replace(VERWEIS, "-- Fertig.")
        assert _meldet(inhalt, "letzte Kopfzeile")

    def test_verstoesse_verweis_nicht_letzte_kopfzeile(self):
        inhalt = GUTE_MIGRATION.replace(VERWEIS, VERWEIS + "\n-- Noch ein Satz.")
        assert _meldet(inhalt, "letzte Kopfzeile")

    @pytest.mark.parametrize(
        "befehl",
        [
            "--   docker exec -i gutgesagt-app-postgres psql -U app_user -d app",
            "--   psql -v ON_ERROR_STOP=1 -f 2026-10-26-beispiel.sql",
            "--   docker compose exec app-postgres sh -c 'cat > x'",
            "-- \\i 2026-10-26-beispiel.sql",
        ],
    )
    def test_verstoesse_befehl_im_kopf(self, befehl: str):
        inhalt = GUTE_MIGRATION.replace(VERWEIS, befehl + "\n" + VERWEIS)
        assert _meldet(inhalt, "Befehl")

    def test_verstoesse_befehl_in_spaeterem_kommentar(self):
        inhalt = GUTE_MIGRATION.replace(
            "BEGIN;", "-- Anwenden mit: docker exec -i pg psql < x.sql\nBEGIN;"
        )
        assert _meldet(inhalt, "Befehl")

    def test_verstoesse_ohne_begin(self):
        inhalt = GUTE_MIGRATION.replace("BEGIN;\n", "")
        assert _meldet(inhalt, "BEGIN")

    def test_verstoesse_ohne_commit(self):
        inhalt = GUTE_MIGRATION.replace("COMMIT;\n", "")
        assert _meldet(inhalt, "kein COMMIT")

    def test_verstoesse_aenderung_nach_commit(self):
        inhalt = GUTE_MIGRATION + "DROP TABLE alt;\n"
        assert _meldet(inhalt, "nach COMMIT")
