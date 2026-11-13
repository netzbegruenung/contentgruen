"""
Meilensteine (GLOSSARY.md "Meilenstein" und "Wegmarke", docs/VISION.md "Motivation",
ADR 0004, #351).

Drei Arten:
- Wirkung: eine erreichte Schwelle bei der Wirkung der eigenen Beitraege (erste
  Nutzung durch andere, 10, 50 und 100 Nutzungen, erste Zustimmung).
- Unterstuetzung: Arbeit, die selbst keine Nutzung erzeugt (ADR 0004, "Drei Stufen"):
  fremde Einwuerfe ausformuliert, eigene Einwuerfe, die andere ausformuliert haben.
- Weg: eine Wegmarke, das eigene Tun (erster Einwurf, erster Beitrag, der drei Tage
  steht, erster Kommentar zu einer Aussage). Wegmarken sieht nur die Person selbst;
  sie zaehlen nicht fuer das Abzeichen am Namen und nicht fuer die Krone, damit die
  Zahl dort weiter Anerkennung durch andere zeigt (docs/DSFA.md V22).

Jeder Meilenstein hat einen sprechenden Namen (wofuer es ihn gibt), einen Untertitel
mit einer Redewendung und eine Beschreibung; das Bild ist ein Motiv aus Fluent Emoji
unter public/meilensteine/ (scripts/meilensteine_holen.py im Frontend). Bild und
Bildnachweis stehen je Meilenstein: Ein eigenes Bild (etwa aus einer spaeteren
Kooperation mit einer Kuenstlerin) ersetzt das Motiv eines einzelnen Meilensteins,
mit eigenem Nachweis, eigener Lizenzdatei daneben und Eintrag in COPYRIGHT. Die Kennungen
bleiben, auch wenn sich ein Name aendert: Der Browser merkt sich an ihnen, welche
Meilensteine schon gezeigt wurden.

Hier steht nur die Rechnung. Woher die Zahlen kommen (entdoppelte Nutzung, Stimmen
ohne eigene und ohne Startkonten), entscheidet services/meilensteine_service.py.
Die Schwellen sind Teil der Produktentscheidung in docs/VISION.md, keine
Stellschrauben wie die Punktegewichte; deshalb stehen sie hier und nicht in der
Konfiguration.
"""

from dataclasses import dataclass
from typing import List, Tuple

WIRKUNG = "wirkung"
UNTERSTUETZUNG = "unterstuetzung"
WEG = "weg"

# Was fuer das Abzeichen am Namen und die Krone zaehlt (services/abzeichen_service.py).
ARTEN_FUERS_ABZEICHEN = frozenset({WIRKUNG, UNTERSTUETZUNG})

# Nachweis der Fluent-Motive (public/meilensteine/FLUENT-EMOJI-LIZENZ.txt).
FLUENT_EMOJI = "Motiv: Fluent Emoji, © Microsoft Corporation, MIT-Lizenz"


@dataclass(frozen=True)
class Meilensteindaten:
    """Was zu Meilensteinen zaehlt, schon gefiltert und gezaehlt."""

    nutzungen: int = 0
    zustimmungen: int = 0
    einwuerfe_ausformuliert: int = 0
    eigene_einwuerfe_von_anderen_ausformuliert: int = 0
    # Wegmarken: eigene, nicht verworfene Einwuerfe; sichtbare Beitraege, die die
    # Wartezeit der Punkte hinter sich haben; sichtbare Kommentare, auf die eine
    # sichtbare Aussage als Antwort verweist.
    einwuerfe: int = 0
    beitraege_gehalten: int = 0
    kommentare_zu_aussagen: int = 0


@dataclass(frozen=True)
class Meilensteinart:
    """Ein Meilenstein ohne Stand: was er heisst, wie er aussieht, wann er erreicht ist."""

    kennung: str
    name: str
    untertitel: str
    beschreibung: str
    bild: str
    art: str
    feld: str
    schwelle: int
    # Wer das Bild gemacht hat und unter welcher Lizenz; gezeigt am Medaillon.
    bildnachweis: str = FLUENT_EMOJI


@dataclass(frozen=True)
class Meilenstein:
    kennung: str
    name: str
    untertitel: str
    beschreibung: str
    bild: str
    art: str
    schwelle: int
    stand: int
    bildnachweis: str = FLUENT_EMOJI

    @property
    def erreicht(self) -> bool:
        return self.stand >= self.schwelle

    @property
    def zaehlt_fuers_abzeichen(self) -> bool:
        return self.art in ARTEN_FUERS_ABZEICHEN


def _bild(datei: str) -> str:
    return f"meilensteine/{datei}"


# In der Reihenfolge der Anzeige: erst die Wegmarken und ersten Schritte, dann die
# Wirkung, zuletzt die grossen Zahlen der Unterstuetzungsarbeit.
MEILENSTEINE: Tuple[Meilensteinart, ...] = (
    Meilensteinart(
        kennung="einwurf-1",
        name="Erster Einwurf",
        untertitel="Fundstück",
        beschreibung=(
            "Dein erster Einwurf liegt im Fangkorb. Was daraus wird, weiß noch "
            "niemand, aber gefunden ist gefunden."
        ),
        bild=_bild("korb.svg"),
        art=WEG,
        feld="einwuerfe",
        schwelle=1,
    ),
    Meilensteinart(
        kennung="beitrag-gehalten-1",
        name="Erster Beitrag hält",
        untertitel="Gut Ding will Weile haben",
        beschreibung=(
            "Dein erster Beitrag steht seit drei Tagen, und niemand musste ihn "
            "sperren. Klingt nach wenig, ist fürs Internet aber eine Leistung."
        ),
        bild=_bild("sanduhr.svg"),
        art=WEG,
        feld="beitraege_gehalten",
        schwelle=1,
    ),
    Meilensteinart(
        kennung="aussage-kommentiert-1",
        name="Erste Gegenrede",
        untertitel="„Nein!“",
        beschreibung=(
            "Irgendwo wurde etwas behauptet, und du hast nicht nur den Kopf "
            "geschüttelt, sondern aufgeschrieben, warum. Dein Nacken dankt es dir."
        ),
        bild=_bild("sprechblase.svg"),
        art=WEG,
        feld="kommentare_zu_aussagen",
        schwelle=1,
    ),
    Meilensteinart(
        kennung="ausformuliert-1",
        name="Erster fremder Einwurf ausformuliert",
        untertitel="Butter bei die Fische",
        beschreibung=(
            "Jemand anderes hat etwas gefunden, du hast es aufgeschrieben. "
            "Arbeitsteilung, bei der du den Teil mit den Kommas übernommen hast."
        ),
        bild=_bild("butter.svg"),
        art=UNTERSTUETZUNG,
        feld="einwuerfe_ausformuliert",
        schwelle=1,
    ),
    Meilensteinart(
        kennung="nutzung-1",
        name="Erstmals genutzt",
        untertitel="Ausgeflogen",
        beschreibung=(
            "Jemand hat deinen Beitrag mitgenommen. Wohin, verraten wir nicht, "
            "weil wir es selbst nicht wissen."
        ),
        bild=_bild("vogel.svg"),
        art=WIRKUNG,
        feld="nutzungen",
        schwelle=1,
    ),
    Meilensteinart(
        kennung="nutzung-10",
        name="10-mal genutzt",
        untertitel="Hat sich rumgesprochen",
        beschreibung=(
            "Deine Worte sind jetzt an Orten unterwegs, an denen du nie warst. "
            "Postkarten schreiben sie keine."
        ),
        bild=_bild("lautsprecher.svg"),
        art=WIRKUNG,
        feld="nutzungen",
        schwelle=10,
    ),
    Meilensteinart(
        kennung="nutzung-50",
        name="50-mal genutzt",
        untertitel="Selbstläufer",
        beschreibung=(
            "Deine Beiträge kommen inzwischen ohne dich zurecht. Nimm es nicht "
            "persönlich, so ist das mit dem Erwachsenwerden."
        ),
        bild=_bild("laufschuh.svg"),
        art=WIRKUNG,
        feld="nutzungen",
        schwelle=50,
    ),
    Meilensteinart(
        kennung="nutzung-100",
        name="100-mal genutzt",
        untertitel="Dreistellig",
        beschreibung=(
            "Hundert Nutzungen. Wir zählen ab hier weiter, feierlicher wird es "
            "allerdings nicht."
        ),
        bild=_bild("hundert.svg"),
        art=WIRKUNG,
        feld="nutzungen",
        schwelle=100,
    ),
    Meilensteinart(
        kennung="zustimmung-1",
        name="Erste Zustimmung",
        untertitel="Nicht allein",
        beschreibung=(
            "Ein Mensch stimmt dir zu. Statistisch noch keine Bewegung, aber "
            "Bewegungen fangen selten größer an."
        ),
        bild=_bild("handschlag.svg"),
        art=WIRKUNG,
        feld="zustimmungen",
        schwelle=1,
    ),
    Meilensteinart(
        kennung="ausformuliert-10",
        name="10 fremde Einwürfe ausformuliert",
        untertitel="Schreibstube",
        beschreibung=(
            "Zehnmal hast du aus fremden Fundstücken einen Beitrag gemacht. "
            "Andere nennen das Ghostwriting, wir nennen es Mannschaftssport."
        ),
        bild=_bild("fueller.svg"),
        art=UNTERSTUETZUNG,
        feld="einwuerfe_ausformuliert",
        schwelle=10,
    ),
    Meilensteinart(
        kennung="eingeworfen-10",
        name="10 deiner Einwürfe aufgegriffen",
        untertitel="Gute Nase",
        beschreibung=(
            "Zehn deiner Funde haben andere ausformuliert. Du riechst offenbar, wo "
            "eine Antwort fehlt, und musst sie nicht einmal selbst schreiben."
        ),
        bild=_bild("nase.svg"),
        art=UNTERSTUETZUNG,
        feld="eigene_einwuerfe_von_anderen_ausformuliert",
        schwelle=10,
    ),
)


def meilensteine_berechnen(daten: Meilensteindaten) -> List[Meilenstein]:
    """Alle Meilensteine mit Stand; ``erreicht`` sagt, welche schon geschafft sind."""
    return [
        Meilenstein(
            kennung=m.kennung,
            name=m.name,
            untertitel=m.untertitel,
            beschreibung=m.beschreibung,
            bild=m.bild,
            art=m.art,
            schwelle=m.schwelle,
            stand=getattr(daten, m.feld),
            bildnachweis=m.bildnachweis,
        )
        for m in MEILENSTEINE
    ]
