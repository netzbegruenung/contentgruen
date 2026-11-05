# Datenschutz-Folgenabschätzung: Punkte, Quests und Ranglisten

> **Entwurf zur Prüfung, nicht beschlossen.** Keine Rechtsberatung. Entscheiden müssen der
> Vorstand der Netzbegrünung als Verantwortlicher und die Datenschutzbeauftragte, am besten in
> derselben Runde wie #296; die Fragen an sie stehen in Abschnitt 6. Bis dahin bleiben die Punkte
> aus (`SEMANTIC_SEARCH_PUNKTE_AKTIV`, Standard aus).

Stand 05.11.2026; Code `main` @ `cdb7ec64` und #476 (gemergt), Datenschutzerklärung nach #499.
`ss/` = `mvp/backend/semantic-search-service/app/`, `DSE` = die Datenschutzerklärung
(`mvp/frontend/gutgesagt-frontend/src/app/datenschutz/datenschutz.component.html`), zitiert mit
dem Titel ihres Abschnitts, **(#476)** = Stand nach dem Merge von #476. Begriffe wie in
[`GLOSSARY.md`](../GLOSSARY.md), dort auch Prüfwert, Paar-Prüfwert, Fensterschlüssel und
Muster-Hinweis; Ausbaustufe steht in
`docs/VISION.md:14-23`, die Krone unter „Siegel“ (`GLOSSARY.md:278-279`).

## 1. Worum es geht

- **Gebaut (#476):** Entdoppelte Nutzung über einen Prüfwert, der nach seinem Tag
  verworfen wird (`ss/services/entdoppelung.py:1-30` (#476)), wirkt ab dem Einspielen auf
  „Diese Woche oft genutzt“. Ausgeschaltet bis zum Ende dieser DSFA: ein Punktestand, den nur die
  Person selbst sieht und der nicht gespeichert, sondern bei jedem Abruf berechnet wird
  (`ss/services/punkte_service.py:1-7` (#476), `ss/api/v1/usage.py:349-375` (#476));
  Muster-Hinweise für Admins, wenn zwei Konten sich innerhalb von 7 Tagen gegenseitig nutzen
  (`ss/services/muster_hinweise_service.py:1-24` (#476)).
- **Geplant, nicht gebaut:** Ranglisten (die ersten 10 und der eigene Platz, nur für Angemeldete,
  nur mit Zustimmung), Quests, Meilenstein-Abzeichen, Krone, Wochenthema
  (`docs/VISION.md:99-103`).
- **Fristen** (`docs/LOESCHKONZEPT.md:160-162` (#476)): Prüfwert 1 Tag, Paar-Prüfwert 7 Tage,
  Muster-Hinweis 56 Tage und mit dem Konto gelöscht
  (`mvp/scripts/manual/person_loeschen.sql:55` (#476)).

## 2. Ist eine DSFA Pflicht?

**Ja, nach Art. 35 Abs. 1** (voraussichtlich hohes Risiko). Die Regelbeispiele aus Abs. 3
treffen nicht zu: Es gibt keine Entscheidung mit Rechtswirkung (lit. a), die Zahl der
Mitwirkenden ist nicht „umfangreich“ (lit. b), und Gut gesagt beobachtet nichts Öffentliches
(lit. c). Auch die DSK-Mussliste (Art. 35 Abs. 4) nennt den Fall nicht ausdrücklich;
sie ist aber nicht abschließend. Nach den Leitlinien WP 248, die der EDSA übernommen hat, reichen
in der Regel zwei von neun Kriterien, und zwei treffen sicher zu:

- **Bewerten oder Einstufen:** Punkte und Rangplatz stufen Personen nach ihrem Verhalten ein
  (`ss/domain/punkte.py:55-73` (#476)).
- **Besondere Kategorien:** Schon die Mitwirkung lässt auf eine politische Meinung schließen
  (Art. 9 Abs. 1; DSE „Rückschlüsse auf deine politische Haltung“; `docs/VISION.md:101`).

Die DSFA muss stehen, **bevor die Punkte eingeschaltet werden**, nicht erst vor den Ranglisten,
wie `docs/VISION.md:134` es vorsieht: Schon der eigene Punktestand ist eine Bewertung von
Personen. Das ist eine Empfehlung; ändern sollte VISION erst, wer die DSFA übernimmt.
Neu zu prüfen ist sie vor Ausbaustufe 2 (Grünes Netz), weil dann lit. b anders aussehen kann.

## 3. Die drei wichtigsten Risiken und die Maßnahmen

| Risiko | Maßnahmen | Rest |
|---|---|---|
| **1. Politische Aktivität wird sichtbar.** Rangliste, Abzeichen, Krone und Wochenthema zeigen anderen, wer wie aktiv ist. Unter den Angemeldeten sind auch Nicht-Mitglieder (Beta-Zugänge, Einladungen; `GLOSSARY.md:423-424`), und Screenshots können nach außen gehen. | **Ein eigenes Opt-in** für alles, was andere an der Person sehen. Zwei gleichwertige Knöpfe, nichts vorbelegt, jederzeit widerrufbar (`docs/VISION.md:101`). Gezeigt wird nur der Anzeigename, nur die ersten 10 und der eigene Platz, nur für Angemeldete. Vorschlag zusätzlich: keine Linkvorschau für Ranglisten und eine Rangliste erst ab etwa 5 Personen mit Opt-in. Ohne Opt-in sieht nur die Person selbst ihre Punkte. | gering |
| **2. Ein Netz, wer wessen Beiträge nutzt.** PR #476 speichert kein Protokoll, nur Prüfwerte als HMAC. Mit einem Schlüssel aus der Konfiguration könnte, wer Datenbank und Schlüssel hat, für jedes Kontenpaar 7 Tage lang nachrechnen, wer einen Beitrag von wem genutzt hat (#499). | **Umgesetzt** (PR #476, BanSe/todo#266): Entdoppelung über Prüfwerte statt Protokoll, und beide Schlüssel liegen nur im Speicher, nach dem Muster des Tagesschlüssels der Besucher (`ss/utils/besucher_pseudonym.py:45-73`): Prüfwerte mit einem eigenen Tagesschlüssel, Paar-Prüfwerte mit einem Fensterschlüssel, der je 7 Tage wechselt und den vorigen einen Block lang zum Vergleich behält (`ss/services/entdoppelung.py:10-30,54-86` (#476)). Kein Bezug mehr zu `SEMANTIC_SEARCH_ACTOR_HASH_SECRET`. Nach einem Neustart beginnt ein Muster neu, und eine Nutzung zählt am selben Tag ein zweites Mal; das ist hinnehmbar. Muster-Hinweise lösen nichts automatisch aus; ein Admin prüft und hört die Personen an. | gering |
| **3. Zweckentfremdung und Druck.** Punkte könnten als Maßstab für Ämter, Listen oder Kampagnen dienen oder Masse und Schärfe belohnen. | Zweckbindung in Datenschutzerklärung und Nutzungsbedingungen: keine Weitergabe, keine Auswahl nach Punkten. Kein Geld und keine Sachleistung (`docs/VISION.md:31`). Punkte vor allem für Wirkung, Tagesdeckel, kein Abzug, keine Punkte fürs Bewerten (`docs/adr/0004-punkte-aus-wirkung-bei-anderen.md:9-19`). | gering bis mittel; in der Acht-Wochen-Bilanz ansehen |

Mit diesen Maßnahmen ist das Restrisiko gering bis mittel. Die Aufsichtsbehörde muss deshalb
nicht konsultiert werden (Art. 36).

## 4. Rechtsgrundlage

**Empfehlung: ausdrückliche Einwilligung, Art. 9 Abs. 2 lit. a, in zwei Stufen.**

1. **Beim ersten Login** fragt die App seit #489 nach der Art.-9-Einwilligung (Lückenliste
   D-N15, `docs/ART9_EINWILLIGUNG.md`); die DSE nennt sie seit #557. Ihr Wortlaut muss zusätzlich
   als Zwecke nennen: Punkte, Quests und Meilensteine, und den Schutz der Punkte durch
   Muster-Hinweise; der Wortlaut vom 05.11.2026 tut das noch nicht. Für die Muster-Hinweise
   reicht Art. 6 Abs. 1 lit. f allein nicht, weil sie Art. 9-Daten betreffen.
2. **Beim ersten Punkt** fragt die App nach dem Opt-in aus Risiko 1, das ist eine eigene
   Einwilligung für die Sichtbarkeit.

**Warum nicht lit. d** (politisch ausgerichtete Organisation): Die Norm deckt nur Mitglieder und
Personen mit regelmäßigem Kontakt und keine Offenlegung „nach außen“. Beta-Zugänge und
Eingeladene sind keine Mitglieder, und spätestens mit Ausbaustufe 2 geht der Kreis darüber hinaus.
Ob die Netzbegrünung überhaupt unter lit. d fällt, ist offen (`docs/VISION.md:134`). Lit. d bleibt
deshalb höchstens eine interne Hilfsbegründung und gehört nicht in die Datenschutzerklärung.

**Besucher** haben nicht eingewilligt. Ihre Kopie erzeugt für einen Tag einen Prüfwert aus dem
Besuchermerkmal (#470), gebildet mit einem Tagesschlüssel nur im Speicher
(`ss/services/entdoppelung.py:93-114` (#476)). Nach dem Tag verweist nichts mehr auf den
Besucher. Für diesen Stand trägt Art. 6 Abs. 1 lit. f wie bei der bestehenden Nutzungsmessung
(DSE „Verwendung von Beiträgen“); zu prüfen mit #495.

## 5. Notwendigkeit und Verhältnismäßigkeit (Art. 35 Abs. 7 lit. b)

Zweck ist, Wirkung bei anderen sichtbar zu machen und zum Mitmachen zu motivieren
(ADR 0004); ohne Zuordnung zu einer Person gibt es keine Punkte. Darüber hinaus entsteht nichts:
Punkte werden beim Abruf berechnet, nicht gespeichert (`ss/services/punkte_service.py:4-7`
(#476)); statt eines Protokolls, wer was genutzt hat, gibt es nur Prüfwerte mit kurzen Fristen
(Abschnitt 1); andere sehen etwas nur mit Opt-in. **Widerruf** (Vorschlag): Wer das Opt-in
zurücknimmt, verschwindet sofort aus Ranglisten und Abzeichen; die eigenen Punkte sieht die
Person weiter. Nach dem Widerruf der Login-Einwilligung kann die Person nichts mehr beitragen und
nichts bewerten; Gespeichertes bleibt, bis sie es löscht oder ihr Konto löschen lässt (#489,
`docs/ART9_EINWILLIGUNG.md`). Geht das Konto, gehen die Muster-Hinweise mit, die Paar-Prüfwerte
laufen nach 7 Tagen aus.

## 6. Fragen an Vorstand und Datenschutzbeauftragte

1. Ist eine DSFA nach Art. 35 Abs. 1 nötig, und genügt dieser Umfang (Abschnitt 2)?
2. Trägt Art. 9 Abs. 2 lit. a in zwei Stufen, auch für die Muster-Hinweise (Abschnitt 4)?
3. Trägt Art. 6 Abs. 1 lit. f den Prüfwert der Besucher (Abschnitt 4, mit #495)?
4. Erledigt: Der Schlüssel der Prüfwerte liegt nur im Speicher (Risiko 2, BanSe/todo#266).

## 7. Vor dem Einschalten der Punkte

Offen:

- DSFA übernommen (Abschnitt 6).
- Login-Einwilligung um die Zwecke aus Abschnitt 4 ergänzt.
- Im Code Punkte und Muster-Hinweise nur für Konten mit geltender Einwilligung (#559): Heute
  prüft der Zählendpunkt der Nutzung (`ss/api/v1/usage.py`) sie nicht, und die DSE stützt
  beides auf lit. a (Abschnitt 4).

Erledigt:

- Datenschutzerklärung angepasst (#499): Prüfwert und Vermerk der ersten Kopie unter
  „Verwendung von Beiträgen“, eigener Abschnitt „Punkte“ mit Paar-Prüfwert (7 Tage) und
  Muster-Hinweisen (8 Wochen), Startkonten; „kein Pseudonym“ beim Kopieren gestrichen, „kein
  Profiling“ gilt nur, solange Punkte aus sind; „Rückmeldung zur Nutzung“ nennt Muster-Hinweise
  als Ausnahme.
- Umstellung auf #470 und Schlüssel im Speicher aus Risiko 2 (PR #476).
