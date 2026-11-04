---
status: accepted
---

# KI schlägt vor, ein Mensch verantwortet jeden Beitrag

KI darf Nutzenden für ihre eigene Verwendung Texte vorschlagen, etwa eine Verbesserung ihrer Argumentation oder eine auf eine Zielgruppe zugeschnittene Fassung eines Beitrags. In den gemeinsamen Vorrat kommt ein solcher Text nur, wenn ein Mensch ihn übernimmt, gegebenenfalls bearbeitet und speichert; er ist dann Autor. Ein Zuschnitt für die eigene Verwendung kommt nicht in den Vorrat, er wird nur kopiert (`docs/VISION.md`, Abschnitt „KI“). KI legt selbst keine Beiträge an. Grund ist das Reputationsrisiko: Ein Beitrag, der einen Fakt erfindet oder eine Position falsch zuschreibt, fällt auf die Partei zurück, und im Vorrat muss für jeden Text eine Person geradestehen.

## Unterschrift eines Bildes

Das gilt auch für die Unterschrift eines Bildes, obwohl sie nur beschreibt, was zu sehen ist: Sie ist der Text, über den das Bild gefunden wird, und kann ebenso einen Fakt erfinden oder eine Position falsch zuschreiben. Die Person schreibt die Unterschrift im Bild-Formular selbst und speichert das Bild. Ein KI-Vorschlag darf ihr nur auf Klick ins Feld gesetzt werden; sie prüft, bearbeitet oder verwirft ihn. Den KI-Vorschlag über OpenAI gibt es seit #393 (30.10.2026) nicht mehr; ein Vorschlagsdienst muss auf eigener Infrastruktur laufen (ADR 0005). Ohne Unterschrift wird kein Bild gespeichert, und kein Hintergrunddienst schreibt eine nach (#281).

Verworfen wurde eine Ausnahme für die Unterschrift, bei der ein Hintergrunddienst die fehlende Unterschrift schreibt und das Bild damit sichtbar macht: Dann stünde für den Text, über den das Bild gefunden wird, niemand gerade, und Bild-URLs gingen ohne Zutun der Person an den KI-Anbieter.

## Ergänzung 28.10.2026: KI-Texte nur für die Suche

Was niemand zu sehen bekommt, braucht keinen Menschen, der dafür geradesteht: Hilfstexte, die nur der Indexierung und Suche dienen, darf ein Hintergrunddienst erzeugen und speichern. Für Bilder sind das der Text im Bild (Texterkennung), eine Bildeinbettung und eine Beschreibung mit Inhalt, Kontext und Stimmung aus einem Modell auf eigener Infrastruktur (ADR 0005). Angezeigt wird weiter nur die Unterschrift, die eine Person gespeichert hat; der erkannte Text darf ihr als Vorschlag angeboten werden. Die Grenze ist die Auslieferung: Sobald ein solcher Text Nutzenden gezeigt wird, gilt wieder der Grundsatz oben (#393).

## Considered Options

- Nur Bewertung und Hinweise, keine Textvorschläge: sicherer, verfehlt aber das Ziel, Argumentation schnell zu verbessern und auf Zielgruppen zuzuschneiden.
- KI legt Beiträge selbst an: füllt den Vorrat am schnellsten, aber niemand verantwortet den Inhalt.

## Consequences

Jede KI-Funktion, die Daten an einen externen Anbieter schickt, braucht vorher eine Erweiterung der Datenschutzerklärung. Ob übernommene KI-Texte als solche gekennzeichnet werden, ist noch nicht entschieden.
