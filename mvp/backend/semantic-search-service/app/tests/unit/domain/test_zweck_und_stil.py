"""
Zweck und Stil am Kommentar (#357, GLOSSARY.md).

Zweck: Antwort in Kommentarspalten (Standard) oder fuer die eigenen Leute. Stil
optional; "bissig" gibt es nur beim Zweck "Fuer die eigenen Leute".
"""

import uuid

import pytest
from pydantic import ValidationError

from domain.models.commentary import Commentary, CommentaryDbEntry, Stil, Zweck
from tests.conftest import create_base_content_fields


def _kommentar(**extra) -> Commentary:
    return Commentary(
        text="Mit Foerderung rechnet sich die Pumpe schon nach wenigen Jahren.",
        title="Waermepumpen lohnen sich auch im Altbau",
        references=[],
        **extra,
    )


def _gelesen(**payload) -> CommentaryDbEntry:
    return CommentaryDbEntry(
        **create_base_content_fields(),
        id=uuid.uuid4(),
        text="Mit Foerderung rechnet sich die Pumpe schon nach wenigen Jahren.",
        title="Waermepumpen lohnen sich auch im Altbau",
        references=[],
        references_count=0,
        **payload,
    )


@pytest.mark.unit
class TestZweckUndStil:
    def test_zweck_ohne_angabe_ist_kommentarspalte(self):
        kommentar = _kommentar()

        assert kommentar.zweck == Zweck.KOMMENTARSPALTE
        assert kommentar.style is None

    def test_zweck_null_gilt_als_kommentarspalte(self):
        assert _kommentar(zweck=None).zweck == Zweck.KOMMENTARSPALTE

    @pytest.mark.parametrize(
        "stil", ["sachlich", "humorvoll", "persoenlich", "brueckenbauend"]
    )
    def test_stil_bei_beiden_zwecken(self, stil):
        for zweck in ("kommentarspalte", "eigene_leute"):
            assert _kommentar(zweck=zweck, style=stil).style == Stil(stil)

    def test_bissig_fuer_die_eigenen_leute(self):
        kommentar = _kommentar(zweck="eigene_leute", style="bissig")

        assert (kommentar.zweck, kommentar.style) == (Zweck.EIGENE_LEUTE, Stil.BISSIG)

    @pytest.mark.parametrize("zweck", [None, "kommentarspalte"])
    def test_bissig_nicht_in_der_kommentarspalte(self, zweck):
        with pytest.raises(ValidationError, match="eigenen Leute"):
            _kommentar(zweck=zweck, style="bissig")

    @pytest.mark.parametrize("leer", ["", "  ", None])
    def test_leerer_stil_heisst_kein_stil(self, leer):
        assert _kommentar(style=leer).style is None

    @pytest.mark.parametrize(
        "wert", ["sarkastisch", "empathisch", "Bissig", "faktisch", "persönlich"]
    )
    def test_unbekannter_stil_wird_abgewiesen(self, wert):
        with pytest.raises(ValidationError):
            _kommentar(style=wert)

    def test_unbekannter_zweck_wird_abgewiesen(self):
        with pytest.raises(ValidationError):
            _kommentar(zweck="zielgruppe")


@pytest.mark.unit
class TestGespeicherteKommentare:
    """Kommentare von vor #357 muessen lesbar bleiben, auch mit freiem Stil."""

    def test_ohne_zweck_gelesen_ist_kommentarspalte(self):
        assert _gelesen().zweck == Zweck.KOMMENTARSPALTE

    @pytest.mark.parametrize(
        "alt, neu",
        [
            ("faktisch", Stil.SACHLICH),
            ("persönlich", Stil.PERSOENLICH),
            ("brückenbauend", Stil.BRUECKENBAUEND),
            ("humorvoll", Stil.HUMORVOLL),
        ],
    )
    def test_alte_schreibweisen_werden_zum_stil(self, alt, neu):
        assert _gelesen(style=alt).style == neu

    @pytest.mark.parametrize(
        "alt", ["sarkastisch", "empathisch", "[faktisch | persönlich]"]
    )
    def test_unbekannter_alter_stil_faellt_weg(self, alt):
        assert _gelesen(style=alt).style is None

    def test_alter_bissiger_in_der_kommentarspalte_verliert_den_stil(self):
        """Lesen scheitert nicht; die Regel gilt fuer Neues."""
        assert _gelesen(style="bissig").style is None

    def test_bissiger_fuer_die_eigenen_leute_bleibt_bissig(self):
        gelesen = _gelesen(zweck="eigene_leute", style="bissig")

        assert (gelesen.zweck, gelesen.style) == (Zweck.EIGENE_LEUTE, Stil.BISSIG)
