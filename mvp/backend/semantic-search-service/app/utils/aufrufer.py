"""
Wer eine Anfrage stellt, wie das BFF es dem Dienst sagt.

Fuer oeffentliche Endpunkte setzt das BFF ``X-User: anonymous``; das ist keine
Kennung, sondern heisst: nicht angemeldet.
"""

ANONYM = "anonymous"
"""Der Wert von ``X-User`` fuer Aufrufe ohne Anmeldung."""
