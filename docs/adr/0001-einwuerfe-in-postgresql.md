---
status: accepted
---

# Was noch Arbeit ist, liegt in PostgreSQL, nicht im Suchindex

Ein Einwurf ist Arbeit, kein Inhalt: Er wird nicht gesucht, nicht kopiert, nicht bewertet und nicht moderiert. Deshalb liegt der Fangkorb als eigene Tabelle in PostgreSQL neben den Beiträgen und nicht als weiterer Beitragstyp im Suchindex. Ausschlaggebend war, dass Stufenwechsel atomar sein müssen und dass Einwürfe weder Rauschen in die Suche bringen noch die Zähler in „Meine Beiträge“ verwässern sollen.

## Considered Options

- Einwurf als Beitragstyp im Suchindex: eine Mechanik weniger, aber jeder Einwurf landet in Suche und Zählern, das Einwerfen erzwingt eine Typwahl, und der Suchindex kennt keine Transaktionen.
- Allgemeines Modell, in dem alles, woran gearbeitet wird, ein Baustein mit Typ ist und Umwandlungen festhalten, woraus etwas entstanden ist: passt zur geplanten Umwandlung und Synthese, ist heute aber ein großer Umbau für eine einzige Kette. Es bleibt die Richtung; diese Entscheidung verbaut es nicht.

## Consequences

Jede weitere Arbeitsform braucht bis zum allgemeinen Modell eigene Tabellen und Verknüpfungen. Die Verknüpfung Einwurf → Beitrag ist n:m, und Einwürfe werden nie gelöscht, damit Einwerfer, Destillierer und Ausformulierer rekonstruierbar bleiben.
