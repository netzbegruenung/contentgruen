"""
Textnormalisierung fuer die Dublettenpruefung: welche Unterschiede zaehlen nicht,
welche schon. Die Faelle stammen aus dem Messset (tests/regression).
"""

import asyncio

import pytest

from utils.text_normalisierung import SperreJeText, ist_dasselbe, text_normalisiert


class TestTextNormalisiert:
    @pytest.mark.parametrize(
        "a, b",
        [
            (
                "Die Grünen sind eine Verbotspartei",
                "Die Grünen sind eine Verbotspartei!",
            ),
            ("windräder sind vogel-schredder", "Windräder sind Vogel-Schredder!"),
            ("„Balkonsolar lohnt sich nie“", "Balkonsolar lohnt sich nie"),
            (
                "Die  Grünen lassen alle Migranten rein. ",
                "Die Grünen lassen alle Migranten rein",
            ),
            ("E-AUTOS SIND EINE TOTGEBURT!!!", "E-Autos sind eine Totgeburt!"),
            (
                '"Habeck will mir meine Heizung verbieten"',
                "Habeck will mir meine Heizung verbieten",
            ),
            ("Das geht's so nicht", "Das geht’s so nicht"),
            ("Klima\n schützen …", "klima schützen"),
            ("STRASSE", "straße"),
        ],
    )
    def test_gleich(self, a, b):
        assert text_normalisiert(a) == text_normalisiert(b)

    @pytest.mark.parametrize(
        "a, b",
        [
            (
                "Die Grünen sind eine Verbotspartei",
                "Die Grünen sind keine Verbotspartei",
            ),
            (
                "Die Grünen zerstören die Wirtschaft!",
                "Die Grünen zerstören unsere Landwirtschaft!",
            ),
            (
                "Deutschland kann das Klima nicht alleine retten",
                "Deutschland kann nicht alleine das Klima retten!",
            ),
            ("E-Autos sind eine Totgeburt", "E Autos sind eine Totgeburt"),
            # Die Frage ist nicht die Behauptung - das Fragezeichen bleibt stehen.
            (
                "Die Grünen wollen alles verbieten?",
                "Die Grünen wollen alles verbieten.",
            ),
            (
                "Wärmepumpen funktionieren nur im Neubau?",
                "Wärmepumpen funktionieren nur im Neubau!",
            ),
        ],
    )
    def test_verschieden(self, a, b):
        assert text_normalisiert(a) != text_normalisiert(b)

    def test_leer_und_none(self):
        assert text_normalisiert("") == ""
        assert text_normalisiert(None) == ""
        assert text_normalisiert(" !. ") == ""


class TestIstDasselbe:
    def test_normalisiert_gleich_unabhaengig_vom_score(self):
        assert ist_dasselbe("a", "a", 0.5, 0.98)
        assert ist_dasselbe("a", "a", None, 0.98)

    def test_score_auf_der_schwelle_zaehlt(self):
        assert ist_dasselbe("a", "b", 0.98, 0.98)

    def test_leere_normalform_ist_nie_gleich(self):
        assert not ist_dasselbe("", "", 0.5, 0.98)

    def test_score_darunter_zaehlt_nicht(self):
        assert not ist_dasselbe("a", "b", 0.979, 0.98)
        assert not ist_dasselbe("a", "b", None, 0.98)


@pytest.mark.asyncio
class TestSperreJeText:
    async def _hoechstens_gleichzeitig(self, sperre, texte):
        laufend = 0
        hoechstens = 0

        async def arbeit(text):
            nonlocal laufend, hoechstens
            async with sperre.halten(text):
                laufend += 1
                hoechstens = max(hoechstens, laufend)
                await asyncio.sleep(0.01)
                laufend -= 1

        await asyncio.gather(*(arbeit(t) for t in texte))
        return hoechstens

    async def test_gleicher_text_laeuft_nacheinander(self):
        sperre = SperreJeText()
        assert (
            await self._hoechstens_gleichzeitig(
                sperre, ["Klima schützen", "  klima SCHÜTZEN!"]
            )
            == 1
        )

    async def test_verschiedene_texte_blockieren_sich_nicht(self):
        sperre = SperreJeText()
        assert await self._hoechstens_gleichzeitig(sperre, ["Klima", "Verkehr"]) == 2

    async def test_liefert_normalform(self):
        async with SperreJeText().halten("  Klima!  ") as schluessel:
            assert schluessel == "klima"

    async def test_sperren_werden_auch_nach_fehler_freigegeben(self):
        sperre = SperreJeText()
        with pytest.raises(RuntimeError):
            async with sperre.halten("klima"):
                raise RuntimeError("qdrant weg")
        assert sperre._sperren == {}
        assert sperre._belegt == {}
