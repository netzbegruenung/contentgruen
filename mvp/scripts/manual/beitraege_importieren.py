#!/usr/bin/env python3
"""
Startbestand einspielen und Beitraege endgueltig entfernen (#592).

Import: liest eine Markdown-Datei mit Aussagen und je Aussage einem oder mehreren
Kommentaren und legt jeden Kommentar ueber dieselbe API an wie das
Kommentar-Formular, als Antwort auf seine Aussage und mit seinen Herkuenften
(``POST /api/v1/commentary/addCommentary``). Die Aussage legt der Server an oder
findet die vorhandene; eine vorhandene Herkunft nimmt er wieder. Autor ist das
angemeldete Konto.

Entfernen (``--entfernen``): liest je Zeile ``<typ> <id>`` und entfernt den
Beitrag endgueltig ueber die Admin-API
(``DELETE /api/v1/moderation/content/{typ}/{id}``); dafuer braucht es ein
Admin-Konto. Im Frontend gibt es dafuer keinen Knopf, nur das Sperren.

Beides ist ohne ``--ausfuehren`` ein Trockenlauf, der nichts schreibt. Aufruf,
Dateiformat und Exit-Codes: ``mvp/SCRIPTS.md``.

Anmeldung, zwei Wege:

- Test und Produktion (Anmeldung nur ueber Keycloak im Browser): die Sitzung des
  Browsers mitgeben. In Gut gesagt mit dem Konto anmelden, das schreiben soll,
  Entwicklertools oeffnen (F12), unter "Web-Speicher" (Firefox) bzw. "Anwendung"
  (Chrome) bei "Cookies" die Adresse von Gut gesagt waehlen und den Wert des
  Cookies ``GutGesagtAuthCookie`` kopieren. Ihn in eine Datei schreiben, die nur
  man selbst lesen kann, und ``--sitzung-datei <datei>`` angeben (oder ihn in
  die Umgebungsvariable ``GUTGESAGT_SITZUNG`` legen). Statt des Werts geht auch
  die ganze Cookie-Zeile einer Anfrage (``name=wert; …``). Nie als Argument auf
  der Kommandozeile: Das stuende in der Shell-Historie.
  Das Cookie gilt wie im Browser bis zu 14 Tage nach der letzten Anfrage, auch
  nach dem Abmelden im Browser (das BFF fuehrt keine Sitzungen auf dem Server);
  die Datei deshalb danach loeschen. Das Skript gibt das Cookie nirgends aus.
- Lokaler Dev-Stack: ``--email`` mit Passwort (Direktanmeldung, nur dort an).

Nur Standardbibliothek, damit das Skript ohne Repo-Checkout und ohne venv laeuft.
"""

import argparse
import getpass
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Protocol, Tuple
from urllib.parse import urlsplit

# Grenzen wie im Dienst (dtos/commentary.py, domain/models/commentary.py).
TITEL_MIN, TITEL_MAX = 3, 120
KURZ_MAX = 280
# Mindestlaenge der Mittelfassung wie im Formular (add-commentary.component.ts).
MITTEL_MIN = 10
MITTEL_MAX = 500
LANG_MAX = 2000
AUSSAGE_MIN, AUSSAGE_MAX = 10, 1000
ZWECKE = ("kommentarspalte", "eigene_leute")
STILE = ("sachlich", "humorvoll", "persoenlich", "brueckenbauend", "bissig")
# Beitragstypen, die der Admin-Endpunkt entfernt (domain/models/content_type.py).
BEITRAGSTYPEN = ("commentary", "generic_text", "post", "image")

# Kennung des CC0-Hinweises, den das Kommentar-Formular zeigt
# (frontend shared/consent-hinweis.ts, docs/CC0_HINWEIS_WORTLAUTE.md). Wer
# importiert, stellt die Texte damit unter CC0 wie beim Absenden im Formular.
# Kennt ein aelterer Dienst die Kennung noch nicht, legt das Skript ohne Kennung
# an, wie der Dienst es fuer eine aeltere App im Browser-Cache annimmt, und
# sagt das (``importieren``).
CC0_WORTLAUT = "2026-11-02-formular"
CC0_UNBEKANNT = "Unbekannter Wortlaut des CC0-Hinweises"


class DateiUnlesbar(ValueError):
    """Die Datei hat ein Format, aus dem sich nichts lesen laesst."""


@dataclass(frozen=True)
class Herkunft:
    link: str
    beschreibung: Optional[str] = None


@dataclass
class Kommentar:
    """Ein Kommentar aus der Datei; ``zeile`` ist die Zeile seiner Ueberschrift."""

    zeile: int
    aussage: str
    titel: Optional[str] = None
    kurz: Optional[str] = None
    mittel: Optional[str] = None
    lang: Optional[str] = None
    herkuenfte: List[Herkunft] = field(default_factory=list)
    zweck: Optional[str] = None
    stil: Optional[str] = None


@dataclass(frozen=True)
class Fehler:
    """Eine Zeile der Datei, die nicht angelegt oder entfernt werden kann, und warum."""

    zeile: int
    grund: str


# --- Markdown lesen -------------------------------------------------------

# "## 1.1 „Aussage“" (nummeriert und in Anfuehrungszeichen) oder "## Aussage: …";
# andere "##"-Ueberschriften ("## Stand", "## 9. Hinweise") gehoeren nicht zum Bestand.
_AUSSAGE = re.compile(
    r"^##\s+(?:\d+(?:\.\d+)*\.?\s+(?P<nummeriert>[„“\"»«‚].+[“”\"«»‘])"
    r"|Aussage:\s*(?P<benannt>.+))$",
    re.I,
)
_KOMMENTAR = re.compile(r"^###\s+(?P<rest>.*)$")
_KOMMENTAR_TITEL = re.compile(r"^Kommentar:\s*(?P<titel>.+)$", re.I)
_UEBERSCHRIFT = re.compile(r"^#{1,3}\s")
# Ein Feld: "**Kurz:** …", "**Kurz**: …", "Kurz: …" oder "- kurz: …". Vor
# "Herkunft" darf ein Wort stehen und dahinter eine Klammer ("Zweite Herkunft
# (Anteil …):"). Tiefere Ueberschriften ("#### …") sind Text im Kommentar.
_FELD = re.compile(
    r"^\s*(?:[-*]\s+)?(?:\*\*)?"
    r"(?P<name>titel|kurz|mittel|lang|zweck|stil|(?:\w+\s+)?herkunft(?:\s*\([^)]*\))?)"
    r"(?:\*\*)?\s*:\s*(?:\*\*)?\s*(?P<wert>.*)$",
    re.I,
)
_LINK = re.compile(r"https?://[^\s<>|„“”»«]+")
# Klammern im Link nur paarweise, eine Ebene tief (".../Rotmilan_(Art)").
_MD_LINK = re.compile(
    r"\[(?P<text>[^\]]*)\]\((?P<link>https?://(?:[^()\s]|\([^()\s]*\))+)\)"
)
_SPITZ_LINK = re.compile(r"<(?P<link>https?://[^>\s]+)>")
# Was zwischen Link und Beschreibung steht und nicht zur Beschreibung gehoert.
_TRENNER = " \t-–—:|"
# Pruefvermerke fuer das Gegenlesen gehoeren nicht in die Beschreibung.
_PRUEFVERMERK = re.compile(r"\s*\bgeprüft:.*$", re.I | re.S)
_ANFUEHRUNG = {"„": "“", "“": "”", '"': '"', "»": "«", "«": "»", "‚": "‘"}
# Felder, deren Wert auf Folgezeilen weitergeht (bis zur Leerzeile).
_MEHRZEILIG = ("kurz", "mittel", "lang")
# Eine "##"-Ueberschrift, die wie eine Aussage nummeriert ist ("## 1.6 …"), aber
# nicht als Aussage erkannt wurde: Ihre Kommentare fielen sonst still weg.
_NUMMERIERT = re.compile(r"^##\s+\d")
# Zeilen im Kommentar, die bewusst nicht uebernommen werden: Pruefvermerke,
# Hinweise zum Gegenlesen, Trennlinien. Andere uebergangene Zeilen meldet das
# Skript als Hinweis.
_VERMERK = re.compile(r"^\s*(?:geprüft\b|hinweis\b[^:]*:|-{3,}\s*$)", re.I)


def _ohne_anfuehrung(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and _ANFUEHRUNG.get(text[0]) == text[-1]:
        return text[1:-1].strip()
    return text


def _herkunft(wert: str) -> Optional[Herkunft]:
    """
    Link und Beschreibung aus ``URL – Beschreibung`` oder ``URL | Beschreibung``;
    der Link auch als ``<URL>`` oder ``[Text](URL)``, dann zaehlt Text mit.
    """
    wert = _MD_LINK.sub(lambda t: f"{t.group('link')} {t.group('text')}", wert)
    wert = _SPITZ_LINK.sub(lambda t: t.group("link"), wert)
    treffer = _LINK.search(wert)
    if not treffer:
        return None
    link = treffer.group(0)
    # Satzzeichen am Ende gehoeren zum Satz; eine schliessende Klammer nur, wenn
    # im Link keine oeffnende zu ihr gehoert.
    while link and (
        link[-1] in ".,;:!?'\""
        or (link[-1] == ")" and link.count(")") > link.count("("))
    ):
        link = link[:-1]
    rest = wert[: treffer.start()] + wert[treffer.start() + len(link) :]
    beschreibung = _PRUEFVERMERK.sub("", rest).strip(_TRENNER)
    return Herkunft(link, beschreibung or None)


def datei_lesen(
    pfad: Path, hinweise: Optional[List[Fehler]] = None
) -> Tuple[List[Kommentar], List[Fehler]]:
    """
    Die Kommentare der Datei und was an ihnen nicht stimmt.

    Gelesen wird die Gliederung ``## <Nummer> „Aussage“`` (oder ``## Aussage: …``),
    darunter je Kommentar eine ``###``-Ueberschrift und die Felder Titel, Kurz,
    Mittel, Lang, Herkunft (mehrfach), Zweck, Stil. Alles andere (Einleitung,
    ``#``-Bloecke, Pruefvermerke, Hinweise) wird uebergangen. Ein Kommentar mit
    Fehler kommt nicht in die erste Liste.

    In ``hinweise`` (falls angegeben) landet, was uebergangen wurde und
    vielleicht zum Bestand gehoeren sollte: ``###``-Kommentare unter einer
    nummerierten, aber nicht erkannten ``##``-Ueberschrift und Textzeilen im
    Kommentar, die zu keinem Feld gehoeren (ausser Vermerken und Trennlinien).
    """
    if hinweise is None:
        hinweise = []
    unerkannt: Optional[int] = None
    text = Path(pfad).read_text(encoding="utf-8-sig")
    kommentare: List[Kommentar] = []
    aussage: Optional[str] = None
    aktuell: Optional[Kommentar] = None
    offenes_feld: Optional[str] = None
    herkunft_fehler: Dict[int, List[str]] = {}

    for nummer, zeile in enumerate(text.splitlines(), start=1):
        if _UEBERSCHRIFT.match(zeile):
            offenes_feld = None
            treffer = _AUSSAGE.match(zeile.strip())
            if treffer:
                aussage = _ohne_anfuehrung(
                    treffer.group("nummeriert") or treffer.group("benannt")
                )
                aktuell = None
                unerkannt = None
                continue
            treffer = _KOMMENTAR.match(zeile.strip())
            if treffer and aussage is not None:
                aktuell = Kommentar(zeile=nummer, aussage=aussage)
                benannt = _KOMMENTAR_TITEL.match(treffer.group("rest").strip())
                if benannt:
                    aktuell.titel = benannt.group("titel").strip()
                kommentare.append(aktuell)
                continue
            if treffer and unerkannt is not None:
                hinweise.append(
                    Fehler(
                        nummer,
                        f"Kommentar uebergangen: die Ueberschrift in Zeile {unerkannt} "
                        "ist keine erkannte Aussage (## 1.1 „…“ oder ## Aussage: …)",
                    )
                )
            # Eine andere Ueberschrift beendet Aussage und Kommentar.
            if zeile.startswith("## ") or zeile.startswith("# "):
                aussage = None
                unerkannt = nummer if _NUMMERIERT.match(zeile) else None
            aktuell = None
            continue
        if aktuell is None:
            continue
        if not zeile.strip():
            offenes_feld = None
            continue
        feld = _FELD.match(zeile)
        if feld:
            name = feld.group("name").lower()
            wert = feld.group("wert").strip()
            offenes_feld = None
            if "herkunft" in name:
                herkunft = _herkunft(wert)
                # "Herkunft: keine …" sagt bewusst, dass es keine braucht;
                # ohne Link sonst ("[Quelle fehlt]") ein Fehler.
                if herkunft is None and wert.lower().startswith("keine"):
                    continue
                if herkunft is None:
                    herkunft_fehler.setdefault(aktuell.zeile, []).append(
                        f"Herkunft in Zeile {nummer} ohne http(s)-Link"
                    )
                else:
                    aktuell.herkuenfte.append(herkunft)
                continue
            # Ein leeres "Titel:" laesst den Titel aus "### Kommentar: …" stehen.
            if wert or name != "titel":
                setattr(aktuell, name, wert or None)
            if name in _MEHRZEILIG:
                offenes_feld = name
            continue
        if offenes_feld:
            bisher = getattr(aktuell, offenes_feld) or ""
            setattr(aktuell, offenes_feld, f"{bisher}\n{zeile.strip()}".strip())
        elif not _VERMERK.match(zeile):
            hinweise.append(
                Fehler(
                    nummer,
                    "Zeile uebergangen, gehoert zu keinem Feld (Absatz nach einer "
                    "Leerzeile oder umbrochene Herkunft?)",
                )
            )

    gut, fehler = [], []
    for kommentar in kommentare:
        gruende = _pruefen(kommentar) + herkunft_fehler.get(kommentar.zeile, [])
        if gruende:
            fehler.append(Fehler(kommentar.zeile, "; ".join(gruende)))
        else:
            gut.append(kommentar)
    return gut, fehler


def _pruefen(k: Kommentar) -> List[str]:
    """Was der Server ablehnen wuerde, vorab und alles auf einmal."""
    gruende = []
    aussage = k.aussage.strip()
    if not AUSSAGE_MIN <= len(aussage) <= AUSSAGE_MAX:
        gruende.append(
            f"Aussage hat {len(aussage)} Zeichen, erlaubt {AUSSAGE_MIN}-{AUSSAGE_MAX}"
        )
    titel = (k.titel or "").strip()
    if not titel:
        gruende.append("kein Titel")
    elif "\n" in titel or not TITEL_MIN <= len(titel) <= TITEL_MAX:
        gruende.append(
            f"Titel hat {len(titel)} Zeichen, erlaubt {TITEL_MIN}-{TITEL_MAX} in einer Zeile"
        )
    mittel = (k.mittel or "").strip()
    if not mittel:
        gruende.append("keine Mittelfassung")
    elif len(mittel) < MITTEL_MIN:
        gruende.append(
            f"Mittelfassung hat {len(mittel)} Zeichen, mindestens {MITTEL_MIN} wie im Formular"
        )
    for name, wert, grenze in (
        ("Kurzfassung", k.kurz, KURZ_MAX),
        ("Mittelfassung", k.mittel, MITTEL_MAX),
        ("Langfassung", k.lang, LANG_MAX),
    ):
        if wert and len(wert.strip()) > grenze:
            gruende.append(
                f"{name} hat {len(wert.strip())} Zeichen, erlaubt {grenze}"
            )
    if k.zweck and k.zweck.strip().lower() not in ZWECKE:
        gruende.append(f"Zweck {k.zweck!r} unbekannt, erlaubt: {', '.join(ZWECKE)}")
    if k.stil and k.stil.strip().lower() not in STILE:
        gruende.append(f"Stil {k.stil!r} unbekannt, erlaubt: {', '.join(STILE)}")
    elif (k.stil or "").strip().lower() == "bissig" and (
        k.zweck or ""
    ).strip().lower() != "eigene_leute":
        gruende.append("Stil bissig geht nur beim Zweck eigene_leute")
    return gruende


def vorschau(k: Kommentar) -> str:
    """Was der Trockenlauf je Kommentar zeigt: Titel, Aussage, Fassungen, Herkuenfte."""
    fassungen = [
        f"{name} ({len(wert.strip())} Zeichen)"
        for name, wert in (("kurz", k.kurz), ("mittel", k.mittel), ("lang", k.lang))
        if wert and wert.strip()
    ]
    zeilen = [
        f"wuerde angelegt: {k.titel}",
        f"    Aussage: {k.aussage.strip()}",
        f"    Fassungen: {', '.join(fassungen)}",
    ]
    if k.zweck or k.stil:
        zeilen.append(f"    Zweck: {k.zweck or '-'}, Stil: {k.stil or '-'}")
    zeilen += [
        f"    Herkunft: {h.link}" + (f" – {h.beschreibung}" if h.beschreibung else "")
        for h in k.herkuenfte
    ] or ["    Herkunft: keine"]
    return "\n".join(zeilen)


def anfrage(k: Kommentar, cc0_wortlaut: Optional[str] = CC0_WORTLAUT) -> Dict:
    """Der Body fuer ``addCommentary``, wie das Formular ihn schickt."""
    commentary = {
        "title": k.titel.strip(),
        "text": k.mittel.strip(),
        "references": [],
    }
    if k.kurz and k.kurz.strip():
        commentary["short_text"] = k.kurz.strip()
    if k.lang and k.lang.strip():
        commentary["long_text"] = k.lang.strip()
    if k.zweck and k.zweck.strip():
        commentary["zweck"] = k.zweck.strip().lower()
    if k.stil and k.stil.strip():
        commentary["style"] = k.stil.strip().lower()
    return {
        "commentary": commentary,
        "references": [
            {"reference_string": h.link, "description": h.beschreibung}
            for h in k.herkuenfte
        ],
        "statement_text": k.aussage.strip(),
        "cc0_wortlaut": cc0_wortlaut,
    }


# --- Liste zum Entfernen --------------------------------------------------


@dataclass(frozen=True)
class ZuEntfernen:
    """Ein Beitrag, der entfernt werden soll: Zeile der Liste, Typ und ID."""

    zeile: int
    typ: str
    id: str


def liste_lesen(pfad: Path) -> Tuple[List[ZuEntfernen], List[Fehler]]:
    """Je Zeile ``<typ> <id>``; Leerzeilen und alles ab ``#`` zaehlen nicht."""
    beitraege, fehler = [], []
    text = Path(pfad).read_text(encoding="utf-8-sig")
    for nummer, zeile in enumerate(text.splitlines(), start=1):
        teile = zeile.split("#", 1)[0].split()
        if not teile:
            continue
        if len(teile) != 2:
            fehler.append(Fehler(nummer, "erwartet: <typ> <id>"))
            continue
        typ, kennung = teile[0].lower(), teile[1]
        if typ not in BEITRAGSTYPEN:
            fehler.append(
                Fehler(
                    nummer, f"Typ {typ!r} unbekannt, erlaubt: {', '.join(BEITRAGSTYPEN)}"
                )
            )
            continue
        try:
            kennung = str(uuid.UUID(kennung))
        except ValueError:
            fehler.append(Fehler(nummer, f"{kennung!r} ist keine ID"))
            continue
        beitraege.append(ZuEntfernen(nummer, typ, kennung))
    return beitraege, fehler


# --- Ablauf ---------------------------------------------------------------


# Name des Sitzungs-Cookies des BFF (BFF/Program.cs, AddCookie).
SITZUNGS_COOKIE = "GutGesagtAuthCookie"
# Antworttext des Suchdienstes ohne Art.-9-Einwilligung (#489, dependencies.py).
ART9_EINWILLIGUNG_FEHLT = "art9_einwilligung_fehlt"
# Rate-Limit des Dienstes fuer addCommentary: 10 je Minute, 100 je Stunde
# (main.py, middleware/rate_limit.py). Nach einer Ablehnung eine Minute warten.
WARTEN_NACH_LIMIT = 61
VERSUCHE_BEI_LIMIT = 3


class ApiFehler(RuntimeError):
    """Das BFF hat eine Anfrage abgelehnt oder ist nicht erreichbar."""

    def __init__(self, status: Optional[int], meldung: str):
        super().__init__(f"HTTP {status}: {meldung}" if status else meldung)
        self.status = status


class Bestand(Protocol):
    """Was Import und Entfernen brauchen; das BFF oder im Test ein Speicher."""

    def kommentar_anlegen(self, daten: Dict) -> Dict: ...

    def ansehen(self, beitrag_id: str) -> Optional[Dict]: ...

    def gesperrte(self) -> List[Dict]: ...

    def entfernen(self, typ: str, beitrag_id: str) -> None: ...


@dataclass
class Bericht:
    """Was mit jeder Zeile geschah: angelegt bzw. entfernt (oder im Trockenlauf
    vorgesehen), uebersprungen, fehlgeschlagen; je Zeilennummer eine Notiz."""

    erledigt: List[Tuple[int, str]] = field(default_factory=list)
    uebersprungen: List[Tuple[int, str]] = field(default_factory=list)
    fehlgeschlagen: List[Tuple[int, str]] = field(default_factory=list)


def _anmelden_noetig(fehler: ApiFehler) -> bool:
    return fehler.status in (401, 403)


def _mit_wartezeit(aufruf: Callable[[], Dict], warten: Callable[[float], None]) -> Dict:
    """Bei 429 eine Minute warten und neu versuchen, hoechstens VERSUCHE_BEI_LIMIT-mal."""
    for versuch in range(VERSUCHE_BEI_LIMIT):
        try:
            return aufruf()
        except ApiFehler as fehler:
            if fehler.status != 429 or versuch == VERSUCHE_BEI_LIMIT - 1:
                raise
            print(f"Rate-Limit erreicht, warte {WARTEN_NACH_LIMIT} s …", file=sys.stderr)
            warten(WARTEN_NACH_LIMIT)
    raise AssertionError("nicht erreichbar")


def _vorhanden(antwort: Dict) -> Optional[Dict]:
    """
    Der vorhandene Kommentar, dessen Dublette der neue waere, oder None. Seit #541
    (v0.8.1) steht er unter "vorhanden", davor als "dublette"/"vorhanden_titel"/
    "vorhanden_eigen"; ein Dienst auf aelterem Stand antwortet so.
    """
    if antwort.get("vorhanden"):
        return antwort["vorhanden"]
    if antwort.get("dublette"):
        return {
            "titel": antwort.get("vorhanden_titel"),
            "eigen": bool(antwort.get("vorhanden_eigen")),
        }
    return None


def _aus_frueherem_lauf(vorhanden: Dict, k: Kommentar) -> bool:
    """Eigener vorhandener Kommentar mit demselben Titel: aus einem frueheren Lauf."""
    titel = (vorhanden.get("titel") or "").strip()
    return bool(vorhanden.get("eigen")) and titel == (k.titel or "").strip()


def importieren(
    kommentare: List[Kommentar],
    bestand: Optional[Bestand],
    ausfuehren: bool = False,
    warten: Callable[[float], None] = time.sleep,
) -> Bericht:
    """
    Je Kommentar einen ``addCommentary``-Aufruf; im Trockenlauf keinen.

    Ist schon ein sehr aehnlicher Kommentar da, legt der Server nichts an; das
    wird als uebersprungen gemeldet, nie mit ``trotz_dublette_von`` uebergangen.
    Ist der vorhandene vom selben Konto und mit demselben Titel (ein frueherer
    Lauf dieser Datei), haengt ein zweiter Aufruf mit ``vorhanden_nehmen`` ihn an
    die Aussage, wie im Formular "den eigenen nehmen". Einen nur aehnlichen
    eigenen Kommentar haengt das Skript nicht um; es meldet ihn. Ein abgelehnter Kommentar haelt den Rest nicht
    auf; ohne gueltige Anmeldung (401/403) bricht der Lauf mit ``ApiFehler`` ab.
    Bleibt das Rate-Limit nach den Versuchen (100 je Stunde erreicht), endet der
    Lauf, und die uebrigen stehen als nicht versucht im Bericht.
    """
    bericht = Bericht()
    cc0: Optional[str] = CC0_WORTLAUT

    def anlegen(k: Kommentar, **zusatz) -> Dict:
        nonlocal cc0

        def aufruf() -> Dict:
            return bestand.kommentar_anlegen({**anfrage(k, cc0), **zusatz})

        try:
            return _mit_wartezeit(aufruf, warten)
        except ApiFehler as fehler:
            if cc0 is None or CC0_UNBEKANNT not in str(fehler):
                raise
            print(
                f"Der Dienst kennt die CC0-Kennung {cc0} nicht (aeltere Version); "
                "lege ohne Kennung an.",
                file=sys.stderr,
            )
            cc0 = None
            return _mit_wartezeit(aufruf, warten)

    for index, k in enumerate(kommentare):
        if not ausfuehren:
            bericht.erledigt.append((k.zeile, vorschau(k)))
            continue
        try:
            antwort = anlegen(k)
            vorhanden = _vorhanden(antwort)
            if vorhanden and _aus_frueherem_lauf(vorhanden, k):
                genommen = anlegen(k, vorhanden_nehmen=antwort.get("id"))
                bericht.uebersprungen.append(
                    (
                        k.zeile,
                        f"eigener Kommentar mit gleichem Titel schon da ({antwort.get('id')}: "
                        f"{vorhanden.get('titel')}), nicht neu angelegt"
                        + (
                            f", an Aussage {genommen.get('statement_id')} gehaengt"
                            if genommen.get("verknuepft")
                            else ", Verknuepfung mit der Aussage gescheitert"
                        )
                        + f": {k.titel}",
                    )
                )
                if not genommen.get("verknuepft"):
                    bericht.fehlgeschlagen.append(
                        (k.zeile, f"nicht mit der Aussage verknuepft: {k.titel}")
                    )
                continue
        except ApiFehler as fehler:
            if _anmelden_noetig(fehler):
                raise
            if fehler.status == 429:
                for rest in kommentare[index:]:
                    bericht.fehlgeschlagen.append(
                        (
                            rest.zeile,
                            "nicht versucht: Rate-Limit (100 je Stunde), in einer "
                            f"Stunde mit derselben Datei erneut laufen lassen: {rest.titel}",
                        )
                    )
                break
            bericht.fehlgeschlagen.append((k.zeile, f"{fehler}: {k.titel}"))
            continue
        if vorhanden:
            bericht.uebersprungen.append(
                (
                    k.zeile,
                    f"aehnlicher Kommentar schon da ({antwort.get('id')}: "
                    f"{vorhanden.get('titel')}), nicht angelegt: {k.titel}",
                )
            )
            continue
        if not antwort.get("verknuepft", True) or not antwort.get("statement_id"):
            bericht.fehlgeschlagen.append(
                (
                    k.zeile,
                    f"angelegt als {antwort.get('id')}, aber nicht mit der Aussage "
                    f"verknuepft: {k.titel}",
                )
            )
            continue
        notiz = (
            f"angelegt als {antwort.get('id')} an Aussage "
            f"{antwort.get('statement_id')}: {k.titel}"
        )
        if cc0 is None:
            notiz += " (ohne CC0-Kennung)"
        if (antwort.get("statement_text") or "").strip() != k.aussage.strip():
            notiz += f" (an vorhandene Aussage: {antwort.get('statement_text')})"
        bericht.erledigt.append((k.zeile, notiz))
    return bericht


def entfernen(
    beitraege: List[ZuEntfernen], bestand: Bestand, ausfuehren: bool = False
) -> Bericht:
    """
    Je Beitrag erst ansehen, gesperrte in der Admin-Liste der gesperrten. Passt der
    Typ nicht zum Beitrag, bleibt er stehen (der Server nimmt den Typ nur fuers
    Log und entfernte sonst, was die ID trifft). Was weder sichtbar noch gesperrt
    ist (geloescht oder nie da), wird nie entfernt. Im Trockenlauf den Titel
    zeigen, sonst den Beitrag entfernen; der Titel steht auch dann dabei.
    """
    bericht = Bericht()
    gesperrte: Optional[Dict[str, Dict]] = None
    for e in beitraege:
        try:
            beitrag = bestand.ansehen(e.id)
            zustand = ""
            if beitrag is None:
                if gesperrte is None:
                    gesperrte = {str(b.get("id")): b for b in bestand.gesperrte()}
                beitrag = gesperrte.get(e.id)
                zustand = " (gesperrt)"
            if beitrag is None:
                bericht.uebersprungen.append(
                    (
                        e.zeile,
                        "nicht gefunden (weder sichtbar noch gesperrt), nicht "
                        f"entfernt: {e.typ} {e.id}",
                    )
                )
                continue
            typ = beitrag.get("content_type")
            if typ != e.typ:
                bericht.fehlgeschlagen.append(
                    (e.zeile, f"Typ passt nicht, der Beitrag ist {typ}: {e.typ} {e.id}")
                )
                continue
            beschreibung = (
                f"{e.typ} {e.id}{zustand} „{beitrag.get('title') or '(ohne Titel)'}“"
            )
            if not ausfuehren:
                bericht.erledigt.append((e.zeile, f"wuerde entfernt: {beschreibung}"))
                continue
            bestand.entfernen(e.typ, e.id)
            bericht.erledigt.append((e.zeile, f"entfernt: {beschreibung}"))
        except ApiFehler as fehler:
            if _anmelden_noetig(fehler):
                raise
            if fehler.status == 404:
                bericht.uebersprungen.append(
                    (e.zeile, f"nicht gefunden oder schon entfernt: {e.typ} {e.id}")
                )
            else:
                bericht.fehlgeschlagen.append((e.zeile, f"{fehler}: {e.typ} {e.id}"))
    return bericht


# --- BFF ------------------------------------------------------------------


class _KeineWeiterleitung(urllib.request.HTTPRedirectHandler):
    """
    Folgt keiner Weiterleitung. urllib kopierte sonst die Kopfzeilen, auch das
    Cookie, auf die neue Adresse, selbst zu einem anderen Host oder ueber http.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url,
            code,
            f"Weiterleitung nach {urlsplit(newurl).netloc or newurl}, nicht gefolgt: "
            "--adresse auf die Adresse setzen, die direkt antwortet",
            headers,
            None,
        )


class BffBestand:
    """
    Der Bestand ueber das BFF, angemeldet mit der Sitzung eines Browsers oder,
    im Dev-Stack, wie im Login-Formular. Das Cookie bleibt im Speicher dieses
    Prozesses und wird nie ausgegeben.
    """

    def __init__(self, adresse: str, timeout: float = 60):
        self.adresse = adresse.rstrip("/")
        self.timeout = timeout
        self._cookie: Optional[str] = None
        self._oeffner = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            _KeineWeiterleitung(),
        )

    def _kopfzeilen(self) -> Dict[str, str]:
        kopf = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._cookie:
            kopf["Cookie"] = self._cookie
        return kopf

    def _anfrage(self, methode: str, pfad: str, daten: Optional[Dict] = None) -> Dict:
        anfrage = urllib.request.Request(
            f"{self.adresse}{pfad}",
            data=json.dumps(daten).encode("utf-8") if daten is not None else None,
            headers=self._kopfzeilen(),
            method=methode,
        )
        try:
            with self._oeffner.open(anfrage, timeout=self.timeout) as antwort:
                text = antwort.read().decode("utf-8")
        except urllib.error.HTTPError as fehler:
            raise ApiFehler(fehler.code, _fehlertext(fehler)) from None
        except (urllib.error.URLError, OSError) as fehler:
            raise ApiFehler(None, f"{self.adresse} nicht erreichbar: {fehler}") from None
        try:
            antwort = json.loads(text) if text else {}
        except ValueError:
            raise ApiFehler(
                None, f"Antwort von {pfad} ist kein JSON (stimmt --adresse?)"
            ) from None
        if not isinstance(antwort, dict):
            raise ApiFehler(None, f"Antwort von {pfad} unerwartet (stimmt --adresse?)")
        return antwort

    def sitzung_nutzen(self, cookie: str) -> None:
        """
        Die Sitzung eines Browsers: der Wert von ``GutGesagtAuthCookie`` oder eine
        ganze Cookie-Zeile (``name=wert; …``, auch mit ``Cookie:`` davor). Das BFF
        prueft weder Antiforgery-Token noch Origin (CORS gilt nur im Browser); das
        Cookie allein reicht.
        """
        cookie = cookie.strip()
        if cookie.lower().startswith("cookie:"):
            cookie = cookie[len("cookie:") :].strip()
        if not cookie:
            raise ApiFehler(None, "Die Sitzung ist leer")
        if any(ord(z) < 32 for z in cookie):
            raise ApiFehler(None, "Die Sitzung enthaelt Zeilenumbrueche oder Steuerzeichen")
        if not cookie.isascii():
            raise ApiFehler(
                None,
                "Die Sitzung enthaelt Zeichen ausserhalb von ASCII (etwa „…“): "
                "Wert vollstaendig kopiert?",
            )
        if "=" not in cookie.split(";")[0]:
            cookie = f"{SITZUNGS_COOKIE}={cookie}"
        self._cookie = cookie

    def anmelden(self, email: str, passwort: str) -> None:
        """Direktanmeldung mit Mail und Passwort; nur im Dev-Stack eingeschaltet."""
        try:
            self._anfrage(
                "POST",
                "/api/auth/login/managed",
                {"email": email, "password": passwort},
            )
        except ApiFehler as fehler:
            if fehler.status == 404:
                raise ApiFehler(
                    404,
                    "Direktanmeldung ist auf dieser Instanz aus (Test und Produktion: "
                    "--sitzung-datei) oder --adresse zeigt nicht auf Gut gesagt",
                ) from None
            raise

    def wer(self) -> Dict:
        """Wer angemeldet ist (``/api/user-info`` des BFF)."""
        try:
            return self._anfrage("GET", "/api/user-info")
        except ApiFehler as fehler:
            if fehler.status == 401:
                raise ApiFehler(
                    401,
                    "nicht angemeldet: Sitzung abgelaufen, unvollstaendig kopiert "
                    "oder von einer anderen Adresse",
                ) from None
            raise

    def kommentar_anlegen(self, daten: Dict) -> Dict:
        pfad = "/api/v1/commentary/addCommentary"
        try:
            antwort = self._anfrage("POST", pfad, daten)
        except ApiFehler as fehler:
            if fehler.status == 403 and ART9_EINWILLIGUNG_FEHLT in str(fehler):
                raise ApiFehler(
                    403,
                    "Das Konto hat noch nicht in die Art.-9-Einwilligung eingewilligt: "
                    "einmal in der App anmelden und unter /einwilligung einwilligen "
                    "(docs/ART9_EINWILLIGUNG.md)",
                ) from None
            raise
        if "id" not in antwort:
            raise ApiFehler(None, f"Antwort von {pfad} ohne id (stimmt --adresse?)")
        return antwort

    def ansehen(self, beitrag_id: str) -> Optional[Dict]:
        """Der Beitrag wie unter /beitrag/:id; None, wenn gesperrt, geloescht oder nie da."""
        try:
            return self._anfrage("GET", f"/api/v1/content/beitrag/{beitrag_id}")
        except ApiFehler as fehler:
            if fehler.status == 404:
                return None
            raise

    def gesperrte(self) -> List[Dict]:
        """Alle gesperrten Beitraege mit Typ und Titel (Admin-Liste der Moderation)."""
        try:
            antwort = self._anfrage("GET", "/api/v1/moderation/gesperrt")
        except ApiFehler as fehler:
            if fehler.status == 403:
                raise ApiFehler(403, "Entfernen braucht ein Admin-Konto") from None
            raise
        beitraege = antwort.get("beitraege")
        if not isinstance(beitraege, list):
            raise ApiFehler(None, "Antwort der gesperrten Beitraege unerwartet")
        return beitraege

    def entfernen(self, typ: str, beitrag_id: str) -> None:
        try:
            self._anfrage("DELETE", f"/api/v1/moderation/content/{typ}/{beitrag_id}")
        except ApiFehler as fehler:
            if fehler.status == 403:
                raise ApiFehler(403, "Entfernen braucht ein Admin-Konto") from None
            raise


def _fehlertext(fehler: "urllib.error.HTTPError") -> str:
    """Die ``detail``-Meldung der API, sonst der HTTP-Grund. Nie den ganzen Body."""
    try:
        detail = json.loads(fehler.read().decode("utf-8")).get("detail")
    except (ValueError, AttributeError, OSError):
        detail = None
    if isinstance(detail, list):  # Validierungsfehler von FastAPI
        detail = "; ".join(str(d.get("msg", d)) for d in detail)
    return str(detail or fehler.reason)


# --- Aufruf ---------------------------------------------------------------


def _ausgeben(
    bericht: Bericht,
    fehler: List[Fehler],
    ausfuehren: bool,
    was: str,
    hinweise: Optional[List[Fehler]] = None,
) -> None:
    ausgabe = (
        [(f.zeile, f"Fehler: {f.grund}") for f in fehler]
        + [(h.zeile, f"Hinweis: {h.grund}") for h in hinweise or []]
        + list(bericht.erledigt)
        + [(z, f"uebersprungen, {t}") for z, t in bericht.uebersprungen]
        + [(z, f"Fehler: {t}") for z, t in bericht.fehlgeschlagen]
    )
    for zeile, text in sorted(ausgabe):
        print(f"Zeile {zeile}: {text}")
    print(
        f"{'' if ausfuehren else 'Trockenlauf, '}"
        f"{was if ausfuehren else 'wuerden ' + was}: {len(bericht.erledigt)}, "
        f"uebersprungen: {len(bericht.uebersprungen)}, "
        f"Fehler: {len(fehler) + len(bericht.fehlgeschlagen)}"
        + (f", Hinweise: {len(hinweise)}" if hinweise else "")
    )
    if not ausfuehren:
        print("Nichts geschrieben; mit --ausfuehren wird geschrieben.")


# Hosts, zu denen das Passwort auch ohne TLS gehen darf: nur dieser Rechner.
_LOKALE_HOSTS = ("localhost", "127.0.0.1", "::1")


def _adresse_pruefen(adresse: str) -> Optional[str]:
    """Warum die Adresse nicht taugt, oder None. Passwort und Sitzung gehen nie im Klartext ins Netz."""
    teile = urlsplit(adresse)
    if teile.scheme not in ("http", "https") or not teile.hostname:
        return f"--adresse {adresse} ist keine http(s)-Adresse"
    if teile.scheme == "http" and teile.hostname not in _LOKALE_HOSTS:
        return f"--adresse {adresse}: ausser fuer localhost nur https, sonst gingen Passwort oder Sitzung unverschluesselt"
    return None


def main(
    argv: Optional[List[str]] = None,
    bestand_bauen: Callable[[str], BffBestand] = BffBestand,
) -> int:
    parser = argparse.ArgumentParser(
        description="Startbestand aus einer Markdown-Datei als Kommentare anlegen "
        "oder mit --entfernen Beitraege endgueltig entfernen.",
    )
    parser.add_argument(
        "datei", type=Path, help="Markdown mit Aussagen und Kommentaren"
    )
    parser.add_argument(
        "--entfernen",
        action="store_true",
        help="DATEI ist eine Liste '<typ> <id>' je Zeile; die Beitraege entfernen (Admin)",
    )
    parser.add_argument(
        "--email",
        help="nur lokaler Dev-Stack: Direktanmeldung mit Mail und Passwort",
    )
    parser.add_argument(
        "--sitzung-datei",
        type=Path,
        help="Datei mit dem Sitzungs-Cookie des Browsers (sonst GUTGESAGT_SITZUNG)",
    )
    parser.add_argument(
        "--adresse",
        default="http://localhost:5054",
        help="Adresse von BFF oder Frontend (Standard: %(default)s)",
    )
    parser.add_argument(
        "--ausfuehren",
        action="store_true",
        help="wirklich schreiben; ohne nur ein Trockenlauf",
    )
    args = parser.parse_args(argv)

    sitzung = os.environ.get("GUTGESAGT_SITZUNG")
    if args.sitzung_datei:
        try:
            sitzung = args.sitzung_datei.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"Sitzung nicht lesbar: {e}", file=sys.stderr)
            return 2
    if args.email and sitzung:
        parser.error("entweder --email oder eine Sitzung, nicht beides")
    if (args.ausfuehren or args.entfernen) and not (args.email or sitzung):
        parser.error(
            "--ausfuehren und --entfernen brauchen eine Anmeldung: "
            "--sitzung-datei (oder GUTGESAGT_SITZUNG), lokal --email"
        )
    unpassend = _adresse_pruefen(args.adresse)
    if unpassend:
        print(f"Abgebrochen: {unpassend}", file=sys.stderr)
        return 2

    hinweise: List[Fehler] = []
    try:
        if args.entfernen:
            beitraege, fehler = liste_lesen(args.datei)
        else:
            kommentare, fehler = datei_lesen(args.datei, hinweise)
    except (OSError, UnicodeDecodeError, DateiUnlesbar) as e:
        print(f"Datei nicht lesbar: {e}", file=sys.stderr)
        return 2

    # Der Trockenlauf des Imports prueft nur lokal und braucht weder Server
    # noch Passwort; der des Entfernens liest die Titel, angemeldet.
    bestand = None
    if args.ausfuehren or args.entfernen:
        bestand = bestand_bauen(args.adresse)
    try:
        if bestand is not None:
            if sitzung:
                bestand.sitzung_nutzen(sitzung)
            else:
                passwort = os.environ.get("GUTGESAGT_PASSWORT") or getpass.getpass(
                    f"Passwort fuer {args.email}: "
                )
                bestand.anmelden(args.email, passwort)
            wer = bestand.wer()
            print(
                f"Angemeldet als {wer.get('userName') or wer.get('userId')}"
                f"{' (Admin)' if wer.get('isAdmin') else ''}"
            )
            if args.entfernen and not wer.get("isAdmin"):
                raise ApiFehler(403, "Entfernen braucht ein Admin-Konto")
        if args.entfernen:
            bericht = entfernen(beitraege, bestand, ausfuehren=args.ausfuehren)
            was = "entfernt"
        else:
            bericht = importieren(kommentare, bestand, ausfuehren=args.ausfuehren)
            was = "angelegt"
    except ApiFehler as e:
        print(f"Abgebrochen: {e}", file=sys.stderr)
        return 2

    _ausgeben(bericht, fehler, args.ausfuehren, was, hinweise)
    return 1 if fehler or bericht.fehlgeschlagen else 0


if __name__ == "__main__":
    sys.exit(main())
