"""
Konten im Realm von Gut gesagt anlegen (#429). Die Einladung (services/einladung_service.py)
kennt nur diese Schnittstelle; die Keycloak-Admin-Schnittstelle steckt dahinter
(infrastructure/keycloak_konten.py).
"""

import enum
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Protocol


class KontoErgebnis(enum.Enum):
    ANGELEGT = "angelegt"
    # Zu der Mail-Adresse gibt es schon ein Konto; es wird nichts geaendert.
    VORHANDEN = "vorhanden"


class IKontenImRealm(Protocol):
    def konto_anlegen(self, email: str) -> KontoErgebnis: ...


@dataclass
class VerknuepfteKonten:
    # alte Kennung -> Kennung des neu angelegten Kontos
    angelegt: Dict[str, str] = field(default_factory=dict)
    # alte Kennungen, deren Mail-Adresse im Realm schon ein Konto hat
    vergeben: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class BetaZugang:
    """Ein Eintrag aus managed-users.json, der in den Realm umzieht (#488)."""

    email: str
    # displayName aus der Datei, etwa "Anna Beispiel"
    name: str
    admin: bool = False


@dataclass
class KontenMitPasswort:
    # alte Kennung -> Kennung des Kontos im Realm (neu angelegt oder schon da)
    angelegt: Dict[str, str] = field(default_factory=dict)
    # alte Kennungen, deren Mail "Passwort festlegen" nicht hinausging
    ohne_mail: List[str] = field(default_factory=list)


class IKennungenImRealm(Protocol):
    """Kennungen umstellen (#487, #488): services/wartung/kennungen_umstellen.py."""

    def kennungen_zuordnen(
        self, identity_provider: str, kennungen: Iterable[str]
    ) -> Dict[str, str]: ...

    def konten_verknuepft_anlegen(
        self, identity_provider: str, konten: Mapping[str, str]
    ) -> VerknuepfteKonten: ...

    def konten_nach_adresse(self, adressen: Iterable[str]) -> Dict[str, str]: ...

    def konten_mit_passwort_anlegen(
        self, zugaenge: Mapping[str, BetaZugang]
    ) -> KontenMitPasswort: ...
