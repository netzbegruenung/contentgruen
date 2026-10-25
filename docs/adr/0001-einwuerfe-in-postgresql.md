---
status: proposed
---

# Einwürfe liegen in PostgreSQL, nicht als Beitragstyp im Suchindex

Ein Einwurf ist Arbeit, kein Inhalt: Er wird nicht gesucht, nicht kopiert, nicht bewertet und nicht moderiert. Deshalb liegt der Fangkorb als eigene Tabelle in PostgreSQL neben den Beiträgen und nicht als weiterer Beitragstyp in Qdrant. Ausschlaggebend war, dass Zuweisung und Stufenwechsel atomar sein müssen und dass Einwürfe weder Rausch-Vektoren in den Suchindex legen noch die Zähler in „Meine Beiträge“ verwässern sollen.

## Considered Options

- Neuer Beitragstyp in der Registry: im Backend am billigsten, aber jeder Einwurf erzeugt einen Vektor, erscheint in „Meine Beiträge“ und in den Zählern und bräuchte dort Ausnahmen.
- Eigener Status an einem bestehenden Beitragstyp: zwingt schon beim Einwerfen zur Typwahl, also genau zu der Entscheidung, die das Einwerfen vermeiden soll.

## Consequences

Der Weg zurück ist offen: Soll der Fangkorb später durchsuchbar werden, entsteht beim Ausformulieren oder per Backfill ein Beitrag. Die Verknüpfung Einwurf → Beitrag ist n:m, und Einwürfe werden nie gelöscht, damit Einwerfer, Destillierer und Ausformulierer rekonstruierbar bleiben.
