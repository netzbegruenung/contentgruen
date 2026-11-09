# Nutzertest vor dem Launch

Vor dem Launch probieren drei bis fünf Personen Gut gesagt aus, auf dem Startbestand vom Schreibwochenende ([`VISION.md`](./VISION.md), „Weg zum Launch“, Schritt 3). Dieses Protokoll ersetzt das aus dem Konzeptarchiv (#347). Begriffe wie in [`GLOSSARY.md`](../GLOSSARY.md).

## Was wir wissen wollen

1. Findet jemand ohne Erklärung eine passende Antwort und bringt sie in eine Kommentarspalte?
2. Wo hakt es auf dem Handy?
3. Verstehen Menschen ohne Uni-Hintergrund die Wörter in der App?
4. Was blockiert den Launch?

Wir prüfen Aufgaben, keine Funktionen. Die Testperson soll etwas erreichen. Wir zeigen ihr nicht, wo was ist.

## Wer testet

- Drei bis fünf Personen. Mehr bringt vor dem Launch wenig Neues.
- Mindestens eine Person mit wenig Digitalerfahrung: nutzt das Handy für Messenger und Fotos, sonst kaum.
- Mindestens eine Person außerhalb des akademischen Milieus: ohne Studium, im Beruf nicht mit Texten befasst.
- Eine Person darf beides erfüllen. Höchstens eine Person aus dem Gründungsteam oder seinem engen Umfeld.
- Gut wäre: mindestens eine Person, die Kommentarspalten liest, aber selten selbst schreibt.

## Rahmen

- **Mobil zuerst.** Alle testen auf ihrem eigenen Handy, im eigenen Browser. Eine Person darf zusätzlich am Rechner testen, wenn Zeit bleibt.
- **Wo:** Auf dem Testsystem (`docs/DEPLOYMENT.md`, „Test System“), mit dem Startbestand über das Importskript. So bleiben die Zahlen auf der echten Instanz echt: Kopieren und Teilen zählen als Nutzung. Den Import stößt der Maintainer beim Betrieb des Testsystems an.
- **Konto:** Jede Testperson bekommt eine eigene Einladung auf dem Testsystem. Die Notiz an der Einladung nennt nur „Nutzertest“ und eine Nummer, keinen Namen. Die Einladung ist der echte Weg für Personen ohne Mitgliedschaft; nur so ist Aufgabe 5 aussagekräftig.
- **Dauer:** 45 Minuten je Person, einzeln.
- **Vor Ort**, wenn es irgend geht, und immer bei Personen mit wenig Digitalerfahrung: Den Handybildschirm im Videoanruf zu teilen, ist selbst schon eine Hürde. Sonst ein Videodienst mit Servern in der EU, ohne Aufzeichnung.
- **Wer dabei ist:** eine Person leitet, eine schreibt mit. Nicht mehr.
- **Wann:** nach dem Schreibwochenende, wenn der Startbestand steht.

## Vorbereitung

- [ ] Startbestand auf dem Testsystem, Suche liefert Treffer für die Beispiele unten
- [ ] Je Testperson eine Einladung
- [ ] Für Aufgabe 1 bis 3 je ein Beispiel aus dem Startbestand ausgesucht; Beispiel 2 hat eine Kurzfassung
- [ ] Je Testperson ein eigenes Beispiel ohne Treffer für Aufgabe 4 und 6, damit ein Beitrag aus einer Sitzung die nächste nicht verfälscht
- [ ] Mit der Testperson vorher klären, ob sie ihre Mails auf dem Handy abrufen kann (für Aufgabe 5)
- [ ] Beobachtungsbogen je Person (unten), ausgedruckt oder als Datei

## Ablauf

### Begrüßung (5 Minuten)

Etwa so sagen:

> Danke, dass du dir Zeit nimmst. Wir testen heute die App, nicht dich. Du kannst nichts falsch machen. Wenn etwas nicht klappt, liegt es an der App, und genau das wollen wir finden.
>
> Bitte sag laut, was du denkst: was du suchst, was du erwartest, was dich wundert. Ich helfe dir erst, wenn du gar nicht weiterkommst.
>
> Wir schreiben mit, aber ohne deinen Namen. Wir nehmen nichts auf. Du kannst jederzeit aufhören.
>
> Später legst du ein Konto an. Das ist ein Testsystem. Konto, Zustimmungen und alles, was du einträgst, löschen wir direkt nach dem Test.

Nach dem Einverständnis fragen. Kein Bildschirm- und kein Tonmitschnitt.

Zwei Fragen vorab, nur fürs eigene Verständnis, nicht notieren, wer was sagt:

- Liest du Kommentare unter Posts oder Artikeln? Schreibst du selbst welche?
- Was machst du, wenn dich ein Kommentar ärgert?

### Aufgaben (30 Minuten)

Jede Aufgabe als kleine Geschichte vorlesen. Keine Wörter aus der App verwenden, also nicht „suchen“, „Kommentar“, „kopieren“ oder „Fassung“, sondern beschreiben, was die Person erreichen will.

1. **Ohne Anmeldung eine Antwort finden.**
   „Du liest unter einem Post auf Facebook: [Beispiel 1]. Du willst etwas Kluges darauf antworten. Hier ist eine App, die dabei helfen soll. Bring eine passende Antwort in die Notizen auf deinem Handy.“
   Startpunkt: die Startseite, nicht angemeldet.
2. **Die kurze Antwort finden.**
   „Unter einem anderen Post steht: [Beispiel 2]. Dort ist wenig Platz. Bring eine möglichst kurze Antwort in deine Notizen.“
3. **Eine Antwort weitergeben.**
   „Eine Freundin hat dieselbe Diskussion in ihrer Familie. Schick ihr eine Antwort zu [Beispiel 3], so dass sie selbst nachlesen kann.“
   Nur bis zur Auswahl, an wen es geht. Nicht wirklich absenden.
4. **Nichts Passendes finden.**
   „Jemand schreibt: [Beispiel ohne Treffer]. Was kannst du hier tun?“
   Beobachten: Versteht die Person, dass es keine passende Antwort gibt? Sieht sie den Weg, selbst eine zu schreiben?
5. **Anmelden.**
   „Du möchtest hier selbst mitmachen. Melde dich mit der Einladung an, die wir dir geschickt haben.“
   Beobachten: Mail mit dem Link zum Passwort, Passwort, Nutzungsbedingungen, das eigene Häkchen zur Einwilligung nach Art. 9 DSGVO. Wo stockt es? Stockt es am Mail-Programm selbst, ist das ein eigener Befund, nicht einer der App.
6. **Selbst etwas beitragen.** Nur wenn noch mindestens zehn Minuten bleiben.
   „Dir fällt eine gute Antwort zu [Beispiel ohne Treffer] ein. Trag sie ein, damit andere sie finden.“
   Beobachten: Formularhilfe, Pflichtfelder, CC0-Hinweis, Anmerkungen beim Gegenlesen.
7. **Etwas melden.** Nur fragen, nicht tun lassen.
   „Angenommen, eine Antwort hier enthält etwas Falsches. Was würdest du tun?“

Wenn die Person nicht weiterkommt: erst warten, dann fragen „Was suchst du gerade?“, erst danach einen Tipp geben. Jeden Tipp im Bogen notieren.

### Abschluss (10 Minuten)

- Was war leicht? Was war schwer?
- Gab es Wörter, die du nicht verstanden hast?
- Würdest du die App beim nächsten Ärger über einen Kommentar benutzen? Warum (nicht)?
- Fehlt dir etwas?

Danken. Direkt danach: die Einladung abschalten, das Konto nach `docs/LOESCHKONZEPT.md` löschen und Beiträge aus der Sitzung ganz löschen. Damit ist auch die Einwilligung weg.

## Beobachtungsbogen

Je Testperson ein Bogen. Oben nur Nummer, Datum, Handy oder Rechner, „wenig Digitalerfahrung“ ja/nein, „außerhalb des akademischen Milieus“ ja/nein. Kein Name, kein Alter, keine Partei.

| Aufgabe | Geschafft (ja / mit Tipp / nein) | Zeit ungefähr | Wo gestockt | Was die Person gesagt hat |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| … | | | | |

Darunter: unverstandene Wörter, Bedienfehler (etwa daneben getippt, zurück statt weiter), Überraschungen.

## Auswertung

- Am selben Tag: Leitung und Mitschrift gehen die Bögen zusammen durch.
- Nach allen Tests: Befunde sammeln. Ein Befund zählt, wenn er bei mindestens zwei Personen auftritt oder eine Person ganz an einer Aufgabe scheitert.
- Jeden Befund einstufen:
  - **Launch-Blocker:** Aufgabe 1, 3, 4 oder 5 scheitert ohne Tipp, oder ein Text ist falsch oder irreführend.
  - **Qualität:** Die Aufgabe klappt, aber mit Umweg, Zögern oder einem unverstandenen Wort.
  - **Später:** Wunsch nach etwas Neuem. Bis zum Launch nur Qualität und Launch-Blocker (VISION, „Weg zum Launch“).
- Je Befund ein Ticket: was passiert ist, bei wie vielen Personen, welche Aufgabe, Einstufung. Keine Namen, keine Zitate, an denen man eine Person erkennt.
- Sobald die Tickets angelegt sind: Bögen löschen, ausgedruckte vernichten. Es bleiben nur die Tickets.
- Ergebnis kurz in #347: Zahl der Personen, Erfüllung der Auswahl (wenig Digitalerfahrung, außerhalb des akademischen Milieus), Links zu den Tickets.
