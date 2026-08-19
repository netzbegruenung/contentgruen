"""
Das Schema des Fangkorbs festnageln - besonders die Teile, die heute nichts tut.

``raw_input_content_links`` ist leer und wird von keinem Codepfad beschrieben:
die Verarbeitung ist nicht gebaut. Genau deshalb steht hier ein Test. Eine
ungenutzte Tabelle ist die erste, die jemand beim Aufraeumen "vereinfacht" - etwa
zu einem Feld ``resulting_content_id`` auf ``raw_inputs``. Das waere billiger und
genau die Blockade, die docs/ROHINPUT.md (Abschnitt 6) benennt: ein Einwurf kann
mehrere Beitraege hervorbringen und ein Beitrag aus mehreren Einwuerfen entstehen.
"""

import pytest

from infrastructure.database.models import RawInput, RawInputContentLink


@pytest.mark.unit
class TestRawInputSchema:
    def test_felder_stehen_fest(self):
        assert set(RawInput.__table__.columns.keys()) == {
            "id",
            "content",
            "url",
            "image_url",
            "submitted_by",
            "source_channel",
            "status",
            "created_at",
        }

    def test_submitted_by_ist_nullable(self):
        """Ein NOT NULL hier verbaut den spaeteren Share-Eingang ohne Sitzung."""
        assert RawInput.__table__.columns["submitted_by"].nullable is True

    def test_status_ist_ein_eigenes_feld(self):
        """Der Andockpunkt der spaeteren Queue - kein abgeleiteter Zustand."""
        status = RawInput.__table__.columns["status"]
        assert status.nullable is False
        assert "open" in str(status.server_default.arg)

    def test_die_drei_inhaltsfelder_sind_alle_optional(self):
        """Pflicht ist nur, dass eines davon dasteht - das prueft der Constraint."""
        for spalte in ("content", "url", "image_url"):
            assert RawInput.__table__.columns[spalte].nullable is True

    def test_leerer_einwurf_ist_per_constraint_ausgeschlossen(self):
        bedingungen = [
            str(c.sqltext)
            for c in RawInput.__table__.constraints
            if c.name == "check_raw_input_not_empty"
        ]
        assert len(bedingungen) == 1
        assert "content IS NOT NULL" in bedingungen[0]
        assert "url IS NOT NULL" in bedingungen[0]
        assert "image_url IS NOT NULL" in bedingungen[0]


@pytest.mark.unit
class TestVerknuepfungstabelle:
    def test_tabelle_existiert_mit_ihren_feldern(self):
        assert set(RawInputContentLink.__table__.columns.keys()) == {
            "id",
            "raw_input_id",
            "content_id",
            "created_by",
            "created_at",
        }

    def test_verknuepfung_ist_n_zu_m(self):
        """
        Kein Unique auf raw_input_id allein und keines auf content_id allein -
        genau eine Paarung darf sich nicht wiederholen.
        """
        eindeutige_indizes = {
            tuple(spalte.name for spalte in index.columns)
            for index in RawInputContentLink.__table__.indexes
            if index.unique
        }
        assert eindeutige_indizes == {("raw_input_id", "content_id")}

    def test_kein_fremdschluessel_auf_inhalte(self):
        """content_id zeigt auf einen Qdrant-Punkt, nicht auf eine Tabelle."""
        assert RawInputContentLink.__table__.columns["content_id"].foreign_keys == set()

    def test_verweis_auf_den_einwurf_kaskadiert(self):
        (fremdschluessel,) = list(
            RawInputContentLink.__table__.columns["raw_input_id"].foreign_keys
        )
        assert fremdschluessel.column.table.name == "raw_inputs"
        assert fremdschluessel.ondelete == "CASCADE"

    def test_wer_verarbeitet_hat_wird_festgehalten(self):
        """Die Rolle, die last_modified_by am Beitrag nicht bewahrt."""
        assert "created_by" in RawInputContentLink.__table__.columns
