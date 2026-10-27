#!/usr/bin/env python3
"""
Einwuerfe aus einer Liste in den Fangkorb legen (#341).

Liest eine CSV- oder Markdown-Liste (Link, optional Hinweis) und wirft je Zeile
einen Einwurf ein, ueber dieselbe API wie das Einwurf-Formular: angemeldet am BFF
unter dem angegebenen Konto. Liegt schon ein Einwurf mit gleichem Link im
Fangkorb, wird die Zeile gemeldet und uebersprungen. Aufruf und Dateiformat:
``mvp/SCRIPTS.md``.

Nur Standardbibliothek, damit das Skript ohne Repo-Checkout und ohne venv laeuft.
"""

import argparse
import csv
import getpass
import http.cookiejar
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple
from urllib.parse import urlsplit


class ListeUnlesbar(ValueError):
    """Die Liste hat ein Format, aus dem sich keine Zeilen lesen lassen."""


@dataclass(frozen=True)
class Zeile:
    """Eine Zeile der Liste, aus der ein Einwurf werden soll."""

    nummer: int
    link: str
    hinweis: Optional[str] = None


@dataclass(frozen=True)
class Fehler:
    """Eine Zeile, aus der kein Einwurf werden kann, und warum."""

    nummer: int
    grund: str


def _ist_link(text: str) -> bool:
    teile = urlsplit(text)
    return teile.scheme.lower() in ("http", "https") and bool(teile.netloc)


def _zeile(nummer: int, link: str, hinweis: Optional[str]) -> "Zeile | Fehler":
    link = (link or "").strip()
    hinweis = (hinweis or "").strip() or None
    if not link:
        return Fehler(nummer, "kein Link")
    if not _ist_link(link):
        return Fehler(nummer, "kein http(s)-Link")
    return Zeile(nummer, link, hinweis)


def _csv_lesen(text: str) -> List["Zeile | Fehler"]:
    try:
        dialekt = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;\t")
    except (csv.Error, IndexError):
        dialekt = csv.excel
    leser = csv.reader(io.StringIO(text), dialekt)
    kopf = [spalte.strip().lower() for spalte in next(leser, [])]
    if "link" not in kopf:
        raise ListeUnlesbar("Die CSV-Datei braucht eine Kopfzeile mit der Spalte link.")
    link_spalte = kopf.index("link")
    hinweis_spalte = kopf.index("hinweis") if "hinweis" in kopf else None

    ergebnis = []
    while True:
        # Die erste Zeile des Datensatzes; ein Hinweis darf ueber mehrere gehen.
        nummer = leser.line_num + 1
        felder = next(leser, None)
        if felder is None:
            break
        if not any(feld.strip() for feld in felder):
            continue
        link = felder[link_spalte] if link_spalte < len(felder) else ""
        hinweis = (
            felder[hinweis_spalte]
            if hinweis_spalte is not None and hinweis_spalte < len(felder)
            else None
        )
        ergebnis.append(_zeile(nummer, link, hinweis))
    return ergebnis


# Ein Listenpunkt: "- ", "* ", "+ " oder "1. " am Zeilenanfang (eingerueckt auch).
_LISTENPUNKT = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?P<rest>.*)$")
# Klammern im Link nur paarweise, eine Ebene tief (".../Foo_(Bar)").
_MD_LINK = re.compile(r"\[(?P<text>[^\]]*)\]\((?P<link>(?:[^()\s]|\([^()\s]*\))+)\)")
_SPITZ_LINK = re.compile(r"<(?P<link>https?://[^>\s]+)>")
_NACKTER_LINK = re.compile(r"https?://\S+")
# Was zwischen Link und Hinweis stehen darf und nicht zum Hinweis gehoert.
_TRENNER = " \t-–—:|"


# Satzzeichen am Ende eines nackten Links gehoeren zum Satz, nicht zum Link.
_SATZZEICHEN = ".,;:!?'\""


def _nackter_link(rest: str, treffer: "re.Match") -> Tuple[str, int, int]:
    """
    Der nackte Link ohne Satzzeichen und ohne schliessende Klammer, die nicht
    zu ihm gehoert, und die Spanne, die aus dem Hinweis faellt: der Link samt
    diesem Rest, und steht er in Klammern, auch die oeffnende.
    """
    link = treffer.group(0)
    while link and (
        link[-1] in _SATZZEICHEN
        or (link[-1] == ")" and link.count(")") > link.count("("))
    ):
        link = link[:-1]
    anfang = treffer.start()
    abgeschnitten = treffer.group(0)[len(link) :]
    if ")" in abgeschnitten and rest[anfang - 1 : anfang] == "(":
        anfang -= 1
    return link, anfang, treffer.end()


def _markdown_zeile(nummer: int, rest: str) -> "Zeile | Fehler":
    """Link und Hinweis aus einem Listenpunkt; der erste Link zaehlt."""
    for muster in (_MD_LINK, _SPITZ_LINK):
        treffer = muster.search(rest)
        if treffer:
            hinweis = (
                rest[: treffer.start()]
                + (treffer.groupdict().get("text") or "")
                + rest[treffer.end() :]
            )
            return _zeile(nummer, treffer.group("link"), hinweis.strip(_TRENNER))
    treffer = _NACKTER_LINK.search(rest)
    if treffer:
        link, anfang, ende = _nackter_link(rest, treffer)
        hinweis = rest[:anfang] + rest[ende:]
        return _zeile(nummer, link, hinweis.strip(_TRENNER))
    return _zeile(nummer, "", None)


def _markdown_lesen(text: str) -> List["Zeile | Fehler"]:
    """Jeder Listenpunkt ist eine Zeile; Ueberschriften und Fliesstext zaehlen nicht."""
    ergebnis = []
    for nummer, zeile in enumerate(text.splitlines(), start=1):
        punkt = _LISTENPUNKT.match(zeile)
        if punkt and punkt.group("rest").strip():
            ergebnis.append(_markdown_zeile(nummer, punkt.group("rest")))
    return ergebnis


def liste_lesen(pfad: Path) -> Tuple[List[Zeile], List[Fehler]]:
    """
    Die Zeilen der Liste und die Zeilen, aus denen kein Einwurf werden kann.

    ``.md``/``.markdown``: Markdown-Liste, sonst CSV mit Kopfzeile.
    """
    text = Path(pfad).read_text(encoding="utf-8-sig")
    if Path(pfad).suffix.lower() in (".md", ".markdown"):
        gelesen = _markdown_lesen(text)
    else:
        gelesen = _csv_lesen(text)
    return (
        [z for z in gelesen if isinstance(z, Zeile)],
        [z for z in gelesen if isinstance(z, Fehler)],
    )


# Stufen eines Einwurfs, wie GLOSSARY.md sie nennt.
STUFEN = {
    "open": "offen",
    "in_progress": "destilliert",
    "processed": "ausformuliert",
    "discarded": "verworfen",
}


class ApiFehler(RuntimeError):
    """Das BFF hat eine Anfrage abgelehnt oder ist nicht erreichbar."""

    def __init__(self, status: Optional[int], meldung: str):
        super().__init__(f"HTTP {status}: {meldung}" if status else meldung)
        self.status = status


class Fangkorb(Protocol):
    """Was der Import vom Fangkorb braucht; das BFF oder im Test ein Speicher."""

    def gleiche_einwuerfe(self, link: str) -> List[Dict]: ...

    def einwerfen(self, link: str, hinweis: Optional[str]) -> str: ...


@dataclass
class Bericht:
    """
    Was mit jeder Zeile geschah. ``angelegt`` traegt die ID des neuen Einwurfs,
    im Trockenlauf None.
    """

    angelegt: List[Tuple[Zeile, Optional[str]]] = field(default_factory=list)
    uebersprungen: List[Tuple[Zeile, str]] = field(default_factory=list)
    fehlgeschlagen: List[Tuple[Zeile, str]] = field(default_factory=list)


def _anmelden_noetig(fehler: ApiFehler) -> bool:
    return fehler.status in (401, 403)


def importieren(
    zeilen: List[Zeile], fangkorb: Fangkorb, trockenlauf: bool = False
) -> Bericht:
    """
    Je Zeile einen Einwurf einwerfen, ausser es liegt schon einer mit gleichem
    Link im Fangkorb.

    Eine abgelehnte Zeile haelt den Rest nicht auf; ohne gueltige Anmeldung
    (401/403) bricht der Lauf mit ``ApiFehler`` ab, weil dann jede Zeile scheitert.
    Gleiche Links innerhalb der Liste findet im echten Lauf der Fangkorb selbst,
    weil die erste Zeile dann schon eingeworfen ist. Im Trockenlauf vergleicht das
    Skript sie wortgleich; die Bereinigung um Tracking-Parameter und Co. kennt nur
    der Server.
    """
    bericht = Bericht()
    vorgemerkt: Dict[str, int] = {}
    for zeile in zeilen:
        if trockenlauf and zeile.link in vorgemerkt:
            bericht.uebersprungen.append(
                (zeile, f"gleicher Link wie Zeile {vorgemerkt[zeile.link]}")
            )
            continue
        try:
            gleiche = fangkorb.gleiche_einwuerfe(zeile.link)
            if gleiche:
                vorhanden = gleiche[0]
                stufe = STUFEN.get(vorhanden.get("status"), vorhanden.get("status"))
                bericht.uebersprungen.append(
                    (
                        zeile,
                        f"gleicher Link wie Einwurf {vorhanden.get('id')} ({stufe})",
                    )
                )
                continue
            if trockenlauf:
                vorgemerkt[zeile.link] = zeile.nummer
                bericht.angelegt.append((zeile, None))
                continue
            bericht.angelegt.append(
                (zeile, fangkorb.einwerfen(zeile.link, zeile.hinweis))
            )
        except ApiFehler as fehler:
            if _anmelden_noetig(fehler):
                raise
            bericht.fehlgeschlagen.append((zeile, str(fehler)))
    return bericht


class BffFangkorb:
    """
    Der Fangkorb ueber das BFF, angemeldet wie im Login-Formular (E-Mail und
    Passwort). Das Auth-Cookie bleibt im Speicher dieses Prozesses.
    """

    def __init__(self, adresse: str, timeout: float = 30):
        self.adresse = adresse.rstrip("/")
        self.timeout = timeout
        self._oeffner = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def _post(self, pfad: str, daten: Dict) -> Dict:
        anfrage = urllib.request.Request(
            f"{self.adresse}{pfad}",
            data=json.dumps(daten).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with self._oeffner.open(anfrage, timeout=self.timeout) as antwort:
                text = antwort.read().decode("utf-8")
        except urllib.error.HTTPError as fehler:
            raise ApiFehler(fehler.code, _fehlertext(fehler)) from None
        except (urllib.error.URLError, OSError) as fehler:
            raise ApiFehler(
                None, f"{self.adresse} nicht erreichbar: {fehler}"
            ) from None
        try:
            return json.loads(text) if text else {}
        except ValueError:
            raise ApiFehler(
                None, f"Antwort von {pfad} ist kein JSON (stimmt --adresse?)"
            ) from None

    def _feld(self, antwort: Dict, name: str, pfad: str):
        if not isinstance(antwort, dict) or name not in antwort:
            raise ApiFehler(None, f"Antwort von {pfad} ohne {name} (stimmt --adresse?)")
        return antwort[name]

    def anmelden(self, email: str, passwort: str) -> None:
        self._post("/api/auth/login/managed", {"email": email, "password": passwort})

    def gleiche_einwuerfe(self, link: str) -> List[Dict]:
        pfad = "/api/v1/rawinput/gleicherLink"
        return self._feld(self._post(pfad, {"url": link}), "results", pfad)

    def einwerfen(self, link: str, hinweis: Optional[str]) -> str:
        daten = {"url": link}
        if hinweis:
            daten["content"] = hinweis
        pfad = "/api/v1/rawinput/addRawInput"
        return self._feld(self._post(pfad, daten), "id", pfad)


def _fehlertext(fehler: "urllib.error.HTTPError") -> str:
    """Die ``detail``-Meldung der API, sonst der HTTP-Grund. Nie den ganzen Body."""
    try:
        detail = json.loads(fehler.read().decode("utf-8")).get("detail")
    except (ValueError, AttributeError, OSError):
        detail = None
    if isinstance(detail, list):  # Validierungsfehler von FastAPI
        detail = "; ".join(str(d.get("msg", d)) for d in detail)
    return str(detail or fehler.reason)


def _ausgeben(bericht: Bericht, fehler: List[Fehler], trockenlauf: bool) -> None:
    zeilen = (
        [(f.nummer, f"Fehler: {f.grund}") for f in fehler]
        + [
            (
                z.nummer,
                (
                    f"wuerde eingeworfen: {z.link}"
                    if trockenlauf
                    else f"eingeworfen als {einwurf_id}: {z.link}"
                ),
            )
            for z, einwurf_id in bericht.angelegt
        ]
        + [
            (z.nummer, f"uebersprungen, {grund}: {z.link}")
            for z, grund in bericht.uebersprungen
        ]
        + [
            (z.nummer, f"Fehler: {grund}: {z.link}")
            for z, grund in bericht.fehlgeschlagen
        ]
    )
    for nummer, text in sorted(zeilen):
        print(f"Zeile {nummer}: {text}")
    print(
        f"{'Trockenlauf, ' if trockenlauf else ''}"
        f"{'wuerden eingeworfen' if trockenlauf else 'eingeworfen'}: {len(bericht.angelegt)}, "
        f"uebersprungen: {len(bericht.uebersprungen)}, "
        f"Fehler: {len(fehler) + len(bericht.fehlgeschlagen)}"
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Einwuerfe aus einer CSV- oder Markdown-Liste in den Fangkorb legen.",
    )
    parser.add_argument("liste", type=Path, help="CSV (Spalten link, hinweis) oder .md")
    parser.add_argument(
        "--email", required=True, help="Konto, unter dem eingeworfen wird"
    )
    parser.add_argument(
        "--adresse",
        default="http://localhost:5054",
        help="Adresse von BFF oder Frontend (Standard: %(default)s)",
    )
    parser.add_argument(
        "--trockenlauf",
        action="store_true",
        help="nur zeigen, was eingeworfen wuerde; legt nichts an",
    )
    args = parser.parse_args(argv)

    try:
        zeilen, fehler = liste_lesen(args.liste)
    except (OSError, UnicodeDecodeError, ListeUnlesbar) as e:
        print(f"Liste nicht lesbar: {e}", file=sys.stderr)
        return 2

    passwort = os.environ.get("GUTGESAGT_PASSWORT") or getpass.getpass(
        f"Passwort fuer {args.email}: "
    )
    fangkorb = BffFangkorb(args.adresse)
    try:
        fangkorb.anmelden(args.email, passwort)
        bericht = importieren(zeilen, fangkorb, trockenlauf=args.trockenlauf)
    except ApiFehler as e:
        print(f"Abgebrochen: {e}", file=sys.stderr)
        return 2

    _ausgeben(bericht, fehler, args.trockenlauf)
    return 1 if fehler or bericht.fehlgeschlagen else 0


if __name__ == "__main__":
    sys.exit(main())
