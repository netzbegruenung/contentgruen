"""
Konten im Realm von Gut gesagt anlegen (#429) und nie benutzte loeschen (#538). Die
Einladung (services/einladung_service.py) kennt nur diese Schnittstelle; die
Keycloak-Admin-Schnittstelle steckt dahinter (infrastructure/keycloak_konten.py).
"""

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Mapping, Protocol


# So lange gilt der Link in der Mail; danach hilft "Passwort vergessen". Die Loeschfrist
# fuer nie benutzte Konten (services/loeschfristen_service.py) zaehlt ab seinem Ablauf.
MAIL_GUELTIG_SEKUNDEN = 3 * 24 * 60 * 60


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


@dataclass(frozen=True)
class BetaZugang:
    """Ein Eintrag aus managed-users.json, der in den Realm umzieht (#488)."""

    email: str
    # displayName aus der Datei, etwa "Anna Beispiel"
    name: str
    admin: bool = False


@dataclass
class KontenMitPasswort(VerknuepfteKonten):
    """Wie VerknuepfteKonten; ``vergeben``: Keycloak legt kein Konto an (Konflikt), und
    zur Adresse gibt es auch keins, etwa ein Benutzername mit anderer Adresse."""

    # alte Kennungen, deren Mail "Passwort festlegen" nicht hinausging
    ohne_mail: List[str] = field(default_factory=list)
    # alte Kennungen, deren Konto Keycloak abwies (etwa eine ungueltige Adresse); der Lauf
    # geht weiter, sie bleiben ohne Konto
    abgewiesen: List[str] = field(default_factory=list)


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
