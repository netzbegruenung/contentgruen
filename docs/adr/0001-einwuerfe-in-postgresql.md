---
status: accepted
---

# Was noch Arbeit ist, liegt in PostgreSQL, nicht im Suchindex

Ein Einwurf ist Arbeit, kein Inhalt: Er wird nicht gesucht, nicht kopiert, nicht bewertet und nicht moderiert. Deshalb liegt der Fangkorb als eigene Tabelle in PostgreSQL neben den Beiträgen und nicht als weiterer Beitragstyp im Suchindex. Ausschlaggebend war, dass Stufenwechsel atomar sein müssen und dass Einwürfe weder Rauschen in die Suche bringen noch die Zähler in „Meine Beiträge“ verwässern sollen.

## Considered Options

- Einwurf als Beitragstyp im Suchindex: eine Mechanik weniger, aber jeder Einwurf landet in Suche und Zählern, das Einwerfen erzwingt eine Typwahl, und der Suchindex kennt keine Transaktionen.
- Allgemeines Modell, in dem alles, woran gearbeitet wird, ein Baustein mit Typ ist und Umwandlungen festhalten, woraus etwas entstanden ist: passt zur geplanten Umwandlung und Synthese, ist heute aber ein großer Umbau für eine einzige Kette. Es bleibt die Richtung; diese Entscheidung verbaut es nicht.

## Consequences

Jede weitere Arbeitsform braucht bis zum allgemeinen Modell eigene Tabellen und Verknüpfungen. Die Verknüpfung Einwurf → Beitrag ist n:m, und Einwürfe, die in einem Beitrag ausformuliert sind, werden nicht gelöscht, solange es den Beitrag gibt, damit Einwerfer, Destillierer und Ausformulierer rekonstruierbar bleiben.

Nachtrag (#421): Ursprünglich hieß es „Einwürfe werden nie gelöscht“. Seit #421 löscht ein täglicher Task Einwürfe, die in keinem Beitrag ausformuliert sind, nach ihrer Löschfrist (`docs/LOESCHKONZEPT.md`, „Fristen“). Die Herkunft eines bestehenden Beitrags bleibt rekonstruierbar; für einen Einwurf, aus dem nichts geworden ist, gibt es nichts zu rekonstruieren, und Speicherbegrenzung (Art. 5 Abs. 1 lit. e DSGVO) verlangt eine Frist.
