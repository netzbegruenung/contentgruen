"""
Wann zwei Links als gleich gelten (#263).

Entscheidung des Maintainers vom 2026-10-26: Zwei Links sind gleich nach
Bereinigung um Tracking-Parameter, "www.", Schraegstrich am Ende und den
Unterschied http/https. Alles andere bleibt ein Unterschied: inhaltliche
Parameter, die Reihenfolge der Parameter, Gross- und Kleinschreibung im Pfad,
andere Subdomains. Der Host ist ohnehin nicht gross/klein-empfindlich.

Die Tracking-Listen spiegeln ``shared/url-bereinigen.ts`` im Frontend, das die
Parameter schon beim Einwerfen entfernt. Hier werden sie trotzdem noch einmal
entfernt: Einwuerfe von vor dieser Bereinigung tragen sie noch, und ein Client
muss sich nicht daran halten. Wer eine Liste aendert, aendert beide;
``test_link_vergleich_tracking_wie_frontend`` prueft das.
"""

from typing import Optional
from urllib.parse import unquote_plus, urlsplit

# Parameter, die vollstaendig entfernt werden.
TRACKING_PARAMETER = frozenset(
    {"stkn", "igsh", "igshid", "fbclid", "gclid", "mc_cid", "mc_eid"}
)

# Praefixe, bei denen jeder Parameter mit diesem Anfang entfernt wird.
TRACKING_PRAEFIXE = ("utm_",)

# Parameter, die nur auf bestimmten Hosts Tracking sind (Subdomains zaehlen mit).
HOST_TRACKING_PARAMETER = (
    (("youtube.com", "youtu.be"), frozenset({"si", "is", "feature", "pp"})),
)


def _host_tracking_parameter(host: str) -> frozenset:
    return frozenset().union(
        *(
            parameter
            for domains, parameter in HOST_TRACKING_PARAMETER
            if any(host == domain or host.endswith(f".{domain}") for domain in domains)
        )
    )


def _ist_tracking(name: str, host_parameter: frozenset) -> bool:
    klein = name.lower()
    return (
        klein in TRACKING_PARAMETER
        or klein in host_parameter
        or klein.startswith(TRACKING_PRAEFIXE)
    )


def vergleichsform(url: Optional[str]) -> Optional[str]:
    """
    Die Form eines Links, in der gleiche Links gleich aussehen, oder None.

    Ohne Schema, ohne "www.", ohne Schraegstrich am Ende des Pfads und ohne
    Tracking-Parameter: ``http://www.example.org/a/?utm_source=x`` wird
    ``example.org/a``. Kein http(s)-Link: None.
    """
    if not url:
        return None
    try:
        teile = urlsplit(url.strip())
        port = teile.port
    except ValueError:
        return None
    if teile.scheme.lower() not in ("http", "https") or not teile.hostname:
        return None

    host = teile.hostname.lower()
    if host.startswith("www."):
        host = host[len("www.") :]
    host_parameter = _host_tracking_parameter(host)
    if port is not None:
        host = f"{host}:{port}"

    # Nur die Tracking-Parameter fallen weg; die uebrigen bleiben wie geschrieben,
    # damit ein Umschreiben die Kodierung nicht veraendert.
    parameter = [
        teil
        for teil in teile.query.split("&")
        if teil
        and not _ist_tracking(unquote_plus(teil.split("=", 1)[0]), host_parameter)
    ]

    form = host + teile.path.rstrip("/")
    if parameter:
        form += "?" + "&".join(parameter)
    if teile.fragment:
        form += "#" + teile.fragment
    return form


def vergleichskern(url: Optional[str]) -> Optional[str]:
    """
    Host und Pfad aus der Vergleichsform, oder None.

    Steht als Teilzeichenkette in jedem gleichen Link, gross/klein-unabhaengig;
    damit kann die Datenbank grob vorfiltern, bevor ``gleicher_link`` entscheidet.
    """
    form = vergleichsform(url)
    if form is None:
        return None
    return form.split("?", 1)[0].split("#", 1)[0]


def gleicher_link(link: Optional[str], anderer: Optional[str]) -> bool:
    """Ob zwei Links nach der Bereinigung gleich sind. Kein Link ist nie gleich."""
    form = vergleichsform(link)
    return form is not None and form == vergleichsform(anderer)
