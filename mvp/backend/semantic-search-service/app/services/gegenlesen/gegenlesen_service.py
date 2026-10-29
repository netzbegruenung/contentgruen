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
from typing import Dict, Iterable, List, Optional, Tuple

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

#: Abzug je Art von Anmerkung von der höchsten Güte 10. Verneinung und übernommene
#: Schlüsselwörter wiegen schwer, weil sie den Vorwurf wiederholen; ein kürzerer Satz
#: oder eine entfernte Verneinung hebt die Güte damit sichtbar um mindestens zwei.
GEWICHTE: Dict[str, int] = {
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
#: Adjektive auch prädikativ: "zu teuer" hat die Wortart ADV, aber den Tag ADJD.
_ADJEKTIV_TAGS = {"ADJA", "ADJD"}
#: Endungen, die das kleine Modell bei seltenen Wörtern nicht abschneidet ("Diskurse").
_ENDUNGEN = ("en", "er", "es", "n", "e", "s")
_FUGEN = ("s", "es")


@dataclass(frozen=True)
class Anmerkung:
    """Eine Beobachtung beim Gegenlesen, als Hinweis für die schreibende Person."""

    art: str
    #: "titel" oder "text": wo die Anmerkung (zuerst) zutrifft.
    stelle: str
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


class _Sprachwerkzeuge:
    """spaCy und CharSplit, einmal je Prozess geladen (zusammen rund 0,5 GB RAM)."""

    _lock = threading.Lock()
    _nlp = None
    _splitter = None

    @classmethod
    def laden(cls):
        with cls._lock:
            if cls._nlp is None:
                import spacy
                from charsplit import Splitter

                cls._nlp = spacy.load(SPACY_MODELL)
                cls._splitter = Splitter()
        return cls._nlp, cls._splitter


def sprachwerkzeuge_laden() -> None:
    """Vorab laden, damit die erste Prüfung nicht auf das Modell wartet."""
    _Sprachwerkzeuge.laden()


class GegenlesenService:
    def __init__(self, statt_sag: Dict[str, Tuple[str, List[str]]]):
        self._statt_sag = statt_sag

    def gegenlesen(self, titel: str, text: str, aussage: Optional[str]) -> Gegengelesen:
        titel, text, aussage = (
            (titel or "").strip(),
            (text or "").strip(),
            (aussage or "").strip(),
        )
        if not titel and not text:
            return Gegengelesen(guete=None, anmerkungen=[])

        nlp, self._splitter = _Sprachwerkzeuge.laden()
        titel_doc = nlp(titel) if titel else None
        text_doc = nlp(text) if text else None
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
                self._schluesselwoerter(aufhaenger, nlp(aussage) if aussage else None),
                self._satzlaenge(saetze),
                self._statt_sag_pruefen(saetze),
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
            for token in _woerter(satz)[:VERNEINUNG_IN_DEN_ERSTEN]:
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
                            f"{wo} beginnt mit „{token.text}“. Wer verneint, "
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

    def _statt_sag_pruefen(self, saetze) -> Optional[Anmerkung]:
        gefunden: List[Tuple[str, str, str]] = []
        for stelle, satz in saetze:
            for token in _woerter(satz):
                for form in self._formen(token, zerlegen=True):
                    if form in self._statt_sag and token.text not in (
                        g[1] for g in gefunden
                    ):
                        gefunden.append((stelle, token.text, form))
                        break
        if not gefunden:
            return None
        vorschlaege = []
        for _, wort, form in gefunden:
            statt, sag = self._statt_sag[form]
            vorschlaege.append(
                f"statt „{wort}“ lieber {' oder '.join(f'„{s}“' for s in sag)}"
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
                kopf = token.head
                # Tag und Merkmal zusammen: Das kleine Modell taggt auch mal einen
                # Infinitiv als VVPP ("dürfen weiterlaufen und repariert werden").
                if (
                    token.tag_ == "VVPP"
                    and "Part" in token.morph.get("VerbForm")
                    and kopf is not token
                    and kopf.lemma_ == "werden"
                    and kopf.pos_ == "AUX"
                ):
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
        gefunden: List[Tuple[str, str, str, str]] = []
        for stelle, satz in saetze:
            for token in satz:
                if token.pos_ not in ("NOUN", "PROPN") or len(token.text) < (
                    KOMPOSITUM_AB_ZEICHEN
                ):
                    continue
                # Lang ist lang, auch wenn CharSplit unsicher ist; die Zerlegung
                # dient hier nur der Erklärung.
                zerlegt = self._zerlegen(token.text, sicher=False)
                if token.text not in (g[1] for g in gefunden):
                    gefunden.append((stelle, token.text, *zerlegt))
        if not gefunden:
            return None
        teile = [
            f"„{wort}“ ({_ohne_fuge(bestimmung)} + {kopf})"
            for _, wort, bestimmung, kopf in gefunden
        ]
        return Anmerkung(
            art="kompositum",
            stelle=gefunden[0][0],
            text=(
                f"Lange Wörter: {_aufzaehlen(teile)}. "
                "Aufgelöst liest es sich leichter."
            ),
            woerter=[wort for _, wort, _, _ in gefunden],
        )

    # --- Hilfen --------------------------------------------------------------

    def _zerlegen(self, wort: str, sicher: bool = True) -> Optional[Tuple[str, str]]:
        """Bestimmungswort und Kopf; mit ``sicher`` nur, wenn CharSplit sich sicher ist."""
        if "-" in wort:
            vorne, _, hinten = wort.rpartition("-")
            return vorne, hinten
        wert, bestimmung, kopf = self._splitter.split_compound(wort)[0]
        if sicher and wert < ZERLEGUNG_AB:
            return None
        return bestimmung, kopf

    def _formen(self, token, zerlegen: bool = True) -> set:
        """Grundformen eines Worts, kleingeschrieben, samt Teilen einer Zusammensetzung."""
        formen = _grundformen(token.lemma_) | _grundformen(token.text)
        if zerlegen and token.pos_ in ("NOUN", "PROPN"):
            zerlegt = self._zerlegen(token.text)
            if zerlegt:
                for teil in zerlegt:
                    formen |= _grundformen(teil)
        return formen


def _ist_inhaltswort(token) -> bool:
    """Nomen, Namen und Adjektive: die Wörter, die einen Vorwurf tragen."""
    return token.pos_ in ("NOUN", "PROPN") or token.tag_ in _ADJEKTIV_TAGS


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
