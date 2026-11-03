"""
Kürzungsvorschlag (#403): eine Kurzfassung aus den eigenen Sätzen eines Kommentars,
auf Klick, ohne KI (ADR 0005).

Extraktiv: Jeder Satz verliert seine Einschübe (Appositionen und Parenthesen zwischen
Kommas, Klammern, Gedankenstrich-Paare), und die zentralen Sätze bleiben, bis die
Kurzfassung voll ist. Zentral ist ein Satz, dessen Grundformen denen des ganzen
Kommentars und der Aussage ähneln. Damit kein Satz und kein Vorschlag seine Bedeutung
verliert (Entscheidung @BanSe 03.11.): Relativsätze bleiben immer stehen, weil sie
einschränken können; ein Einschub mit Verneinung oder Zahl bleibt stehen; ein Satz mit
Verneinung fällt nie weg. Der Vorschlag besteht so nur aus Wörtern des Originals, in
Originalreihenfolge; er kann nicht umformulieren (das wäre #412).

Die Person übernimmt oder verwirft ihn (ADR 0003). Nichts davon wird gespeichert oder
geloggt.
"""

import math
from collections import Counter
from typing import List, Optional, Set

from dtos.commentary import KURZFASSUNG_MAX
from services.gegenlesen.gegenlesen_service import Sprachwerkzeuge

#: Abhängigkeiten, deren Teilbaum ein Einschub ist, wenn ein Komma davor steht:
#: Apposition, Parenthese (TIGER-Schema von de_core_news_sm). Relativsätze ("rc") nie.
_EINSCHUB_DEPS = {"app", "par"}
#: Nur echte Gedankenstriche: Ein Bindestrich mit Leerzeichen steht auch in
#: "Ost - West - Problem".
_GEDANKENSTRICHE = {"–", "—"}
_VERNEINUNGSWOERTER = {
    "nicht",
    "kein",
    "keine",
    "keiner",
    "keinen",
    "keinem",
    "keines",
    "nie",
    "niemals",
    "nichts",
    "niemand",
    "nirgends",
    "keinesfalls",
    "weder",
    "kaum",
    "ohne",
}
#: Zahlwörter, die spaCy nicht als Zahl erkennt (Anteile und Vielfache).
_ZAHLWOERTER = {
    "hälfte",
    "drittel",
    "viertel",
    "fünftel",
    "zehntel",
    "prozent",
    "halb",
    "doppelt",
    "dreifach",
    "verdoppeln",
    "halbieren",
}
#: So endet ein Satz ("...", "?!" eingeschlossen); spaCy trennt manchmal mitten im
#: Satz ("gilt ab | 2024.").
_SATZENDE = set(".!?…")
#: Was nach dem Satzzeichen noch zum Satz gehört: "Er sagt: „Das geht.“"
_SCHLIESSEND = {"“", "”", '"', "»", "«", "'", "’", ")", "]"}
#: Wortarten, deren Grundformen tragen, worum es geht.
_INHALT = {"NOUN", "PROPN", "VERB", "ADJ"}


class KuerzungsvorschlagService:
    def __init__(self, werkzeuge: Sprachwerkzeuge, max_zeichen: int = KURZFASSUNG_MAX):
        self._werkzeuge = werkzeuge
        self._max = max_zeichen

    def vorschlagen(self, text: str, aussage: Optional[str]) -> Optional[str]:
        """Die Kurzfassung als Vorschlag; None, wenn kein Satz hineinpasst."""
        text = (text or "").strip()
        if not text:
            return None
        doc = self._werkzeuge.analysieren(text)
        saetze = _saetze(doc)
        behalten = [_ohne_einschuebe(s) for s in saetze]
        gekuerzt = [_zusammensetzen(b) for b in behalten]

        # Bewertet wird, was im Vorschlag steht: der Satz ohne seine Einschübe. Der
        # Bezug ist der ganze Kommentar.
        formen = [_grundformen(b) for b in behalten]
        ganz = sum((_grundformen(s) for s in saetze), Counter())
        aussage = (aussage or "").strip()
        bezug = _grundformen(self._werkzeuge.analysieren(aussage)) if aussage else None

        def wert(i: int) -> float:
            # Ähnlichkeit zum Rest des Kommentars (ohne den Satz selbst, sonst ähnelt
            # jeder Satz sich selbst) und zur Aussage.
            w = _kosinus(formen[i], ganz - _grundformen(saetze[i]))
            if bezug:
                w += _kosinus(formen[i], bezug)
            return w

        # Sätze mit Verneinung müssen hinein; passen sie nicht, gibt es keinen
        # Vorschlag. Danach die zentralsten, bei Gleichstand der frühere Satz. Ein
        # Satz, der mit nichts anderem etwas gemein hat, schweift ab und kommt nicht
        # in Frage; nur wenn alle so sind, bleibt der erste, der passt.
        werte = {i: wert(i) for i in range(len(saetze))}
        noetig = [i for i, s in enumerate(saetze) if any(_verneint(t) for t in s)]
        nur_zentrale = any(w > 0 for w in werte.values())
        reihenfolge = sorted(werte, key=lambda i: (-werte[i], i))
        gewaehlt: List[int] = []
        laenge = 0

        def passt(i: int) -> bool:
            nonlocal laenge
            # Mit einem Leerzeichen zwischen den Sätzen.
            neu = laenge + len(gekuerzt[i]) + (1 if gewaehlt else 0)
            if neu > self._max:
                return False
            gewaehlt.append(i)
            laenge = neu
            return True

        for i in noetig:
            if not passt(i):
                return None
        for i in reihenfolge:
            if i in gewaehlt or not gekuerzt[i] or (nur_zentrale and werte[i] <= 0):
                continue
            passt(i)
        if not gewaehlt:
            return None
        return " ".join(gekuerzt[j] for j in sorted(gewaehlt))


def _saetze(doc) -> List[list]:
    """Die Sätze, wie spaCy sie trennt, aber nie mitten im Satz: Endet einer weder
    mit einem Satzzeichen noch mit dem Absatz, gehört der nächste noch dazu
    ("gilt ab" + "2024.")."""
    saetze: List[list] = []
    for satz in doc.sents:
        tokens = [t for t in satz if not t.is_space]
        if not tokens:
            continue
        if saetze and not _endet(saetze[-1], tokens[0], doc.text):
            saetze[-1].extend(tokens)
        else:
            saetze.append(tokens)
    return saetze


def _endet(satz: list, naechstes, text: str) -> bool:
    letztes = satz[-1]
    if "\n" in text[letztes.idx + len(letztes.text) : naechstes.idx]:
        return True
    for t in reversed(satz):
        if t.text in _SCHLIESSEND:
            continue
        return t.is_punct and any(z in _SATZENDE for z in t.text)
    return False


def _ohne_einschuebe(satz: list) -> list:
    """Die Tokens des Satzes ohne seine Einschübe, in Originalreihenfolge."""
    weg: Set[int] = set()
    for span in _einschuebe(satz):
        if not any(_traegt_bedeutung(t) or _relativsatz(t) for t in span):
            weg.update(t.i for t in span)
    # Kommas um einen weggefallenen Einschub: das davor immer, das danach nur, wenn
    # auch eines davor stand ("Robert, unser Nachbar, heizt" -> "Robert heizt").
    nach_index = {t.i: t for t in satz}
    for start, ende in _laeufe(sorted(weg)):
        davor, danach = nach_index.get(start - 1), nach_index.get(ende + 1)
        if davor is not None and davor.text == ",":
            weg.add(davor.i)
            if danach is not None and danach.text == ",":
                weg.add(danach.i)
    return [t for t in satz if t.i not in weg and not t.is_space]


def _zusammensetzen(tokens: list) -> str:
    """Tokens zu Text, mit dem Leerraum des Originals zwischen Nachbarn."""
    teile: List[str] = []
    letzter = None
    for t in tokens:
        if letzter is not None:
            if letzter.i == t.i - 1:
                teile.append(" " if _leerraum_nach(letzter) else "")
            elif t.is_punct:
                # Satzzeichen direkt nach einem Einschub: "Strom – xyz – ." -> "Strom."
                teile.append("")
            else:
                teile.append(" ")
        teile.append(t.text)
        letzter = t
    return "".join(teile).strip()


def _einschuebe(satz: list) -> List[list]:
    spans: List[list] = []
    # Klammern (die äußerste, samt verschachtelten) und Gedankenstrich-Paare, samt
    # den Zeichen selbst.
    offen = None
    tiefe = 0
    strich = None
    for pos, t in enumerate(satz):
        if t.text == "(":
            if tiefe == 0:
                offen = pos
            tiefe += 1
        elif t.text == ")" and tiefe > 0:
            tiefe -= 1
            if tiefe == 0:
                spans.append(satz[offen : pos + 1])
        elif t.text in _GEDANKENSTRICHE and t.is_punct:
            if strich is None:
                strich = pos
            else:
                spans.append(satz[strich : pos + 1])
                strich = None
    # Appositionen und Parenthesen, wenn ein Komma sie abtrennt.
    nach_index = {t.i: t for t in satz}
    for t in satz:
        if t.dep_ not in _EINSCHUB_DEPS:
            continue
        baum = list(t.subtree)
        # Nur ein zusammenhängender Teilbaum ist ein Einschub.
        if baum[-1].i - baum[0].i + 1 != len(baum):
            continue
        davor = nach_index.get(baum[0].i - 1)
        if davor is not None and davor.text == ",":
            spans.append(baum)
    return spans


def _verneint(token) -> bool:
    return (
        token.dep_ == "ng"
        or token.tag_ == "PTKNEG"
        or token.lower_ in _VERNEINUNGSWOERTER
    )


def _relativsatz(token) -> bool:
    """Gehört zu einem Relativsatz, auch in Klammern oder zwischen Gedankenstrichen,
    wo das Modell ihn nicht immer als "rc" erkennt: am Relativpronomen."""
    return token.dep_ == "rc" or token.tag_ in {"PRELS", "PRELAT"}


def _traegt_bedeutung(token) -> bool:
    """Verneinungen und Zahlen fallen nie weg."""
    return (
        _verneint(token)
        or token.lower_ in _ZAHLWOERTER
        or token.lemma_.lower() in _ZAHLWOERTER
        or token.like_num
        or token.pos_ == "NUM"
        or any(z.isdigit() for z in token.text)
    )


def _leerraum_nach(token) -> bool:
    return bool(token.whitespace_) or token.is_space


def _laeufe(indizes: List[int]):
    """Zusammenhängende Läufe in einer sortierten Liste: [1,2,3,7] -> (1,3), (7,7)."""
    if not indizes:
        return
    start = vorher = indizes[0]
    for i in indizes[1:]:
        if i != vorher + 1:
            yield start, vorher
            start = i
        vorher = i
    yield start, vorher


def _grundformen(tokens) -> Counter:
    return Counter(
        t.lemma_.lower() for t in tokens if t.pos_ in _INHALT and not t.is_stop
    )


def _kosinus(a: Counter, b: Counter) -> float:
    gemeinsam = sum(a[k] * b[k] for k in a.keys() & b.keys())
    if not gemeinsam:
        return 0.0
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(
        sum(v * v for v in b.values())
    )
    return gemeinsam / norm
