"""
Unit-Tests fuer Einladungen (#429).

Repository und Keycloak sind gemockt. Geprueft wird, wann eine Einladung ein Konto
anlegen laesst, dass der Zaehler nur angelegte Konten zaehlt und dass nirgends ein
Bezug zwischen Einladung und Konto entsteht.
"""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from services.einladung_service import (
    Einladung,
    EinladungZustand,
    EinladungService,
    EinladungUngueltig,
    KontoAnlegen,
    KontoAnlegenFehlgeschlagen,
    EinloesenNichtEingerichtet,
)

pytestmark = pytest.mark.unit

HEUTE = date(2026, 10, 30)
CODE = "Ab3dEf6hIj9kLm2n"


def _zeile(**werte):
    standard = dict(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        code=CODE,
        notiz="Kreisverband, Herbsttreffen",
        erlaubte_einloesungen=50,
        einloesungen=3,
        gueltig_bis=date(2026, 11, 27),
        abgeschaltet=False,
        angelegt_am=HEUTE,
    )
    standard.update(werte)
    return SimpleNamespace(**standard)


@pytest.fixture
def repository():
    repository = Mock()
    repository.platz_belegen.return_value = True
    return repository


@pytest.fixture
def konten():
    konten = Mock()
    konten.konto_anlegen.return_value = KontoAnlegen.ANGELEGT
    return konten


class TestAnlegen:
    def test_neue_einladung_bekommt_einen_zufaelligen_code(self, repository):
        repository.anlegen.side_effect = lambda **w: _zeile(**w, einloesungen=0)

        einladung = EinladungService(repository, None).anlegen(
            "Persoenlicher Link", 1, date(2026, 11, 13), heute=HEUTE
        )

        assert len(einladung.code) >= 16
        assert einladung.erlaubte_einloesungen == 1
        assert einladung.einloesungen == 0
        assert einladung.angelegt_am == HEUTE

    def test_zwei_einladungen_haben_verschiedene_codes(self, repository):
        repository.anlegen.side_effect = lambda **w: _zeile(**w, einloesungen=0)
        service = EinladungService(repository, None)

        a = service.anlegen("a", 1, date(2026, 11, 13), heute=HEUTE)
        b = service.anlegen("b", 1, date(2026, 11, 13), heute=HEUTE)

        assert a.code != b.code


class TestZustand:
    @pytest.mark.parametrize(
        "werte, zustand",
        [
            ({}, "aktiv"),
            ({"abgeschaltet": True}, "abgeschaltet"),
            ({"gueltig_bis": date(2026, 10, 29)}, "abgelaufen"),
            ({"einloesungen": 50}, "aufgebraucht"),
            # Am letzten Tag gilt sie noch.
            ({"gueltig_bis": HEUTE}, "aktiv"),
            # Abgeschaltet geht vor abgelaufen: das hat jemand bewusst getan.
            ({"abgeschaltet": True, "gueltig_bis": date(2026, 1, 1)}, "abgeschaltet"),
        ],
    )
    def test_zustand(self, werte, zustand):
        assert Einladung.aus_zeile(_zeile(**werte)).zustand(HEUTE) is EinladungZustand(
            zustand
        )


class TestEinloesen:
    def test_gueltiger_code_legt_ein_konto_an(self, repository, konten):
        EinladungService(repository, konten).einloesen(
            CODE, "neu@example.org", heute=HEUTE
        )

        repository.platz_belegen.assert_called_once_with(CODE, HEUTE)
        konten.konto_anlegen.assert_called_once_with("neu@example.org")
        repository.platz_freigeben.assert_not_called()

    def test_ungueltiger_code_legt_kein_konto_an(self, repository, konten):
        repository.platz_belegen.return_value = False

        with pytest.raises(EinladungUngueltig):
            EinladungService(repository, konten).einloesen(
                CODE, "neu@example.org", heute=HEUTE
            )

        konten.konto_anlegen.assert_not_called()

    def test_vorhandenes_konto_zaehlt_wie_ein_neues(self, repository, konten):
        # Sonst verriete /pruefen danach, dass die Adresse ein Konto hat.
        konten.konto_anlegen.return_value = KontoAnlegen.VORHANDEN

        EinladungService(repository, konten).einloesen(
            CODE, "alt@example.org", heute=HEUTE
        )

        repository.platz_freigeben.assert_not_called()

    def test_fehler_bei_keycloak_gibt_den_platz_frei(self, repository, konten):
        konten.konto_anlegen.side_effect = RuntimeError("Keycloak weg")

        with pytest.raises(KontoAnlegenFehlgeschlagen):
            EinladungService(repository, konten).einloesen(
                CODE, "neu@example.org", heute=HEUTE
            )

        repository.platz_freigeben.assert_called_once_with(CODE)

    def test_ohne_keycloak_ist_registrierung_nicht_eingerichtet(self, repository):
        with pytest.raises(EinloesenNichtEingerichtet):
            EinladungService(repository, None).einloesen(
                CODE, "neu@example.org", heute=HEUTE
            )

        repository.platz_belegen.assert_not_called()

    def test_kein_bezug_zwischen_einladung_und_konto(self, repository, konten):
        EinladungService(repository, konten).einloesen(
            CODE, "neu@example.org", heute=HEUTE
        )

        # Keycloak erfaehrt den Code nicht, die Datenbank die Mail-Adresse nicht.
        for aufruf in konten.method_calls:
            assert CODE not in repr(aufruf)
        for aufruf in repository.method_calls:
            assert "neu@example.org" not in repr(aufruf)


class TestPruefen:
    def test_einloesbar_nur_wenn_aktiv(self, repository):
        repository.nach_code.return_value = _zeile(einloesungen=50)
        service = EinladungService(repository, None)

        assert service.ist_einloesbar(CODE, heute=HEUTE) is False

        repository.nach_code.return_value = _zeile()
        assert service.ist_einloesbar(CODE, heute=HEUTE) is True

    def test_unbekannter_code_ist_nicht_einloesbar(self, repository):
        repository.nach_code.return_value = None

        assert EinladungService(repository, None).ist_einloesbar(CODE) is False


class TestAbschalten:
    def test_abschalten_und_wieder_einschalten(self, repository):
        repository.schalten.return_value = _zeile(abgeschaltet=True)
        service = EinladungService(repository, None)

        einladung = service.schalten(uuid.uuid4(), True)

        assert einladung is not None and einladung.abgeschaltet is True

    def test_unbekannte_einladung(self, repository):
        repository.schalten.return_value = None

        assert EinladungService(repository, None).schalten(uuid.uuid4(), True) is None
