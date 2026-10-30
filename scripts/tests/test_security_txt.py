"""
security.txt (RFC 9116, #430) liegt im Frontend und wird von dessen nginx ausgeliefert.
Ein abgelaufenes Expires macht die Datei ungueltig, ohne dass es jemand merkt. Dieser Test
wird deshalb 30 Tage vor Ablauf rot: Dann ist Expires zu erneuern (SECURITY.md,
"Renewing security.txt").
"""

import datetime
import pathlib
import re

WURZEL = pathlib.Path(__file__).resolve().parents[2]
SECURITY_TXT = WURZEL / "mvp/frontend/gutgesagt-frontend/public/.well-known/security.txt"
SECURITY_MD = WURZEL / "SECURITY.md"
NGINX = [
    WURZEL / "mvp/frontend/gutgesagt-frontend/nginx.conf",
    WURZEL / "mvp/frontend/gutgesagt-frontend/nginx.docker.conf",
]

VORLAUF = datetime.timedelta(days=30)
HOECHSTENS = datetime.timedelta(days=366)


def _felder() -> dict[str, list[str]]:
    felder: dict[str, list[str]] = {}
    for zeile in SECURITY_TXT.read_text(encoding="utf-8").splitlines():
        if not zeile or zeile.startswith("#"):
            continue
        name, wert = zeile.split(":", 1)
        felder.setdefault(name.strip().lower(), []).append(wert.strip())
    return felder


def _ablauf() -> datetime.datetime:
    (wert,) = _felder()["expires"]
    return datetime.datetime.fromisoformat(wert.replace("Z", "+00:00"))


def test_pflichtfelder_genau_einmal_expires():
    felder = _felder()

    assert felder["contact"]
    assert len(felder["expires"]) == 1
    assert felder["preferred-languages"] == ["de"]
    assert felder["policy"] == ["https://github.com/netzbegruenung/contentgruen/blob/main/SECURITY.md"]


def test_contact_ist_die_adresse_aus_security_md():
    (kontakt,) = _felder()["contact"]
    adresse = kontakt.removeprefix("mailto:")

    assert f"**{adresse}**" in SECURITY_MD.read_text(encoding="utf-8")


def test_expires_hoechstens_ein_jahr_voraus():
    jetzt = datetime.datetime.now(datetime.timezone.utc)

    assert _ablauf() - jetzt <= HOECHSTENS


def test_expires_rechtzeitig_erneuert():
    jetzt = datetime.datetime.now(datetime.timezone.utc)

    assert _ablauf() - jetzt > VORLAUF, (
        "security.txt laeuft in weniger als 30 Tagen ab: Expires erneuern "
        "(SECURITY.md, 'Renewing security.txt')"
    )


def test_beide_nginx_konfigurationen_liefern_sie_als_text_plain_utf8():
    for datei in NGINX:
        text = datei.read_text()
        block = re.search(r"location = /\.well-known/security\.txt \{(.*?)\n    \}\n", text, re.S)

        assert block, datei.name
        assert "default_type text/plain;" in block.group(1), datei.name
        assert "charset utf-8;" in block.group(1), datei.name
