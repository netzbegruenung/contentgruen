"""
Was das Einspielen der Migrationen ohne Datenbank pruefen laesst
(infrastructure/database/migrationen.py); das Einspielen selbst pruefen die
Integrationstests in tests/integration/test_migrationen.py.
"""

from pathlib import Path

import pytest

from infrastructure.database import migrationen

REPO_WURZEL = next((p for p in Path(__file__).parents if (p / "mvp").is_dir()), None)
MIGRATIONEN = REPO_WURZEL / "mvp" / "backend" / "postgres-app" / "migrations"


@pytest.mark.unit
class TestMigrationenZerlegen:
    def test_zerlegen_trennt_am_commit(self):
        skript = (
            "-- Kopf; mit Semikolon\n\nBEGIN; -- los\n"
            "ALTER TABLE a ADD COLUMN IF NOT EXISTS b TEXT;\n"
            "COMMIT;\n\n-- Platz zurueckgeben\nVACUUM FULL a;\n"
        )

        assert migrationen.zerlegen(skript) == (
            ["BEGIN", "ALTER TABLE a ADD COLUMN IF NOT EXISTS b TEXT"],
            ["VACUUM FULL a"],
        )

    def test_zerlegen_ohne_commit_abgewiesen(self):
        with pytest.raises(ValueError, match="COMMIT"):
            migrationen.zerlegen("BEGIN;\nSELECT 1;\n")

    def test_zerlegen_dollar_block_abgewiesen(self):
        with pytest.raises(ValueError, match=r"\$\$"):
            migrationen.zerlegen("BEGIN;\nDO $$ BEGIN END $$;\nCOMMIT;\n")

    @pytest.mark.parametrize(
        "datei", migrationen.dateien(MIGRATIONEN), ids=lambda p: p.name
    )
    def test_zerlegen_jede_migration(self, datei: Path):
        transaktion, _ = migrationen.zerlegen(datei.read_text(encoding="utf-8"))

        assert transaktion[0].upper() == "BEGIN"

    def test_nicht_wiederholbare_gibt_es_als_datei(self):
        """Eine Umbenennung liesse das Skript sonst ungeschuetzt erneut laufen."""
        namen = {p.name for p in migrationen.dateien(MIGRATIONEN)}

        assert migrationen.NICHT_WIEDERHOLBAR.keys() <= namen

    def test_dateien_ordnet_ohne_endung(self):
        namen = [p.name for p in migrationen.dateien(MIGRATIONEN)]

        assert namen.index("2026-10-26-suchen-ohne-treffer.sql") < namen.index(
            "2026-10-26-suchen-ohne-treffer-personen.sql"
        )
