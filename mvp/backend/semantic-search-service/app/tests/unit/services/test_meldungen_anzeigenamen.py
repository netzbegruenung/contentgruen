"""
Anzeigenamen in den Meldungslisten der Moderation (Folge zu #673).

"Gemeldet von" und "Bearbeitet von" zeigen den Namen, wo es einen gibt; sonst
bleibt das Feld None und das Frontend zeigt die Kurzform der Kennung.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.moderation_service import ModerationService


def _meldung(**felder):
    meldung = {
        "id": "m-1",
        "content_id": None,
        "reported_by_user_id": None,
        "reviewed_by": None,
    }
    meldung.update(felder)
    return meldung


def _service(meldungen, namen):
    report_repo = MagicMock()
    report_repo.get_reports = MagicMock(return_value=meldungen)
    report_repo.von_melder = MagicMock(return_value=meldungen)
    anzeigenamen = MagicMock()
    anzeigenamen.namen = MagicMock(return_value=namen)
    service = ModerationService(
        report_repo=report_repo,
        moderation_repo=AsyncMock(),
        anzeigenamen=anzeigenamen,
    )
    return service, anzeigenamen


@pytest.mark.unit
@pytest.mark.asyncio
async def test_liste_bekommt_namen_der_meldenden_und_bearbeitenden_person():
    meldungen = [
        _meldung(id="a", reported_by_user_id="person-1", reviewed_by="admin-1"),
        _meldung(id="b", reported_by_user_id="person-2"),
    ]
    service, anzeigenamen = _service(
        meldungen, {"person-1": "Anna B.", "admin-1": "Henrike P."}
    )

    liste = await service.get_reports(status="all")

    assert liste[0]["reported_by_name"] == "Anna B."
    assert liste[0]["reviewed_by_name"] == "Henrike P."
    # Ohne bekannten Namen bleibt das Feld leer; das Frontend zeigt die Kurzform.
    assert liste[1]["reported_by_name"] is None
    assert liste[1]["reviewed_by_name"] is None
    # Eine Abfrage fuer alle Kennungen
    anzeigenamen.namen.assert_called_once()
    assert set(anzeigenamen.namen.call_args.args[0]) == {
        "person-1",
        "person-2",
        "admin-1",
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_anonyme_meldungen_fragen_keine_namen_ab():
    service, anzeigenamen = _service([_meldung()], {})

    liste = await service.get_reports()

    anzeigenamen.namen.assert_not_called()
    assert liste[0]["reported_by_name"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_meldungen_einer_person_bekommen_namen():
    service, _ = _service(
        [_meldung(reported_by_user_id="person-1")], {"person-1": "Anna B."}
    )

    liste = await service.meldungen_einer_person(MagicMock())

    assert liste[0]["reported_by_name"] == "Anna B."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scheitert_das_nachschlagen_bleibt_die_liste_ohne_namen():
    service, anzeigenamen = _service([_meldung(reported_by_user_id="person-1")], {})
    anzeigenamen.namen.side_effect = RuntimeError("weg")

    liste = await service.get_reports()

    assert len(liste) == 1
    assert liste[0]["reported_by_name"] is None
