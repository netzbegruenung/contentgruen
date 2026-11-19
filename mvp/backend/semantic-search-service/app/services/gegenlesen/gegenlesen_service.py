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
import re
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
PARTEISTIMME_DATEI = Path(__file__).with_name("parteistimme.yaml")

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

#: Zahlen ohne Herkunft: Ziffern bis zu dieser Zahl ohne Einheit sind eine kleine
#: Aufzählung ("3 Gründe", "1.") und zählen nicht.
AUFZAEHLUNG_BIS = 12
#: Eine Jahreszahl allein ("seit 2020", "bis 2035") ist keine Zahl, die eine Herkunft
#: braucht.
JAHRESZAHLEN = range(1900, 2100)
#: So viele Zahlen nennt die Anmerkung, danach "und weitere".
ZAHLEN_NENNEN = 3

#: Die Arten von Anmerkungen, je eine Regel; das Frontend kennt dieselben
#: (gegenlesen.service.ts, siegel-erklaerung.ts).
Art = Literal[
    "verneinung",
    "schluesselwoerter",
    "satzlaenge",
    "statt_sag",
    "passiv",
    "kompositum",
    "gedankenstrich",
    "parteistimme",
    "titel_frage",
    "zahl_ohne_herkunft",
]
#: Wo eine Anmerkung (zuerst) zutrifft.
Stelle = Literal["titel", "text"]

#: Abzug je Art von Anmerkung von der höchsten Güte 10. Verneinung und übernommene
#: Schlüsselwörter wiegen schwer, weil sie den Vorwurf wiederholen; ein kürzerer Satz
#: oder eine entfernte Verneinung hebt die Güte damit sichtbar um mindestens zwei.
#: Die Parteistimme wiegt wie die Schlüsselwörter: Sie verfehlt den Kern des Tons
#: (die Nachbarin spricht, nicht die Partei), und wer sie umschreibt, sieht das am
#: Siegel. Die übrigen sind Feinschliff und ziehen einen Punkt ab.
GEWICHTE: Dict[Art, int] = {
    "verneinung": 3,
    "schluesselwoerter": 2,
    "satzlaenge": 2,
    "parteistimme": 2,
    "statt_sag": 1,
    "passiv": 1,
    "kompositum": 1,
    "gedankenstrich": 1,
    "titel_frage": 1,
    "zahl_ohne_herkunft": 1,
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

#: Gedankenstrich: Halbgeviert- oder Geviertstrich mit Leerzeichen davor und danach
#: ("so – oder so"), am Zeilenanfang nicht (Aufzählung), und der Geviertstrich auch
#: ohne Leerzeichen ("so—oder so"). Bindestriche ("Klima-Schutz") sind andere Zeichen.
_GEDANKENSTRICH = re.compile(r"(?<=\S[^\S\n])[–—](?=\s)|(?<=\w)—(?=\w)")
#: Was nach einem Fragezeichen am Ende eines Titels noch stehen darf (wie ist_frage in
#: services/dieselbe_behauptung/regel.py, ohne dessen Fragewörter am Anfang), dazu
#: Ausrufezeichen und Auslassung ("Echt?!", "Und dann?…").
_TITEL_SCHLUSS = " \t\r\n\"'„“”‚‘’«»)!…"
#: Anführungszeichen: Darin zitiert der Beitrag, statt selbst zu sprechen.
_ZITAT = re.compile(
    r"„[^“”\n]*[“”]|\"[^\"\n]*\"|»[^«\n]*«|«[^»\n]*»|‚[^‘’\n]*[‘’]|“[^”\n]*”"
)
_VERNEINT = {"kein", "nicht", "nie", "niemals", "niemand", "niemandem"}
#: Größenwörter: nach einer Ziffer eine Einheit ("3 Prozent"), nach einem Zahlwort
#: selbst eine Zahl ("zehn Prozent").
_GROESSENWOERTER = r"Prozent|Million(?:en)?|Milliarden?|Mio\.?|Mrd\.?"
#: Zahlwörter vor einem Größenwort ("zehn Prozent", "drei Millionen").
_ZAHLWOERTER = (
    r"ein|eine|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf|halbe"
    r"|\w+zehn|\w+zig|\w+ßig|\w*hundert|\w*tausend"
)
#: Einheiten, mit denen auch eine kleine Ziffer eine Zahl ist ("3 Prozent", "5 €").
_EINHEIT = re.compile(
    rf"\s?(?:%|€|Euro\b|Cent\b|(?:{_GROESSENWOERTER})(?!\w))", re.IGNORECASE
)
_ZIFFERN = re.compile(r"(?<![\w,.])\d[\d.,]*(?<![.,])(?!\w)")
_GROESSENWORT = re.compile(
    rf"\b(?P<zahlwort>(?:{_ZAHLWOERTER})\s+)(?:{_GROESSENWOERTER})(?!\w)",
    re.IGNORECASE,
)
#: Ziffern, die keine Zahl mit Herkunft sind: Links, Uhrzeit, Datum, Paragraf, "Tempo 30",
#: Ziffern vor einem Bindestrich-Wort ("1,5-Grad-Ziel", "49-Euro-Ticket") und der Name
#: "Bündnis 90", auch am Satzanfang (dort greift _ist_name nicht).
_KEINE_ZAHL = re.compile(
    r"(?:https?://|www\.)\S+"
    r"|\b\d{1,2}:\d{2}\b"
    r"|\b\d{1,2}\s*Uhr\b"
    r"|\b\d{1,2}\.\d{1,2}\.(?:\d{2,4}\b)?"
    r"|§+\s*\d+\w*"
    r"|\bTempo\s*\d+"
    r"|\d[\d.,]*-(?=\w)"
    r"|Bündnis\s*90",
    re.IGNORECASE,
)
#: Eine Ordinalzahl mit Punkt ("24. Oktober", "20. Jahrhundert", "am 3. und 4. Mai").
_ORDINALZAHL = re.compile(r"\b(\d{1,4})\.(?=\s*[„\"'(]*(\w+))")
#: Nach "<Zahl>." machen diese Wörter die Zahl zur Ordinalzahl, wie NACH_ORDINALZAHL
#: in titel-vorschlag.ts; dazu jedes klein geschriebene Wort.
_NACH_ORDINALZAHL = {
    "januar", "jänner", "februar", "märz", "april", "mai", "juni", "juli", "august",
    "september", "oktober", "november", "dezember", "jahrhundert", "jahrtausend",
}  # fmt: skip
#: Das Wort direkt vor einer Ziffer, und was davor steht (für _ist_name).
_WORT_DAVOR = re.compile(r"(\S?)\s*(\w+)\s+$")
#: Ein großgeschriebenes Wort direkt nach einer Ziffer: Dann zählt sie etwas
#: ("5000 Bäume"), statt einen Namen zu tragen.
_WORT_DANACH = re.compile(r"\s+(\w)")


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


@dataclass(frozen=True)
class Parteistimme:
    """Die Liste parteistimme.yaml: Subjekt mit Verb, und feste Folgen von Grundformen."""

    #: (Grundformen des Subjekts, Grundformen der Verben)
    wer_tut: List[Tuple[frozenset, frozenset]] = field(default_factory=list)
    folgen: List[Tuple[str, ...]] = field(default_factory=list)


def lade_parteistimme(datei: Path = PARTEISTIMME_DATEI) -> Parteistimme:
    eintraege = yaml.safe_load(datei.read_text(encoding="utf-8")) or []

    def klein(woerter) -> List[str]:
        return [str(w).lower() for w in woerter]

    return Parteistimme(
        wer_tut=[
            (frozenset(klein(e["wer"])), frozenset(klein(e["tut"])))
            for e in eintraege
            if "wer" in e
        ],
        folgen=[tuple(klein(e["folge"])) for e in eintraege if "folge" in e],
    )


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

    @property
    def geladen(self) -> bool:
        """Ob spaCy schon geladen ist; die Suche (Inhaltstor) wartet nicht darauf."""
        return self._nlp is not None

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
        parteistimme: Optional[Parteistimme] = None,
    ):
        self._statt_sag = statt_sag
        self._werkzeuge = werkzeuge
        self._parteistimme = (
            parteistimme if parteistimme is not None else lade_parteistimme()
        )

    def gegenlesen(
        self,
        titel: str,
        text: str,
        aussage: Optional[str],
        titel_ist_behauptung: bool = True,
        hat_herkunft: Optional[bool] = None,
    ) -> Gegengelesen:
        # Ein Post-Titel beschreibt, statt zu behaupten: dort keine Verneinungsregel
        # und keine Regel zum Titel als Frage. ``hat_herkunft`` ist None, wenn das
        # Formular kein Herkunftsfeld hat (Post, Bild) oder die Karte gegenliest: Dann
        # entfällt die Regel zu Zahlen ohne Herkunft.
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
                self._verneinung(aufhaenger) if titel_ist_behauptung else None,
                self._schluesselwoerter(
                    aufhaenger, analysieren(aussage) if aussage else None
                ),
                self._satzlaenge(saetze),
                self._statt_sag_finden(saetze),
                self._passiv(saetze),
                self._komposita(saetze),
                self._gedankenstrich(titel, text),
                self._parteistimme_finden(saetze),
                self._titel_frage(titel) if titel_ist_behauptung else None,
                (
                    self._zahl_ohne_herkunft(titel, text)
                    if hat_herkunft is False
                    else None
                ),
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
                f"Passiv: {_aufzaehlen(woerter)}. Sag, wer handelt, "
                "dann liest es sich klarer."
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
                # Mit Bindestrich ist ein Wort schon gegliedert ("Klima-Schutz-Gesetz",
                # #618); jeder Teil zählt dann für sich.
                if "-" in token.text and all(
                    len(teil) < KOMPOSITUM_AB_ZEICHEN for teil in token.text.split("-")
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

    def _gedankenstrich(self, titel: str, text: str) -> Optional[Anmerkung]:
        for stelle, inhalt in (("titel", titel), ("text", text)):
            # Ein Zahlenbereich mit Leerzeichen ("3 – 5") ist kein Gedankenstrich.
            striche = [
                m.group()
                for m in _GEDANKENSTRICH.finditer(inhalt)
                if not _zwischen_ziffern(inhalt, m.start())
            ]
            if striche:
                return Anmerkung(
                    art="gedankenstrich",
                    stelle=stelle,
                    text=(
                        f"Gedankenstrich („{striche[0]}“): Das liest sich wie ein "
                        "Einschub. Ein Punkt macht es klarer."
                    ),
                    woerter=sorted(set(striche)),
                )
        return None

    def _parteistimme_finden(self, saetze) -> Optional[Anmerkung]:
        gefunden: List[Tuple[str, str]] = []
        for stelle, satz in saetze:
            for wendung in self._wendungen(satz):
                if wendung not in (w for _, w in gefunden):
                    gefunden.append((stelle, wendung))
        if not gefunden:
            return None
        woerter = [w for _, w in gefunden]
        return Anmerkung(
            art="parteistimme",
            stelle=gefunden[0][0],
            text=(
                f"Klingt nach Partei: {_aufzaehlen(f'„{w}“' for w in woerter)}. "
                "Erzähl es lieber so, wie du es deiner Nachbarin sagen würdest."
            ),
            woerter=woerter,
        )

    def _titel_frage(self, titel: str) -> Optional[Anmerkung]:
        # Nur das Fragezeichen am Ende. Ein Verb vorn ist hier keine Frage ("Helfen
        # statt meckern", "Braucht keiner: die Ölheizung"), anders als bei Suchanfragen
        # im Abgleich auf dieselbe Aussage (ist_frage, #387).
        if not titel.rstrip(_TITEL_SCHLUSS).endswith("?"):
            return None
        return Anmerkung(
            art="titel_frage",
            stelle="titel",
            text=(
                "Der Titel ist eine Frage. Die Frage steckt schon in der Aussage; "
                "sag im Titel deine Antwort."
            ),
        )

    def _zahl_ohne_herkunft(self, titel: str, text: str) -> Optional[Anmerkung]:
        gefunden: List[Tuple[str, str]] = []
        for stelle, inhalt in (("titel", titel), ("text", text)):
            for zahl in _zahlen(inhalt):
                if zahl not in (z for _, z in gefunden):
                    gefunden.append((stelle, zahl))
        if not gefunden:
            return None
        woerter = [z for _, z in gefunden]
        # Bei vielen Zahlen nennt der Satz die ersten; markiert werden alle.
        genannt = [f"„{z}“" for z in woerter[:ZAHLEN_NENNEN]]
        zahl, stammen = (
            ("Zahl", "stammt") if len(woerter) == 1 else ("Zahlen", "stammen")
        )
        if len(woerter) > ZAHLEN_NENNEN:
            genannt.append("weitere")
        return Anmerkung(
            art="zahl_ohne_herkunft",
            stelle=gefunden[0][0],
            text=(
                f"{zahl} ohne Herkunft: {_aufzaehlen(genannt)}. Trag bei „Herkunft“ "
                f"ein, woher sie {stammen}."
            ),
            woerter=woerter,
        )

    # --- Hilfen --------------------------------------------------------------

    def _wendungen(self, satz) -> List[str]:
        """Die Wendungen der Parteistimme in einem Satz, so wie sie dort stehen."""
        liste = self._parteistimme
        # Zitiert der Beitrag den Spruch ("„Die Grünen wollen alles verbieten“"),
        # spricht er nicht selbst.
        woerter = [t for t in _woerter(satz) if not _im_zitat(t)]
        formen = [_grundformen(t.lemma_) | _grundformen(t.text) for t in woerter]
        wendungen: List[str] = []
        for i in range(len(woerter)):
            for folge in liste.folgen:
                stueck = formen[i : i + len(folge)]
                if len(stueck) == len(folge) and all(
                    teil in f for teil, f in zip(folge, stueck)
                ):
                    wendungen.append(
                        " ".join(t.text for t in woerter[i : i + len(folge)])
                    )
        for token, f in zip(woerter, formen):
            # Das Subjekt, auch als zweites Glied ("Bündnis 90/Die Grünen fordert").
            subjekt = token.dep_ == "sb" or (
                token.dep_ == "cj" and token.head.dep_ == "sb"
            )
            if not subjekt:
                continue
            verb = token.head.head if token.dep_ == "cj" else token.head
            # Verneint ("Die Grünen wollen kein Heizungsverbot") antwortet der Satz
            # auf den Vorwurf; das merkt die Verneinungsregel an, wenn es vorn steht.
            if _im_zitat(verb) or _verneint(verb):
                continue
            verbformen = _grundformen(verb.lemma_) | _grundformen(verb.text)
            for wer, tut in liste.wer_tut:
                if f & wer and verbformen & tut:
                    vorne, hinten = sorted((token, verb), key=lambda t: t.i)
                    wendung = f"{vorne.text} {hinten.text}"
                    # "Wir Grüne fordern" ist schon als Folge "Wir Grüne" gefunden.
                    if not any(token.text in w.split() for w in wendungen):
                        wendungen.append(wendung)
                    break
        return wendungen

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


def _im_zitat(token) -> bool:
    """Steht das Wort zwischen Anführungszeichen?"""
    return any(m.start() < token.idx < m.end() for m in _ZITAT.finditer(token.doc.text))


def _verneint(verb, tiefer: bool = True) -> bool:
    """
    Hängt am Verb eine Verneinung, auch als "kein" vor seinem Objekt? Bei Modalverb und
    Infinitiv auch am Infinitiv ("wollen kein Heizungsverbot einführen").
    """
    for kind in verb.children:
        if kind.dep_ == "ng" or kind.lemma_.lower() in _VERNEINT:
            return True
        if any(
            enkel.dep_ == "nk" and enkel.lemma_.lower() == "kein"
            for enkel in kind.children
        ):
            return True
        if tiefer and kind.dep_ == "oc" and _verneint(kind, tiefer=False):
            return True
    return False


def _zwischen_ziffern(inhalt: str, i: int) -> bool:
    """Steht der Strich an Stelle i zwischen zwei Zahlen ("3 – 5")?"""
    davor = inhalt[:i].rstrip()
    danach = inhalt[i + 1 :].lstrip()
    return bool(davor[-1:].isdigit() and danach[:1].isdigit())


def _zahlen(inhalt: str) -> List[str]:
    """
    Die Zahlen, die eine Herkunft brauchen, so wie sie im Text stehen. Bewusst schlicht:

    - Ziffern zählen, auch mit Punkt oder Komma ("10.000", "3,5"), mit Einheit
      ("30 Prozent", "5 €").
    - Nicht: eine Jahreszahl allein (1900 bis 2099, "seit 2020"); kleine Ziffern bis
      AUFZAEHLUNG_BIS ohne Einheit ("3 Gründe", "1."); Ordinalzahlen ("24. Oktober",
      "20. Jahrhundert"); Datum und Uhrzeit ("3.10.2025", "18:30", "18 Uhr");
      Paragrafen ("§ 218"), "Tempo 30"; Ziffern vor einem Bindestrich-Wort
      ("1,5-Grad-Ziel", "49-Euro-Ticket"); Ziffern in Wörtern ("CO2") und in Links;
      eine Ziffer nur aus Ziffern ohne Einheit nach einem großgeschriebenen Wort mitten
      im Satz, das sie benennt, wenn danach kein großgeschriebenes Wort folgt ("Linie
      14 fährt", "Stuttgart 21", "Bündnis 90"; aber "im Jahr 5000 Bäume", "Hamburg hat
      1.500 Busse").
    - Größenwörter zählen nach einem Zahlwort ("zehn Prozent"), allein nicht ("Wie viel
      Prozent?", "Millionen Menschen").
    """
    inhalt = _ohne_ordinalzahlen(
        _KEINE_ZAHL.sub(lambda m: " " * len(m.group()), inhalt)
    )
    zahlen: List[Tuple[int, str]] = []
    belegt: List[range] = []
    for m in _ZIFFERN.finditer(inhalt):
        einheit = _EINHEIT.match(inhalt, m.end())
        ende = einheit.end() if einheit else m.end()
        if einheit is None:
            if (
                m.group().isdigit()
                and not _gross_danach(inhalt, m.end())
                and _ist_name(inhalt[: m.start()])
            ):
                continue
            if m.group().isdigit():
                wert = int(m.group())
                if wert <= AUFZAEHLUNG_BIS or wert in JAHRESZAHLEN:
                    continue
        zahlen.append((m.start(), inhalt[m.start() : ende]))
        belegt.append(range(m.start(), ende))
    for m in _GROESSENWORT.finditer(inhalt):
        if not any(m.start() in r for r in belegt):
            zahlen.append((m.start(), m.group()))
    return [z for _, z in sorted(zahlen)]


def _ohne_ordinalzahlen(inhalt: str) -> str:
    """Ordinalzahlen durch Leerzeichen ersetzen, damit die Stellen gleich bleiben."""

    def ersetzen(m) -> str:
        wort = m.group(2)
        if wort.lower() in _NACH_ORDINALZAHL or wort[0].islower():
            return " " * len(m.group())
        return m.group()

    return _ORDINALZAHL.sub(ersetzen, inhalt)


def _gross_danach(inhalt: str, ende: int) -> bool:
    """Folgt auf die Ziffer ein großgeschriebenes Wort ("5000 Bäume")?"""
    m = _WORT_DANACH.match(inhalt, ende)
    return m is not None and m.group(1).isupper()


def _ist_name(davor: str) -> bool:
    """Steht direkt vor der Ziffer ein großgeschriebenes Wort, das nicht den Satz beginnt?"""
    # Nur das Ende: Die Suche läuft für jede Ziffer, der Text davor kann lang sein.
    davor = davor[-60:]
    m = _WORT_DAVOR.search(davor)
    if m is None or not m.group(2)[0].isupper():
        return False
    zeichen = m.group(1)
    return bool(zeichen) and zeichen not in ".!?:" and m.start(2) > 0


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
