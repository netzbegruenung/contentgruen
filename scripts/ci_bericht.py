"""CI-Bericht: kommentiert bei einem roten Pull-Request-Lauf die roten Schritte in den PR.

Sichtbar sind je rotem Schritt die Fehlerzeilen, das Log ist eingeklappt. Ist der Fehler
derselbe wie im letzten Bericht des PRs (Fingerabdruck als HTML-Kommentar am Ende), kommt
nur ein Einzeiler mit Verweis auf diesen Bericht.

Letzter Schritt von ``.woodpecker/ci.yaml`` (docs/CI.md, "CI-Bericht"). Liest
``.ci/<schritt>.log`` und ``.ci/<schritt>.status``, die ``scripts/ci-protokoll.sh``
schreibt. Nur Standardbibliothek: der Bericht kommt auch, wenn die Installation scheiterte.

Aufruf: python3 scripts/ci_bericht.py <schritt> ...  (die Schritte in Pipeline-Reihenfolge)
Umgebung: CI_FORGE_URL, CI_REPO_OWNER, CI_REPO_NAME, CI_COMMIT_PULL_REQUEST,
CI_COMMIT_SHA, CI_PIPELINE_NUMBER, CI_PIPELINE_URL (setzt Woodpecker),
FORGEJO_TOKEN (Secret forgejo_ci_bericht_token).
"""

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional, Sequence

ZEILEN_JE_SCHRITT = 80
# Sichtbare Fehlerzeilen je Schritt; der Fingerabdruck nimmt alle
FEHLERZEILEN_JE_SCHRITT = 20
# Laengere Zeilen werden gekuerzt, damit auch viele rote Schritte unter MAX_ZEICHEN passen
ZEICHEN_JE_ZEILE = 1000
# Forgejo nimmt deutlich mehr an; so bleibt der Kommentar lesbar.
MAX_ZEICHEN = 60_000
ZEITLIMIT_S = 30
ERSATZ = "[Secret entfernt]"
PROTOKOLL = pathlib.Path(".ci")

# OSC (ESC ] ... BEL oder ESC \, abgeschnitten auch ohne Ende), CSI (ESC [ ... Endzeichen),
# uebrige Zwei-Zeichen-Folgen
_ANSI = re.compile(
    r"\x1b\][^\x07\x1b\n]*(?:\x07|\x1b\\)?|\x1b\[[0-?]*[ -/]*[@-~]|\x1b[@-_]"
)
# Steuerzeichen ausser Tab und Zeilenumbruch, C1, Null-Breite- und Bidi-Zeichen
# ("Trojan Source"), die die Anzeige verdrehen koennen
_STEUERZEICHEN = re.compile(
    r"[\x00-\x08\x0b-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2066-\u2069]"
)

# pytest-Kurzzusammenfassung: Zeilen, die (nach einem Zeitstempel) mit FAILED/ERROR beginnen
_FEHLERZEILE = re.compile(r"^(?:\S*\d:\d\d\S*\s+)?(?:FAILED|ERROR)\b")
# Was sich von Lauf zu Lauf aendert, ohne dass der Fehler ein anderer ist: Zeitstempel,
# Uhrzeiten, Laufzeiten, Speicheradressen
_VERAENDERLICH = re.compile(
    r"\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:[.,]\d+)?(?:Z|[+-]\d\d:?\d\d)?"
    r"|\b\d+:\d\d(?::\d\d)?(?:[.,]\d+)?\b"
    r"|\b\d+(?:[.,]\d+)?\s*(?:ms|s|secs?|seconds?|min)\b"
    r"|\b0x[0-9a-fA-F]+\b"
)
_MARKE = "<!-- ci-bericht fingerabdruck={} -->"
# Nur am Ende des Kommentars: im Log kann die Zeichenfolge auch stehen
_MARKE_LESEN = re.compile(r"<!-- ci-bericht fingerabdruck=([0-9a-f]+) -->\s*\Z")


@dataclass
class Schritt:
    name: str
    # None: nicht gelaufen (keine Ausgabe) oder abgebrochen (Ausgabe ohne Exit-Code)
    exit_code: Optional[int]
    ausgabe: Optional[str]

    @property
    def gelaufen(self) -> bool:
        return self.ausgabe is not None

    @property
    def rot(self) -> bool:
        """Gelaufen und nicht gruen: Exit-Code ungleich 0 oder abgebrochen."""
        return self.gelaufen and self.exit_code != 0


def ausgabe_bereinigen(text: str, geheimnisse: Sequence[str]) -> str:
    """Ohne ANSI-Codes und Steuerzeichen, Fortschrittszeilen (\\r) auf ihrem letzten
    Stand, Werte der Secrets ersetzt."""
    for geheimnis in geheimnisse:
        if geheimnis:
            text = text.replace(geheimnis, ERSATZ)
    text = _ANSI.sub("", text).replace("\r\n", "\n")
    text = "\n".join(zeile.rsplit("\r", 1)[-1] for zeile in text.split("\n"))
    return _STEUERZEICHEN.sub("", text)


def _codeblock(text: str) -> str:
    """Zaun laenger als jede Backtick-Folge im Text, damit der Block nicht vorzeitig endet."""
    laengste = max((len(m) for m in re.findall(r"`+", text)), default=0)
    zaun = "`" * max(3, laengste + 1)
    return f"{zaun}text\n{text}\n{zaun}"


def _ende(text: str, zeilen: int) -> tuple[str, int]:
    """Die letzten ``zeilen`` Zeilen (jede hoechstens ZEICHEN_JE_ZEILE lang) und wie
    viele Zeilen davor ausgelassen sind."""
    alle = text.rstrip("\n").split("\n")
    ende = [
        z if len(z) <= ZEICHEN_JE_ZEILE else z[:ZEICHEN_JE_ZEILE] + "…"
        for z in alle[-zeilen:]
    ]
    return "\n".join(ende), max(0, len(alle) - zeilen)


def _zustand(schritt: Schritt) -> str:
    return (
        "abgebrochen" if schritt.exit_code is None else f"Exit-Code {schritt.exit_code}"
    )


def fehlerzeilen(ausgabe: str) -> list[str]:
    """Die FAILED/ERROR-Zeilen; gibt es keine, die letzte nicht leere Zeile (die
    Zusammenfassung von Karma, dotnet, Ruff ...)."""
    zeilen = [z.rstrip() for z in ausgabe.split("\n")]
    treffer = [z for z in zeilen if _FEHLERZEILE.match(z)]
    if treffer:
        return treffer
    letzte = [z for z in zeilen if z.strip()][-1:]
    return letzte


def fingerabdruck(schritte: Sequence[Schritt], geheimnisse: Sequence[str]) -> str:
    """Rote Schritte mit Zustand und Fehlerzeilen, ohne Zeitstempel und Laufzeiten."""
    rot = [
        [
            s.name,
            _zustand(s),
            [
                _VERAENDERLICH.sub("#", z)
                for z in fehlerzeilen(ausgabe_bereinigen(s.ausgabe, geheimnisse))
            ],
        ]
        for s in schritte
        if s.rot
    ]
    return hashlib.sha256(json.dumps(rot).encode()).hexdigest()[:16]


def fingerabdruck_lesen(text: str) -> Optional[str]:
    treffer = _MARKE_LESEN.search(text)
    return treffer.group(1) if treffer else None


def _kopf(pipeline: str) -> str:
    return (
        f"*Automatischer CI-Bericht (Woodpecker, Pipeline `#{pipeline}`), kein Agent*"
    )


def unveraendert_erstellen(
    pipeline: str,
    pipeline_url: str,
    commit: str,
    fingerabdruck: str,
    voriger_url: str,
) -> str:
    """Einzeiler, wenn der Fehler derselbe ist wie im letzten Bericht."""
    return (
        f"{_kopf(pipeline)}: Unverändert rot, Commit `{commit}` "
        f"([Pipeline]({pipeline_url})), gleicher Fehler wie im "
        f"[letzten Bericht]({voriger_url}).\n\n{_MARKE.format(fingerabdruck)}\n"
    )


def bericht_erstellen(
    pipeline: str,
    pipeline_url: str,
    commit: str,
    schritte: Sequence[Schritt],
    geheimnisse: Sequence[str],
) -> str:
    """Der Kommentar: rote und abgebrochene Schritte mit ihren Fehlerzeilen und dem
    eingeklappten Ende ihrer Ausgabe, dazu die Schritte, die nicht gelaufen sind."""
    kopf = f"{_kopf(pipeline)}\n\nCommit `{commit}` ist rot: {pipeline_url}"
    rot = [s for s in schritte if s.rot]
    nicht_gelaufen = [s.name for s in schritte if not s.gelaufen]
    marke = _MARKE.format(fingerabdruck(schritte, geheimnisse))
    bereinigt = {s.name: ausgabe_bereinigen(s.ausgabe, geheimnisse) for s in rot}

    zeilen = ZEILEN_JE_SCHRITT
    while True:
        teile = [kopf]
        for s in rot:
            ausgabe = bereinigt[s.name]
            fehler = fehlerzeilen(ausgabe)
            sichtbar = min(FEHLERZEILEN_JE_SCHRITT, zeilen)
            weitere = len(fehler) - sichtbar
            fehler_text, _ = _ende("\n".join(fehler[:sichtbar]), sichtbar)
            if weitere > 0:
                fehler_text += f"\n… {weitere} weitere"
            ende, ausgelassen = _ende(ausgabe, zeilen)
            hinweis = (
                f"Letzte {zeilen} Zeilen, {ausgelassen} davor ausgelassen.\n\n"
                if ausgelassen
                else ""
            )
            teile.append(
                f"### `{s.name}`: {_zustand(s)}\n\n{_codeblock(fehler_text)}\n\n"
                f"<details><summary>Log {s.name}</summary>\n\n"
                f"{hinweis}{_codeblock(ende)}\n\n</details>"
            )
        if nicht_gelaufen:
            teile.append(
                "Nicht gelaufen: " + ", ".join(f"`{n}`" for n in nicht_gelaufen)
            )
        teile.append(marke)
        text = "\n\n".join(teile) + "\n"
        # Bei einer Zeile je Schritt passt es dank ZEICHEN_JE_ZEILE immer
        if len(text) <= MAX_ZEICHEN or zeilen <= 1:
            return text
        zeilen //= 2


def _lesen(pfad: pathlib.Path) -> Optional[str]:
    try:
        return pfad.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None


def schritte_lesen(namen: Sequence[str], verzeichnis: pathlib.Path) -> list[Schritt]:
    schritte = []
    for name in namen:
        status = (_lesen(verzeichnis / f"{name}.status") or "").strip()
        schritte.append(
            Schritt(
                name=name,
                exit_code=int(status) if status.isdigit() else None,
                ausgabe=_lesen(verzeichnis / f"{name}.log"),
            )
        )
    return schritte


def _pflicht(env, name: str) -> str:
    wert = env.get(name)
    if not wert:
        raise SystemExit(f"{name} ist nicht gesetzt")
    return wert


def _senden(url: str, token: str, daten: Optional[dict] = None) -> tuple[int, bytes]:
    """GET (ohne ``daten``) oder POST an die Forgejo-API; wirft wie urlopen."""
    anfrage = urllib.request.Request(
        url,
        data=None if daten is None else json.dumps(daten).encode(),
        method="GET" if daten is None else "POST",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT_S) as antwort:
        return antwort.status, antwort.read()


def _fehler_melden(was: str, fehler: Exception) -> None:
    """Nur den Status melden, nie den Antworttext: Forgejo gibt bei ungueltigem Token
    den Token zurueck."""
    if isinstance(fehler, urllib.error.HTTPError):
        print(f"{was}: HTTP {fehler.code}", file=sys.stderr)
    else:
        grund = getattr(fehler, "reason", fehler)
        print(f"{was}: nicht gesendet ({type(grund).__name__})", file=sys.stderr)


_NETZFEHLER = (urllib.error.URLError, TimeoutError)


def letzter_bericht(kommentare: Sequence[dict]) -> Optional[tuple[str, str]]:
    """Fingerabdruck und Adresse des juengsten Kommentars mit Fingerabdruck."""
    for kommentar in reversed(kommentare):
        abdruck = fingerabdruck_lesen(kommentar.get("body") or "")
        if abdruck:
            return abdruck, kommentar.get("html_url") or ""
    return None


def main(
    argv: Sequence[str], env=os.environ, verzeichnis: pathlib.Path = PROTOKOLL
) -> int:
    token = env.get("FORGEJO_TOKEN")
    if not token:
        print(
            "FORGEJO_TOKEN ist nicht gesetzt (Secret forgejo_ci_bericht_token): "
            "kein CI-Bericht im PR."
        )
        return 0
    forge = _pflicht(env, "CI_FORGE_URL").rstrip("/")
    repo = f"{_pflicht(env, 'CI_REPO_OWNER')}/{_pflicht(env, 'CI_REPO_NAME')}"
    pr = _pflicht(env, "CI_COMMIT_PULL_REQUEST")
    kommentare_url = (
        f"{forge}/api/v1/repos/{repo}/issues/{urllib.parse.quote(pr)}/comments"
    )
    pipeline = _pflicht(env, "CI_PIPELINE_NUMBER")
    pipeline_url = _pflicht(env, "CI_PIPELINE_URL")
    commit = _pflicht(env, "CI_COMMIT_SHA")
    schritte = schritte_lesen(argv, verzeichnis)
    abdruck = fingerabdruck(schritte, [token])

    # Sind die Kommentare nicht lesbar, kommt der volle Bericht: lieber einmal zu viel
    # als ein roter Lauf ohne Bericht.
    voriger = None
    try:
        _, antwort = _senden(kommentare_url, token)
        voriger = letzter_bericht(json.loads(antwort))
    except (*_NETZFEHLER, ValueError) as fehler:
        _fehler_melden(f"Kommentare in PR #{pr} lesen", fehler)

    if voriger and voriger[0] == abdruck:
        art = "unverändert, Einzeiler"
        body = unveraendert_erstellen(
            pipeline, pipeline_url, commit, abdruck, voriger[1]
        )
    else:
        art = "Bericht"
        body = bericht_erstellen(pipeline, pipeline_url, commit, schritte, [token])

    # Ein Versuch, keine Wiederholung: lieber kein Bericht als zwei.
    try:
        status, _ = _senden(kommentare_url, token, {"body": body})
    except _NETZFEHLER as fehler:
        _fehler_melden(f"CI-Bericht in PR #{pr}", fehler)
        return 1
    print(f"CI-Bericht in PR #{pr} ({art}): HTTP {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
