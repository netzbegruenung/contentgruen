"""
Die Güte an Karten (#427, services/guete_service.py): welche Stimmen zählen, was die
Karte über die Kriterien erfährt, und dass eine typische kleine Verbesserung die Güte
sichtbar hebt (gegen das echte Gegenlesen, sofern das Sprachmodell da ist).
"""

import importlib.util
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from domain.guete import Guetegewichte
from services.gegenlesen.gegenlesen_service import (
    SPACY_MODELL,
    Anmerkung,
    Gegengelesen,
    GegenlesenService,
    Sprachwerkzeuge,
    lade_statt_sag_liste,
)
from services.guete_service import GueteService

pytestmark = pytest.mark.unit

AUTORIN = "autorin-1"
START = "start-9"


def _beitrag(**felder):
    werte = dict(
        id=uuid.uuid4(),
        content_type="commentary",
        title="Wärmepumpen sparen Geld",
        text="Sie laufen mit Strom.",
        original_author=AUTORIN,
    )
    werte.update(felder)
    return SimpleNamespace(**werte)


def _gegenlesen(guete=8, arten=("passiv",)):
    gegenlesen = MagicMock()
    gegenlesen.gegenlesen.return_value = Gegengelesen(
        guete=guete,
        anmerkungen=[Anmerkung(art=a, stelle="text", text="") for a in arten],
    )
    return gegenlesen


def _service(gegenlesen=None, stimmen=None):
    repository = MagicMock()
    repository.stimmen_je_beitrag.side_effect = lambda ids, aus: stimmen or {}
    return (
        GueteService(
            gegenlesen or _gegenlesen(),
            repository,
            startkonten=[START],
            gewichte=Guetegewichte(stimmen_ab=3),
        ),
        repository,
    )


def test_kriterienanteil_und_erfuellte_kriterien():
    service, _ = _service()
    [beitrag] = service.ergaenzen([_beitrag()])
    assert beitrag.guete == 8
    assert "passiv" not in beitrag.guete_erfuellt
    assert "verneinung" in beitrag.guete_erfuellt
    # Die Schlüsselwörter brauchen die Aussage; die Karte behauptet sie nicht.
    assert "schluesselwoerter" not in beitrag.guete_erfuellt
    assert beitrag.guete_stimmen_zaehlen is False
    # Unter der Mindestzahl keine Zähler, auch nicht 0 (M5).
    assert getattr(beitrag, "stimmen_hilfreich", None) is None


def test_post_ohne_verneinungsregel():
    gegenlesen = _gegenlesen(arten=())
    service, _ = _service(gegenlesen)
    [beitrag] = service.ergaenzen([_beitrag(content_type="post")])
    assert gegenlesen.gegenlesen.call_args.kwargs["titel_ist_behauptung"] is False
    assert "verneinung" not in beitrag.guete_erfuellt


def test_startkonten_gehen_an_die_abfrage():
    service, repository = _service()
    service.ergaenzen([_beitrag()])
    assert repository.stimmen_je_beitrag.call_args.args[1] == frozenset({START})


def test_eigene_stimme_zaehlt_weder_fuer_die_guete_noch_im_zaehler():
    beitrag = _beitrag()
    stimmen = {
        str(beitrag.id): [(AUTORIN, "like"), ("a", "like"), ("b", "like")],
    }
    service, _ = _service(stimmen=stimmen)
    service.ergaenzen([beitrag])
    # Zwei fremde Stimmen: unter der Mindestzahl, die Güte bleibt beim Kriterienanteil.
    assert beitrag.guete_stimmen_zaehlen is False
    assert beitrag.guete == 8
    # Unter der Mindestzahl verrät die API keine Zahl.
    assert getattr(beitrag, "stimmen_hilfreich", None) is None


def test_zaehler_erst_ab_der_mindestzahl_ohne_autorin():
    beitrag = _beitrag()
    stimmen = {
        str(beitrag.id): [
            (AUTORIN, "like"),
            ("a", "like"),
            ("b", "like"),
            ("c", "dislike"),
        ],
    }
    service, _ = _service(stimmen=stimmen)
    service.ergaenzen([beitrag])
    assert beitrag.guete_stimmen_zaehlen is True
    assert (beitrag.stimmen_hilfreich, beitrag.stimmen_nicht_hilfreich) == (2, 1)


@pytest.mark.parametrize("anzahl", [1, 2])
def test_unter_der_mindestzahl_keine_zahl_in_der_antwort(anzahl):
    beitrag = _beitrag()
    stimmen = {str(beitrag.id): [(k, "dislike") for k in "xyz"[:anzahl]]}
    service, _ = _service(stimmen=stimmen)
    service.ergaenzen([beitrag])
    assert getattr(beitrag, "stimmen_hilfreich", None) is None
    assert getattr(beitrag, "stimmen_nicht_hilfreich", None) is None


def test_ab_der_mindestzahl_heben_stimmen_die_guete():
    beitrag = _beitrag()
    stimmen = {str(beitrag.id): [(k, "like") for k in "abcdefghij"]}
    service, _ = _service(stimmen=stimmen)
    service.ergaenzen([beitrag])
    assert beitrag.guete_stimmen_zaehlen is True
    assert beitrag.guete == 9


def test_ohne_datenbank_ohne_zaehler_aber_mit_kriterien():
    service, repository = _service()
    repository.stimmen_je_beitrag.side_effect = ConnectionError()
    [beitrag] = service.ergaenzen([_beitrag()])
    assert beitrag.guete == 8
    assert getattr(beitrag, "stimmen_hilfreich", None) is None


def test_ohne_sprachmodell_neu():
    gegenlesen = MagicMock()
    gegenlesen.gegenlesen.side_effect = OSError("kein Modell")
    service, _ = _service(gegenlesen)
    [beitrag] = service.ergaenzen([_beitrag()])
    assert beitrag.guete is None
    assert beitrag.guete_erfuellt == []


def test_scheitert_das_gegenlesen_an_einem_text_bleibt_nur_diese_karte_neu():
    def lesen(titel, *_, **__):
        if titel == "kaputt":
            raise ValueError()
        return Gegengelesen(guete=9, anmerkungen=[])

    gegenlesen = MagicMock()
    gegenlesen.gegenlesen.side_effect = lesen
    service, _ = _service(gegenlesen)
    kaputt, heil = service.ergaenzen([_beitrag(title="kaputt"), _beitrag()])
    assert kaputt.guete is None
    assert heil.guete == 9


def test_gegenlesen_wird_je_text_zwischengehalten():
    gegenlesen = _gegenlesen()
    service, _ = _service(gegenlesen)
    service.ergaenzen([_beitrag(), _beitrag()])
    assert gegenlesen.gegenlesen.call_count == 1


_MODELL_DA = all(
    importlib.util.find_spec(p) is not None
    for p in ("spacy", "charsplit", SPACY_MODELL)
)


@pytest.mark.skipif(not _MODELL_DA, reason="Sprachmodell nicht installiert")
@pytest.mark.parametrize(
    "vorher, nachher",
    [
        # Verneinung am Anfang entfernt
        (
            "Keine Wärmepumpe ist zu teuer im Altbau.",
            "Wärmepumpen sind auch im Altbau günstig.",
        ),
        # Kürzere Sätze statt eines langen
        (
            "Wärmepumpen lohnen sich auch im Altbau, weil die Förderung hoch ist und "
            "die Kosten für Strom über die Jahre im Vergleich zu Gas deutlich sinken",
            "Wärmepumpen lohnen sich auch im Altbau. Die Förderung ist hoch. "
            "Strom wird über die Jahre billiger als Gas.",
        ),
    ],
)
def test_kleine_verbesserung_hebt_die_guete_sichtbar(vorher, nachher):
    echtes = GegenlesenService(
        statt_sag=lade_statt_sag_liste(), werkzeuge=Sprachwerkzeuge()
    )
    service, _ = _service(echtes)
    # Im Text, denn der Titel gilt immer als ein Satz.
    titel = "Wärmepumpen lohnen sich"
    a, b = _beitrag(title=titel, text=vorher), _beitrag(title=titel, text=nachher)
    service.ergaenzen([a, b])
    assert b.guete - a.guete >= 2
