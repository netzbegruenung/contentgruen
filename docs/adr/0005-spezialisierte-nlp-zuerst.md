---
status: accepted
---

# Spezialisierte NLP-Modelle zuerst, generische Sprachmodelle nur als Ausnahme

Gut gesagt verarbeitet Texte mit spezialisierten, lokal laufenden Werkzeugen: Suche und Indexierung, Verknüpfung, Verschlagwortung, Umwandlung und Synthese. Ziel ist vor allem, dass der Bestand nicht zerfasert: Dieselbe Behauptung, nur anders formuliert, landet auf einer Aussage, und verwandte Aussagen werden miteinander verknüpft. Ob zwei Texte dieselbe Behauptung sind, ob sie sich widersprechen oder nur verwandt sind, entscheiden spezialisierte Modelle: Einbettungen für die Ähnlichkeit, NLI- oder Paraphrase-Modelle für Folgerung und Widerspruch, linguistische Werkzeuge etwa für Negation. Als spezialisiert gelten auch Einbettungs- und Reranker-Modelle, die auf einem Sprachmodell aufbauen, solange sie nur Vektoren oder Werte liefern und keinen Text erzeugen.

Ein generisches Sprachmodell ist die Ausnahme: nur, wo es für eine Aufgabe kein taugliches Spezialwerkzeug gibt, etwa beim Zuschnitt eines Beitrags für die eigene Verwendung, und dann über den Grünerator auf eigener Hardware der Netzbegrünung, nicht über einen externen Anbieter. Für erzeugte Texte gilt ADR 0003: Ein Mensch verantwortet jeden Beitrag.

Gründe: Ein spezialisiertes Modell liefert für dieselbe Eingabe dasselbe Ergebnis und lässt sich am Messset (`tests/regression/aehnlichkeit_paare.py`) prüfen und nachmessen. Es läuft auf eigener Infrastruktur, Suchanfragen und Beiträge verlassen sie nicht. Und es ist klein genug, um heute auf einer normalen VM ohne GPU bei jeder Suche und jedem Speichern zu laufen; größere Modelle können als eigener Dienst auf einem Inference-Server der Netzbegrünung laufen. Ein falsches Zusammenlegen sieht niemand und verfälscht die Antworten; deshalb zählt die Prüfbarkeit mehr als die Breite eines generischen Modells.

## Considered Options

- Nur Einbettungsähnlichkeit mit einer Schwelle (bisheriger Stand, 0,98): sicher gegen falsches Zusammenlegen, aber schon eine andere Wortstellung gilt als neue Aussage, während Gegenteile nah beieinanderliegen.
- Ein generisches Sprachmodell für alles: versteht Umformulierungen breit, ist aber schwer zu messen, nicht immer gleich im Ergebnis, braucht viel Rechenleistung und je nach Betrieb eine Übermittlung an Dritte.
- Nur Spezialwerkzeuge, auch für Umwandlung: hält alles prüfbar, verzichtet aber auf den Zuschnitt, für den es kein deutsches Spezialmodell gibt.

## Consequences

Neue Funktionen, die Texte vergleichen, gruppieren, verschlagworten oder verknüpfen, nehmen ein spezialisiertes Modell und erweitern das Messset um ihre Fälle. Jedes Modell muss heute auf CPU laufen oder als eigener Dienst auf einem Inference-Server. Ein weiteres lokales Modell braucht eine Prüfung der Datenschutzerklärung (D-N8 in `docs/RECHTSTEXTE_LUECKEN.md`), aber keine neue Übermittlung. Erster Schritt ist #387.
