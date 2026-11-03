"""
Kürzungsvorschlag (#403): eine Kurzfassung aus den eigenen Sätzen eines Kommentars,
auf Klick, ohne KI (ADR 0005).

Extraktiv: Jeder Satz verliert seine Einschübe (Relativsätze und Appositionen zwischen
Kommas, Klammern, Gedankenstrich-Paare), und die zentralen Sätze bleiben, bis die
Kurzfassung voll ist. Zentral ist ein Satz, dessen Grundformen denen des ganzen
Kommentars und der Aussage ähneln. Ein Einschub mit Verneinung oder Zahl bleibt stehen,
damit kein Satz seine Bedeutung verliert. Der Vorschlag besteht so nur aus Wörtern des
Originals, in Originalreihenfolge; er kann nicht umformulieren (das wäre #412).

Die Person übernimmt oder verwirft ihn (ADR 0003). Nichts davon wird gespeichert oder
geloggt.
"""

import math
from collections import Counter
from typing import List, Optional, Set

from dtos.commentary import KURZFASSUNG_MAX
from services.gegenlesen.gegenlesen_service import Sprachwerkzeuge

#: Abhängigkeiten, deren Teilbaum ein Einschub ist, wenn ein Komma davor steht:
#: Relativsatz, Apposition, Parenthese (TIGER-Schema von de_core_news_sm).
_EINSCHUB_DEPS = {"rc", "app", "par"}
_GEDANKENSTRICHE = {"–", "—", "-"}
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
}
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
        saetze = [list(s) for s in doc.sents]
        gekuerzt = [_ohne_einschuebe(s) for s in saetze]

        formen = [_grundformen(s) for s in saetze]
        ganz = sum(formen, Counter())
        aussage = (aussage or "").strip()
        bezug = _grundformen(self._werkzeuge.analysieren(aussage)) if aussage else None

        def wert(i: int) -> float:
            # Ähnlichkeit zum Rest des Kommentars (ohne den Satz selbst, sonst ähnelt
            # jeder Satz sich selbst) und zur Aussage.
            w = _kosinus(formen[i], ganz - formen[i])
            if bezug:
                w += _kosinus(formen[i], bezug)
            return w

        # Die zentralsten zuerst, bei Gleichstand der frühere Satz. Ein Satz, der mit
        # nichts anderem etwas gemein hat, schweift ab und füllt keinen Platz auf; nur
        # wenn alle so sind, bleibt der erste, der passt.
        werte = {i: wert(i) for i in range(len(saetze))}
        reihenfolge = sorted(werte, key=lambda i: (-werte[i], i))
        gewaehlt: List[int] = []
        for i in reihenfolge:
            if not gekuerzt[i] or (gewaehlt and werte[i] <= 0):
                continue
            probe = sorted(gewaehlt + [i])
            if len(" ".join(gekuerzt[j] for j in probe)) <= self._max:
                gewaehlt = probe
        if not gewaehlt:
            return None
        return " ".join(gekuerzt[j] for j in gewaehlt)


def _ohne_einschuebe(satz: list) -> str:
    """Der Satz ohne Einschübe, aus seinen eigenen Tokens zusammengesetzt."""
    weg: Set[int] = set()
    for span in _einschuebe(satz):
        if not any(_traegt_bedeutung(t) for t in span):
            weg.update(t.i for t in span)
    # Kommas um einen weggefallenen Einschub: das davor immer, das danach nur, wenn
    # auch eines davor stand ("Die Pumpe, die laut ist, spart" -> "Die Pumpe spart").
    nach_index = {t.i: t for t in satz}
    for start, ende in _laeufe(sorted(weg)):
        davor, danach = nach_index.get(start - 1), nach_index.get(ende + 1)
        if davor is not None and davor.text == ",":
            weg.add(davor.i)
            if danach is not None and danach.text == ",":
                weg.add(danach.i)

    teile: List[str] = []
    for t in satz:
        if t.i in weg or t.is_space:
            continue
        if teile:
            vorher = nach_index.get(t.i - 1)
            teile.append(" " if vorher is not None and _leerraum_nach(vorher) else "")
        teile.append(t.text)
    return "".join(teile).strip()


def _einschuebe(satz: list) -> List[list]:
    spans: List[list] = []
    # Klammern und Gedankenstrich-Paare, samt den Zeichen selbst.
    offen = None
    strich = None
    for pos, t in enumerate(satz):
        if t.text == "(":
            offen = pos
        elif t.text == ")" and offen is not None:
            spans.append(satz[offen : pos + 1])
            offen = None
        elif t.text in _GEDANKENSTRICHE and t.is_punct:
            if strich is None:
                strich = pos
            else:
                spans.append(satz[strich : pos + 1])
                strich = None
    # Relativsätze, Appositionen und Parenthesen, wenn ein Komma sie abtrennt.
    erstes = satz[0].i if satz else 0
    for t in satz:
        if t.dep_ not in _EINSCHUB_DEPS:
            continue
        baum = list(t.subtree)
        links = baum[0].i - erstes
        if links > 0 and satz[links - 1].text == ",":
            spans.append(baum)
    return spans


def _traegt_bedeutung(token) -> bool:
    """Verneinungen und Zahlen fallen nie weg."""
    return (
        token.dep_ == "ng"
        or token.tag_ == "PTKNEG"
        or token.lower_ in _VERNEINUNGSWOERTER
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
