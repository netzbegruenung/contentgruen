"""
Gegenlesen ohne KI (#358): feste, prüfbare Regeln über den Titel und den Text eines
Beitrags, bevor irgendeine KI hilft (docs/VISION.md, "Ton"; ADR 0005).

Geprüft wird mit spaCy (Lemmata, Abhängigkeiten) und CharSplit (Zerlegung
zusammengesetzter Wörter), beides lokal und deterministisch. Jede Regel ergibt höchstens
eine Anmerkung; keine sperrt das Speichern. Aus den Anmerkungen folgt der Kriterienanteil
der Güte, den das Siegel in der Vorschau zeigt.

Nichts davon wird gespeichert oder geloggt: Das Ergebnis sieht nur die schreibende Person.
"""

import math
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Tuple

import yaml

#: Das kleine deutsche Modell: Die Regeln brauchen Lemmata, Wortarten und
#: Abhängigkeiten, keine Wortvektoren. Es braucht rund die Hälfte des Speichers von
#: de_core_news_md und erkennt Verneinung und Lemmata hier genauso gut (PR zu #358).
SPACY_MODELL = "de_core_news_sm"

STATT_SAG_DATEI = Path(__file__).with_name("statt_sag.yaml")

#: Ab so vielen Wörtern gilt ein Satz als lang ("etwa 12 bis 15", docs/VISION.md).
SATZ_MAX_WOERTER = 15

#: Die Verneinung zählt, wenn sie unter den ersten so vielen Wörtern steht.
VERNEINUNG_IN_DEN_ERSTEN = 3

#: Mindestens so viele Schlüsselwörter der Aussage müssen im Aufhänger wiederkehren,
#: und mindestens dieser Anteil von ihnen: Ein gemeinsames Thema ("Wärmepumpe",
#: "Windräder" und "Strom") ist keine Übernahme des Vorwurfs, alle oder fast alle
#: Schlüsselwörter sind es ("Die Grünen sind eine Verbotspartei").
SCHLUESSELWOERTER_AB = 2
SCHLUESSELWOERTER_ANTEIL = 0.75

#: Ab dieser Länge ist ein zusammengesetztes Wort lang (Gebäudeenergiegesetz: 20).
KOMPOSITUM_AB_ZEICHEN = 18

#: Unter diesem Wert ist CharSplit sich der Zerlegung nicht sicher ("Gesetz" -> "Ges|etz").
ZERLEGUNG_AB = 0.6

#: Ab diesem Wert zeigt die Anmerkung die Zerlegung als Erklärung. Bei dreiteiligen
#: Wörtern liegt auch eine richtige Zerlegung unter ZERLEGUNG_AB ("Gebäude +
#: Energiegesetz" -0,50, "Mietpreis + Bremse" -0,57), falsche liegen tiefer
#: ("Verantwortungs + Losigkeit" -0,86, "Unverhältnis + Mäßigkeit" -1,22).
ERKLAEREN_AB = -0.7

#: Abzug je Art von Anmerkung von der höchsten Güte 10. Verneinung und übernommene
#: Schlüsselwörter wiegen schwer, weil sie den Vorwurf wiederholen; ein kürzerer Satz
#: oder eine entfernte Verneinung hebt die Güte damit sichtbar um mindestens zwei.
#: Die Arten von Anmerkungen, je eine Regel; das Frontend kennt dieselben
#: (gegenlesen.service.ts).
Art = Literal[
    "verneinung", "schluesselwoerter", "satzlaenge", "statt_sag", "passiv", "kompositum"
]
#: Wo eine Anmerkung (zuerst) zutrifft.
Stelle = Literal["titel", "text"]

GEWICHTE: Dict[Art, int] = {
    "verneinung": 3,
    "schluesselwoerter": 2,
    "satzlaenge": 2,
    "statt_sag": 1,
    "passiv": 1,
    "kompositum": 1,
}
GUETE_MAX = 10
GUETE_MIN = 1

_VERNEINUNGSWOERTER = {
    "kein",
    "keiner",
    "nie",
    "niemals",
    "nichts",
    "niemand",
    "nirgends",
    "keinesfalls",
    "nein",
}
#: Feste Wendungen, die nur so aussehen wie eine Verneinung.
_KEINE_VERNEINUNG = {("nicht", "nur"), ("kein", "wunder")}
_NOMEN = ("NOUN", "PROPN")
#: Adjektive auch prädikativ: "zu teuer" hat die Wortart ADV, aber den Tag ADJD.
_ADJEKTIV_TAGS = {"ADJA", "ADJD"}
#: Endungen, die das kleine Modell bei seltenen Wörtern nicht abschneidet ("Diskurse").
_ENDUNGEN = ("en", "er", "es", "n", "e", "s")
_FUGEN = ("s", "es")
#: Ein Listenwort am Anfang oder Ende eines längeren Worts zählt als Teil einer
#: Zusammensetzung, auch wenn CharSplit unsicher ist ("Narrativwechsel"), sofern der
#: Rest mindestens so lang ist.
_REST_AB_ZEICHEN = 3


@dataclass(frozen=True)
class Anmerkung:
    """Was das Gegenlesen an einem Beitrag findet, je Regel höchstens eine (GLOSSARY.md)."""

    art: Art
    stelle: Stelle
    text: str
    #: Die betroffenen Wörter, so wie sie im Beitrag stehen.
    woerter: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Gegengelesen:
    #: Kriterienanteil der Güte, 1–10; None, solange Titel und Text leer sind ("neu").
    guete: Optional[int]
    anmerkungen: List[Anmerkung]


def lade_statt_sag_liste(
    datei: Path = STATT_SAG_DATEI,
) -> Dict[str, Tuple[str, List[str]]]:
    """Die Liste "statt X sag Y": Grundform klein -> (Grundform, Vorschläge)."""
    eintraege = yaml.safe_load(datei.read_text(encoding="utf-8")) or []
    return {
        str(e["statt"]).lower(): (str(e["statt"]), [str(s) for s in e["sag"]])
        for e in eintraege
    }


class Sprachwerkzeuge:
    """
    spaCy und CharSplit, beim ersten Gebrauch geladen (zusammen rund 0,5 GB RAM).

    Die Anfragen laufen im Threadpool. spaCy sagt nicht zu, dass dieselbe Pipeline
    gleichzeitig aus mehreren Threads rechnen darf; ``analysieren`` reiht die Aufrufe
    deshalb hintereinander. Bei wenigen Millisekunden je Beitrag kostet das nichts.
    """

    def __init__(self, modell: str = SPACY_MODELL):
        self._modell = modell
        self._lock = threading.Lock()
        self._nlp_lock = threading.Lock()
        self._nlp = None
        self._splitter = None

    def laden(self) -> None:
        """Vorab laden, damit das erste Gegenlesen nicht auf das Modell wartet."""
        with self._lock:
            if self._nlp is None:
                import spacy
                from charsplit import Splitter

                self._nlp = spacy.load(self._modell)
                self._splitter = Splitter()

    def analysieren(self, text: str):
        self.laden()
        with self._nlp_lock:
            return self._nlp(text)

    def zerlegen(self, wort: str) -> Tuple[float, str, str]:
        """Beste Zerlegung in Bestimmungswort und Kopf, mit CharSplits Sicherheit."""
        if "-" in wort:
            vorne, _, hinten = wort.rpartition("-")
            return 1.0, vorne, hinten
        self.laden()
        wert, bestimmung, kopf = self._splitter.split_compound(wort)[0]
        return wert, bestimmung, kopf


#: Eine Instanz je Prozess: Der Dienst nutzt sie, der Start lädt sie vor (main.py).
SPRACHWERKZEUGE = Sprachwerkzeuge()


class GegenlesenService:
    def __init__(
        self,
        statt_sag: Dict[str, Tuple[str, List[str]]],
        werkzeuge: Sprachwerkzeuge,
    ):
        self._statt_sag = statt_sag
        self._werkzeuge = werkzeuge

    def gegenlesen(self, titel: str, text: str, aussage: Optional[str]) -> Gegengelesen:
        titel, text, aussage = (
            (titel or "").strip(),
            (text or "").strip(),
            (aussage or "").strip(),
        )
        if not titel and not text:
            return Gegengelesen(guete=None, anmerkungen=[])

        analysieren = self._werkzeuge.analysieren
        titel_doc = analysieren(titel) if titel else None
        text_doc = analysieren(text) if text else None
        # Der Titel ist ein Satz, auch ohne Punkt; im Text zählt jeder Satz für sich.
        saetze: List[Tuple[str, list]] = []
        if titel_doc is not None:
            saetze.append(("titel", list(titel_doc)))
        if text_doc is not None:
            saetze.extend(("text", list(s)) for s in text_doc.sents)
        # Der Aufhänger: der Titel und der erste Satz des Texts.
        aufhaenger = [s for s in saetze if s[0] == "titel"][:1] + [
            s for s in saetze if s[0] == "text"
        ][:1]

        anmerkungen = [
            a
            for a in (
                self._verneinung(aufhaenger),
                self._schluesselwoerter(
                    aufhaenger, analysieren(aussage) if aussage else None
                ),
                self._satzlaenge(saetze),
                self._statt_sag_finden(saetze),
                self._passiv(saetze),
                self._komposita(saetze),
            )
            if a is not None
        ]
        abzug = sum(GEWICHTE[a.art] for a in anmerkungen)
        return Gegengelesen(
            guete=max(GUETE_MIN, GUETE_MAX - abzug), anmerkungen=anmerkungen
        )

    # --- Regeln --------------------------------------------------------------

    def _verneinung(self, aufhaenger) -> Optional[Anmerkung]:
        for stelle, satz in aufhaenger:
            woerter = _woerter(satz)
            for i, token in enumerate(woerter[:VERNEINUNG_IN_DEN_ERSTEN]):
                folgt = woerter[i + 1].lower_ if i + 1 < len(woerter) else ""
                if (token.lower_, folgt) in _KEINE_VERNEINUNG:
                    continue
                if (
                    token.dep_ == "ng"
                    or token.tag_ == "PTKNEG"
                    or token.lemma_.lower() in _VERNEINUNGSWOERTER
                    or token.lower_ in _VERNEINUNGSWOERTER
                ):
                    wo = "Der Titel" if stelle == "titel" else "Der erste Satz"
                    return Anmerkung(
                        art="verneinung",
                        stelle=stelle,
                        text=(
                            f"{wo} verneint gleich am Anfang („{token.text}“). Wer verneint, "
                            "wiederholt das Bild der anderen. Sag lieber, was stimmt."
                        ),
                        woerter=[token.text],
                    )
        return None

    def _schluesselwoerter(self, aufhaenger, aussage_doc) -> Optional[Anmerkung]:
        if aussage_doc is None:
            return None
        schluessel = [self._formen(t) for t in aussage_doc if _ist_inhaltswort(t)]
        if not schluessel:
            return None
        getroffen = set()
        woerter: List[str] = []
        stelle = None
        for satz_stelle, satz in aufhaenger:
            for token in satz:
                if not _ist_inhaltswort(token):
                    continue
                formen = self._formen(token)
                treffer = [i for i, s in enumerate(schluessel) if s & formen]
                if treffer:
                    getroffen.update(treffer)
                    stelle = stelle or satz_stelle
                    if token.text not in woerter:
                        woerter.append(token.text)
        if len(getroffen) < max(
            SCHLUESSELWOERTER_AB, math.ceil(SCHLUESSELWOERTER_ANTEIL * len(schluessel))
        ):
            return None
        return Anmerkung(
            art="schluesselwoerter",
            stelle=stelle,
            text=(
                f"Übernimmt Wörter der Aussage: {_aufzaehlen(woerter)}. "
                "So bleibt der Vorwurf hängen. Setz lieber eigene Begriffe."
            ),
            woerter=woerter,
        )

    def _satzlaenge(self, saetze) -> Optional[Anmerkung]:
        lange = [(stelle, len(_woerter(s))) for stelle, s in saetze]
        lange = [(stelle, n) for stelle, n in lange if n > SATZ_MAX_WOERTER]
        if not lange:
            return None
        laengster = max(n for _, n in lange)
        anfang = (
            f"Ein Satz hat {laengster} Wörter."
            if len(lange) == 1
            else f"{len(lange)} Sätze sind länger als {SATZ_MAX_WOERTER} Wörter, "
            f"der längste hat {laengster} Wörter."
        )
        return Anmerkung(
            art="satzlaenge",
            stelle=lange[0][0],
            text=f"{anfang} Kürzer liest es sich leichter, am besten bis {SATZ_MAX_WOERTER}.",
        )

    def _statt_sag_finden(self, saetze) -> Optional[Anmerkung]:
        gefunden: List[Tuple[str, str, str]] = []
        for stelle, satz in saetze:
            for token in _woerter(satz):
                form = self._listenwort(token)
                if form is not None and token.text not in (g[1] for g in gefunden):
                    gefunden.append((stelle, token.text, form))
        if not gefunden:
            return None
        vorschlaege = []
        for _, wort, form in gefunden:
            statt, sag = self._statt_sag[form]
            # In einer Zusammensetzung das Listenwort nennen: "statt „Transformation“
            # (in „Transformationsprozess“)", nicht das ganze Wort ersetzen.
            worin = "" if _grundformen(wort) & {form} else f" (in „{wort}“)"
            vorschlaege.append(
                f"statt „{statt}“{worin} lieber {' oder '.join(f'„{s}“' for s in sag)}"
            )
        return Anmerkung(
            art="statt_sag",
            stelle=gefunden[0][0],
            text=f"Fachwörter schrecken ab: {'; '.join(vorschlaege)}.",
            woerter=[wort for _, wort, _ in gefunden],
        )

    def _passiv(self, saetze) -> Optional[Anmerkung]:
        gefunden: List[Tuple[str, str]] = []
        for stelle, satz in saetze:
            for token in satz:
                # Tag und Merkmal zusammen: Das kleine Modell taggt auch mal einen
                # Infinitiv als VVPP ("dürfen weiterlaufen und repariert werden").
                if token.tag_ != "VVPP" or "Part" not in token.morph.get("VerbForm"):
                    continue
                # In einer Reihung ("geprüft und beschlossen") hängt nur das erste
                # Glied an "werden".
                kopf = _erstes_glied(token).head
                if kopf.lemma_ == "werden" and kopf.pos_ == "AUX":
                    vorne, hinten = sorted((kopf, token), key=lambda t: t.i)
                    gefunden.append((stelle, f"{vorne.text} {hinten.text}"))
        if not gefunden:
            return None
        woerter = [w for _, w in gefunden]
        return Anmerkung(
            art="passiv",
            stelle=gefunden[0][0],
            text=(
                f"Passiv: {_aufzaehlen(woerter)}. Sag, wer handelt: "
                "„Die Regierung beschließt …“ statt „… wird beschlossen“."
            ),
            woerter=woerter,
        )

    def _komposita(self, saetze) -> Optional[Anmerkung]:
        gefunden: List[Tuple[str, str, str]] = []
        for stelle, satz in saetze:
            for token in satz:
                if token.pos_ not in _NOMEN or len(token.text) < (
                    KOMPOSITUM_AB_ZEICHEN
                ):
                    continue
                # Lang ist lang, auch wenn CharSplit unsicher ist; die Zerlegung
                # dient hier nur der Erklärung.
                if token.text not in (g[1] for g in gefunden):
                    gefunden.append((stelle, token.text, self._erklaeren(token.text)))
        if not gefunden:
            return None
        teile = [f"„{wort}“{erklaerung}" for _, wort, erklaerung in gefunden]
        return Anmerkung(
            art="kompositum",
            stelle=gefunden[0][0],
            text=(
                f"Lange Wörter: {_aufzaehlen(teile)}. "
                "Aufgelöst liest es sich leichter."
            ),
            woerter=[wort for _, wort, _ in gefunden],
        )

    # --- Hilfen --------------------------------------------------------------

    def _erklaeren(self, wort: str) -> str:
        """Die Zerlegung als Klammer, nur wenn CharSplit sich einigermaßen sicher ist."""
        wert, bestimmung, kopf = self._werkzeuge.zerlegen(wort)
        if wert < ERKLAEREN_AB:
            return ""
        return f" ({_ohne_fuge(bestimmung)} + {kopf})"

    def _listenwort(self, token) -> Optional[str]:
        """Das Wort der Liste "statt X sag Y", das im Wort steckt, sonst None."""
        for form in self._formen(token):
            if form in self._statt_sag:
                return form
        # Vorne oder hinten in einer Zusammensetzung, auch wenn CharSplit unsicher ist.
        wort = token.text.lower()
        for statt in self._statt_sag:
            if len(wort) - len(statt) >= _REST_AB_ZEICHEN and (
                wort.startswith(statt) or wort.endswith(statt)
            ):
                return statt
        return None

    def _formen(self, token) -> set:
        """Grundformen eines Worts, kleingeschrieben, samt Teilen einer Zusammensetzung."""
        formen = _grundformen(token.lemma_) | _grundformen(token.text)
        if token.pos_ in _NOMEN:
            wert, bestimmung, kopf = self._werkzeuge.zerlegen(token.text)
            if wert >= ZERLEGUNG_AB:
                formen |= _grundformen(bestimmung) | _grundformen(kopf)
        return formen


def _ist_inhaltswort(token) -> bool:
    """Nomen, Namen und Adjektive: die Wörter, die einen Vorwurf tragen."""
    return token.pos_ in _NOMEN or token.tag_ in _ADJEKTIV_TAGS


def _erstes_glied(token):
    """In einer Reihung das erste Glied, an dem der gemeinsame Kopf hängt."""
    while token.dep_ == "cj" and token.head.dep_ == "cd":
        token = token.head.head
    return token


def _woerter(satz) -> list:
    return [t for t in satz if not (t.is_punct or t.is_space)]


def _grundformen(wort: str) -> set:
    wort = wort.lower()
    formen = {wort}
    for endung in _ENDUNGEN:
        if wort.endswith(endung) and len(wort) - len(endung) >= 4:
            formen.add(wort[: -len(endung)])
    return formen


def _ohne_fuge(bestimmung: str) -> str:
    for fuge in _FUGEN:
        if bestimmung.lower().endswith(fuge) and len(bestimmung) - len(fuge) >= 4:
            return bestimmung[: -len(fuge)]
    return bestimmung


def _aufzaehlen(teile: Iterable[str]) -> str:
    teile = list(teile)
    if len(teile) <= 1:
        return "".join(teile)
    return ", ".join(teile[:-1]) + " und " + teile[-1]
