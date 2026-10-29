"""Wartet, bis die Dienste der CI Verbindungen annehmen (.woodpecker/ci.yaml, Schritt integration).

Woodpecker startet die Dienste gleichzeitig mit den Schritten. Im Pflichtmodus
(INTEGRATION_STACK_PFLICHT=1) bricht die Suite ab, wenn ein Dienst noch startet.
Aufruf: python3 scripts/ci_dienste_warten.py <host:port> ...   (Zeitlimit WARTEN_S)
"""

import socket
import sys
import time

WARTEN_S = 120


def erreichbar(adresse: str) -> bool:
    host, _, port = adresse.rpartition(":")
    try:
        with socket.create_connection((host, int(port)), timeout=2):
            return True
    except OSError:
        return False


def main(adressen: list[str]) -> int:
    if not adressen:
        print("Aufruf: python3 scripts/ci_dienste_warten.py <host:port> ...")
        return 2
    ende = time.monotonic() + WARTEN_S
    offen = list(adressen)
    while offen:
        offen = [a for a in offen if not erreichbar(a)]
        if not offen:
            break
        if time.monotonic() > ende:
            print(f"Nicht erreichbar nach {WARTEN_S} s: {', '.join(offen)}")
            return 1
        time.sleep(1)
    print(f"Erreichbar: {', '.join(adressen)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
