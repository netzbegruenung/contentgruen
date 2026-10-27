# Vision

Wofür Gut gesagt da ist, für wen, und wo seine Grenzen liegen. Grundlage sind ein privates Konzeptarchiv aus den Jahren 2024 und 2025 und ein Klärungsgespräch mit dem Maintainer im Oktober 2026. Begriffe wie in [`GLOSSARY.md`](../GLOSSARY.md); den Weg in Schritten beschreibt [`ROADMAP.md`](./ROADMAP.md), harte Abwägungen stehen in [`adr/`](./adr/).

## Wofür

Gut gesagt hilft Menschen, in Kommentarspalten schnell eine gute Antwort zu finden und zu verwenden, und sammelt diese Antworten gemeinsam: von vielen geschrieben, von vielen verbessert, frei weiterverwendbar (CC0).

- **Für die Mitlesenden.** Eine Antwort auf eine Aussage richtet sich an die Unentschiedenen, die mitlesen, nicht an die Person, die die Aussage gemacht hat. Daneben sind Beiträge „für die eigenen Leute“ ausdrücklich erlaubt (siehe Zweck).
- **Auch für Lesende ohne Abitur.** Kurze Sätze, Alltagswörter, Zahlen in den Alltag übersetzt.
- **Sanft lenken, nicht sperren.** Regeln stehen in der Formularhilfe, Hinweise kommen beim Speichern; gespeichert werden kann trotzdem.
- **Agieren, nicht nur reagieren.** Neben Antworten auf Aussagen gehören eigene Posts dazu, und Aussagen dürfen vorab angelegt werden, wenn ein Thema absehbar kommt.

## Ausbaustufen

1. **Netzbegrünung**: der Launch.
2. **Grünes Netz** (#225).
3. **Eigene Instanzen** weiterer, vor allem progressiver und zivilgesellschaftlicher Organisationen.
4. **Föderation**: Instanzen tauschen Beiträge aus, jede Organisation legt selbst fest, was sie sichtbar macht.

Stufe 3 und 4 sind langfristig; dafür gibt es noch keine Tickets. Was nichts kostet, wird schon jetzt organisationsneutral gebaut (`CODING_STANDARDS.md`), Bestehendes bleibt bis Stufe 3 so.

„Ausbaustufe“ meint diese Liste, „Roadmap-Stufe“ die Leiter in `ROADMAP.md`.

## Rechte und Geld

- Der Code steht unter der AGPL; Urheber des heutigen Codes ist der Maintainer. Die Netzbegrünung ist Diensteanbieterin der Instanz.
- Beiträge Dritter zum Code laufen über das Developer Certificate of Origin (DCO) in `CONTRIBUTING.md`.
- Geld kommt, wenn überhaupt, später über Dienstleistungen: Betrieb, Anpassung, Schnittstellen, Support. Premium-Funktionen werden getrennt gebaut und sind tendenziell ebenfalls Open Source.

## Inhalt und Moderation

- **Keine offizielle Linie.** Welche Antwort oben steht, entscheiden Ähnlichkeit, Stimmen und Nutzung. Offizielles Material erscheint nur als Herkunft an Beiträgen.
- **Sofort sichtbar, nachträglich moderiert.** Sachlich Falsches wird gemeldet; das reicht vorerst. Hinweise an Karten im Stil von Community Notes erst, wenn sich Meldungen häufen.
- **Keine Moderationsrolle**, solange Admins die Meldungen schaffen. Auslöser für eine eigene Rolle: Meldungen bleiben länger als zwei bis drei Tage liegen.
- **Keine automatische Ausblendung** durch Stimmen oder Meldungen; sperren tut ein Mensch.
- Die bestehende Drosselung reicht für Ausbaustufe 1 und wird mit Stufe 2 neu angesehen. Ab Stufe 3 gilt all das je Organisation, mit eigenen Admins.

## KI

- KI schlägt vor, ein Mensch verantwortet jeden Beitrag ([ADR 0003](./adr/0003-keine-generierten-antworten.md)). Keine Kanäle, auf denen KI selbst postet.
- Zuschnitt eines Beitrags für die eigene Verwendung: ja (#226), aber nicht in den Bestand.
- Beim Schreiben kommt zuerst Gegenlesen ohne KI (siehe Ton), ein KI-Verbesserungsvorschlag erst danach.
- Ein KI-Entwurf bei null Treffern kommt frühestens, wenn Roadmap-Stufe 4 (Quellen) steht.
- Anbieter bevorzugt Grünerator oder eine eigene Instanz bei verdigado, OpenAI höchstens übergangsweise; Eingaben ohne Personendaten.

## Produktgrenze

| Gehört dazu | Später denkbar | Gehört nicht dazu |
|---|---|---|
| Teilen (Teilen-Menü, Messenger, Linkvorschau) | Browsererweiterung | Monitoring und Frühwarnung |
| Umwandeln und Synthese (#226) | Messenger-Bot | Hass- und Strafanzeigen (Verweis auf Beratungsstellen) |
| Inhalte gemeinsam herstellen: Videoschnipsel teilen, Beiträge anderer remixen und verbessern (langfristig) | | Kanalbetreuung |
| Trends und eine Social Wall | | Inhalte, die KI herstellt (höchstens Verweis auf Grünerator) |

## Bestand

- **Fertige Beiträge schreiben Menschen.** Automatik, auch Crawler, liefert höchstens Einwürfe in den Fangkorb; Crawler sind ausdrücklich nicht ausgeschlossen, die Rechtslage wird je Quelle geprüft. Zulieferer für Positionspapiere und Arguhilfen kommen später, #224 ist der erste Fall.
- **Der KI-Seed v1.0 kommt nicht in den Bestand.** Er wird bereinigt und bleibt reine Testdaten für die Entwicklung: keine erfundenen Erlebnisse, kein Sarkasmus, Nutzung 0.
- **Material Dritter.** Material von Parteigliederungen wird neu formuliert, das Original als Herkunft verlinkt; eine Freigabe für wörtliche Übernahme ist Kür. Presse, Videos und Blogs stehen nur als Link in der Herkunft, nie als Text im Bestand; höchstens ein kurzes Zitat mit Quellenangabe in einer Hintergrundinfo, wenn das Zitatrecht es deckt.
- **Alle sichtbaren Zahlen sind echt.** Der Startbestand beginnt bei 0, Abzeichen erscheinen erst mit echter Nutzung.
- **Startkonten.** Damit der Startbestand nicht von einer einzigen Person zu kommen scheint, schreibt das Gründungsteam ihn unter wenigen Startkonten (Beta-Zugänge, Admins kennen die Zuordnung). Startkonten vergeben keine Stimmen und keine Nutzung, sammeln keine Punkte, tragen neutrale Namen ohne Beruf oder erfundene Lebensgeschichte und schreiben nur den Startbestand.

## Ton und Schreiben

- **Zweck** (optional): „Antwort in Kommentarspalten“ (Standard) oder „Für die eigenen Leute“. Bei Aussagen zeigt die Suche zuerst Kommentarspalten-Antworten; die Karte markiert Beiträge für die eigenen Leute. Zugespitzter Humor („bissig“) nur dort. Nie: Personen herabwürdigen.
- **Sechs Regeln** in der Formularhilfe: für Unentschiedene schreiben; den Vorwurf nicht wiederholen; erst die Gemeinsamkeit; wofür statt wogegen; nichts erfinden; kurz, ohne Belehrung, ohne Häme.
- **Nichts erfinden.** Eigene Erlebnisse nur als Platzhalter („[Hier ein eigenes Erlebnis: …]“); erfundene Erlebnisse oder Zahlen sind ein Meldegrund.
- **Schreibhilfen**: der Küchenzuruf als Leitfrage für die Kurzfassung („Was würdest du in einem Satz durch die Küche rufen?“); erst der Aufhänger, dann der Beleg; die Lesenden als Hauptfigur („du“); optional die Gliederung Ausgang, Wandel, Ziel für die Langfassung; Zahlen in den Alltag übersetzen.
- **Gegenlesen ohne KI** beim Speichern, als Hinweis: Schlüsselwörter der Aussage übernommen, Beginn mit Verneinung, Satz länger als etwa 12 bis 15 Wörter, Begriff aus der Liste „statt X sag Y“ (im Repo, per PR gepflegt, Startliste mit Fachwörtern wie „Diskurs“ oder „Transformation“).
- **Fassungen**: Beim Kommentar ist der Haupttext (Mittel) Pflicht, Kurz (≤ 280 Zeichen) und Lang (Begründung, Herkunft) sind optional. Die Karte zeigt Reiter nur für vorhandene Fassungen, Kopieren und Nutzung je Fassung.
- **Stil** optional (sachlich, humorvoll, persönlich, brückenbauend; bissig nur beim Zweck „für die eigenen Leute“), sichtbar an der Karte.
- **Titel** bleibt Pflicht, die Hilfe zeigt gute und schwache Beispiele. Beim Post ist der Text Pflicht und in eigenen Worten.
- **Nicht jede Aussage braucht eine Antwort**; kleine Accounts lieber melden. Der Hinweis steht in der Hilfe und auf der Ergebnisseite.
- **Über-Seite**: weg von „Falschbehauptungen widerlegen“, hin zu „Antworten, die Unentschiedene mitnehmen, gesammelt und verbessert von vielen“.

## Teilen

- Teilen-Knöpfe auf der Ergebnisseite („Ergebnis teilen“) und an jeder Karte (Link auf die Beitragsansicht); mobil das Teilen-Menü, am Desktop Link kopieren. Mastodon ist ein Ziel neben anderen.
- Linkvorschau für Beitragsansichten und Ergebnisseiten („Antworten auf: …“).
- Eine Karte teilen zählt als Nutzung; eine Ergebnisseite teilen und geteilte Links öffnen zählt nicht.
- Kopieren bleibt Text ohne Link auf Gut gesagt, wahlweise „Text“ oder „Text + Herkunft“.
- Datenschutz: Referrer-Policy `strict-origin`; wer geteilte Links öffnet, wird nicht protokolliert, weder in der App noch im vorgelagerten Webserver (#336).

## Motivation

Soziales Feedback, also sichtbare Nutzung durch andere, ist der wichtigste Antrieb und kommt direkt nach dem Launch, nicht erst am Ende der Roadmap.

- **Rückmeldung**: „Meine Beiträge“ zeigt die Nutzung je Beitrag und Fassung mit dem Zuwachs der letzten Woche; beim Anmelden ein Hinweis „Seit deinem letzten Besuch wurden deine Beiträge 12-mal genutzt“, nur in der App.
- **Meilensteine**: erste Nutzung durch andere, 10, 50, 100 Nutzungen, erste Stimme; ein kleines Abzeichen am Anzeigenamen.
- **Punkte** kommen aus der Wirkung bei anderen, nicht aus Menge ([ADR 0004](./adr/0004-punkte-aus-wirkung-bei-anderen.md)): Nutzung durch andere (Hauptanteil), Zustimmung, abgeschlossene Quests. Ein Beitrag ohne Nutzung bringt nichts.
- **Ranglisten** für Einzelne, je Woche und je Monat, nur für Angemeldete: die ersten 10 und der eigene Platz. Wer nicht erscheinen will, schaltet das ab.
- **Quests**: zwei Tagesaufgaben am Tag und ein gemeinsames Wochenziel. Zum Start: eine unbeantwortete Aussage beantworten, eine Fassung ergänzen, eine Variante anlegen, einen Einwurf ausformulieren, einen Einwurf einreichen, drei Beiträge bewerten. Später ein wählbarer Schwerpunkt (Sammeln oder Formulieren), langfristig vielleicht Fähigkeiten, die realen Tätigkeiten entsprechen. Kein kriegerisches Setting.
- **Bedarf sichtbar**: Eine Seite „Hier fehlt eine Antwort“ zeigt Angemeldeten unbeantwortete Aussagen; dort lassen sich Aussagen auch vorab anlegen.
- **Varianten**: „Als Vorlage nehmen“ legt einen neuen Beitrag mit eigenem Autor an, der auf dem Original beruht. Vorschläge an fremde Beiträge kommen später.
- **Trends**: „Diese Woche oft genutzt“ auf der Startseite; die Social Wall (Vollbild für Treffen) mit Ausbaustufe 2; öffentliche Gesamtzahlen erst, wenn sie etwas hergeben.

## Suche und Struktur

- **Testset vor Stellschrauben.** Ein kleines Set aus Suchanfragen und erwarteten Treffern misst, wie oft die Suche richtig und falsch trifft; danach werden Schwellen eingestellt. Dasselbe Set ist das Tor für Roadmap-Stufe 3.
- **Lieber keine Antwort als eine falsche.** Bei null Treffern zeigt die Seite höchstens drei ähnliche Aussagen, markiert als „passt vielleicht“, dazu wie viele Personen schon danach gesucht haben, „Selbst beantworten“ und den Weg zu „Hier fehlt eine Antwort“.
- **Themen** aus einer festen, kurzen Liste (per PR gepflegt), ein bis zwei je Aussage; keine freien Tags. Ab Roadmap-Stufe 3 schlägt eine Automatik Themen vor.
- Die Ergebnisseite erklärt in je einer Zeile, was ein Kommentar und was eine Hintergrundinfo ist. Keine Autovervollständigung: Die Suche ist auf ganze Sätze ausgelegt.

## Erfolg messen

Drei Kennzahlen, deren Zielwerte der Maintainer vor dem Launch festlegt: Personen pro Woche, die suchen; Nutzungen pro Woche; Anteil der Suchen ohne Treffer. Acht Wochen nach dem Launch wird Bilanz gezogen.

## Weg zum Launch

1. Einwürfe aus gesammeltem Material vorbereiten, per Skript, mit Link als Herkunft (#288).
2. Schreibwochenende im Gründungsteam: die 10 bis 15 häufigsten Aussagen mit je zwei Kommentaren (einer für die Kommentarspalte, einer sachlich mit Herkunft) und einige Posts.
3. Nutzertest mit drei bis fünf Personen auf diesem Bestand, mobil zuerst, mit mindestens einer Person mit wenig Digitalerfahrung und einer außerhalb des akademischen Milieus. Bis dahin nur Qualität und Launch-Blocker.
4. Was den Launch blockiert, beheben.
5. Launch in der Netzbegrünung.
6. Eine Woche später ein Schreibsprint in der Netzbegrünung, mit „Hier fehlt eine Antwort“ und Rückmeldung zur Nutzung.
