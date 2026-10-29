# Wortlaute des CC0-Hinweises

Jedes Formular, das etwas für andere sichtbar speichert, zeigt über dem Absende-Knopf den
CC0-Hinweis (`GLOSSARY.md`, „CC0-Hinweis“) und schickt die Kennung des gezeigten Wortlauts mit.
Gespeichert wird sie an jedem neuen Beitrag (Qdrant-Payload), Satz und Einwurf (PostgreSQL,
Spalte `cc0_wortlaut`). So bleibt nachvollziehbar, welchem Wortlaut jemand zugestimmt hat.
Bestand von vor #431 hat keine Kennung (`NULL`/fehlt).

## Einen Wortlaut ändern

1. Neue Kennung vergeben: Datum der Änderung und Formularart, z. B. `2027-03-01-formular`.
   Eine vergebene Kennung nie für einen anderen Wortlaut wiederverwenden.
2. Hier eine Zeile ergänzen; die alte bleibt stehen, mit „bis“-Datum.
3. Die Kennung in `CC0_WORTLAUTE` eintragen
   (`mvp/backend/semantic-search-service/app/domain/cc0_hinweis.py`); alte Kennungen bleiben
   dort, sonst sind gespeicherte Kennungen nicht mehr zuzuordnen.
4. Wortlaut und Kennung im Frontend ändern (`shared/consent-hinweis.ts`) samt Spec.

Der Dienst nimmt nur Kennungen aus `CC0_WORTLAUTE` an. Frontend und Semantic-Service deshalb
zusammen ausrollen, den Dienst zuerst. `scripts/tests/test_cc0_wortlaute.py` prüft, dass
Dienst, Frontend und diese Liste dieselben Kennungen kennen.

## Wortlaute

Der Link steht auf „Nutzungsbedingungen“ (`/nutzungsbedingungen`, neuer Tab).

| Kennung | Wo | Wortlaut | gültig |
|---------|----|----------|--------|
| `2026-10-29-formular` | Einwurf, Kommentar, Hintergrundinfo, Bild, Post, Aussage vorab anlegen | Mit dem Absenden stellst du deine eigene Formulierung unter CC0 und bestätigst die Nutzungsbedingungen – keine personenbezogenen Daten Dritter. | seit 29.10.2026 |
| `2026-10-29-satz` | Satz (Destillieren, wird beim Tippen gespeichert) | Dein Satz wird beim Tippen gespeichert. Damit stellst du deine eigene Formulierung unter CC0 und bestätigst die Nutzungsbedingungen – keine personenbezogenen Daten Dritter. | seit 29.10.2026 |

Vorher (55bb5cb8 bis #431) stand im Formular „… deine eigene Formulierung unwiderruflich unter
CC0 …“, ohne Kennung; Beiträge, Sätze und Einwürfe aus dieser Zeit haben keine.
