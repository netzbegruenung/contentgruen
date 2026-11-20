"""
Cache-Regeln des Frontend-nginx (nginx.conf fuer Test und Produktion, nginx.docker.conf fuer
den Dev-Stack): Nur Dateien mit Inhalts-Hash im Namen liegen ein Jahr im Cache. Alle anderen
statischen Dateien kommen ungehasht aus public/ und behalten beim Ersetzen ihren Namen; mit
"expires 1y" sahen Browser nach #725 ein Jahr lang das alte /profilbild-2026.jpg (20.11.2026).

Ohne nginx: Der Test liest die location-Bloecke aus beiden Dateien und waehlt fuer einen Pfad
die Regel wie nginx ("=" vor Regex, Regex in Reihenfolge der Datei, sonst Praefix). Die
Regex-Muster sind schlicht genug, dass Python sie wie PCRE liest.
"""

import json
import pathlib
import re

import pytest

WURZEL = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = WURZEL / "mvp/frontend/gutgesagt-frontend"
PUBLIC = FRONTEND / "public"
KONFIGURATIONEN = ["nginx.conf", "nginx.docker.conf"]

LOCATION = re.compile(r"^\s*location\s+(=|~\*|~)?\s*(\"[^\"]*\"|\S+)\s*\{(.*?)^\s*\}", re.M | re.S)
CACHE_CONTROL = re.compile(r'add_header\s+Cache-Control\s+"([^"]*)"')

# Namen aus einem echten "ng build --configuration production" (outputHashing "all"); media/
# entsteht, sobald eine Komponente eine Datei per url() einbindet.
GEHASHT = [
    "/main-XJITCGMB.js",
    "/chunk-3642N7JF.js",
    "/polyfills-B6TNHZQ6.js",
    "/styles-4INU76GJ.css",
    "/media/roboto-latin-4KX2JQ7M.woff2",
]
EIN_JAHR = "public, max-age=31536000, immutable"


def _regeln(konfiguration: str) -> list[tuple[str, str, str | None]]:
    text = (FRONTEND / konfiguration).read_text(encoding="utf-8")
    regeln = []
    for art, muster, rumpf in LOCATION.findall(text):
        cache = CACHE_CONTROL.search(rumpf)
        regeln.append((art, muster.strip('"'), cache.group(1) if cache else None))
    return regeln


def _cache_control(konfiguration: str, pfad: str) -> str | None:
    regeln = _regeln(konfiguration)
    for art, muster, cache in regeln:
        if art == "=" and muster == pfad:
            return cache
    for art, muster, cache in regeln:
        if art in ("~", "~*") and re.search(muster, pfad, re.I if art == "~*" else 0):
            return cache
    return None


def _public_dateien() -> list[str]:
    return sorted("/" + p.relative_to(PUBLIC).as_posix() for p in PUBLIC.rglob("*") if p.is_file())


def test_regeln_gefunden():
    # Sonst prueften die Tests unten nach einer Umformatierung still nichts mehr
    for konfiguration in KONFIGURATIONEN:
        assert len(_regeln(konfiguration)) >= 6, konfiguration
    assert len(_public_dateien()) >= 50


def test_angular_hasht_die_build_ausgabe():
    angular = json.loads((FRONTEND / "angular.json").read_text(encoding="utf-8"))
    produktion = angular["projects"]["gutgesagt-frontend"]["architect"]["build"]["configurations"][
        "production"
    ]
    assert produktion["outputHashing"] == "all"


def test_beide_konfigurationen_cachen_gleich():
    def cache_regeln(konfiguration):
        return [r for r in _regeln(konfiguration) if r[1] not in ("/", "/api/")]

    assert cache_regeln("nginx.conf") == cache_regeln("nginx.docker.conf")


@pytest.mark.parametrize("konfiguration", KONFIGURATIONEN)
@pytest.mark.parametrize("pfad", GEHASHT)
def test_gehashte_dateien_ein_jahr(konfiguration, pfad):
    assert _cache_control(konfiguration, pfad) == EIN_JAHR


@pytest.mark.parametrize("konfiguration", KONFIGURATIONEN)
def test_nichts_aus_public_ein_jahr(konfiguration):
    """Keine ungehashte Datei darf der Hash-Regel zufaellig gleichen (etwa mensch-01.png)."""
    zu_lange = [p for p in _public_dateien() if "max-age" in (_cache_control(konfiguration, p) or "")]
    assert not zu_lange


@pytest.mark.parametrize("konfiguration", KONFIGURATIONEN)
@pytest.mark.parametrize(
    "pfad",
    [
        "/profilbild-2026.jpg",
        "/avatars/fuchs.png",
        "/marke/wegweiser.svg",
        "/fonts/roboto-latin.woff2",
        "/vorschau/bewerten-v1.webp",
    ],
)
def test_ungehashte_dateien_revalidieren(konfiguration, pfad):
    assert (PUBLIC / pfad.lstrip("/")).is_file(), pfad
    assert _cache_control(konfiguration, pfad) == "no-cache"


@pytest.mark.parametrize("konfiguration", KONFIGURATIONEN)
def test_sonderfaelle_unveraendert(konfiguration):
    assert _cache_control(konfiguration, "/sw.js") == "no-cache, no-store, must-revalidate"
    assert _cache_control(konfiguration, "/index.html") == "no-cache, no-store, must-revalidate"
    assert _cache_control(konfiguration, "/manifest.webmanifest") == "no-cache"
    assert _cache_control(konfiguration, "/.well-known/security.txt") == "no-cache"
