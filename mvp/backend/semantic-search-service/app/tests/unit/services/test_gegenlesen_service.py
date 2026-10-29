"""
Gegenlesen ohne KI (#358): feste Regeln über spaCy-Lemmata und CharSplit.

Die Tests laufen gegen das echte Sprachmodell; ohne spaCy (etwa auf einer Dev-VM,
auf der requirements.txt noch nicht nachinstalliert ist) werden sie übersprungen.
In der CI und im Image ist es da.
"""

import pytest

pytest.importorskip("spacy")
pytest.importorskip("charsplit")

from services.gegenlesen.gegenlesen_service import (  # noqa: E402
    GegenlesenService,
    lade_statt_sag_liste,
)

pytestmark = [pytest.mark.unit]


@pytest.fixture(scope="module")
def service():
    return GegenlesenService(statt_sag=lade_statt_sag_liste())


def arten(ergebnis):
    return [a.art for a in ergebnis.anmerkungen]


def anmerkung(ergebnis, art):
    return next(a for a in ergebnis.anmerkungen if a.art == art)


class TestOhneText:
    def test_leerer_beitrag_hat_keine_guete(self, service):
        ergebnis = service.gegenlesen(titel="  ", text="", aussage="")

        assert ergebnis.guete is None
        assert ergebnis.anmerkungen == []


class TestGuterBeitrag:
    def test_kurzer_positiver_beitrag_ohne_anmerkung_hat_hoechste_guete(self, service):
        ergebnis = service.gegenlesen(
            titel="Wärmepumpe lohnt sich auch im Altbau",
            text="Mit der Förderung zahlt sich die Pumpe nach wenigen Jahren aus.",
            aussage="Wärmepumpen sind zu teuer",
        )

        assert ergebnis.anmerkungen == []
        assert ergebnis.guete == 10


class TestVerneinungAmAnfang:
    def test_titel_beginnt_mit_nicht(self, service):
        ergebnis = service.gegenlesen(
            titel="Nicht die Wärmepumpe ist das Problem", text="", aussage=""
        )

        assert "verneinung" in arten(ergebnis)
        assert anmerkung(ergebnis, "verneinung").stelle == "titel"

    def test_erster_satz_beginnt_mit_kein(self, service):
        ergebnis = service.gegenlesen(
            titel="Klimaschutz schafft Arbeit",
            text="Kein Betrieb verliert dadurch Aufträge. Viele gewinnen neue.",
            aussage="",
        )

        assert anmerkung(ergebnis, "verneinung").stelle == "text"

    def test_verneinung_spaeter_im_satz_zaehlt_nicht(self, service):
        ergebnis = service.gegenlesen(
            titel="Der Umbau der Heizung kostet weniger als gedacht, aber nicht nichts",
            text="",
            aussage="",
        )

        assert "verneinung" not in arten(ergebnis)

    def test_verneinung_nur_im_zweiten_satz_zaehlt_nicht(self, service):
        ergebnis = service.gegenlesen(
            titel="Klimaschutz schafft Arbeit",
            text="Viele Betriebe gewinnen neue Aufträge. Niemand muss Angst haben.",
            aussage="",
        )

        assert "verneinung" not in arten(ergebnis)

    def test_verneinung_entfernen_hebt_die_guete(self, service):
        vorher = service.gegenlesen(
            titel="Nicht die Wärmepumpe ist das Problem", text="", aussage=""
        )
        nachher = service.gegenlesen(
            titel="Die Wärmepumpe löst das Problem", text="", aussage=""
        )

        assert nachher.guete > vorher.guete


class TestSchluesselwoerterDerAussage:
    def test_titel_wiederholt_den_vorwurf(self, service):
        ergebnis = service.gegenlesen(
            titel="Die Grünen sind eine Partei der Freiheit statt eine Verbotspartei",
            text="",
            aussage="Die Grünen sind eine Verbotspartei",
        )

        uebernommen = anmerkung(ergebnis, "schluesselwoerter")
        assert "Verbotspartei" in uebernommen.woerter
        assert "Grünen" in uebernommen.woerter

    def test_beugung_und_zusammensetzung_finden_zusammen(self, service):
        # "Verbote" (Lemma Verbot) trifft das Bestimmungswort von "Verbotspartei".
        ergebnis = service.gegenlesen(
            titel="Verbote schützen die Grünen nicht",
            text="",
            aussage="Die Grünen sind eine Verbotspartei",
        )

        assert set(anmerkung(ergebnis, "schluesselwoerter").woerter) == {
            "Verbote",
            "Grünen",
        }

    def test_ein_gemeinsames_thema_ist_keine_uebernahme(self, service):
        ergebnis = service.gegenlesen(
            titel="Wärmepumpe lohnt sich auch im Altbau",
            text="",
            aussage="Wärmepumpen sind zu teuer und laut",
        )

        assert "schluesselwoerter" not in arten(ergebnis)

    def test_ohne_aussage_kein_abgleich(self, service):
        ergebnis = service.gegenlesen(
            titel="Die Grünen sind keine Verbotspartei", text="", aussage=None
        )

        assert "schluesselwoerter" not in arten(ergebnis)


class TestSatzlaenge:
    LANG = (
        "Wer heute eine neue Heizung kauft, sollte sich vorher genau ansehen, "
        "welche Förderung es gibt und wie sich die Kosten über zwanzig Jahre entwickeln."
    )

    def test_langer_satz_im_text(self, service):
        ergebnis = service.gegenlesen(
            titel="Förderung lohnt", text=self.LANG, aussage=""
        )

        lang = anmerkung(ergebnis, "satzlaenge")
        assert lang.stelle == "text"
        assert lang.woerter == []
        assert "24 Wörter" in lang.text

    def test_kurze_saetze_sind_in_ordnung(self, service):
        ergebnis = service.gegenlesen(
            titel="Förderung lohnt",
            text="Vor dem Kauf die Förderung prüfen. Über zwanzig Jahre rechnen.",
            aussage="",
        )

        assert "satzlaenge" not in arten(ergebnis)

    def test_kuerzerer_satz_hebt_die_guete(self, service):
        vorher = service.gegenlesen(titel="Förderung lohnt", text=self.LANG, aussage="")
        nachher = service.gegenlesen(
            titel="Förderung lohnt",
            text="Vor dem Kauf die Förderung prüfen. Über zwanzig Jahre rechnen.",
            aussage="",
        )

        assert nachher.guete > vorher.guete


class TestStattSag:
    def test_fachwort_aus_der_liste_mit_vorschlag(self, service):
        ergebnis = service.gegenlesen(
            titel="Der Diskurs über Heizungen braucht Fakten", text="", aussage=""
        )

        statt = anmerkung(ergebnis, "statt_sag")
        assert statt.woerter == ["Diskurs"]
        assert "Debatte" in statt.text

    def test_gebeugt_und_in_zusammensetzung(self, service):
        ergebnis = service.gegenlesen(
            titel="Klimaschutz gelingt",
            text="Der Transformationsprozess braucht neue Narrative.",
            aussage="",
        )

        assert set(anmerkung(ergebnis, "statt_sag").woerter) == {
            "Transformationsprozess",
            "Narrative",
        }

    def test_liste_hat_die_startwoerter(self):
        liste = lade_statt_sag_liste()

        assert {"diskurs", "transformation", "narrativ"} <= set(liste)


class TestPassiv:
    def test_werden_mit_partizip(self, service):
        ergebnis = service.gegenlesen(
            titel="Klimaschutz schafft Arbeit",
            text="Das Gesetz wird von der Regierung verabschiedet.",
            aussage="",
        )

        assert anmerkung(ergebnis, "passiv").woerter == ["wird verabschiedet"]

    def test_futur_ist_kein_passiv(self, service):
        ergebnis = service.gegenlesen(
            titel="Klimaschutz schafft Arbeit",
            text="Die Regierung wird das Gesetz verabschieden.",
            aussage="",
        )

        assert "passiv" not in arten(ergebnis)


class TestLangeKomposita:
    def test_langes_zusammengesetztes_wort(self, service):
        ergebnis = service.gegenlesen(
            titel="Das Gebäudeenergiegesetz hilft Mietern", text="", aussage=""
        )

        lang = anmerkung(ergebnis, "kompositum")
        assert lang.woerter == ["Gebäudeenergiegesetz"]
        assert "(Gebäude + Energiegesetz)" in lang.text

    def test_kurzes_zusammengesetztes_wort_ist_in_ordnung(self, service):
        ergebnis = service.gegenlesen(
            titel="Die Wärmepumpe hilft Mietern", text="", aussage=""
        )

        assert "kompositum" not in arten(ergebnis)


class TestGuete:
    def test_viele_anmerkungen_senken_die_guete_nie_unter_eins(self, service):
        ergebnis = service.gegenlesen(
            titel="Nicht die Grünen sind eine Verbotspartei im Diskurs",
            text=(
                "Kein Narrativ der Transformation wird von der Regierung beschlossen, "
                "obwohl das Gebäudeenergiegesetz und der Paradigmenwechsel im Diskurs "
                "seit langem von vielen Akteuren gefordert worden sind."
            ),
            aussage="Die Grünen sind eine Verbotspartei",
        )

        assert ergebnis.guete == 1


class TestSchluesselwoerterAnteil:
    def test_zwei_von_drei_themenwoertern_sind_keine_uebernahme(self, service):
        ergebnis = service.gegenlesen(
            titel="Windräder sichern günstigen Strom für alle",
            text="",
            aussage="Windräder machen den Strom teurer",
        )

        assert "schluesselwoerter" not in arten(ergebnis)


class TestPassivKoordination:
    def test_infinitiv_neben_partizip_ist_kein_passivpaar(self, service):
        ergebnis = service.gegenlesen(
            titel="Alte Heizungen bleiben",
            text="Bestehende Anlagen dürfen weiterlaufen und repariert werden.",
            aussage="",
        )

        assert "werden weiterlaufen" not in (
            anmerkung(ergebnis, "passiv").woerter if "passiv" in arten(ergebnis) else []
        )


class TestSchluesselwoerterPraedikativ:
    def test_adjektiv_nach_sein_zaehlt_als_schluesselwort(self, service):
        ergebnis = service.gegenlesen(
            titel="Wärmepumpen sind gar nicht teuer",
            text="",
            aussage="Wärmepumpen sind zu teuer",
        )

        assert anmerkung(ergebnis, "schluesselwoerter").woerter == [
            "Wärmepumpen",
            "teuer",
        ]


class TestReviewBefunde:
    @pytest.mark.parametrize(
        "titel",
        [
            "Nicht nur Wärmepumpen, sondern auch Netze helfen",
            "Kein Wunder: Wärmepumpen sparen Geld",
        ],
    )
    def test_feste_wendung_ist_keine_verneinung(self, service, titel):
        ergebnis = service.gegenlesen(titel=titel, text="", aussage="")

        assert "verneinung" not in arten(ergebnis)

    def test_verneinung_an_dritter_stelle_wird_benannt(self, service):
        ergebnis = service.gegenlesen(
            titel="Wärmepumpen sind nicht zu teuer", text="", aussage=""
        )

        assert (
            "verneint gleich am Anfang („nicht“)"
            in anmerkung(ergebnis, "verneinung").text
        )

    def test_zusammensetzung_nennt_das_listenwort(self, service):
        ergebnis = service.gegenlesen(
            titel="Klimaschutz gelingt",
            text="Der Transformationsprozess braucht Mut.",
            aussage="",
        )

        assert (
            "statt „Transformation“ (in „Transformationsprozess“) lieber „Umbau“"
            in (anmerkung(ergebnis, "statt_sag").text)
        )
