"""
Konten im Realm von Gut gesagt anlegen (#429) und nie benutzte loeschen (#538). Die Einladung (services/einladung_service.py)
kennt nur diese Schnittstelle; die Keycloak-Admin-Schnittstelle steckt dahinter
(infrastructure/keycloak_konten.py).
"""

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Mapping, Protocol


class KontoErgebnis(enum.Enum):
    ANGELEGT = "angelegt"
    # Zu der Mail-Adresse gibt es schon ein Konto; es wird nichts geaendert.
    VORHANDEN = "vorhanden"


class IKontenImRealm(Protocol):
    def konto_anlegen(self, email: str) -> KontoErgebnis: ...


class INieBenutzteKonten(Protocol):
    """Loeschfrist fuer Konten aus Einladungen: services/loeschfristen_service.py."""

    def nie_benutzte_loeschen(self, angelegt_vor: datetime) -> int: ...


@dataclass
class VerknuepfteKonten:
    # alte Kennung -> Kennung des neu angelegten Kontos
    angelegt: Dict[str, str] = field(default_factory=dict)
    # alte Kennungen, deren Mail-Adresse im Realm schon ein Konto hat
    vergeben: List[str] = field(default_factory=list)


class IKennungenImRealm(Protocol):
    """Kennungen umstellen (#487): services/wartung/kennungen_umstellen.py."""

    def kennungen_zuordnen(
        self, identity_provider: str, kennungen: Iterable[str]
    ) -> Dict[str, str]: ...

    def konten_verknuepft_anlegen(
        self, identity_provider: str, konten: Mapping[str, str]
    ) -> VerknuepfteKonten: ...
