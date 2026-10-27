"""CI-Bericht: kommentiert bei einem roten Pull-Request-Lauf die roten Schritte in den PR.

Letzter Schritt von ``.woodpecker/ci.yaml`` (docs/CI.md, "CI-Bericht"). Liest
``.ci/<schritt>.log`` und ``.ci/<schritt>.status``, die ``scripts/ci-protokoll.sh``
schreibt. Nur Standardbibliothek: der Bericht kommt auch, wenn die Installation scheiterte.

Aufruf: python3 scripts/ci_bericht.py <schritt> ...  (die Schritte in Pipeline-Reihenfolge)
Umgebung: CI_FORGE_URL, CI_REPO_OWNER, CI_REPO_NAME, CI_COMMIT_PULL_REQUEST,
CI_COMMIT_SHA, CI_PIPELINE_NUMBER, CI_PIPELINE_URL (setzt Woodpecker),
FORGEJO_TOKEN (Secret forgejo_ci_bericht_token).
"""

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


def bericht_erstellen(
    pipeline: str,
    pipeline_url: str,
    commit: str,
    schritte: Sequence[Schritt],
    geheimnisse: Sequence[str],
) -> str:
    """Der Kommentar: rote und abgebrochene Schritte mit dem Ende ihrer Ausgabe, dazu
    die Schritte, die nicht gelaufen sind."""
    kopf = (
        f"*Automatischer CI-Bericht (Woodpecker, Pipeline `#{pipeline}`), kein Agent*\n\n"
        f"Commit `{commit}` ist rot: {pipeline_url}"
    )
    rot = [s for s in schritte if s.rot]
    nicht_gelaufen = [s.name for s in schritte if not s.gelaufen]

    zeilen = ZEILEN_JE_SCHRITT
    while True:
        teile = [kopf]
        for s in rot:
            zustand = (
                "abgebrochen" if s.exit_code is None else f"Exit-Code {s.exit_code}"
            )
            ende, ausgelassen = _ende(
                ausgabe_bereinigen(s.ausgabe, geheimnisse), zeilen
            )
            hinweis = (
                f" (letzte {zeilen} Zeilen, {ausgelassen} davor ausgelassen)"
                if ausgelassen
                else ""
            )
            teile.append(f"### `{s.name}`: {zustand}{hinweis}\n\n{_codeblock(ende)}")
        if nicht_gelaufen:
            teile.append(
                "Nicht gelaufen: " + ", ".join(f"`{n}`" for n in nicht_gelaufen)
            )
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
    body = bericht_erstellen(
        pipeline=_pflicht(env, "CI_PIPELINE_NUMBER"),
        pipeline_url=_pflicht(env, "CI_PIPELINE_URL"),
        commit=_pflicht(env, "CI_COMMIT_SHA"),
        schritte=schritte_lesen(argv, verzeichnis),
        geheimnisse=[token],
    )
    anfrage = urllib.request.Request(
        f"{forge}/api/v1/repos/{repo}/issues/{urllib.parse.quote(pr)}/comments",
        data=json.dumps({"body": body}).encode(),
        method="POST",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    # Ein Versuch, keine Wiederholung: lieber kein Bericht als zwei. Nur den Status
    # melden, nie den Antworttext: Forgejo gibt bei ungueltigem Token den Token zurueck.
    try:
        with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT_S) as antwort:
            status = antwort.status
    except urllib.error.HTTPError as fehler:
        print(f"CI-Bericht in PR #{pr}: HTTP {fehler.code}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError) as fehler:
        grund = getattr(fehler, "reason", fehler)
        print(
            f"CI-Bericht in PR #{pr}: nicht gesendet ({type(grund).__name__})",
            file=sys.stderr,
        )
        return 1
    print(f"CI-Bericht in PR #{pr}: HTTP {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
