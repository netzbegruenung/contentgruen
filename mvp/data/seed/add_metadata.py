"""
Ergaenzt die Metadaten in den Seed-Dateien unter v1.0/.

Nur fuer die Entwicklung (siehe README.md). Die Nutzung ist immer 0: Kein Zaehler
wird vorbelegt (GLOSSARY.md, "Nutzung"). Ein fehlendes created_at wird aus der
Position in der Datei abgeleitet, damit zwei Laeufe dasselbe Ergebnis liefern.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

# Fester Ausgangspunkt fuer created_at; jeder weitere Eintrag eine Stunde spaeter.
BEGINN = datetime(2025, 9, 1, 9, 0, 0)


def _metadaten_ohne_nutzung(metadata: dict | None, position: int) -> dict:
    metadata = dict(metadata or {})
    metadata["usage_count"] = 0
    metadata.setdefault("created_at", (BEGINN + timedelta(hours=position)).isoformat())
    return metadata


def metadaten_ergaenzen(daten: list[dict]) -> None:
    """Setzt bei jeder Aussage und jedem Beitrag die Nutzung auf 0 und ergaenzt created_at."""
    position = 0
    for aussage in daten:
        aussage["metadata"] = _metadaten_ohne_nutzung(aussage.get("metadata"), position)
        position += 1
        for feld in ("commentaries", "generic_texts"):
            for beitrag in aussage.get(feld, []):
                beitrag["metadata"] = _metadaten_ohne_nutzung(
                    beitrag.get("metadata"), position
                )
                position += 1


def main() -> None:
    seed = Path(__file__).parent / "v1.0"
    dateien = sorted(seed.glob("statements_with_*/*.json"))
    for datei in dateien:
        daten = json.loads(datei.read_text(encoding="utf-8"))
        metadaten_ergaenzen(daten)
        datei.write_text(
            json.dumps(daten, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
        )
        print(f"{datei.relative_to(seed)}: {len(daten)} Aussagen")


if __name__ == "__main__":
    main()
