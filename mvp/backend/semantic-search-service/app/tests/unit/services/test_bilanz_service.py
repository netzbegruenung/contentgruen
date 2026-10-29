"""
Unit-Tests fuer die Kennzahlen der Bilanz je Woche (#467, Signale in #417).

K1 Personen pro Tag, die suchen (Wochenmittel), K2 Nutzungen pro Woche, K3 Anteil
der Suchen ohne Treffer, H Nutzungen je Suche. Geprueft wird die Rechnung aus
Tageswerten; woher die kommen, pruefen die Integrationstests gegen PostgreSQL.
"""

from datetime import date

import pytest

from services.bilanz_service import BilanzService, Tageswert, bilanz_je_woche

pytestmark = pytest.mark.unit

# Ein Donnerstag; die laufende Woche beginnt am Montag, dem 2026-10-26.
HEUTE = date(2026, 10, 29)
MONTAG = date(2026, 10, 26)
VORWOCHE = date(2026, 10, 19)


def _tag(tag, suchen, personen, ohne_treffer=0):
    return Tageswert(
        tag=tag, suchen=suchen, personen=personen, ohne_treffer=ohne_treffer
    )


class TestBilanzJeWoche:
    def test_bilanz_je_woche_neueste_woche_zuerst_mit_montag(self):
        wochen = bilanz_je_woche([], {}, heute=HEUTE, wochen=3)

        assert [w.woche_ab for w in wochen] == [
            MONTAG,
            VORWOCHE,
            date(2026, 10, 12),
        ]

    def test_bilanz_je_woche_k1_ist_mittel_ueber_alle_tage_der_woche(self):
        # 4 + 2 Personen an zwei Tagen, an den uebrigen fuenf niemand.
        tage = [
            _tag(date(2026, 10, 20), 5, 4),
            _tag(date(2026, 10, 22), 3, 2),
        ]

        vorwoche = bilanz_je_woche(tage, {}, heute=HEUTE, wochen=2)[1]

        assert vorwoche.tage == 7
        assert vorwoche.personen_pro_tag == pytest.approx(6 / 7, abs=0.05)
        assert vorwoche.suchen == 8

    def test_bilanz_je_woche_laufende_woche_zaehlt_nur_tage_bis_heute(self):
        # Montag bis Donnerstag: vier Tage, zusammen 8 Personen.
        tage = [_tag(MONTAG, 3, 3), _tag(HEUTE, 6, 5)]

        laufende = bilanz_je_woche(tage, {}, heute=HEUTE, wochen=1)[0]

        assert laufende.tage == 4
        assert laufende.personen_pro_tag == 2.0

    def test_bilanz_je_woche_k2_summiert_nutzungen_der_woche(self):
        nutzungen = {date(2026, 10, 19): 2, date(2026, 10, 25): 5, MONTAG: 7}

        laufende, vorwoche = bilanz_je_woche([], nutzungen, heute=HEUTE, wochen=2)

        assert laufende.nutzungen == 7
        assert vorwoche.nutzungen == 7

    def test_bilanz_je_woche_k3_ist_anteil_in_prozent(self):
        tage = [_tag(MONTAG, 8, 3, ohne_treffer=2), _tag(HEUTE, 2, 1, ohne_treffer=1)]

        laufende = bilanz_je_woche(tage, {}, heute=HEUTE, wochen=1)[0]

        assert laufende.anteil_ohne_treffer == 30.0

    def test_bilanz_je_woche_h_ist_nutzungen_je_suche(self):
        tage = [_tag(MONTAG, 8, 3)]

        laufende = bilanz_je_woche(tage, {HEUTE: 2}, heute=HEUTE, wochen=1)[0]

        assert laufende.nutzungen_je_suche == 0.25

    def test_bilanz_je_woche_ohne_suchen_kein_anteil_und_kein_h(self):
        laufende = bilanz_je_woche([], {HEUTE: 3}, heute=HEUTE, wochen=1)[0]

        assert laufende.suchen == 0
        assert laufende.personen_pro_tag == 0.0
        assert laufende.anteil_ohne_treffer is None
        assert laufende.nutzungen_je_suche is None

    def test_bilanz_je_woche_unbekannte_ohne_treffer_ergeben_keinen_anteil(self):
        """Tageszaehler von vor #467 kennen die Suchen ohne Treffer nicht."""
        tage = [_tag(VORWOCHE, 4, 2, ohne_treffer=None), _tag(date(2026, 10, 20), 4, 2)]

        vorwoche = bilanz_je_woche(tage, {}, heute=HEUTE, wochen=2)[1]

        assert vorwoche.suchen == 8
        assert vorwoche.anteil_ohne_treffer is None

    def test_bilanz_je_woche_vor_nutzung_ab_keine_nutzungen_und_kein_h(self):
        """Vor der Frist der Nutzungsereignisse fehlen Nutzungen; 0 waere falsch."""
        tage = [_tag(VORWOCHE, 4, 2), _tag(MONTAG, 4, 2)]

        laufende, vorwoche = bilanz_je_woche(
            tage, {MONTAG: 1}, heute=HEUTE, wochen=2, nutzung_ab=date(2026, 10, 20)
        )

        assert laufende.nutzungen == 1
        assert vorwoche.nutzungen is None
        assert vorwoche.nutzungen_je_suche is None

    def test_bilanz_je_woche_tage_ausserhalb_zaehlen_nicht(self):
        tage = [_tag(date(2026, 10, 18), 9, 9), _tag(date(2026, 10, 30), 9, 9)]

        (laufende,) = bilanz_je_woche(tage, {}, heute=HEUTE, wochen=1)

        assert laufende.suchen == 0


class _Suchen:
    def __init__(self, tage):
        self.tage = tage
        self.zeitraum = None

    def get_tageswerte(self, erster, letzter):
        self.zeitraum = (erster, letzter)
        return self.tage


class _Nutzungen:
    def __init__(self, je_tag):
        self.je_tag = je_tag
        self.zeitraum = None

    def get_nutzungen_je_tag(self, erster, letzter):
        self.zeitraum = (erster, letzter)
        return self.je_tag


class TestBilanzService:
    def test_wochen_liest_vom_ersten_montag_bis_heute(self):
        suchen, nutzungen = _Suchen([_tag(MONTAG, 2, 1)]), _Nutzungen({HEUTE: 1})
        service = BilanzService(suchen, nutzungen, nutzung_frist_tage=90)

        wochen = service.wochen(2, heute=HEUTE)

        assert suchen.zeitraum == (VORWOCHE, HEUTE)
        assert nutzungen.zeitraum == (VORWOCHE, HEUTE)
        assert wochen[0].nutzungen_je_suche == 0.5

    def test_wochen_vor_der_frist_der_nutzungsereignisse_ohne_nutzungen(self):
        # Frist 7 Tage: alles vor dem 22.10. ist schon geloescht.
        service = BilanzService(_Suchen([]), _Nutzungen({}), nutzung_frist_tage=7)

        laufende, vorwoche = service.wochen(2, heute=HEUTE)

        assert laufende.nutzungen == 0
        assert vorwoche.nutzungen is None

    def test_wochen_ohne_frist_der_nutzungsereignisse_alle_nutzungen(self):
        """Ist der Bereinigungsjob aus, bleiben alle Nutzungsereignisse."""
        service = BilanzService(_Suchen([]), _Nutzungen({}), nutzung_frist_tage=None)

        _, vorwoche = service.wochen(2, heute=HEUTE)

        assert vorwoche.nutzungen == 0
