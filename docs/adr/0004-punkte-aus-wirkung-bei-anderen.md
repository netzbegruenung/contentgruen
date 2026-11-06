---
status: accepted
---

# Punkte gibt es für die Wirkung bei anderen, nicht für Menge

Punkte, Ranglisten und Meilensteine entstehen aus dem, was andere mit einem Beitrag tun: Nutzung durch andere (der Hauptanteil), Zustimmung durch andere und abgeschlossene Quests. Ein Beitrag, den niemand nutzt, bringt keine Punkte, auch nicht fürs Schreiben. Grund ist, dass Ranglisten ausdrücklich gewollt sind, aber Masse und Schärfe belohnen würden, wenn schon das Anlegen zählte: Der Bestand würde voller und schlechter, und das Ziel, Unentschiedene mitzunehmen, ginge verloren.

Damit die Punkte nicht zu fälschen sind, zählt eine Nutzung für Punkte höchstens einmal je Person (bei Besuchern je Sitzung), Beitrag und Tag. Eigene Nutzung und Nutzung durch Startkonten zählen nicht, Startkonten sammeln selbst keine. Ablehnung zieht nichts ab, damit niemand gezielt nach unten drückt. Gesperrte oder endgültig entfernte Beiträge verlieren ihre Punkte, und Punkte für Quest-Beiträge gibt es erst, wenn der Beitrag drei Tage ohne Sperre steht. Auffällige Muster, etwa zwei Konten, die sich gegenseitig nutzen, sehen Admins als Hinweis; eine Automatik straft niemanden ab.

## Drei Stufen (Ergänzung 28.10.2026)

Damit auch Neue sofort eine Rückmeldung sehen, gibt es Punkte in drei Stufen:

- **Tun** bringt kleine Punkte, gedeckelt je Tag: ein gespeicherter Beitrag, ein Einwurf, der ausformuliert wird (für die einwerfende Person). Ein Beitrag zählt erst, wenn er drei Tage ohne Sperre steht. Bewerten bringt keine Punkte, damit Stimmen ein echtes Signal bleiben.
- **Explizite Aufgaben** (abgeschlossene Quests) bringen mehr, ebenfalls gedeckelt.
- **Wirkung bei anderen** (Nutzung, Zustimmung) bringt die großen Punkte und bleibt der Hauptanteil.

Unterstützungsarbeit ohne eigene Nutzung (Einwerfen, Destillieren, Fangkorb) erkennen zusätzlich Meilensteine an. Gewichte und Deckel stehen in der Konfiguration.

## Besucher ohne Sitzung (Ergänzung 30.10.2026, #446)

Die Sitzung, über die oben Nutzungen von Besuchern entdoppelt werden, gibt es seit #446 nicht mehr: Der Browser trägt keine Kennung, und Nutzungsereignisse halten keine fest. Wie Nutzungen von Besuchern für Punkte entdoppelt werden, ist damit offen und wird mit der Punktezählung entschieden. Das Tagespseudonym wäre ein Kandidat; es müsste dann an der Nutzung gespeichert werden, was die Datenschutzerklärung heute ausschließt.

## Entdoppelung ohne gespeicherte Nutzung (Ergänzung 05.11.2026, #352)

Entschieden mit der Punktezählung (PR #476, BanSe/todo#266): Besucher werden über ihr Besuchermerkmal entdoppelt, angemeldete Personen über ihre Kennung. An der Nutzung wird dafür weder Kennung noch Tagespseudonym gespeichert, sondern nur ein Prüfwert für den laufenden Tag, gebildet mit einem eigenen Schlüssel, der nur im Arbeitsspeicher liegt; die Muster-Hinweise vergleichen ebenso Paar-Prüfwerte mit dem Fensterschlüssel. Preis: Nach einem Neustart zählt eine Nutzung am selben Tag ein zweites Mal, und ein Muster beginnt neu. Bestand von vor der Umstellung, der keine Sitzung trägt, zählt je Beitrag und Tag einmal.

## Ranglisten nur mit Zustimmung (Ergänzung 05.11.2026)

Ranglisten erscheinen nur bei Personen, die ausdrücklich zugestimmt haben. Die Zustimmung ist freiwillig, nichts ist vorbelegt, und sie lässt sich jederzeit widerrufen. Meilenstein-Abzeichen, die anderen sichtbar sind, brauchen ebenfalls eine gesonderte Zustimmung. Grund: Schon die Teilnahme an einer Rangliste verrät eine politische Haltung (DSGVO Art. 9), und Ranglisten zeigen anderen nur den Anzeigenamen. Die Entscheidung steht in `docs/VISION.md` und `docs/DSFA_PUNKTE.md`. Der Satz in Consequences unten ist entsprechend ersetzt.

## Considered Options

- Punkte für jede Tätigkeit in voller Höhe (Schreiben, Einwerfen, Bewerten): am einfachsten, belohnt aber Menge statt Qualität. Übernommen ist nur die gedeckelte Form (siehe „Drei Stufen“).
- Keine Ranglisten, nur persönliche Meilensteine: kein Wettbewerb um Masse, verschenkt aber den Antrieb, den Ranglisten nach den Testsessions haben.
- Abzug für Ablehnung: macht Punkte zum Ziel von Absprachen gegen Einzelne.

## Consequences

Der Zähler an der Karte darf weiter jede Nutzung zählen, die Punkte brauchen aber eine eigene, entdoppelte Zählung. Die Gewichte stehen in der Konfiguration, nicht im Code. Ranglisten zeigen Anzeigenamen; die Datenschutzerklärung braucht dafür einen Abschnitt, und die Teilnahme an Ranglisten braucht die Zustimmung der Person (siehe Ergänzung vom 05.11.2026).
