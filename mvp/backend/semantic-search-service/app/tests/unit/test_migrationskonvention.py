"""
Konvention fuer die SQL-Migrationen in mvp/backend/postgres-app/migrations/.

Die Regeln stehen in der README.md dort ("Konvention fuer neue Migrationen"):

- Dateiname ``JJJJ-MM-TT-<thema>.sql`` mit gueltigem Datum. Nach dem Namen mit
  und ohne ``.sql`` geordnet ergibt sich dieselbe Reihenfolge.
- Der Kopf (fuehrender SQL-Kommentar bis zur ersten Leerzeile) endet mit dem
  Verweis auf die README. Kein Kommentar der Datei, auch keiner am
  Zeilenende, enthaelt einen eigenen Befehl zum Anwenden: Der Befehl steht nur
  in der README, damit eine Umbenennung (Container, Datenbank, Pfad) nur sie
  aendert.
- Das SQL laeuft in ``BEGIN; ... COMMIT;``. Danach steht hoechstens, was nicht
  in einer Transaktion laufen darf: ``VACUUM`` und die ``CONCURRENTLY``-Formen
  von ``CREATE INDEX``, ``DROP INDEX`` und ``REINDEX``.

``verstoesse`` prueft einen Dateiinhalt und nennt je Abweichung die Regel; die
Tests mit absichtlichen Verstoessen belegen, dass jede Regel ihren Fehler
meldet. Kein SQL-Parser: Kommentare beginnen bei ``--``, Anweisungen enden an
``;``. Das traegt, solange die Skripte keine Strings mit ``--`` oder ``;`` und
keine $$-Bloecke haben.
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
    r"\bpsql\b|\b(docker|podman)(\s+compose|-compose)?\s+exec\b|ON_ERROR_STOP"
    r"|^--\s*\\i\s",
    re.I,
)
NACH_COMMIT_ERLAUBT = re.compile(
    r"^(VACUUM\b|(CREATE\s+(UNIQUE\s+)?|DROP\s+)INDEX\s+CONCURRENTLY\b"
    r"|REINDEX\b.*\bCONCURRENTLY\b)",
    re.I | re.S,
)

# Regeln, wie verstoesse sie meldet.
REGEL_DATEINAME = "dateiname"
REGEL_KOPF = "kopf"
REGEL_VERWEIS = "verweis"
REGEL_BEFEHL = "befehl"
REGEL_BEGIN = "begin"
REGEL_COMMIT = "commit"
REGEL_NACH_COMMIT = "nach_commit"


def _code_und_kommentar(zeile: str) -> tuple[str, str]:
    """Teilt eine Zeile am ersten ``--`` in SQL und Kommentar."""
    i = zeile.find("--")
    return (zeile, "") if i < 0 else (zeile[:i], zeile[i:])


def _kopf_und_rumpf(inhalt: str) -> tuple[list[str], list[str]]:
    """Trennt den fuehrenden Kommentarblock (bis zur ersten Leerzeile) vom Rest."""
    zeilen = inhalt.splitlines()
    kopf: list[str] = []
    for i, zeile in enumerate(zeilen):
        code, kommentar = _code_und_kommentar(zeile)
        if kommentar and not code.strip():
            kopf.append(zeile.strip())
        elif zeile.strip() or kopf:
            return kopf, zeilen[i:]
    return kopf, []


def _anweisungen(zeilen: list[str]) -> list[str]:
    """SQL ohne Kommentare, an ``;`` zerlegt."""
    sql = "\n".join(_code_und_kommentar(z)[0] for z in zeilen)
    return [a.strip() for a in sql.split(";") if a.strip()]


def _datum_gueltig(text: str) -> bool:
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def verstoesse(dateiname: str, inhalt: str) -> list[tuple[str, str]]:
    """Alle Abweichungen einer Migrationsdatei als (Regel, Meldung)."""
    fehler: list[tuple[str, str]] = []
    treffer = DATEINAME.match(dateiname)
    if not treffer or not _datum_gueltig(treffer.group(1)):
        fehler.append((REGEL_DATEINAME, "Dateiname folgt nicht JJJJ-MM-TT-<thema>.sql"))

    kopf, rumpf = _kopf_und_rumpf(inhalt)
    if not kopf:
        fehler.append((REGEL_KOPF, "kein Kopf (fuehrender SQL-Kommentar)"))
    elif kopf[-1] != VERWEIS:
        meldung = f"letzte Kopfzeile ist nicht {VERWEIS!r}"
        if VERWEIS in inhalt:
            meldung += " (der Kopf endet an der ersten Leerzeile)"
        fehler.append((REGEL_VERWEIS, meldung))
    for zeile in inhalt.splitlines():
        kommentar = _code_und_kommentar(zeile)[1]
        if BEFEHL.search(kommentar):
            fehler.append(
                (REGEL_BEFEHL, f"Befehl zum Anwenden im Kommentar: {zeile!r}")
            )

    anweisungen = _anweisungen(rumpf)
    gross = [a.upper() for a in anweisungen]
    if not gross or gross[0] != "BEGIN":
        fehler.append((REGEL_BEGIN, "erste Anweisung ist nicht BEGIN;"))
    if "COMMIT" not in gross:
        fehler.append((REGEL_COMMIT, "kein COMMIT;"))
    else:
        for anweisung in anweisungen[gross.index("COMMIT") + 1 :]:
            if not NACH_COMMIT_ERLAUBT.match(anweisung):
                erste_zeile = anweisung.splitlines()[0]
                fehler.append(
                    (
                        REGEL_NACH_COMMIT,
                        f"nach COMMIT steht, was in die Transaktion gehoert: "
                        f"{erste_zeile!r}",
                    )
                )
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


def _regeln(inhalt: str, dateiname: str = DATEI) -> set[str]:
    """Welche Regeln fuer diesen Inhalt anschlagen."""
    return {regel for regel, _ in verstoesse(dateiname, inhalt)}


@pytest.mark.unit
class TestMigrationsdateien:
    def test_migrationsdateien_verzeichnis_nicht_leer(self):
        # Ohne Dateien liefe die Parametrisierung unten leer und waere gruen.
        assert _migrationsdateien(), (
            "keine Migrationen gefunden: Test muss im Repo-Checkout laufen "
            "(mvp/backend/postgres-app/migrations/)"
        )

    def test_migrationsdateien_reihenfolge_mit_und_ohne_endung_gleich(self):
        """
        Die README ordnet nach dem Namen ohne ``.sql``; ``ls`` und ``*.sql``
        ordnen mit Endung. Beides muss dieselbe Reihenfolge ergeben, bis auf das
        Paar, das schon angewendet ist und in der README steht.
        """
        bekannt = {
            "2026-10-26-suchen-ohne-treffer.sql",
            "2026-10-26-suchen-ohne-treffer-personen.sql",
        }
        dateien = [p for p in _migrationsdateien() if p.name not in bekannt]

        assert [p.name for p in sorted(dateien, key=lambda p: p.stem)] == [
            p.name for p in sorted(dateien)
        ]

    @pytest.mark.parametrize("datei", _migrationsdateien(), ids=lambda p: p.name)
    def test_migrationsdateien_folgen_konvention(self, datei: Path):
        # utf-8-sig: ein BOM soll nicht als fehlender Kopf erscheinen.
        assert verstoesse(datei.name, datei.read_text(encoding="utf-8-sig")) == []


@pytest.mark.unit
class TestVerstoesse:
    """Absichtliche Verstoesse: jede Regel muss genau ihren Fehler melden."""

    def test_verstoesse_gute_migration_keine(self):
        assert verstoesse(DATEI, GUTE_MIGRATION) == []

    def test_verstoesse_vacuum_nach_commit_erlaubt(self):
        inhalt = GUTE_MIGRATION + "\n-- Platz zurueckgeben\nVACUUM FULL beispiel;\n"
        assert verstoesse(DATEI, inhalt) == []

    @pytest.mark.parametrize(
        "anweisung",
        [
            "CREATE INDEX CONCURRENTLY ix_neu ON beispiel (neu);",
            "CREATE UNIQUE INDEX CONCURRENTLY ix_neu ON beispiel (neu);",
            "DROP INDEX CONCURRENTLY IF EXISTS ix_alt;",
            "REINDEX INDEX CONCURRENTLY ix_neu;",
        ],
    )
    def test_verstoesse_concurrently_nach_commit_erlaubt(self, anweisung: str):
        assert verstoesse(DATEI, GUTE_MIGRATION + anweisung + "\n") == []

    def test_verstoesse_kommentar_am_zeilenende_erlaubt(self):
        inhalt = GUTE_MIGRATION.replace("BEGIN;", "BEGIN; -- alles oder nichts")
        inhalt = inhalt.replace("COMMIT;", "COMMIT; -- fertig")
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
        assert _regeln(GUTE_MIGRATION, dateiname) == {REGEL_DATEINAME}

    def test_verstoesse_ohne_kopf(self):
        inhalt = GUTE_MIGRATION.split("\n\n", 1)[1]
        assert _regeln(inhalt) == {REGEL_KOPF}

    def test_verstoesse_ohne_verweis(self):
        inhalt = GUTE_MIGRATION.replace(VERWEIS, "-- Fertig.")
        assert _regeln(inhalt) == {REGEL_VERWEIS}

    def test_verstoesse_verweis_nicht_letzte_kopfzeile(self):
        inhalt = GUTE_MIGRATION.replace(VERWEIS, VERWEIS + "\n-- Noch ein Satz.")
        assert _regeln(inhalt) == {REGEL_VERWEIS}

    def test_verstoesse_kopf_durch_leerzeile_geteilt(self):
        inhalt = GUTE_MIGRATION.replace(VERWEIS, "\n" + VERWEIS)
        meldungen = [m for r, m in verstoesse(DATEI, inhalt) if r == REGEL_VERWEIS]
        assert len(meldungen) == 1 and "ersten Leerzeile" in meldungen[0]

    @pytest.mark.parametrize(
        "befehl",
        [
            "--   docker exec -i gutgesagt-app-postgres psql -U app_user -d app",
            "--   psql -v ON_ERROR_STOP=1 -f 2026-10-26-beispiel.sql",
            "--   docker compose exec app-postgres sh -c 'cat > x'",
            "--   podman exec -i app-postgres sh -c 'cat > x'",
            "-- \\i 2026-10-26-beispiel.sql",
        ],
    )
    def test_verstoesse_befehl_im_kopf(self, befehl: str):
        inhalt = GUTE_MIGRATION.replace(VERWEIS, befehl + "\n" + VERWEIS)
        assert _regeln(inhalt) == {REGEL_BEFEHL}

    def test_verstoesse_befehl_in_spaeterem_kommentar(self):
        inhalt = GUTE_MIGRATION.replace(
            "BEGIN;", "-- Anwenden mit: docker exec -i pg psql < x.sql\nBEGIN;"
        )
        assert _regeln(inhalt) == {REGEL_BEFEHL}

    def test_verstoesse_befehl_im_kommentar_am_zeilenende(self):
        inhalt = GUTE_MIGRATION.replace("COMMIT;", "COMMIT; -- danach: psql -f x.sql")
        assert _regeln(inhalt) == {REGEL_BEFEHL}

    def test_verstoesse_ohne_begin(self):
        inhalt = GUTE_MIGRATION.replace("BEGIN;\n", "")
        assert _regeln(inhalt) == {REGEL_BEGIN}

    def test_verstoesse_ohne_commit(self):
        inhalt = GUTE_MIGRATION.replace("COMMIT;\n", "")
        assert _regeln(inhalt) == {REGEL_COMMIT}

    def test_verstoesse_aenderung_nach_commit(self):
        inhalt = GUTE_MIGRATION + "DROP TABLE alt;\n"
        assert _regeln(inhalt) == {REGEL_NACH_COMMIT}

    def test_verstoesse_index_ohne_concurrently_nach_commit(self):
        inhalt = GUTE_MIGRATION + "CREATE INDEX ix_neu ON beispiel (neu);\n"
        assert _regeln(inhalt) == {REGEL_NACH_COMMIT}
