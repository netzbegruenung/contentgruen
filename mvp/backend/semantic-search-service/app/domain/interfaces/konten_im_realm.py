"""
Konten im Realm von Gut gesagt anlegen (#429). Die Einladung (services/einladung_service.py)
kennt nur diese Schnittstelle; die Keycloak-Admin-Schnittstelle steckt dahinter
(infrastructure/keycloak_konten.py).
"""

import enum
from typing import Protocol


class KontoErgebnis(enum.Enum):
    ANGELEGT = "angelegt"
    # Zu der Mail-Adresse gibt es schon ein Konto; es wird nichts geaendert.
    VORHANDEN = "vorhanden"


class IKontenImRealm(Protocol):
    def konto_anlegen(self, email: str) -> KontoErgebnis: ...
