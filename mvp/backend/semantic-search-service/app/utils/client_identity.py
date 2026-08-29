"""
Kurzlebiger Client-Schluessel fuer Rate-Limits auf unauthentifizierten Routen.

Hintergrund: Das Rate-Limit auf POST /api/v1/moderation/report war auf
X-Session-Id gekeyed. Den Header erzeugt die SPA selbst und legt ihn in
localStorage ab -- er ist frei waehlbar und wurde nirgends geprueft. Wer je
Anfrage einen neuen Wert schickt, hat kein Limit. Extern nachgewiesen: zwoelf
Meldungen in derselben Sekunde von einer Adresse, jede mit anderem
X-Session-Id, alle 200.

Dieselbe Fehlerklasse wie beim durchgereichten X-User-Id: einem Wert, den der
Client bestimmt, wird eine Sicherheitsentscheidung anvertraut.

Die Adresse ist das einzige Merkmal auf einer bewusst anonymen Route, das der
Aufrufer nicht beliebig wechseln kann. Sie wird deshalb hier verwendet -- aber
nicht gespeichert und nicht geloggt:

- Gehasht mit einem Salt, der beim Prozessstart zufaellig erzeugt wird. Nach
  einem Neustart ergibt dieselbe Adresse einen anderen Schluessel; ein
  Wiedererkennen ueber Neustarts hinweg ist damit ausgeschlossen.
- Nur im Prozessspeicher, im gleitenden Fenster des Rate-Limiters. Nichts
  davon erreicht die Datenbank oder eine Logzeile.
- Auf 16 Hex-Zeichen gekuerzt: genug, um Aufrufer innerhalb eines Fensters
  auseinanderzuhalten, zu wenig fuer einen Abgleich gegen eine Adressliste.

Das bleibt im Rahmen von 67e50dd, das die IP-Verarbeitung aus den
usage_events entfernt hat: dort wurde die Adresse persistiert, hier existiert
sie fluechtig und pseudonymisiert.
"""

import hashlib
import secrets
import uuid
from typing import Optional

from fastapi import Request

# Prozessweiter Salt, nur im Speicher. Bewusst kein konfigurierter Wert: er soll
# einen Neustart nicht ueberleben.
_SALT = secrets.token_bytes(32)

# Header, den nginx setzt (proxy_set_header X-Real-IP $remote_addr) und den YARP
# unveraendert weiterreicht. nginx ueberschreibt einen vom Client mitgeschickten
# Wert, weshalb er hinter dem Reverse Proxy vertrauenswuerdig ist. Voraussetzung
# ist, dass das BFF nur ueber nginx erreichbar ist -- auf tst und prod bindet es
# an 127.0.0.1, siehe "Erforderliche Salt-Aenderungen" in der PR.
_REAL_IP_HEADER = "X-Real-IP"


def get_client_address(request: Request) -> Optional[str]:
    """
    Die Adresse des Aufrufers, so gut sie hier bekannt ist.

    Hinter nginx ist das X-Real-IP; ohne Reverse Proxy (Dev-Stack, direkter
    Zugriff auf Port 8000) der Peer der Verbindung. Im Dev-Stack ist dieser Peer
    der BFF-Container, alle anonymen Aufrufe teilen sich dort also einen
    Schluessel. Das ist fuer die Entwicklung unerheblich und in der
    Produktionstopologie nicht der Fall.
    """
    forwarded = request.headers.get(_REAL_IP_HEADER)
    if forwarded:
        # Nur der erste Eintrag, falls doch einmal eine Liste ankommt.
        candidate = forwarded.split(",")[0].strip()
        if candidate:
            return candidate

    if request.client and request.client.host:
        return request.client.host

    return None


def derive_client_key(request: Request) -> str:
    """
    Pseudonymer, prozesslokaler Schluessel fuer das Rate-Limit.

    Gibt "unknown" zurueck, wenn keine Adresse zu ermitteln ist -- solche
    Aufrufe teilen sich dann ein Kontingent, was die sichere Richtung ist.
    """
    address = get_client_address(request)
    if not address:
        return "ip:unknown"

    digest = hashlib.sha256(_SALT + address.encode("utf-8")).hexdigest()
    return f"ip:{digest[:16]}"


def normalize_session_id(session_id: Optional[str]) -> Optional[str]:
    """
    Nimmt eine clientseitige Session-Kennung an, wenn sie wie eine aussieht.

    Was diese Pruefung *nicht* leistet: Sicherheit. Der Wert kommt vom Client,
    und wer ihn wechseln will, erzeugt eben gueltige UUIDs -- seit dieser
    Aenderung erzeugt die SPA selbst welche. Deshalb haengt seit dem Umbau von
    /moderation/report auch keine Entscheidung mehr an diesem Wert.

    Was sie leistet, ist Hygiene: der Wert landet in einer Spalte, die anonyme
    Meldungen zusammenhaelt und im Moderationsposteingang angezeigt wird. Ohne
    Pruefung kann dort auf einer Route ohne Anmeldung beliebiger Text mit bis zu
    255 Zeichen stehen.

    Ein unpassender Wert wird verworfen, nicht abgewiesen: eine kaputte Kennung
    darf niemanden seine Meldung kosten (DSA Art. 16). Der Aufrufer wird dann
    behandelt, als haette er gar keine geschickt.
    """
    if not session_id:
        return None

    candidate = session_id.strip()
    try:
        # Akzeptiert die kanonische Form mit Bindestrichen ebenso wie ohne.
        uuid.UUID(candidate)
    except (ValueError, AttributeError):
        return None

    return candidate
