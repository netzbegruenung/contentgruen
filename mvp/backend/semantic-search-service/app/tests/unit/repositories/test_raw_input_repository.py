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

AM = datetime(2026, 9, 13, 18, 0, tzinfo=timezone.utc)


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
    zeile.destilled_by = overrides.get("destilled_by", None)
    return zeile


def _entwurf(user_id, sentence, einwurf=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        raw_input_id=einwurf or uuid.uuid4(),
        user_id=user_id,
        sentence=sentence,
        updated_at=AM,
    )


def _verknuepfung(created_by, einwurf=None, draft_id=None, content_type="commentary"):
    return SimpleNamespace(
        raw_input_id=einwurf or uuid.uuid4(),
        content_id=uuid.uuid4(),
        content_type=content_type,
        draft_id=draft_id,
        created_by=created_by,
        created_at=AM,
    )


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


def _gesperrte_zeile(session, zeile):
    """Die Abfragekette fuer eine per FOR UPDATE gelesene Einwurf-Zeile."""
    query = MagicMock()
    session.query.return_value = query
    query.filter.return_value = query
    query.with_for_update.return_value = query
    query.one_or_none.return_value = zeile
    return query


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

        with patch.object(
            RawInputRepository,
            "_mit_bearbeitungsstand",
            side_effect=lambda s, rows, user: [
                RawInputRepository._to_dict(r) for r in rows
            ],
        ):
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
    def test_to_dict_uebersetzt_erste_verknuepfung_in_processed_felder(self):
        satz_id = uuid.uuid4()
        zuerst = _verknuepfung("bob", draft_id=satz_id)
        danach = _verknuepfung("carol", content_type="generic_text")

        eintrag = RawInputRepository._to_dict(_zeile(), [], [zuerst, danach])

        assert eintrag["processed_content_id"] == str(zuerst.content_id)
        assert eintrag["processed_by"] == "bob"
        assert eintrag["processed_at"] == AM
        assert eintrag["links"] == [
            {
                "content_id": str(zuerst.content_id),
                "content_type": "commentary",
                "draft_id": str(satz_id),
                "processed_by": "bob",
                "processed_at": AM,
            },
            {
                "content_id": str(danach.content_id),
                "content_type": "generic_text",
                "draft_id": None,
                "processed_by": "carol",
                "processed_at": AM,
            },
        ]

    def test_to_dict_ohne_verknuepfung_und_entwurf(self):
        eintrag = RawInputRepository._to_dict(_zeile())

        assert eintrag["own_draft"] is None
        assert eintrag["destilled_by"] is None
        assert eintrag["processed_content_id"] is None
        assert eintrag["processed_by"] is None
        assert eintrag["processed_at"] is None
        assert eintrag["drafts"] == []
        assert eintrag["links"] == []

    def test_to_dict_liefert_alle_saetze_und_den_eigenen(self):
        """Alle Saetze sind fuer alle sichtbar; own_draft ist der eigene daraus."""
        von_bob = _entwurf("bob", "Satz von Bob")
        von_alice = _entwurf("alice", "Satz von Alice")

        eintrag = RawInputRepository._to_dict(
            _zeile(destilled_by="bob"), [von_bob, von_alice], [], "alice"
        )

        assert eintrag["destilled_by"] == "bob"
        assert eintrag["own_draft"] == "Satz von Alice"
        assert eintrag["drafts"] == [
            {
                "id": str(von_bob.id),
                "user_id": "bob",
                "sentence": "Satz von Bob",
                "updated_at": AM,
            },
            {
                "id": str(von_alice.id),
                "user_id": "alice",
                "sentence": "Satz von Alice",
                "updated_at": AM,
            },
        ]

    def test_ohne_person_kein_eigener_satz(self):
        eintrag = RawInputRepository._to_dict(
            _zeile(), [_entwurf("bob", "Satz")], [], None
        )

        assert eintrag["own_draft"] is None
        assert len(eintrag["drafts"]) == 1

    def test_verknuepfungen_werden_je_einwurf_gruppiert(self, session):
        einwurf = uuid.uuid4()
        zuerst = _verknuepfung("alice", einwurf=einwurf)
        danach = _verknuepfung("bob", einwurf=einwurf)
        query = MagicMock()
        session.query.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = [zuerst, danach]

        gruppiert = RawInputRepository._verknuepfungen(session, [einwurf])

        assert gruppiert == {einwurf: [zuerst, danach]}
        assert "created_at" in _sql(query.order_by.call_args.args[0])

    def test_saetze_aller_personen_werden_gelesen(self, session):
        einwurf = uuid.uuid4()
        von_bob = _entwurf("bob", "Satz", einwurf=einwurf)
        query = MagicMock()
        session.query.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = [von_bob]

        gruppiert = RawInputRepository._entwuerfe(session, [einwurf])

        assert gruppiert == {einwurf: [von_bob]}
        bedingungen = " ".join(_sql(b) for b in query.filter.call_args.args)
        assert "raw_input_drafts.raw_input_id IN" in bedingungen
        assert "user_id" not in bedingungen
        assert "updated_at" in _sql(query.order_by.call_args.args[0])


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
    @pytest.fixture(autouse=True)
    def _zeitpunkt(self, session):
        session.execute.return_value.scalar_one.return_value = AM

    def test_upsert_sql_zielt_auf_den_eindeutigen_index(self):
        """Nur gegen echtes PostgreSQL pruefbar ist, ob der Index dazu passt."""
        sql = _sql(RawInputRepository._entwurf_upsert(uuid.uuid4(), "alice", "Satz"))

        assert sql.startswith("INSERT INTO raw_input_drafts")
        assert "ON CONFLICT (raw_input_id, user_id) DO UPDATE SET" in sql
        assert "sentence = excluded.sentence" in sql
        assert "updated_at = now()" in sql
        assert sql.endswith("RETURNING raw_input_drafts.updated_at")

    def test_satz_wird_per_upsert_gespeichert(self, repository, session):
        zeile = _zeile()
        _gesperrte_zeile(session, zeile)

        ergebnis = repository.save_draft(zeile.id, "alice", "Satz")

        assert ergebnis == {
            "raw_input_id": str(zeile.id),
            "sentence": "Satz",
            "updated_at": AM,
        }
        (statement,) = session.execute.call_args.args
        assert "ON CONFLICT" in _sql(statement)
        session.commit.assert_called_once()

    def test_erster_satz_macht_offenen_einwurf_destilliert(self, repository, session):
        zeile = _zeile(status=RawInputStatus.OPEN.value)
        query = _gesperrte_zeile(session, zeile)

        repository.save_draft(zeile.id, "alice", "Satz")

        assert zeile.status == RawInputStatus.IN_PROGRESS.value
        assert zeile.destilled_by == "alice"
        query.with_for_update.assert_called_once()

    def test_weiterer_satz_aendert_destilled_by_nicht(self, repository, session):
        """destilled_by ist, wer als Erste/r einen Satz gespeichert hat."""
        zeile = _zeile(status=RawInputStatus.IN_PROGRESS.value, destilled_by="bob")
        _gesperrte_zeile(session, zeile)

        repository.save_draft(zeile.id, "alice", "Mein Satz")

        assert zeile.status == RawInputStatus.IN_PROGRESS.value
        assert zeile.destilled_by == "bob"

    @pytest.mark.parametrize(
        "stand", [RawInputStatus.DISCARDED, RawInputStatus.PROCESSED]
    )
    def test_satz_aendert_verworfenes_und_verarbeitetes_nicht(
        self, repository, session, stand
    ):
        zeile = _zeile(status=stand.value)
        _gesperrte_zeile(session, zeile)

        repository.save_draft(zeile.id, "alice", "Satz")

        assert zeile.status == stand.value
        assert zeile.destilled_by == "alice"

    def test_leerer_satz_loescht_statt_zu_speichern(self, repository, session):
        zeile = _zeile(status=RawInputStatus.OPEN.value)
        query = _gesperrte_zeile(session, zeile)

        ergebnis = repository.save_draft(zeile.id, "alice", None)

        assert ergebnis["sentence"] is None
        query.delete.assert_called_once_with(synchronize_session=False)
        session.execute.assert_not_called()
        session.commit.assert_called_once()

    def test_letzter_satz_geloescht_macht_wieder_offen(self, repository, session):
        zeile = _zeile(status=RawInputStatus.IN_PROGRESS.value, destilled_by="alice")
        query = _gesperrte_zeile(session, zeile)
        query.first.return_value = None

        repository.save_draft(zeile.id, "alice", None)

        assert zeile.status == RawInputStatus.OPEN.value
        assert zeile.destilled_by is None

    def test_leerer_satz_laesst_stand_wenn_andere_saetze_bleiben(
        self, repository, session
    ):
        zeile = _zeile(status=RawInputStatus.IN_PROGRESS.value, destilled_by="alice")
        query = _gesperrte_zeile(session, zeile)
        query.first.return_value = (uuid.uuid4(),)

        repository.save_draft(zeile.id, "alice", None)

        assert zeile.status == RawInputStatus.IN_PROGRESS.value
        assert zeile.destilled_by == "alice"

    @pytest.mark.parametrize(
        "stand", [RawInputStatus.DISCARDED, RawInputStatus.PROCESSED]
    )
    def test_leerer_satz_setzt_verworfenes_und_verarbeitetes_nicht_zurueck(
        self, repository, session, stand
    ):
        zeile = _zeile(status=stand.value, destilled_by="alice")
        query = _gesperrte_zeile(session, zeile)
        query.first.return_value = None

        repository.save_draft(zeile.id, "alice", None)

        assert zeile.status == stand.value
        assert zeile.destilled_by == "alice"
        query.first.assert_not_called()

    def test_unbekannter_einwurf_wirft(self, repository, session):
        _gesperrte_zeile(session, None)

        with pytest.raises(EinwurfNichtGefunden):
            repository.save_draft(uuid.uuid4(), "alice", "Satz")

        session.execute.assert_not_called()
        session.commit.assert_not_called()


@pytest.mark.unit
class TestStatusSetzen:
    @pytest.fixture(autouse=True)
    def _ohne_bearbeitungsstand(self):
        with patch.object(
            RawInputRepository, "_mit_bearbeitungsstand", return_value=[{"id": "x"}]
        ):
            yield

    def test_verknuepfung_sql_ist_idempotent(self):
        sql = _sql(
            RawInputRepository._verknuepfung_einfuegen(
                uuid.uuid4(), uuid.uuid4(), "alice", uuid.uuid4(), "commentary"
            )
        )

        assert sql.startswith("INSERT INTO raw_input_content_links")
        assert "created_by" in sql
        assert "draft_id" in sql
        assert "content_type" in sql
        # SQLAlchemy haengt fuer den server-generierten Schluessel RETURNING an;
        # bei einem Konflikt kommt dann schlicht keine Zeile zurueck.
        assert "ON CONFLICT (raw_input_id, content_id) DO NOTHING" in sql

    @pytest.mark.parametrize("stand", [RawInputStatus.OPEN, RawInputStatus.IN_PROGRESS])
    def test_einwerfer_verwirft_offenen_oder_destillierten_einwurf(
        self, repository, session, stand
    ):
        zeile = _zeile(submitted_by="alice", status=stand.value)
        query = _gesperrte_zeile(session, zeile)

        repository.set_status(zeile.id, RawInputStatus.DISCARDED, "alice")

        assert zeile.status == RawInputStatus.DISCARDED.value
        query.with_for_update.assert_called_once()
        session.execute.assert_not_called()
        session.commit.assert_called_once()

    def test_andere_duerfen_nicht_verwerfen(self, repository, session):
        zeile = _zeile(submitted_by="alice", status=RawInputStatus.OPEN.value)
        _gesperrte_zeile(session, zeile)

        with pytest.raises(AktionNichtErlaubt):
            repository.set_status(zeile.id, RawInputStatus.DISCARDED, "bob")

        assert zeile.status == RawInputStatus.OPEN.value
        session.commit.assert_not_called()

    def test_einwurf_ohne_einwerfer_kann_niemand_verwerfen(self, repository, session):
        zeile = _zeile(submitted_by=None, status=RawInputStatus.OPEN.value)
        _gesperrte_zeile(session, zeile)

        with pytest.raises(AktionNichtErlaubt):
            repository.set_status(zeile.id, RawInputStatus.DISCARDED, "bob")

    def test_verarbeitetes_wird_nicht_verworfen(self, repository, session):
        zeile = _zeile(submitted_by="alice", status=RawInputStatus.PROCESSED.value)
        _gesperrte_zeile(session, zeile)

        with pytest.raises(UebergangNichtErlaubt):
            repository.set_status(zeile.id, RawInputStatus.DISCARDED, "alice")

        session.commit.assert_not_called()

    def test_andere_verarbeiten_verworfenes_mit_verknuepfung(self, repository, session):
        """Verworfen heisst nicht gesperrt: andere duerfen trotzdem destillieren."""
        zeile = _zeile(submitted_by="alice", status=RawInputStatus.DISCARDED.value)
        query = _gesperrte_zeile(session, zeile)
        query.scalar.return_value = None
        inhalt_id = uuid.uuid4()

        repository.set_status(zeile.id, RawInputStatus.PROCESSED, "bob", inhalt_id)

        assert zeile.status == RawInputStatus.PROCESSED.value
        (statement,) = session.execute.call_args.args
        assert "INSERT INTO raw_input_content_links" in _sql(statement)
        assert statement.compile().params["created_by"] == "bob"
        assert statement.compile().params["content_id"] == inhalt_id
        session.commit.assert_called_once()

    def test_verknuepfung_haelt_satz_und_beitragstyp_fest(self, repository, session):
        """draft_id ist der Satz der verarbeitenden Person - die Karte zeigt ihn."""
        zeile = _zeile(status=RawInputStatus.IN_PROGRESS.value)
        query = _gesperrte_zeile(session, zeile)
        satz_id = uuid.uuid4()
        query.scalar.return_value = satz_id

        repository.set_status(
            zeile.id, RawInputStatus.PROCESSED, "bob", uuid.uuid4(), "generic_text"
        )

        assert zeile.status == RawInputStatus.PROCESSED.value
        (statement,) = session.execute.call_args.args
        parameter = statement.compile().params
        assert parameter["draft_id"] == satz_id
        assert parameter["content_type"] == "generic_text"
        bedingungen = " ".join(_sql(b) for b in query.filter.call_args.args)
        assert "raw_input_drafts.user_id =" in bedingungen

    def test_verarbeitet_ohne_beitrag_wirft_vor_der_datenbank(
        self, repository, session
    ):
        with pytest.raises(ValueError):
            repository.set_status(uuid.uuid4(), RawInputStatus.PROCESSED, "bob")

        session.query.assert_not_called()

    def test_unbekannter_einwurf_wirft(self, repository, session):
        _gesperrte_zeile(session, None)

        with pytest.raises(EinwurfNichtGefunden):
            repository.set_status(uuid.uuid4(), RawInputStatus.DISCARDED, "alice")
