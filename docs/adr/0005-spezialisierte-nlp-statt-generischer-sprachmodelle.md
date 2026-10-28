---
status: accepted
---

# Spezialisierte NLP-Modelle gegen Zerfaserung, keine generischen Sprachmodelle

Der Bestand soll nicht zerfasern: Dieselbe Behauptung, nur anders formuliert, landet auf einer Aussage, und verwandte Aussagen werden miteinander verknüpft. Ob zwei Texte dieselbe Behauptung sind, ob sie sich widersprechen oder nur verwandt sind, entscheiden spezialisierte, lokal laufende Modelle: Einbettungen für die Ähnlichkeit, NLI- oder Paraphrase-Modelle für Folgerung und Widerspruch, linguistische Werkzeuge etwa für Negation. Generische Sprachmodelle übernehmen diese Entscheidungen nicht.

Gründe: Ein spezialisiertes Modell liefert für dieselbe Eingabe dasselbe Ergebnis und lässt sich am Messset (`tests/regression/aehnlichkeit_paare.py`) prüfen und nachmessen. Es läuft im eigenen Rechenzentrum, Suchanfragen und Beiträge verlassen es nicht. Und es ist schnell und günstig genug, um bei jeder Suche und jedem Speichern zu laufen. Ein falsches Zusammenlegen sieht niemand und verfälscht die Antworten; deshalb zählt die Prüfbarkeit mehr als die Breite eines generischen Modells.

## Considered Options

- Nur Einbettungsähnlichkeit mit einer Schwelle (bisheriger Stand, 0,98): sicher gegen falsches Zusammenlegen, aber schon eine andere Wortstellung gilt als neue Aussage, während Gegenteile nah beieinanderliegen.
- Ein generisches Sprachmodell entscheidet: versteht Umformulierungen breit, ist aber schwer zu messen, nicht immer gleich im Ergebnis, langsamer und je nach Anbieter mit Übermittlung an Dritte.

## Consequences

Neue Funktionen, die Texte vergleichen, gruppieren oder verknüpfen, nehmen ein spezialisiertes Modell und erweitern das Messset um ihre Fälle. Ein weiteres lokales Modell braucht eine Prüfung der Datenschutzerklärung (D-N8 in `docs/RECHTSTEXTE_LUECKEN.md`), aber keine neue Übermittlung. Texte vorschlagen bleibt bei ADR 0003. Erster Schritt ist #387.
