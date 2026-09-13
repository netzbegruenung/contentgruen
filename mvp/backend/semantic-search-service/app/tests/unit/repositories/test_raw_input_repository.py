"""
Unit-Tests fuer das RawInputRepository.

Die Datenbanksitzung ist gemockt; gepruefte Sache ist, *was* das Repository in
die Zeile schreibt und in welcher Reihenfolge es liest - nicht, ob PostgreSQL
funktioniert.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from domain.models.raw_input import (
    AktionNichtErlaubt,
    EinwurfNichtGefunden,
    RawInputSource,
    RawInputStatus,
    UebergangNichtErlaubt,
)
from repositories.raw_input_repository import RawInputRepository


def _sql(statement) -> str:
    """Ein Statement so kompilieren, wie PostgreSQL es bekaeme."""
    return " ".join(str(statement.compile(dialect=postgresql.dialect())).split())


def _zeile(**overrides):
    """Eine gelesene raw_inputs-Zeile nachbilden."""
    zeile = MagicMock()
    zeile.id = overrides.get("id", uuid.uuid4())
    zeile.content = overrides.get("content", "ein Satz")
    zeile.url = overrides.get("url", None)
    zeile.image_url = overrides.get("image_url", None)
    zeile.submitted_by = overrides.get("submitted_by", "testuser")
    zeile.source_channel = overrides.get("source_channel", RawInputSource.WEB.value)
    zeile.status = overrides.get("status", RawInputStatus.OPEN.value)
    zeile.created_at = overrides.get(
        "created_at", datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
    )
    return zeile


@pytest.fixture
def session():
    """Eine gemockte SQLAlchemy-Session als Context-Manager."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session


@pytest.fixture
def repository(session):
    datenbank = MagicMock()
    datenbank.get_session.return_value = session
    with patch(
        "repositories.raw_input_repository.get_app_database", return_value=datenbank
    ):
        return RawInputRepository()


@pytest.mark.unit
class TestCreate:
    def test_create_legt_einwurf_mit_status_open_an(self, repository, session):
        """Der Eingang setzt genau einen Zustand: offen."""
        repository.create(content="ein Satz", submitted_by="testuser")

        angelegt = session.add.call_args[0][0]
        assert angelegt.status == RawInputStatus.OPEN.value
        assert angelegt.source_channel == RawInputSource.WEB.value
        assert angelegt.content == "ein Satz"
        assert angelegt.submitted_by == "testuser"
        session.commit.assert_called_once()

    def test_create_ohne_person_speichert_null(self, repository, session):
        """submitted_by ist nullable - der Share-Eingang kommt ohne Sitzung."""
        repository.create(url="https://example.org/post", submitted_by=None)

        angelegt = session.add.call_args[0][0]
        assert angelegt.submitted_by is None
        assert angelegt.url == "https://example.org/post"

    def test_create_gibt_dict_statt_orm_objekt_zurueck(self, repository, session):
        """Nach dem Schliessen der Session waere ein ORM-Objekt nicht mehr lesbar."""
        session.refresh.side_effect = lambda obj: None
        with patch.object(
            RawInputRepository, "_to_dict", return_value={"id": "abc"}
        ) as to_dict:
            ergebnis = repository.create(content="x")

        assert ergebnis == {"id": "abc"}
        to_dict.assert_called_once()


@pytest.mark.unit
class TestGetAll:
    def _query_kette(self, session, zeilen):
        query = MagicMock()
        session.query.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query
        query.offset.return_value = query
        query.all.return_value = zeilen
        query.count.return_value = len(zeilen)
        return query

    def test_get_all_liefert_dicts(self, repository, session):
        self._query_kette(session, [_zeile(content="a"), _zeile(content="b")])

        ergebnis = repository.get_all(limit=10, offset=0)

        assert [e["content"] for e in ergebnis] == ["a", "b"]
        assert ergebnis[0]["status"] == RawInputStatus.OPEN.value

    def test_get_all_paginiert(self, repository, session):
        query = self._query_kette(session, [])

        repository.get_all(limit=5, offset=10)

        query.limit.assert_called_once_with(5)
        query.offset.assert_called_once_with(10)

    def test_get_all_filtert_nicht_ohne_status(self, repository, session):
        """Ohne Statusangabe kommt der ganze Fangkorb - auch Verarbeitetes."""
        query = self._query_kette(session, [])

        repository.get_all()

        query.filter.assert_not_called()

    def test_get_all_filtert_mit_status(self, repository, session):
        query = self._query_kette(session, [])

        repository.get_all(status=RawInputStatus.OPEN.value)

        query.filter.assert_called_once()

    def test_count_zaehlt_alles(self, repository, session):
        query = self._query_kette(session, [_zeile(), _zeile(), _zeile()])

        assert repository.count() == 3
        query.filter.assert_not_called()

    def test_get_all_sortiert_eigene_zuerst(self, repository, session):
        """Erst die eigenen, dann nach Neuheit - in der Datenbank, wegen Paginierung."""
        query = self._query_kette(session, [])

        repository.get_all(current_user="alice")

        (reihenfolge,) = [aufruf.args for aufruf in query.order_by.call_args_list]
        assert len(reihenfolge) == 2
        erste = _sql(reihenfolge[0])
        assert "CASE WHEN (raw_inputs.submitted_by =" in erste
        assert "created_at DESC" in _sql(reihenfolge[1])

    def test_get_all_ohne_person_sortiert_nur_nach_neuheit(self, repository, session):
        query = self._query_kette(session, [])

        repository.get_all()

        (reihenfolge,) = [aufruf.args for aufruf in query.order_by.call_args_list]
        assert len(reihenfolge) == 1
        assert "created_at DESC" in _sql(reihenfolge[0])

    def test_get_all_haengt_bearbeitungsstand_an(self, repository, session):
        zeile = _zeile()
        self._query_kette(session, [zeile])
        with patch.object(
            RawInputRepository, "_mit_bearbeitungsstand", return_value=[{"id": "x"}]
        ) as stand:
            ergebnis = repository.get_all(current_user="alice")

        assert ergebnis == [{"id": "x"}]
        assert stand.call_args.args[1:] == ([zeile], "alice")


@pytest.mark.unit
class TestBearbeitungsstand:
    def test_to_dict_uebersetzt_verknuepfung_in_processed_felder(self):
        inhalt_id = uuid.uuid4()
        am = datetime(2026, 9, 13, 18, 0, tzinfo=timezone.utc)
        verknuepfung = SimpleNamespace(
            content_id=inhalt_id, created_by="bob", created_at=am
        )

        eintrag = RawInputRepository._to_dict(_zeile(), "Mein Satz", verknuepfung)

        assert eintrag["own_draft"] == "Mein Satz"
        assert eintrag["processed_content_id"] == str(inhalt_id)
        assert eintrag["processed_by"] == "bob"
        assert eintrag["processed_at"] == am

    def test_to_dict_ohne_verknuepfung_und_entwurf(self):
        eintrag = RawInputRepository._to_dict(_zeile())

        assert eintrag["own_draft"] is None
        assert eintrag["processed_content_id"] is None
        assert eintrag["processed_by"] is None
        assert eintrag["processed_at"] is None

    def test_erste_verknuepfung_ist_die_aelteste(self, session):
        """Bei mehreren Beitraegen aus einem Einwurf zaehlt, wer zuerst verarbeitet hat."""
        einwurf = uuid.uuid4()
        zuerst = SimpleNamespace(raw_input_id=einwurf, created_by="alice")
        danach = SimpleNamespace(raw_input_id=einwurf, created_by="bob")
        query = MagicMock()
        session.query.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = [zuerst, danach]

        erste = RawInputRepository._erste_verknuepfungen(session, [einwurf])

        assert erste == {einwurf: zuerst}
        query.order_by.assert_called_once()

    def test_ohne_person_gibt_es_keine_entwuerfe(self, session):
        """Fremde Entwurfssaetze werden nie ausgeliefert."""
        assert RawInputRepository._eigene_entwuerfe(session, [uuid.uuid4()], None) == {}
        session.query.assert_not_called()

    def test_entwuerfe_werden_auf_die_person_gefiltert(self, session):
        einwurf = uuid.uuid4()
        query = MagicMock()
        session.query.return_value = query
        query.filter.return_value = query
        query.all.return_value = [
            SimpleNamespace(raw_input_id=einwurf, sentence="Satz")
        ]

        entwuerfe = RawInputRepository._eigene_entwuerfe(session, [einwurf], "alice")

        assert entwuerfe == {einwurf: "Satz"}
        bedingungen = " ".join(_sql(b) for b in query.filter.call_args.args)
        assert "raw_input_drafts.user_id =" in bedingungen
        assert "raw_input_drafts.raw_input_id IN" in bedingungen


@pytest.mark.unit
class TestGetById:
    def _query_kette(self, session, zeile):
        query = MagicMock()
        session.query.return_value = query
        query.filter.return_value = query
        query.one_or_none.return_value = zeile
        return query

    def test_unbekannte_id_liefert_none(self, repository, session):
        self._query_kette(session, None)

        assert repository.get_by_id(uuid.uuid4(), "alice") is None

    def test_gefundener_einwurf_bekommt_bearbeitungsstand(self, repository, session):
        zeile = _zeile()
        self._query_kette(session, zeile)
        with patch.object(
            RawInputRepository, "_mit_bearbeitungsstand", return_value=[{"id": "x"}]
        ) as stand:
            ergebnis = repository.get_by_id(zeile.id, "alice")

        assert ergebnis == {"id": "x"}
        assert stand.call_args.args[1:] == ([zeile], "alice")


@pytest.mark.unit
class TestEntwurfSpeichern:
    def _query_kette(self, session, vorhanden):
        query = MagicMock()
        session.query.return_value = query
        query.filter.return_value = query
        query.one_or_none.return_value = vorhanden
        return query

    def test_upsert_sql_zielt_auf_den_eindeutigen_index(self):
        """Nur gegen echtes PostgreSQL pruefbar ist, ob der Index dazu passt."""
        sql = _sql(RawInputRepository._entwurf_upsert(uuid.uuid4(), "alice", "Satz"))

        assert sql.startswith("INSERT INTO raw_input_drafts")
        assert "ON CONFLICT (raw_input_id, user_id) DO UPDATE SET" in sql
        assert "sentence = excluded.sentence" in sql
        assert "updated_at = now()" in sql
        assert sql.endswith("RETURNING raw_input_drafts.updated_at")

    def test_satz_wird_per_upsert_gespeichert(self, repository, session):
        self._query_kette(session, (uuid.uuid4(),))
        am = datetime(2026, 9, 13, 18, 0, tzinfo=timezone.utc)
        session.execute.return_value.scalar_one.return_value = am
        einwurf = uuid.uuid4()

        ergebnis = repository.save_draft(einwurf, "alice", "Satz")

        assert ergebnis == {
            "raw_input_id": str(einwurf),
            "sentence": "Satz",
            "updated_at": am,
        }
        (statement,) = session.execute.call_args.args
        assert "ON CONFLICT" in _sql(statement)
        session.commit.assert_called_once()

    def test_leerer_satz_loescht_statt_zu_speichern(self, repository, session):
        query = self._query_kette(session, (uuid.uuid4(),))

        ergebnis = repository.save_draft(uuid.uuid4(), "alice", None)

        assert ergebnis["sentence"] is None
        query.delete.assert_called_once_with(synchronize_session=False)
        session.execute.assert_not_called()

    def test_unbekannter_einwurf_wirft(self, repository, session):
        self._query_kette(session, None)

        with pytest.raises(EinwurfNichtGefunden):
            repository.save_draft(uuid.uuid4(), "alice", "Satz")

        session.execute.assert_not_called()
        session.commit.assert_not_called()


@pytest.mark.unit
class TestStatusSetzen:
    def _gesperrte_zeile(self, session, zeile):
        query = MagicMock()
        session.query.return_value = query
        query.filter.return_value = query
        query.with_for_update.return_value = query
        query.one_or_none.return_value = zeile
        return query

    @pytest.fixture(autouse=True)
    def _ohne_bearbeitungsstand(self):
        with patch.object(
            RawInputRepository, "_mit_bearbeitungsstand", return_value=[{"id": "x"}]
        ):
            yield

    def test_verknuepfung_sql_ist_idempotent(self):
        sql = _sql(
            RawInputRepository._verknuepfung_einfuegen(
                uuid.uuid4(), uuid.uuid4(), "alice"
            )
        )

        assert sql.startswith("INSERT INTO raw_input_content_links")
        assert "created_by" in sql
        # SQLAlchemy haengt fuer den server-generierten Schluessel RETURNING an;
        # bei einem Konflikt kommt dann schlicht keine Zeile zurueck.
        assert "ON CONFLICT (raw_input_id, content_id) DO NOTHING" in sql

    def test_einwerfer_verwirft_offenen_einwurf(self, repository, session):
        zeile = _zeile(submitted_by="alice", status=RawInputStatus.OPEN.value)
        query = self._gesperrte_zeile(session, zeile)

        repository.set_status(zeile.id, RawInputStatus.DISCARDED, "alice")

        assert zeile.status == RawInputStatus.DISCARDED.value
        query.with_for_update.assert_called_once()
        session.execute.assert_not_called()
        session.commit.assert_called_once()

    def test_andere_duerfen_nicht_verwerfen(self, repository, session):
        zeile = _zeile(submitted_by="alice", status=RawInputStatus.OPEN.value)
        self._gesperrte_zeile(session, zeile)

        with pytest.raises(AktionNichtErlaubt):
            repository.set_status(zeile.id, RawInputStatus.DISCARDED, "bob")

        assert zeile.status == RawInputStatus.OPEN.value
        session.commit.assert_not_called()

    def test_einwurf_ohne_einwerfer_kann_niemand_verwerfen(self, repository, session):
        zeile = _zeile(submitted_by=None, status=RawInputStatus.OPEN.value)
        self._gesperrte_zeile(session, zeile)

        with pytest.raises(AktionNichtErlaubt):
            repository.set_status(zeile.id, RawInputStatus.DISCARDED, "bob")

    def test_verarbeitetes_wird_nicht_verworfen(self, repository, session):
        zeile = _zeile(submitted_by="alice", status=RawInputStatus.PROCESSED.value)
        self._gesperrte_zeile(session, zeile)

        with pytest.raises(UebergangNichtErlaubt):
            repository.set_status(zeile.id, RawInputStatus.DISCARDED, "alice")

        session.commit.assert_not_called()

    def test_andere_verarbeiten_verworfenes_mit_verknuepfung(self, repository, session):
        """Verworfen heisst nicht gesperrt: andere duerfen trotzdem destillieren."""
        zeile = _zeile(submitted_by="alice", status=RawInputStatus.DISCARDED.value)
        self._gesperrte_zeile(session, zeile)
        inhalt_id = uuid.uuid4()

        repository.set_status(zeile.id, RawInputStatus.PROCESSED, "bob", inhalt_id)

        assert zeile.status == RawInputStatus.PROCESSED.value
        (statement,) = session.execute.call_args.args
        sql = _sql(statement)
        assert "INSERT INTO raw_input_content_links" in sql
        assert statement.compile().params["created_by"] == "bob"
        assert statement.compile().params["content_id"] == inhalt_id
        session.commit.assert_called_once()

    def test_verarbeitet_ohne_beitrag_wirft_vor_der_datenbank(
        self, repository, session
    ):
        with pytest.raises(ValueError):
            repository.set_status(uuid.uuid4(), RawInputStatus.PROCESSED, "bob")

        session.query.assert_not_called()

    def test_unbekannter_einwurf_wirft(self, repository, session):
        self._gesperrte_zeile(session, None)

        with pytest.raises(EinwurfNichtGefunden):
            repository.set_status(uuid.uuid4(), RawInputStatus.DISCARDED, "alice")
