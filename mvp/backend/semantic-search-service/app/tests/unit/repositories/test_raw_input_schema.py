"""
Das Schema des Fangkorbs festnageln.

``raw_input_content_links`` ist die n:m-Verknuepfung zwischen Einwurf und
Beitrag. Eine schmale Tabelle ist die erste, die jemand beim Aufraeumen
"vereinfacht" - etwa zu einem Feld ``resulting_content_id`` auf ``raw_inputs``.
Das waere billiger und genau die Blockade, die docs/ROHINPUT.md (Abschnitt 6)
benennt: ein Einwurf kann mehrere Beitraege hervorbringen und ein Beitrag aus
mehreren Einwuerfen entstehen.

Neue Spalten an bestehenden Tabellen legt ``create_all`` nicht an; wer hier eine
Spalte ergaenzt, braucht ein Migrationsskript in mvp/backend/postgres-app/migrations.
"""

import pytest

from infrastructure.database.models import RawInput, RawInputContentLink, RawInputDraft


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
            "destilled_by",
        }

    def test_submitted_by_ist_nullable(self):
        """Ein NOT NULL hier verbaut den spaeteren Share-Eingang ohne Sitzung."""
        assert RawInput.__table__.columns["submitted_by"].nullable is True

    def test_destilled_by_ist_nullable(self):
        """Offene Einwuerfe hat noch niemand destilliert."""
        assert RawInput.__table__.columns["destilled_by"].nullable is True

    def test_status_ist_ein_eigenes_feld(self):
        """Der Bearbeitungsstand wird geschrieben, nicht bei jedem Lesen abgeleitet."""
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
            "draft_id",
            "content_type",
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

    def test_geleerter_satz_loescht_die_verknuepfung_nicht(self):
        """
        Ein leerer Satz loescht seine Zeile in raw_input_drafts. Die Verknuepfung
        mit dem Beitrag muss das ueberleben - nur draft_id wird leer.
        """
        spalte = RawInputContentLink.__table__.columns["draft_id"]
        (fremdschluessel,) = list(spalte.foreign_keys)
        assert spalte.nullable is True
        assert fremdschluessel.column.table.name == "raw_input_drafts"
        assert fremdschluessel.ondelete == "SET NULL"

    def test_beitragstyp_ist_optional(self):
        """Verknuepfungen aus der Zeit vor Fangkorb v2 kennen keinen Typ."""
        assert RawInputContentLink.__table__.columns["content_type"].nullable is True


@pytest.mark.unit
class TestEntwurfstabelle:
    """
    Der Entwurfssatz gehoert zu (Einwurf, Person). Der Upsert haengt am eindeutigen
    Index; ohne ihn wuerde ON CONFLICT in PostgreSQL mit einem Fehler abbrechen.
    """

    def test_tabelle_existiert_mit_ihren_feldern(self):
        assert set(RawInputDraft.__table__.columns.keys()) == {
            "id",
            "raw_input_id",
            "user_id",
            "sentence",
            "updated_at",
        }

    def test_genau_ein_entwurf_je_person_und_einwurf(self):
        eindeutige_indizes = {
            tuple(spalte.name for spalte in index.columns)
            for index in RawInputDraft.__table__.indexes
            if index.unique
        }
        assert eindeutige_indizes == {("raw_input_id", "user_id")}

    def test_person_und_satz_sind_pflicht(self):
        """Ein leerer Satz wird geloescht, nicht als "" oder NULL abgelegt."""
        assert RawInputDraft.__table__.columns["user_id"].nullable is False
        assert RawInputDraft.__table__.columns["sentence"].nullable is False

    def test_verweis_auf_den_einwurf_kaskadiert(self):
        (fremdschluessel,) = list(
            RawInputDraft.__table__.columns["raw_input_id"].foreign_keys
        )
        assert fremdschluessel.column.table.name == "raw_inputs"
        assert fremdschluessel.ondelete == "CASCADE"
