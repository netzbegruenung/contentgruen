"""
Die Regel der NLI-Stufe (#387): Ist ein Kandidat dieselbe Behauptung wie der neue Text,
und widerspricht er ihm? Ohne Modell und ohne Dienst, damit Dienst und Messset
(tests/regression/nli_messen.py) dieselbe Regel anwenden.

Ein NLI-Modell sagt je Richtung, wie wahrscheinlich der eine Text den anderen folgert
(Folgerung) oder ihm widerspricht (Widerspruch). Dieselbe Behauptung heisst: beide
Richtungen folgern sich (Paraphrase als beidseitige Folgerung) und keine widerspricht.

Zwei Vorpruefungen per Regel kommen davor, weil das Modell diese Faelle nicht trennt:

- Fragen: Eine Frage behauptet nichts (MESSSET.md, Regel 4). Frage gegen Behauptung
  wird nie dieselbe Aussage. Erkannt am Fragezeichen am Ende oder an einem finiten
  Verb an erster Stelle (FRAGEVERBEN).
- Quantoren: "Manche Windraeder toeten Voegel" folgert das Modell in beide Richtungen
  aus "Windraeder toeten Voegel"; nach Regel 1 und 3 ist es aber eine andere
  Behauptung. Andere Quantoren in beiden Texten fuehren deshalb nie zusammen. Der Preis:
  Gleichwertige Umformungen mit anderem Quantor ("immer unpuenktlich" / "nie
  puenktlich") bleiben getrennt - lieber eine Aussage zu viel als eine falsche
  Zusammenfuehrung.
"""

import re
from typing import NamedTuple, Optional

from utils.text_normalisierung import text_normalisiert

# Woerter, deren Unterschied eine andere Behauptung ergibt, auch wenn das Modell beide
# Texte gegenseitig folgert. Verneinungen (nicht, kein ...) erkennt das Modell als
# Widerspruch; kein und nie stehen trotzdem hier, weil sie auch Quantoren sind.
QUANTOREN = frozenset(
    {
        "alle",
        "allen",
        "aller",
        "alles",
        "einige",
        "gelegentlich",
        "größtenteils",
        "häufig",
        "einigen",
        "immer",
        "jede",
        "jedem",
        "jeden",
        "jeder",
        "jedes",
        "kaum",
        "kein",
        "keine",
        "keinem",
        "keinen",
        "keiner",
        "manche",
        "manchen",
        "mancher",
        "manches",
        "manchmal",
        "meist",
        "meistens",
        "mehrheitlich",
        "nie",
        "niemals",
        "nur",
        "oft",
        "sämtliche",
        "selten",
        "ständig",
        "stets",
        "teilweise",
        "viele",
        "vielen",
        "wenige",
        "wenigen",
    }
)

# Finite Verben, die an erster Stelle eine Entscheidungsfrage einleiten ("Sind
# Waermepumpen im Altbau sinnvoll"): Suchanfragen kommen oft ohne Fragezeichen. Nur
# Hilfs- und Modalverben und haeufige Verben aus Suchanfragen, keine, die am Satzanfang
# meist einen Imperativ einleiten ("Macht ...", "Geht ...").
FRAGEVERBEN = frozenset(
    {
        "ist",
        "sind",
        "bin",
        "bist",
        "seid",
        "war",
        "waren",
        "wäre",
        "wären",
        "hat",
        "haben",
        "hast",
        "habt",
        "hatte",
        "hatten",
        "hätte",
        "hätten",
        "wird",
        "werden",
        "wirst",
        "wurde",
        "wurden",
        "würde",
        "würden",
        "kann",
        "können",
        "kannst",
        "konnte",
        "könnte",
        "könnten",
        "muss",
        "müssen",
        "musste",
        "müsste",
        "soll",
        "sollen",
        "sollte",
        "sollten",
        "darf",
        "dürfen",
        "dürfte",
        "will",
        "wollen",
        "wollte",
        "gibt",
        "gab",
        "lohnt",
        "lohnen",
        "stimmt",
        "braucht",
        "brauchen",
        "hilft",
        "helfen",
        "kostet",
        "schadet",
        "funktioniert",
        "funktionieren",
        "bringt",
        "bringen",
    }
)

_WORT = re.compile(r"\w+")
_SCHLUSS = " \t\r\n\"'„“”‚‘’«»)"


class Richtung(NamedTuple):
    """Das Urteil des Modells in eine Richtung (Praemisse -> Hypothese)."""

    folgerung: float
    widerspruch: float


class Urteil(NamedTuple):
    """Das Urteil fuer ein Paar: hin = neuer Text -> Kandidat, rueck = umgekehrt."""

    hin: Richtung
    rueck: Richtung

    @property
    def folgerung(self) -> float:
        """Die schwaechere Folgerung beider Richtungen."""
        return min(self.hin.folgerung, self.rueck.folgerung)

    @property
    def widerspruch(self) -> float:
        """Der staerkere Widerspruch beider Richtungen."""
        return max(self.hin.widerspruch, self.rueck.widerspruch)


def ist_frage(text: str) -> bool:
    """Eine Frage: endet (ohne Anfuehrungszeichen und Leerraum) mit einem Fragezeichen
    oder beginnt mit einem finiten Verb (FRAGEVERBEN)."""
    if text.rstrip(_SCHLUSS).endswith("?"):
        return True
    erstes = _WORT.search(text)
    return erstes is not None and erstes.group().lower() in FRAGEVERBEN


def quantoren(text: str) -> frozenset[str]:
    return frozenset(w for w in _WORT.findall(text.lower()) if w in QUANTOREN)


def nli_darf_pruefen(text: str, kandidat: str) -> bool:
    """Die Vorpruefungen: gleiche Satzart (Frage/Behauptung) und gleiche Quantoren."""
    return ist_frage(text) == ist_frage(kandidat) and quantoren(text) == quantoren(
        kandidat
    )


def ist_dieselbe_behauptung(
    urteil: Urteil, folgerung_ab: float, widerspruch_unter: float
) -> bool:
    """Beide Richtungen folgern mit mindestens folgerung_ab, keine widerspricht."""
    return urteil.folgerung >= folgerung_ab and urteil.widerspruch < widerspruch_unter


def widerspricht(urteil: Urteil, widerspruch_ab: float) -> bool:
    """Widerspruch in mindestens einer Richtung - fuer die Vorschlaege im Feld
    "Antwort auf"."""
    return urteil.widerspruch >= widerspruch_ab


def entscheiden(
    text: str,
    kandidat: str,
    score: float,
    urteil: Optional[Urteil],
    *,
    kandidaten_ab: float,
    folgerung_ab: float,
    widerspruch_unter: float,
) -> bool:
    """
    Die ganze Entscheidung fuer ein Paar mit der NLI-Stufe: normalisiert gleich zaehlt
    immer; sonst muss der Kandidat ueber der Untergrenze liegen, die Vorpruefungen
    bestehen und das Modell dieselbe Behauptung sehen. urteil None heisst, das Modell
    hat das Paar nicht geprueft (Vorpruefung oder Untergrenze): nicht dieselbe.
    """
    normalform = text_normalisiert(text)
    if normalform and normalform == text_normalisiert(kandidat):
        return True
    if score < kandidaten_ab or not nli_darf_pruefen(text, kandidat):
        return False
    return urteil is not None and ist_dieselbe_behauptung(
        urteil, folgerung_ab, widerspruch_unter
    )
