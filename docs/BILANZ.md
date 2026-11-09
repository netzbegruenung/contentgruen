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
- Der Maintainer trägt die Basislinie in Woche 4 in #348 ein. Später geht das nicht mehr: Die Einzelzeilen sind nach 90 Tagen gelöscht.

## Wann ein Signal gilt

Verglichen werden die Wochen 5 bis 8 nach dem öffentlichen Launch mit der Basislinie.

1. **Zwei Wochen hintereinander.** Ein Wert zählt erst, wenn er in zwei aufeinanderfolgenden Wochen auftritt. Bei wenigen Aktiven schwanken die Zahlen stark.
2. **Genug Suchen.** K3 und H zählen nur in Wochen mit mindestens 30 Suchen. Darunter sagt ein Anteil zu wenig.
3. **Die Gespräche stützen es.** Mindestens drei der fünf Gespräche (unten) passen zum Signal. Sonst gilt es als offen und wird in #348 so vermerkt.

## Signale und Konsequenzen

Jedes Signal führt zu einer von drei Konsequenzen: **weiter**, **umbauen** oder **einstellen**. Treffen mehrere Signale zu, gilt die strengste Konsequenz. Beim Umbauen kommt das Signal mit dem größten Abstand zur Schwelle zuerst.

### Weiter

| Signal | Konsequenz |
|---|---|
| K1 mindestens doppelt so hoch wie die Basislinie, K3 höchstens 50 % und höchstens 15 Prozentpunkte über der Basislinie, H mindestens halb so hoch wie die Basislinie | Weiter nach Roadmap. Jetzt feste Zielwerte setzen, relativ zu den Wochen 5 bis 8. |

### Umbauen

| Signal | Woran es liegt | Konsequenz |
|---|---|---|
| K3 über 50 % oder mindestens 15 Prozentpunkte über der Basislinie | Der Bestand ist zu klein | Schwerpunkt Bestand: Schreibsprint auf die Liste „Suchen ohne Treffer“. Neue Funktionen warten. |
| K1 gleich oder höher als die Basislinie, aber H unter der Hälfte der Basislinie | Die Antworten passen nicht | In den Gesprächen nachfragen. Schwellen der Suche mit dem Testset prüfen. |
| K1 nicht mindestens doppelt so hoch wie die Basislinie, oder in den Wochen 5 bis 8 unter der Hälfte der Wochen 1 bis 2 | Gut gesagt ist zu wenig bekannt | Anlässe und Werbung in der Netzbegrünung. Am Werkzeug ändert sich nichts. |

Nach einem Umbau ziehen wir acht Wochen später erneut Bilanz, mit denselben Regeln.

### Einstellen

| Signal | Konsequenz |
|---|---|
| Alle drei zugleich: K1 unter der Basislinie, H unter der Hälfte der Basislinie, und höchstens eines der fünf Gespräche sagt, Gut gesagt habe geholfen | Erst eine Umbaurunde von acht Wochen, mit dem Schwerpunkt, den die Gespräche nennen. Gilt das Signal danach wieder: Gut gesagt einstellen. |

Einstellen heißt: keine neuen Funktionen, keine Werbung, die Anmeldung schließen. Der Bestand steht unter CC0 und bleibt als Datei abrufbar. Den Betrieb beenden wir mit Vorlauf und sagen es vorher in der Netzbegrünung an. Löschen nach `docs/LOESCHKONZEPT.md`.

## Gespräche

Nach acht Wochen führt der Maintainer fünf kurze Gespräche mit Aktiven, je etwa 15 Minuten. Notiert wird ohne Namen.

1. Wann hast du Gut gesagt zuletzt benutzt? Wofür?
2. Hast du schneller eine gute Antwort gefunden als ohne?
3. Hast du eine Antwort kopiert oder geteilt? Wenn nein: Was hat gefehlt?
4. Wonach hast du gesucht und nichts gefunden?
5. Würdest du Gut gesagt jemandem empfehlen? Warum (nicht)?

Frage 2 entscheidet, ob ein Gespräch „hat geholfen“ zählt.

## Was die Zahlen verfälschen kann

- **Methodenbruch bei K1.** Kommen das Server-Pseudonym (#444) oder die neuen Kennungen aus #429 zwischen den beiden Launches, ändert sich die Zählung. Dann messen wir die Basislinie neu oder vermerken den Bruch in #348.
- **Kopien eigener Beiträge.** Ob sie in K2 mitzählen, klärt #444. Für den Vergleich ist das egal, solange es in beiden Phasen gleich bleibt.
- **Annahmen.** Der öffentliche Launch erreicht deutlich mehr Personen als der interne; darauf beruht der Faktor 2 bei K1. Die interne Phase dauert mindestens vier Wochen.

## Ablauf

| Wann | Wer | Was |
|---|---|---|
| Woche 4 nach dem internen Launch | Maintainer | Basislinie in #348 eintragen |
| Wochen 5 bis 8 nach dem öffentlichen Launch | Maintainer | Kennzahlen je Woche im Dashboard ablesen |
| Woche 8 nach dem öffentlichen Launch | Maintainer | Fünf Gespräche führen, dann die Bilanz als Kommentar in #348: Werte, geltende Signale, Konsequenz |
