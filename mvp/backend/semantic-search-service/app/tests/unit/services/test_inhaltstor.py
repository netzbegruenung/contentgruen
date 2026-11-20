"""
Das Inhaltstor der Suche (services/search/inhaltstor.py): Ein Treffer im unsicheren Band
zaehlt nur, wenn Suchanfrage und Treffer ein Inhaltswort (Lemma eines Nomens oder
Eigennamens) teilen. Die Sprachwerkzeuge sind ein kleines Woerterbuch statt spaCy.
"""

import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services.search.inhaltstor import Inhaltstor

AB = 0.82
AUSSAGE_BIS = 0.92
DIREKT_BIS = 0.90

# Wort (klein) -> (Lemma, Wortart); unbekannte Woerter: Lemma = Wort, Wortart "X".
WOERTERBUCH = {
    "open": ("Open", "PROPN"),
    "source": ("Source", "PROPN"),
    "ist": ("sein", "AUX"),
    "unsicher": ("unsicher", "ADJ"),
    "arbeitserlaubnis": ("Arbeitserlaubnis", "NOUN"),
    "schuld": ("Schuld", "NOUN"),
    "problem": ("Problem", "NOUN"),
    "gründen": ("Grund", "NOUN"),
    "menschen": ("Mensch", "NOUN"),
    "flüchtlinge": ("Flüchtling", "NOUN"),
    "wollen": ("wollen", "VERB"),
    "arbeiten": ("arbeiten", "VERB"),
    "ausländer": ("Ausländer", "NOUN"),
    "migranten": ("Migrant", "NOUN"),
    "machen": ("machen", "VERB"),
    "städte": ("Stadt", "NOUN"),
    "zuwanderung": ("Zuwanderung", "NOUN"),
    "kriminalität": ("Kriminalität", "NOUN"),
    "katzen": ("Katze", "NOUN"),
    "man": ("man", "PRON"),
    "darf": ("dürfen", "VERB"),
    "rauchen": ("rauchen", "VERB"),
    "migration": ("Migration", "NOUN"),
}


class _Werkzeuge:
    """Ersatz fuer SPRACHWERKZEUGE: zerlegt an Leerraum und Satzzeichen."""

    def __init__(self, geladen=True):
        self.geladen = geladen
        self.aufrufe = 0

    def analysieren(self, text):
        self.aufrufe += 1
        tokens = []
        for wort in re.findall(r"\w+", text):
            lemma, pos = WOERTERBUCH.get(wort.lower(), (wort, "X"))
            tokens.append(SimpleNamespace(lemma_=lemma, pos_=pos))
        return tokens


class _KaputteWerkzeuge(_Werkzeuge):
    def analysieren(self, text):
        raise RuntimeError("Modell kaputt")


def _tor(werkzeuge=None, aussagen_zu_antwort=None):
    return Inhaltstor(
        werkzeuge if werkzeuge is not None else _Werkzeuge(),
        aussagen_zu_antwort,
        AB,
        AUSSAGE_BIS,
        DIREKT_BIS,
    )


def _beitrag(score=0.85, title="", text="", id="b-1"):
    return SimpleNamespace(id=id, score=score, title=title, text=text)


def _aussagen(*texte):
    return AsyncMock(return_value=[SimpleNamespace(text=t) for t in texte])


# Befund auf Produktion 0.9.3 (19.11.2026)
OPEN_SOURCE = "Open Source ist unsicher!"
ARBEITSERLAUBNIS_TITEL = "Arbeitserlaubnis ist Schuld"
ARBEITSERLAUBNIS_TEXT = (
    "Das Problem hier ist die oft fehlende Arbeitserlaubnis, dies aus verschiedensten "
    "Gründen viel zu lange auf sich warten lässt. Die Menschen hingegen wollen "
    "größtenteils unbedingt arbeiten, dürfen jedoch nicht!"
)
FLUECHTLINGE = "Flüchtlinge wollen gar nicht arbeiten."


# --- inhaltsworte ---------------------------------------------------------------------


@pytest.mark.unit
def test_inhaltsworte_sind_kleingeschriebene_lemmata_der_nomen_und_eigennamen():
    assert _tor().inhaltsworte(OPEN_SOURCE) == frozenset({"open", "source"})


@pytest.mark.unit
def test_inhaltsworte_leer_bei_unter_drei_woertern():
    assert _tor().inhaltsworte("Migration Kriminalität") == frozenset()


@pytest.mark.unit
def test_inhaltsworte_leer_ohne_nomen():
    assert _tor().inhaltsworte("Man darf ja gar nicht mehr rauchen") == frozenset()


@pytest.mark.unit
def test_inhaltsworte_leer_wenn_modell_nicht_geladen():
    werkzeuge = _Werkzeuge(geladen=False)
    assert _tor(werkzeuge).inhaltsworte(OPEN_SOURCE) == frozenset()
    assert werkzeuge.aufrufe == 0


@pytest.mark.unit
def test_inhaltsworte_leer_wenn_analyse_scheitert():
    assert _tor(_KaputteWerkzeuge()).inhaltsworte(OPEN_SOURCE) == frozenset()


# --- aussage_zaehlt -------------------------------------------------------------------


@pytest.mark.unit
def test_aussage_ausserhalb_des_bands_zaehlt():
    # Gleiches Thema, andere Worte: 0,967 liegt ueber dem Band.
    tor = _tor()
    assert tor.aussage_zaehlt(
        "Ausländer machen unsere Städte unsicher",
        0.967,
        "Migranten machen unsere Städte unsicher.",
        _beitrag(),
    )


@pytest.mark.unit
def test_gleich_gebauter_satz_ohne_gemeinsames_nomen_zaehlt_nicht():
    assert not _tor().aussage_zaehlt(
        "Katzen wollen gar nicht arbeiten", 0.912, FLUECHTLINGE, _beitrag()
    )


@pytest.mark.unit
def test_aussage_mit_gemeinsamem_nomen_zaehlt():
    assert _tor().aussage_zaehlt(
        "Ausländer machen unsere Städte unsicher",
        0.9,
        "Migranten machen unsere Städte unsicher.",
        _beitrag(),
    )


@pytest.mark.unit
def test_aussage_zaehlt_ueber_titel_oder_text_des_beitrags():
    tor = _tor()
    query = "Durch die Zuwanderung gibt es mehr Kriminalität"
    assert tor.aussage_zaehlt(
        query, 0.85, FLUECHTLINGE, _beitrag(title="Kriminalität sinkt")
    )
    assert tor.aussage_zaehlt(
        query, 0.85, FLUECHTLINGE, _beitrag(text="Die Zuwanderung hilft.")
    )


@pytest.mark.unit
@pytest.mark.parametrize("aehnlichkeit", [0.8199, 0.92])
def test_aussage_an_den_bandgrenzen_zaehlt(aehnlichkeit):
    assert _tor().aussage_zaehlt(
        "Katzen wollen gar nicht arbeiten", aehnlichkeit, FLUECHTLINGE, _beitrag()
    )


@pytest.mark.unit
def test_aussage_an_der_unteren_grenze_liegt_im_band():
    assert not _tor().aussage_zaehlt(
        "Katzen wollen gar nicht arbeiten", 0.82, FLUECHTLINGE, _beitrag()
    )


@pytest.mark.unit
def test_aussage_zaehlt_bei_suchanfrage_ohne_nomen():
    assert _tor().aussage_zaehlt(
        "Man darf ja gar nicht mehr rauchen", 0.85, FLUECHTLINGE, _beitrag()
    )


@pytest.mark.unit
def test_aussage_zaehlt_bei_schlagwoertern():
    assert _tor().aussage_zaehlt(
        "Migration Kriminalität", 0.85, FLUECHTLINGE, _beitrag()
    )


@pytest.mark.unit
def test_aussage_zaehlt_wenn_modell_nicht_geladen():
    assert _tor(_Werkzeuge(geladen=False)).aussage_zaehlt(
        "Katzen wollen gar nicht arbeiten", 0.912, FLUECHTLINGE, _beitrag()
    )


# --- direkt_zaehlt --------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_produktionsbefund_open_source_zu_arbeitserlaubnis_zaehlt_nicht():
    aussagen = _aussagen(FLUECHTLINGE)
    tor = _tor(aussagen_zu_antwort=aussagen)
    beitrag = _beitrag(
        score=0.821,
        title=ARBEITSERLAUBNIS_TITEL,
        text=ARBEITSERLAUBNIS_TEXT,
        id="kommentar-arbeitserlaubnis",
    )
    assert not await tor.direkt_zaehlt(OPEN_SOURCE, beitrag)
    aussagen.assert_awaited_once_with("kommentar-arbeitserlaubnis")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_direkter_treffer_mit_gemeinsamem_nomen_fragt_keine_aussagen():
    aussagen = _aussagen(FLUECHTLINGE)
    tor = _tor(aussagen_zu_antwort=aussagen)
    beitrag = _beitrag(
        score=0.879,
        title="Zahlen der Polizei",
        text="Die Kriminalität ist laut Statistik seit Jahren rückläufig.",
    )
    assert await tor.direkt_zaehlt(
        "Durch die Zuwanderung gibt es mehr Kriminalität", beitrag
    )
    aussagen.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_direkter_treffer_zaehlt_ueber_die_aussage_auf_die_er_antwortet():
    aussagen = _aussagen("Durch Zuwanderung steigt die Kriminalität.")
    tor = _tor(aussagen_zu_antwort=aussagen)
    beitrag = _beitrag(
        score=0.879, title="Stimmt nicht", text="Das zeigen die Zahlen nicht.", id="k-7"
    )
    assert await tor.direkt_zaehlt(
        "Durch die Zuwanderung gibt es mehr Kriminalität", beitrag
    )
    aussagen.assert_awaited_once_with("k-7")


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("score", [0.82, 0.90])
async def test_direkt_an_den_bandgrenzen_zaehlt(score):
    aussagen = _aussagen(FLUECHTLINGE)
    tor = _tor(aussagen_zu_antwort=aussagen)
    beitrag = _beitrag(
        score=score, title=ARBEITSERLAUBNIS_TITEL, text=ARBEITSERLAUBNIS_TEXT
    )
    assert await tor.direkt_zaehlt(OPEN_SOURCE, beitrag)
    aussagen.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_direkt_zaehlt_bei_suchanfrage_ohne_nomen():
    aussagen = _aussagen(FLUECHTLINGE)
    tor = _tor(aussagen_zu_antwort=aussagen)
    beitrag = _beitrag(score=0.85, title=ARBEITSERLAUBNIS_TITEL)
    assert await tor.direkt_zaehlt("Man darf ja gar nicht mehr rauchen", beitrag)
    aussagen.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_direkt_zaehlt_bei_schlagwoertern():
    tor = _tor(aussagen_zu_antwort=_aussagen(FLUECHTLINGE))
    beitrag = _beitrag(score=0.85, title=ARBEITSERLAUBNIS_TITEL)
    assert await tor.direkt_zaehlt("Migration Kriminalität", beitrag)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_direkt_zaehlt_wenn_modell_nicht_geladen():
    tor = _tor(_Werkzeuge(geladen=False), aussagen_zu_antwort=_aussagen(FLUECHTLINGE))
    beitrag = _beitrag(
        score=0.821, title=ARBEITSERLAUBNIS_TITEL, text=ARBEITSERLAUBNIS_TEXT
    )
    assert await tor.direkt_zaehlt(OPEN_SOURCE, beitrag)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_direkt_zaehlt_nicht_ohne_aussagenquelle():
    tor = _tor(aussagen_zu_antwort=None)
    beitrag = _beitrag(
        score=0.821, title=ARBEITSERLAUBNIS_TITEL, text=ARBEITSERLAUBNIS_TEXT
    )
    assert not await tor.direkt_zaehlt(OPEN_SOURCE, beitrag)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_direkt_zaehlt_nicht_wenn_aussagen_nicht_laden():
    aussagen = AsyncMock(side_effect=RuntimeError("Qdrant weg"))
    tor = _tor(aussagen_zu_antwort=aussagen)
    beitrag = _beitrag(
        score=0.821, title=ARBEITSERLAUBNIS_TITEL, text=ARBEITSERLAUBNIS_TEXT
    )
    assert not await tor.direkt_zaehlt(OPEN_SOURCE, beitrag)
    aussagen.assert_awaited_once()
