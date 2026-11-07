#!/usr/bin/env python3
"""
Startbestand einspielen und Altbeitraege entfernen (#592).

Import: liest eine Markdown-Datei mit Aussagen und je Aussage einem oder mehreren
Kommentaren und legt jeden Kommentar ueber dieselbe API an wie das
Kommentar-Formular, als Antwort auf seine Aussage und mit seinen Herkuenften
(``POST /api/v1/commentary/addCommentary``). Die Aussage legt der Server an oder
findet die vorhandene; eine vorhandene Herkunft nimmt er wieder. Angemeldet wird
am BFF wie im Login-Formular, fuer den Startbestand mit einem Startkonto.

Entfernen (``--entfernen``): liest je Zeile ``<typ> <id>`` und entfernt den
Beitrag endgueltig ueber die Admin-API
(``DELETE /api/v1/moderation/content/{typ}/{id}``); dafuer braucht es ein
Admin-Konto. Im Frontend gibt es dafuer keinen Knopf, nur das Sperren.

Beides ist ohne ``--ausfuehren`` ein Trockenlauf, der nichts schreibt. Aufruf,
Dateiformat und Exit-Codes: ``mvp/SCRIPTS.md``.

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
    """Ein Eintrag der Datei, der nicht angelegt oder entfernt werden kann, und warum."""

    zeile: int
    grund: str


# --- Markdown lesen -------------------------------------------------------

# "## 1.1 „Aussage“" oder "## Aussage: …"; andere "##"-Ueberschriften (etwa
# "## Stand") gehoeren nicht zum Bestand.
_AUSSAGE = re.compile(
    r"^##\s+(?:(?:\d+(?:\.\d+)*\.?)\s+(?P<nummeriert>.+)|Aussage:\s*(?P<benannt>.+))$",
    re.I,
)
_KOMMENTAR = re.compile(r"^###\s+(?P<rest>.*)$")
_KOMMENTAR_TITEL = re.compile(r"^Kommentar:\s*(?P<titel>.+)$", re.I)
_UEBERSCHRIFT = re.compile(r"^#{1,6}\s")
# Ein Feld: "**Kurz:** …", "Kurz: …" oder "- kurz: …". Vor "Herkunft" darf ein
# Wort stehen und dahinter eine Klammer ("Zweite Herkunft (Anteil …):").
_FELD = re.compile(
    r"^\s*(?:[-*]\s+)?(?:\*\*)?"
    r"(?P<name>titel|kurz|mittel|lang|zweck|stil|(?:\w+\s+)?herkunft(?:\s*\([^)]*\))?)"
    r"\s*:\s*(?:\*\*)?\s*(?P<wert>.*)$",
    re.I,
)
_LINK = re.compile(r"https?://[^\s<>|]+")
_MD_LINK = re.compile(r"\[(?P<text>[^\]]*)\]\((?P<link>https?://[^\s)]+)\)")
_SPITZ_LINK = re.compile(r"<(?P<link>https?://[^>\s]+)>")
# Was zwischen Link und Beschreibung steht und nicht zur Beschreibung gehoert.
_TRENNER = " \t-–—:|"
# Pruefvermerke fuer das Gegenlesen gehoeren nicht in die Beschreibung.
_PRUEFVERMERK = re.compile(r"\s*\bgeprüft:.*$", re.I | re.S)
_ANFUEHRUNG = {"„": "“", "“": "”", '"': '"', "»": "«", "«": "»", "‚": "‘"}
# Felder, deren Wert auf Folgezeilen weitergeht (bis zur Leerzeile).
_MEHRZEILIG = ("kurz", "mittel", "lang")


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
    link = treffer.group(0).rstrip(".,;:!?)'\"")
    rest = wert[: treffer.start()] + wert[treffer.start() + len(link) :]
    beschreibung = _PRUEFVERMERK.sub("", rest).strip(_TRENNER)
    return Herkunft(link, beschreibung or None)


def datei_lesen(pfad: Path) -> Tuple[List[Kommentar], List[Fehler]]:
    """
    Die Kommentare der Datei und was an ihnen nicht stimmt.

    Gelesen wird die Gliederung ``## <Nummer> „Aussage“`` (oder ``## Aussage: …``),
    darunter je Kommentar eine ``###``-Ueberschrift und die Felder Titel, Kurz,
    Mittel, Lang, Herkunft (mehrfach), Zweck, Stil. Alles andere (Einleitung,
    ``#``-Bloecke, Pruefvermerke, Hinweise) wird uebergangen. Ein Kommentar mit
    Fehler kommt nicht in die erste Liste.
    """
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
                continue
            treffer = _KOMMENTAR.match(zeile.strip())
            if treffer and aussage is not None:
                aktuell = Kommentar(zeile=nummer, aussage=aussage)
                benannt = _KOMMENTAR_TITEL.match(treffer.group("rest").strip())
                if benannt:
                    aktuell.titel = benannt.group("titel").strip()
                kommentare.append(aktuell)
                continue
            # Eine andere Ueberschrift beendet Aussage und Kommentar.
            if zeile.startswith("## ") or zeile.startswith("# "):
                aussage = None
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
                if herkunft is None:
                    herkunft_fehler.setdefault(aktuell.zeile, []).append(
                        f"Herkunft in Zeile {nummer} ohne http(s)-Link"
                    )
                else:
                    aktuell.herkuenfte.append(herkunft)
                continue
            setattr(aktuell, name, wert or None)
            if name in _MEHRZEILIG:
                offenes_feld = name
            continue
        if offenes_feld:
            bisher = getattr(aktuell, offenes_feld) or ""
            setattr(aktuell, offenes_feld, f"{bisher}\n{zeile.strip()}".strip())
        # Sonst: Vermerk zum Gegenlesen, gehoert nicht zum Kommentar.

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
    if not (k.mittel or "").strip():
        gruende.append("keine Mittelfassung")
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
class Eintrag:
    """Ein Beitrag, der entfernt werden soll."""

    zeile: int
    typ: str
    id: str


def liste_lesen(pfad: Path) -> Tuple[List[Eintrag], List[Fehler]]:
    """Je Zeile ``<typ> <id>``; Leerzeilen und alles ab ``#`` zaehlen nicht."""
    eintraege, fehler = [], []
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
        eintraege.append(Eintrag(nummer, typ, kennung))
    return eintraege, fehler


# --- Ablauf ---------------------------------------------------------------


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

    def titel(self, beitrag_id: str) -> Optional[str]: ...

    def entfernen(self, typ: str, beitrag_id: str) -> None: ...


@dataclass
class Bericht:
    """Was mit jedem Eintrag geschah; ``angelegt`` traegt je Eintrag eine Notiz."""

    angelegt: List[Tuple[int, str]] = field(default_factory=list)
    uebersprungen: List[Tuple[int, str]] = field(default_factory=list)
    fehlgeschlagen: List[Tuple[int, str]] = field(default_factory=list)


def _anmelden_noetig(fehler: ApiFehler) -> bool:
    return fehler.status in (401, 403)


def _mit_wartezeit(
    aufruf: Callable[[], Dict], warten: Callable[[float], None]
) -> Dict:
    for versuch in range(VERSUCHE_BEI_LIMIT):
        try:
            return aufruf()
        except ApiFehler as fehler:
            if fehler.status != 429 or versuch == VERSUCHE_BEI_LIMIT - 1:
                raise
            print(
                f"Rate-Limit erreicht, warte {WARTEN_NACH_LIMIT} s …", file=sys.stderr
            )
            warten(WARTEN_NACH_LIMIT)
    raise AssertionError("nicht erreichbar")


def importieren(
    kommentare: List[Kommentar],
    bestand: Optional[Bestand],
    ausfuehren: bool = False,
    warten: Callable[[float], None] = time.sleep,
) -> Bericht:
    """
    Je Kommentar einen ``addCommentary``-Aufruf; im Trockenlauf keinen.

    Ist schon ein sehr aehnlicher Kommentar da, legt der Server nichts an; das
    wird als uebersprungen gemeldet, nicht mit ``trotz_dublette_von`` uebergangen.
    Ein abgelehnter Kommentar haelt den Rest nicht auf; ohne gueltige Anmeldung
    (401/403) bricht der Lauf mit ``ApiFehler`` ab.
    """
    bericht = Bericht()
    cc0: Optional[str] = CC0_WORTLAUT
    for k in kommentare:
        if not ausfuehren:
            bericht.angelegt.append((k.zeile, f"wuerde angelegt: {k.titel}"))
            continue
        try:
            try:
                antwort = _mit_wartezeit(
                    lambda: bestand.kommentar_anlegen(anfrage(k, cc0)), warten
                )
            except ApiFehler as fehler:
                if cc0 is None or CC0_UNBEKANNT not in str(fehler):
                    raise
                print(
                    f"Der Dienst kennt die CC0-Kennung {cc0} nicht (aeltere "
                    "Version); lege ohne Kennung an.",
                    file=sys.stderr,
                )
                cc0 = None
                antwort = _mit_wartezeit(
                    lambda: bestand.kommentar_anlegen(anfrage(k, cc0)), warten
                )
        except ApiFehler as fehler:
            if _anmelden_noetig(fehler):
                raise
            bericht.fehlgeschlagen.append((k.zeile, f"{fehler}: {k.titel}"))
            continue
        # Seit #541 (v0.8.1) steht der vorhandene unter "vorhanden", davor als
        # "dublette"/"vorhanden_titel"; ein Dienst auf aelterem Stand antwortet so.
        vorhanden = antwort.get("vorhanden") or (
            {"titel": antwort.get("vorhanden_titel")} if antwort.get("dublette") else None
        )
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
        bericht.angelegt.append((k.zeile, notiz))
    return bericht


def entfernen(
    eintraege: List[Eintrag], bestand: Bestand, ausfuehren: bool = False
) -> Bericht:
    """
    Im Trockenlauf je Eintrag den Titel zeigen, sonst den Beitrag entfernen.

    Gesperrte Beitraege zeigt die oeffentliche Ansicht nicht; im Trockenlauf
    stehen sie als "nicht gefunden oder gesperrt" da, entfernen laesst sich ein
    gesperrter trotzdem.
    """
    bericht = Bericht()
    for e in eintraege:
        try:
            if not ausfuehren:
                titel = bestand.titel(e.id)
                if titel is None:
                    bericht.uebersprungen.append(
                        (e.zeile, f"nicht gefunden oder gesperrt: {e.typ} {e.id}")
                    )
                else:
                    bericht.angelegt.append(
                        (e.zeile, f"wuerde entfernt: {e.typ} {e.id} „{titel}“")
                    )
                continue
            bestand.entfernen(e.typ, e.id)
            bericht.angelegt.append((e.zeile, f"entfernt: {e.typ} {e.id}"))
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


class BffBestand:
    """
    Der Bestand ueber das BFF, angemeldet wie im Login-Formular (E-Mail und
    Passwort). Das Auth-Cookie bleibt im Speicher dieses Prozesses.
    """

    def __init__(self, adresse: str, timeout: float = 60):
        self.adresse = adresse.rstrip("/")
        self.timeout = timeout
        self._oeffner = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def _kopfzeilen(self) -> Dict[str, str]:
        return {"Content-Type": "application/json", "Accept": "application/json"}

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
            raise ApiFehler(
                None, f"{self.adresse} nicht erreichbar: {fehler}"
            ) from None
        try:
            antwort = json.loads(text) if text else {}
        except ValueError:
            raise ApiFehler(
                None, f"Antwort von {pfad} ist kein JSON (stimmt --adresse?)"
            ) from None
        if not isinstance(antwort, dict):
            raise ApiFehler(None, f"Antwort von {pfad} unerwartet (stimmt --adresse?)")
        return antwort

    def anmelden(self, email: str, passwort: str) -> None:
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
                    "Login mit Beta-Zugang ist auf dieser Instanz aus oder "
                    "--adresse zeigt nicht auf Gut gesagt",
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

    def titel(self, beitrag_id: str) -> Optional[str]:
        try:
            antwort = self._anfrage("GET", f"/api/v1/content/beitrag/{beitrag_id}")
        except ApiFehler as fehler:
            if fehler.status == 404:
                return None
            raise
        return antwort.get("title") or "(ohne Titel)"

    def entfernen(self, typ: str, beitrag_id: str) -> None:
        try:
            self._anfrage("DELETE", f"/api/v1/moderation/content/{typ}/{beitrag_id}")
        except ApiFehler as fehler:
            if fehler.status == 403:
                raise ApiFehler(
                    403, "Entfernen braucht ein Admin-Konto (--email)"
                ) from None
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
    bericht: Bericht, fehler: List[Fehler], ausfuehren: bool, was: str
) -> None:
    ausgabe = (
        [(f.zeile, f"Fehler: {f.grund}") for f in fehler]
        + list(bericht.angelegt)
        + [(z, f"uebersprungen, {t}") for z, t in bericht.uebersprungen]
        + [(z, f"Fehler: {t}") for z, t in bericht.fehlgeschlagen]
    )
    for zeile, text in sorted(ausgabe):
        print(f"Zeile {zeile}: {text}")
    print(
        f"{'' if ausfuehren else 'Trockenlauf, '}"
        f"{was if ausfuehren else 'wuerden ' + was}: {len(bericht.angelegt)}, "
        f"uebersprungen: {len(bericht.uebersprungen)}, "
        f"Fehler: {len(fehler) + len(bericht.fehlgeschlagen)}"
    )
    if not ausfuehren:
        print("Nichts geschrieben; mit --ausfuehren wird geschrieben.")


# Hosts, zu denen das Passwort auch ohne TLS gehen darf: nur dieser Rechner.
_LOKALE_HOSTS = ("localhost", "127.0.0.1", "::1")


def _adresse_pruefen(adresse: str) -> Optional[str]:
    """Warum die Adresse nicht taugt, oder None. Das Passwort geht nie im Klartext ins Netz."""
    teile = urlsplit(adresse)
    if teile.scheme not in ("http", "https") or not teile.hostname:
        return f"--adresse {adresse} ist keine http(s)-Adresse"
    if teile.scheme == "http" and teile.hostname not in _LOKALE_HOSTS:
        return f"--adresse {adresse}: ausser fuer localhost nur https, sonst ginge das Passwort unverschluesselt"
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
        "--email", help="Konto: Startkonto beim Import, Admin beim Entfernen"
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

    if (args.ausfuehren or args.entfernen) and not args.email:
        parser.error("--ausfuehren und --entfernen brauchen --email")
    unpassend = _adresse_pruefen(args.adresse)
    if unpassend:
        print(f"Abgebrochen: {unpassend}", file=sys.stderr)
        return 2

    try:
        if args.entfernen:
            eintraege, fehler = liste_lesen(args.datei)
        else:
            kommentare, fehler = datei_lesen(args.datei)
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
            passwort = os.environ.get("GUTGESAGT_PASSWORT") or getpass.getpass(
                f"Passwort fuer {args.email}: "
            )
            bestand.anmelden(args.email, passwort)
        if args.entfernen:
            bericht = entfernen(eintraege, bestand, ausfuehren=args.ausfuehren)
            was = "entfernt"
        else:
            bericht = importieren(kommentare, bestand, ausfuehren=args.ausfuehren)
            was = "angelegt"
    except ApiFehler as e:
        print(f"Abgebrochen: {e}", file=sys.stderr)
        return 2

    _ausgeben(bericht, fehler, args.ausfuehren, was)
    return 1 if fehler or bericht.fehlgeschlagen else 0


if __name__ == "__main__":
    sys.exit(main())
