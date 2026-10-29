"""
Unit-Tests fuer die Kennzahl "Suchen ohne Treffer".

Das Repository ist durch eine Fake-Klasse ersetzt, die Aussagen kommen aus einem
gemockten StatementService. Geprueft wird, wann eine Suche zaehlt, wann sie als
weitere Person zaehlt, in welche Woche sie faellt und was Admins am Ende sehen.
"""

import asyncio
import threading
import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from domain.models.content_status import ContentStatus
from services.suchen_ohne_treffer_service import (
    PersonenDesTages,
    SuchenOhneTrefferService,
    alte_wochen_loeschen,
    aufbewahrungsgrenze,
    loeschen_im_takt,
)

pytestmark = pytest.mark.unit

AUSSAGE = uuid.UUID("11111111-1111-1111-1111-111111111111")
ANDERE = uuid.UUID("22222222-2222-2222-2222-222222222222")
GELOESCHT = uuid.UUID("33333333-3333-3333-3333-333333333333")
GESPERRT = uuid.UUID("44444444-4444-4444-4444-444444444444")

# Ein Mittwoch; die Woche beginnt am Montag, dem 2026-10-26.
MITTWOCH = date(2026, 10, 28)
DONNERSTAG = date(2026, 10, 29)
MONTAG = date(2026, 10, 26)

# Tagespseudonyme zweier Personen, wie sie SearchTrackingService bildet.
PERSON_A = "a" * 64
PERSON_B = "b" * 64


class FakeRepository:
    def __init__(self, haeufigste=None):
        self.gezaehlt = []
        self.abfragen = []
        self.geloescht_vor = []
        self._haeufigste = haeufigste or []

    def zaehlen(self, statement_id, woche, neue_person):
        self.gezaehlt.append((statement_id, woche, neue_person))

    def haeufigste(self, seit_woche, mindestanzahl, limit, offset=0):
        self.abfragen.append((seit_woche, mindestanzahl, limit, offset))
        return self._haeufigste[offset : offset + limit]

    def loeschen_vor(self, woche):
        self.geloescht_vor.append(woche)
        return 3

    def ueber_der_schwelle(self, seit_woche, mindestanzahl):
        self.abfragen.append((seit_woche, mindestanzahl))
        self.thread = threading.current_thread()
        return [AUSSAGE, ANDERE]


def _statement_service(aussagen):
    """aussagen: ID -> (Text, Status); fehlende IDs gibt es nicht."""
    service = Mock()

    async def get(statement_id):
        if statement_id not in aussagen:
            raise ValueError("nicht gefunden")
        text, status = aussagen[statement_id]
        return SimpleNamespace(id=statement_id, text=text, status=status)

    service.get = AsyncMock(side_effect=get)
    return service


def _service(repo, aussagen=None, personen=None):
    return SuchenOhneTrefferService(
        repo, _statement_service(aussagen or {}), personen or PersonenDesTages()
    )


SICHTBAR = ContentStatus.VISIBLE


class TestErfassen:
    def test_erfassen_ohne_treffer_zaehlt_in_der_woche_ab_montag(self):
        repo = FakeRepository()

        _service(repo).erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)

        assert repo.gezaehlt == [(AUSSAGE, MONTAG, True)]

    def test_erfassen_mit_treffern_zaehlt_nicht(self):
        repo = FakeRepository()

        _service(repo).erfassen(AUSSAGE, 1, PERSON_A, heute=MITTWOCH)

        assert repo.gezaehlt == []

    def test_erfassen_ohne_aussage_zaehlt_nicht(self):
        """Ohne Aussage (Rate-Limit beim Anlegen) gibt es nichts, woran man zaehlt."""
        repo = FakeRepository()

        _service(repo).erfassen(None, 0, PERSON_A, heute=MITTWOCH)

        assert repo.gezaehlt == []

    def test_erfassen_zaehlt_dieselbe_person_am_selben_tag_nur_einmal(self):
        repo = FakeRepository()
        service = _service(repo)

        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)

        assert repo.gezaehlt == [
            (AUSSAGE, MONTAG, True),
            (AUSSAGE, MONTAG, False),
        ]

    def test_erfassen_zaehlt_zwei_personen_als_zwei(self):
        repo = FakeRepository()
        service = _service(repo)

        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, PERSON_B, heute=MITTWOCH)

        assert [neu for *_, neu in repo.gezaehlt] == [True, True]

    def test_erfassen_zaehlt_dieselbe_person_je_aussage(self):
        repo = FakeRepository()
        service = _service(repo)

        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(ANDERE, 0, PERSON_A, heute=MITTWOCH)

        assert repo.gezaehlt == [
            (AUSSAGE, MONTAG, True),
            (ANDERE, MONTAG, True),
        ]

    def test_erfassen_ohne_pseudonym_zaehlt_die_suche_aber_keine_person(self):
        """Ohne Nutzer- und Sitzungskennung laesst sich keine Person unterscheiden."""
        repo = FakeRepository()

        _service(repo).erfassen(AUSSAGE, 0, None, heute=MITTWOCH)

        assert repo.gezaehlt == [(AUSSAGE, MONTAG, False)]

    def test_erfassen_am_naechsten_tag_zaehlt_wieder_als_person(self):
        """
        Das Tagespseudonym wechselt um Mitternacht (UTC): am naechsten Tag ist es
        ein anderes, und die Merkliste des Vortags ist verworfen.
        """
        repo = FakeRepository()
        service = _service(repo)

        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, PERSON_A, heute=DONNERSTAG)

        assert [neu for *_, neu in repo.gezaehlt] == [True, True]

    def test_erfassen_merkt_sich_personen_ueber_anfragen_hinweg(self):
        """Der Service entsteht je Anfrage neu; die Merkliste des Tages bleibt."""
        repo = FakeRepository()
        personen = PersonenDesTages()

        _service(repo, personen=personen).erfassen(AUSSAGE, 0, PERSON_A, MITTWOCH)
        _service(repo, personen=personen).erfassen(AUSSAGE, 0, PERSON_A, MITTWOCH)

        assert [neu for *_, neu in repo.gezaehlt] == [True, False]

    def test_erfassen_vergisst_die_person_wenn_das_schreiben_scheitert(self):
        """Sonst galte sie fuer den Rest des Tages als gezaehlt, ohne es zu sein."""
        repo = FakeRepository()
        personen = PersonenDesTages()
        service = _service(repo, personen=personen)
        repo.zaehlen = Mock(side_effect=[RuntimeError("weg"), None])

        with pytest.raises(RuntimeError):
            service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)

        assert repo.zaehlen.call_args.args == (AUSSAGE, MONTAG, True)

    def test_erfassen_vergisst_bei_fehler_keine_schon_gezaehlte_person(self):
        repo = FakeRepository()
        personen = PersonenDesTages()
        service = _service(repo, personen=personen)
        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        repo.zaehlen = Mock(side_effect=RuntimeError("weg"))

        with pytest.raises(RuntimeError):
            service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)

        assert personen.neu(PERSON_A, AUSSAGE, MITTWOCH) is False


class TestPersonenDesTages:
    def test_neu_zaehlt_bei_voller_merkliste_keine_weitere_person(self):
        """Lieber eine Person zu wenig: so rutscht keine Aussage ueber die Schwelle."""
        personen = PersonenDesTages(obergrenze=1)

        assert personen.neu(PERSON_A, AUSSAGE, MITTWOCH) is True
        assert personen.neu(PERSON_B, AUSSAGE, MITTWOCH) is False
        assert personen.anzahl() == 1

    def test_neu_beginnt_am_naechsten_tag_mit_leerer_merkliste(self):
        personen = PersonenDesTages(obergrenze=1)
        personen.neu(PERSON_A, AUSSAGE, MITTWOCH)

        assert personen.neu(PERSON_B, AUSSAGE, DONNERSTAG) is True

    def test_verwerfen_vor_vergisst_die_personen_des_vortags(self):
        personen = PersonenDesTages()
        personen.neu(PERSON_A, AUSSAGE, MITTWOCH)

        personen.verwerfen_vor(DONNERSTAG)

        assert personen.anzahl() == 0

    def test_verwerfen_vor_behaelt_die_personen_des_laufenden_tags(self):
        personen = PersonenDesTages()
        personen.neu(PERSON_A, AUSSAGE, MITTWOCH)

        personen.verwerfen_vor(MITTWOCH)

        assert personen.neu(PERSON_A, AUSSAGE, MITTWOCH) is False


class TestAufbewahrung:
    def test_aufbewahrungsgrenze_behaelt_acht_wochen_samt_laufender(self):
        # Es bleiben die Montage 26.10., 19.10., 12.10., 05.10., 28.09., 21.09.,
        # 14.09. und 07.09.
        assert aufbewahrungsgrenze(MITTWOCH) == date(2026, 9, 7)

    def test_alte_wochen_loeschen_loescht_vor_der_aufbewahrungsgrenze(self):
        repo = FakeRepository()

        assert alte_wochen_loeschen(repo, heute=MITTWOCH) == 3
        assert repo.geloescht_vor == [date(2026, 9, 7)]

    @pytest.mark.asyncio
    async def test_loeschen_im_takt_loescht_sofort_und_laeuft_nach_fehler_weiter(self):
        repo = FakeRepository()
        repo.loeschen_vor = Mock(side_effect=[RuntimeError("weg"), 0, 0])

        task = asyncio.create_task(
            loeschen_im_takt(repo, PersonenDesTages(), takt_sekunden=0)
        )
        while repo.loeschen_vor.call_count < 2:
            await asyncio.sleep(0.01)
        task.cancel()

        assert repo.loeschen_vor.call_count >= 2

    @pytest.mark.asyncio
    async def test_loeschen_im_takt_verwirft_die_personen_des_vortags(self):
        repo = FakeRepository()
        personen = PersonenDesTages()
        personen.neu(PERSON_A, AUSSAGE, date(2000, 1, 1))

        task = asyncio.create_task(loeschen_im_takt(repo, personen, takt_sekunden=0))
        while not repo.geloescht_vor:
            await asyncio.sleep(0.01)
        task.cancel()

        assert personen.anzahl() == 0


class TestHaeufigste:
    @pytest.mark.asyncio
    async def test_haeufigste_liefert_text_anzahl_und_personen_der_aussage(self):
        repo = FakeRepository(haeufigste=[(AUSSAGE, 7, 4), (ANDERE, 3, 2)])
        service = _service(
            repo,
            {
                AUSSAGE: ("Windräder töten Vögel", SICHTBAR),
                ANDERE: ("Wärmepumpe im Altbau", SICHTBAR),
            },
        )

        ergebnis = await service.haeufigste(wochen=4, heute=MITTWOCH)

        assert [(e.statement_id, e.text, e.anzahl, e.personen) for e in ergebnis] == [
            (AUSSAGE, "Windräder töten Vögel", 7, 4),
            (ANDERE, "Wärmepumpe im Altbau", 3, 2),
        ]

    @pytest.mark.asyncio
    async def test_haeufigste_fragt_die_laufende_und_drei_vorwochen_ab(self):
        repo = FakeRepository()

        await _service(repo).haeufigste(wochen=4, heute=MITTWOCH)

        assert repo.abfragen == [(date(2026, 10, 5), 2, 20, 0)]

    @pytest.mark.asyncio
    async def test_haeufigste_laesst_nicht_mehr_vorhandene_aussagen_weg(self):
        repo = FakeRepository(haeufigste=[(GELOESCHT, 9, 2), (AUSSAGE, 4, 2)])
        service = _service(repo, {AUSSAGE: ("Windräder töten Vögel", SICHTBAR)})

        ergebnis = await service.haeufigste(wochen=4, heute=MITTWOCH)

        assert [e.statement_id for e in ergebnis] == [AUSSAGE]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "status",
        [
            ContentStatus.BLOCKED,
            ContentStatus.DELETED,
            ContentStatus.PENDING_DESCRIPTION,
        ],
    )
    async def test_haeufigste_zeigt_nur_sichtbare(self, status):
        repo = FakeRepository(haeufigste=[(GESPERRT, 9, 2), (AUSSAGE, 4, 2)])
        service = _service(
            repo,
            {
                GESPERRT: ("enthält einen Namen", status),
                AUSSAGE: ("Windräder töten Vögel", SICHTBAR),
            },
        )

        ergebnis = await service.haeufigste(wochen=4, heute=MITTWOCH)

        assert [e.statement_id for e in ergebnis] == [AUSSAGE]

    @pytest.mark.asyncio
    async def test_haeufigste_laedt_nach_wenn_aussagen_herausfallen(self):
        """Gesperrte Aussagen belegen keine Plaetze: es wird nachgeladen."""
        gesperrte = [(uuid.uuid4(), 9, 2) for _ in range(2)]
        repo = FakeRepository(haeufigste=gesperrte + [(AUSSAGE, 4, 2), (ANDERE, 3, 2)])
        aussagen = {sid: ("gesperrt", ContentStatus.BLOCKED) for sid, *_ in gesperrte}
        aussagen[AUSSAGE] = ("Windräder töten Vögel", SICHTBAR)
        aussagen[ANDERE] = ("Wärmepumpe im Altbau", SICHTBAR)

        ergebnis = await _service(repo, aussagen).haeufigste(
            wochen=4, limit=2, heute=MITTWOCH
        )

        assert [e.statement_id for e in ergebnis] == [AUSSAGE, ANDERE]
        assert [offset for *_, offset in repo.abfragen] == [0, 2]


class TestUeberDerSchwelle:
    @pytest.mark.asyncio
    async def test_ueber_der_schwelle_fragt_den_zeitraum_der_kennzahl_ab(self):
        repo = FakeRepository()

        ergebnis = await _service(repo).ueber_der_schwelle(wochen=4, heute=MITTWOCH)

        assert ergebnis == frozenset({AUSSAGE, ANDERE})
        assert repo.abfragen == [(date(2026, 10, 5), 2)]

    @pytest.mark.asyncio
    async def test_ueber_der_schwelle_blockiert_den_event_loop_nicht(self):
        """Die synchrone Datenbankabfrage laeuft nicht im Thread des Event-Loops."""
        repo = FakeRepository()

        await _service(repo).ueber_der_schwelle(heute=MITTWOCH)

        assert repo.thread is not threading.current_thread()
