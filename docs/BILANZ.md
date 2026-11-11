# Bilanz: Signale und Konsequenzen

Acht Wochen nach dem öffentlichen Launch ziehen wir Bilanz (#348). Was wir bei welchem Signal tun, steht hier, bevor die Zahlen da sind. So deuten wir die Zahlen nicht im Nachhinein schön. Begriffe wie in [`GLOSSARY.md`](../GLOSSARY.md) (Bilanz, Basislinie), Rahmen in [`VISION.md`](./VISION.md), Abschnitt „Erfolg messen“.

Feste Zielwerte gibt es nicht. Bei zehn bis zwanzig Aktiven wären sie geraten (Entscheidung Maintainer, 28.10.2026). Ein Signal ist eine Abweichung von der Basislinie (Entscheidung Maintainer, 30.10.2026, #417).

## Kennzahlen

Admins lesen sie je Kalenderwoche im Dashboard unter „Bilanz“ ab.

| Kurz | Kennzahl | Was sie zeigt |
|---|---|---|
| K1 | Personen pro Tag, die suchen (Wochenmittel) | Ob Gut gesagt bekannt ist und benutzt wird |
| K2 | Nutzungen pro Woche | Ob Beiträge kopiert oder geteilt werden |
| K3 | Anteil der Suchen ohne Treffer | Ob der Bestand die Fragen abdeckt |
| H | Nutzungen je Suche (K2 geteilt durch die Suchen der Woche) | Ob die Treffer passen |

H ist eine Hilfskennzahl. Sie trennt „niemand kommt“ von „wer kommt, findet nichts Brauchbares“.

## Basislinie

- Gemessen im internen Launch: je Kennzahl der Median der Wochen 2 bis 4.
- Woche 1 zählt nicht. Neugier und Schreibsprint verzerren sie.
- Der Maintainer trägt die Basislinie gleich nach Ende von Woche 4 in #348 ein, spätestens vor Tag 90. Später geht das nicht mehr: Die Einzelzeilen sind nach 90 Tagen gelöscht.

## Wann ein Signal gilt

Verglichen werden die Wochen 5 bis 8 nach dem öffentlichen Launch mit der Basislinie.

1. **Zwei Wochen hintereinander.** Ein Wert zählt erst, wenn er in zwei aufeinanderfolgenden Wochen auftritt. Bei wenigen Aktiven schwanken die Zahlen stark.
2. **Genug Suchen.** K3 und H zählen nur in Wochen mit mindestens 30 Suchen. Darunter sagt ein Anteil zu wenig.
3. **Die Gespräche stützen es.** Mindestens drei der fünf Gespräche (unten) passen zum Signal. Sonst gilt es als offen: Wir machen vorerst weiter wie bisher, vermerken es in #348 und ziehen vier Wochen später erneut Bilanz. Für „weiter“ braucht es keine Gespräche.
4. **Zu wenige Suchen.** Haben zwei oder mehr der Wochen 5 bis 8 weniger als 30 Suchen, gilt das Signal „zu wenig bekannt“ (unten).

## Signale und Konsequenzen

Jedes Signal führt zu einer von zwei Konsequenzen: **weiter** oder **umbauen**. Einstellen ist keine Konsequenz der Bilanz (Entscheidung Maintainer, 09.11.2026). Trifft ein Umbau-Signal zu, wird umgebaut. Treffen mehrere zu, gilt diese Reihenfolge: erst Bestand (K3), dann Passung (H), dann Bekanntheit (K1).

### Weiter

| Signal | Konsequenz |
|---|---|
| In denselben zwei aufeinanderfolgenden Wochen: K1 mindestens doppelt so hoch wie die Basislinie, K3 höchstens 50 % und weniger als 15 Prozentpunkte über der Basislinie, H mindestens halb so hoch wie die Basislinie | Weiter nach Roadmap. Jetzt feste Zielwerte setzen, relativ zu den Wochen 5 bis 8. |

### Umbauen

| Signal | Woran es liegt | Konsequenz |
|---|---|---|
| K3 über 50 % oder mindestens 15 Prozentpunkte über der Basislinie | Der Bestand ist zu klein | Schwerpunkt Bestand: Schreibsprint auf die Liste „Suchen ohne Treffer“. Neue Funktionen warten. |
| K1 gleich oder höher als die Basislinie, aber H unter der Hälfte der Basislinie | Die Antworten passen nicht | In den Gesprächen nachfragen. Schwellen der Suche mit dem Suchtestset prüfen. |
| K1 nicht mindestens doppelt so hoch wie die Basislinie, oder K1 in den Wochen 5 bis 8 unter der Hälfte der Wochen 1 bis 2 nach dem öffentlichen Launch (die Neugier am Start ist schnell verflogen) | Gut gesagt ist zu wenig bekannt | Anlässe und Werbung in der Netzbegrünung. Am Werkzeug ändert sich nichts. |

Nach einem Umbau ziehen wir acht Wochen später erneut Bilanz, mit denselben Regeln.

## Gespräche

Nach acht Wochen führt der Maintainer fünf kurze Gespräche mit Aktiven, je etwa 15 Minuten. Notiert wird ohne Namen.

1. Wann hast du Gut gesagt zuletzt benutzt? Wofür?
2. Hast du schneller eine gute Antwort gefunden als ohne?
3. Hast du eine Antwort kopiert oder geteilt? Wenn nein: Was hat gefehlt?
4. Wonach hast du gesucht und nichts gefunden?
5. Würdest du Gut gesagt jemandem empfehlen? Warum (nicht)?

## Was die Zahlen verfälschen kann

- **Die Zählweise von K1 ändert sich.** Kommen das Server-Pseudonym (#444) oder die neuen Kennungen aus #429 zwischen den beiden Launches, zählt K1 anders. Dann messen wir die Basislinie neu oder vermerken den Bruch in #348. Ebenso seit #495: Besucher zählen je Anschluss, nicht mehr je Anschluss und Browser; K1 kann dadurch kleiner ausfallen.
- **Kopien eigener Beiträge.** Ob die Zählung heute auch Kopien eigener Beiträge erfasst (das wäre keine Nutzung im Sinne des Glossars), klärt #444. Für den Vergleich ist das egal, solange es in beiden Phasen gleich bleibt.
- **Annahmen.** Der öffentliche Launch erreicht deutlich mehr Personen als der interne; darauf beruht der Faktor 2 bei K1. Die interne Phase dauert mindestens vier Wochen.

## Ablauf

| Wann | Wer | Was |
|---|---|---|
| Gleich nach Woche 4 des internen Launchs | Maintainer | Basislinie in #348 eintragen |
| Wochen 5 bis 8 nach dem öffentlichen Launch | Maintainer | Kennzahlen je Woche im Dashboard ablesen |
| Woche 8 nach dem öffentlichen Launch | Maintainer | Fünf Gespräche führen, dann die Bilanz als Kommentar in #348: Werte, geltende Signale, Konsequenz |
