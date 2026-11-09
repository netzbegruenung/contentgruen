# Datenschutz-Folgenabschätzung

> **Entwurf, nicht juristisch geprüft, nicht beschlossen.** Keine Rechtsberatung. Entscheiden
> müssen der Vorstand der Netzbegrünung als Verantwortlicher und die Datenschutzbeauftragte, am
> besten in derselben Runde wie #296; die Fragen an sie stehen in Abschnitt 6. Bis dahin bleiben
> die Punkte aus (`SEMANTIC_SEARCH_PUNKTE_AKTIV`, Standard aus). Aussagen ohne Beleg im Repo
> stehen als **offen** da.

Abschnitte 1 bis 7 prüfen Punkte, Quests und Ranglisten, Abschnitte 8 und 9 alle übrigen
Verarbeitungen des Dienstes (#374).

Abschnitte 1 bis 7: Stand 05.11.2026; Code `main` @ `cdb7ec64` und #476 (gemergt),
Datenschutzerklärung nach #499. Abschnitte 8 und 9: Stand 07.11.2026, Code `main` @ `c2c9bbe5`
(einen Tag `v0.8.1` gibt es noch nicht, der letzte ist `v0.8.0`).
`ss/` = `mvp/backend/semantic-search-service/app/`, `DSE` = die Datenschutzerklärung
(`mvp/frontend/gutgesagt-frontend/src/app/datenschutz/datenschutz.component.html`), in
Abschnitt 1 bis 7 zitiert mit dem Titel ihres Abschnitts, in Abschnitt 8 und 9 mit Zeile
(`DSE:<Zeile>`); `LK` = [`docs/LOESCHKONZEPT.md`](./LOESCHKONZEPT.md), `A9` =
[`docs/ART9_EINWILLIGUNG.md`](./ART9_EINWILLIGUNG.md); **(#476)** = Stand nach dem Merge von #476.
Begriffe wie in
[`GLOSSARY.md`](../GLOSSARY.md), dort auch Prüfwert, Paar-Prüfwert, Fensterschlüssel und
Muster-Hinweis; Ausbaustufe steht in
`docs/VISION.md:14-23`, die Krone unter „Siegel“ (`GLOSSARY.md:278-279`).

## 1. Worum es geht

- **Gebaut (#476):** Entdoppelte Nutzung über einen Prüfwert, der nach seinem Tag
  verworfen wird (`ss/services/entdoppelung.py:1-30` (#476)), wirkt ab dem Einspielen auf
  „Diese Woche oft genutzt“. Ausgeschaltet bis zum Ende dieser DSFA: ein Punktestand, den nur die
  Person selbst sieht und der nicht gespeichert, sondern bei jedem Abruf berechnet wird
  (`ss/services/punkte_service.py:1-7` (#476), `ss/api/v1/usage.py:389-415` (#476));
  Muster-Hinweise für Admins, wenn zwei Konten sich innerhalb von 7 Tagen gegenseitig nutzen
  (`ss/services/muster_hinweise_service.py:1-24` (#476)).
- **Gebaut (#351), hinter demselben Schalter:** Meilensteine, die nur die Person selbst in
  „Meine Beiträge“ sieht, bei jedem Abruf aus denselben Zählern berechnet und nicht gespeichert,
  ohne Startkonten und nur mit Art.-9-Einwilligung (`ss/services/meilensteine_service.py`).
- **Geplant, nicht gebaut:** Ranglisten (die ersten 10 und der eigene Platz, nur für Angemeldete,
  nur mit Zustimmung), Quests, Meilenstein-Abzeichen am Anzeigenamen, Krone, Wochenthema
  (`docs/VISION.md:99-103`).
- **Fristen** (`docs/LOESCHKONZEPT.md:161-163` (#476)): Prüfwert 1 Tag, Paar-Prüfwert 7 Tage,
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
Für den Grundbetrieb ohne Punkte trifft sicher nur WP-248-Kriterium 4 (vertrauliche Daten) zu
(Abschnitt 8.1).

## 3. Die drei wichtigsten Risiken und die Maßnahmen

| Risiko | Maßnahmen | Rest |
|---|---|---|
| **1. Politische Aktivität wird sichtbar.** Rangliste, Abzeichen, Krone und Wochenthema zeigen anderen, wer wie aktiv ist. Unter den Angemeldeten sind auch Nicht-Mitglieder (Beta-Zugänge, Einladungen; `GLOSSARY.md:489-490`), und Screenshots können nach außen gehen. | **Ein eigenes Opt-in** für alles, was andere an der Person sehen. Zwei gleichwertige Knöpfe, nichts vorbelegt, jederzeit widerrufbar (`docs/VISION.md:101`). Gezeigt wird nur der Anzeigename, nur die ersten 10 und der eigene Platz, nur für Angemeldete. Vorschlag zusätzlich: keine Linkvorschau für Ranglisten und eine Rangliste erst ab etwa 5 Personen mit Opt-in. Ohne Opt-in sieht nur die Person selbst ihre Punkte. | gering |
| **2. Ein Netz, wer wessen Beiträge nutzt.** PR #476 speichert kein Protokoll, nur Prüfwerte als HMAC. Mit einem Schlüssel aus der Konfiguration könnte, wer Datenbank und Schlüssel hat, für jedes Kontenpaar 7 Tage lang nachrechnen, wer einen Beitrag von wem genutzt hat (#499). | **Umgesetzt** (PR #476): Entdoppelung über Prüfwerte statt Protokoll, und beide Schlüssel liegen nur im Speicher, nach dem Muster des Tagesschlüssels der Besucher (`ss/utils/besucher_pseudonym.py:45-73`): Prüfwerte mit einem eigenen Tagesschlüssel, Paar-Prüfwerte mit einem Fensterschlüssel, der je 7 Tage wechselt und den vorigen einen Block lang zum Vergleich behält (`ss/services/entdoppelung.py:10-30,54-86` (#476)). Kein Bezug mehr zu `SEMANTIC_SEARCH_ACTOR_HASH_SECRET`. Nach einem Neustart beginnt ein Muster neu, und eine Nutzung zählt am selben Tag ein zweites Mal; das ist hinnehmbar. Muster-Hinweise lösen nichts automatisch aus; ein Admin prüft und hört die Personen an. | gering |
| **3. Zweckentfremdung und Druck.** Punkte könnten als Maßstab für Ämter, Listen oder Kampagnen dienen oder Masse und Schärfe belohnen. | Zweckbindung in Datenschutzerklärung und Nutzungsbedingungen: keine Weitergabe, keine Auswahl nach Punkten. Kein Geld und keine Sachleistung (`docs/VISION.md:31`). Punkte vor allem für Wirkung, Tagesdeckel, kein Abzug, keine Punkte fürs Bewerten (`docs/adr/0004-punkte-aus-wirkung-bei-anderen.md:9-19`). | gering bis mittel; in der Acht-Wochen-Bilanz ansehen |

Mit diesen Maßnahmen ist das Restrisiko gering bis mittel. Die Aufsichtsbehörde muss deshalb
nicht konsultiert werden (Art. 36).

## 4. Rechtsgrundlage

**Empfehlung: ausdrückliche Einwilligung, Art. 9 Abs. 2 lit. a, in zwei Stufen.**

1. **Beim ersten Login** fragt die App seit #489 nach der Art.-9-Einwilligung (Lückenliste
   D-N15, `docs/ART9_EINWILLIGUNG.md`); die DSE nennt sie seit #557. Ihr Wortlaut muss zusätzlich
   als Zwecke nennen: Punktestand, Level, Quests und Meilenstein-Abzeichen (nur für die Person,
   solange sie nicht gesondert zustimmt, sie anderen Angemeldeten zu zeigen; Opt-in aus Risiko 1),
   neue Aktionen, die ein höheres Level freischaltet, und den Schutz der Punkte durch
   Muster-Hinweise; das tut der Wortlaut `2026-11-05-b` (#559), der den ersten vom selben
   Tag ablöst, bevor er in einem Release war. Für die Muster-Hinweise
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

**Lücke vor der Einwilligung:** Zwischen Anmeldung und Einwilligung, und nach einem Widerruf,
verarbeitet Gut gesagt trotzdem Art.-9-relevante Daten: das Konto, den Anzeigenamen, Suchereignisse
mit Tagespseudonym und Meldungen mit Kennung (Abschnitt 8.2, V1, V7, V12). Drei Wege:

1. Für Mitglieder der Netzbegrünung lit. d als Grundlage für das Konto; für Einladungen und
   Beta-Zugänge bleibt die Lücke.
2. Den Anzeigenamen erst nach der Einwilligung ablegen und Suchereignisse ohne Einwilligung wie
   bei Besuchern bilden. Kostet eine kleine Codeänderung.
3. Die Einwilligung vor der Kontoanlage einholen (Einladung, Realm). Kostet Änderungen in Keycloak.

Empfehlung: Weg 2; lit. d bleibt, wie oben, höchstens Hilfsbegründung.

## 5. Notwendigkeit und Verhältnismäßigkeit (Art. 35 Abs. 7 lit. b)

Zweck ist, Wirkung bei anderen sichtbar zu machen und zum Mitmachen zu motivieren
(ADR 0004); ohne Zuordnung zu einer Person gibt es keine Punkte. Darüber hinaus entsteht nichts:
Punkte werden beim Abruf berechnet, nicht gespeichert (`ss/services/punkte_service.py:4-7`
(#476)); statt eines Protokolls, wer was genutzt hat, gibt es nur Prüfwerte mit kurzen Fristen
(Abschnitt 1); andere sehen etwas nur mit Opt-in. **Widerruf** (Vorschlag): Wer das Opt-in
zurücknimmt, verschwindet sofort aus Ranglisten und Abzeichen; die eigenen Punkte sieht die
Person weiter. Nach dem Widerruf der Login-Einwilligung kann die Person nichts mehr beitragen und
nichts bewerten, ihre Punkte sind 0, und ihre Kopien zählen nur noch am Zähler der Karte, ohne
Prüfwert und ohne Meldung für Muster-Hinweise (#559); Gespeichertes bleibt, bis sie es löscht
oder ihr Konto löschen lässt (#489, `docs/ART9_EINWILLIGUNG.md`). Geht das Konto, gehen die
Muster-Hinweise mit, die Paar-Prüfwerte laufen nach 7 Tagen aus.

## 6. Fragen an Vorstand und Datenschutzbeauftragte

1. Ist eine DSFA nach Art. 35 Abs. 1 nötig, und genügt dieser Umfang (Abschnitt 2)?
2. Trägt Art. 9 Abs. 2 lit. a in zwei Stufen, auch für die Muster-Hinweise (Abschnitt 4)?
3. Trägt Art. 6 Abs. 1 lit. f den Prüfwert der Besucher (Abschnitt 4, mit #495)?
4. Erledigt: Der Schlüssel der Prüfwerte liegt nur im Speicher (Risiko 2, PR #476).
5. Ist eine DSFA auch für den Grundbetrieb ohne Punkte zu führen, und genügt Abschnitt 8 dafür?
   Wie wird die Lücke vor der Einwilligung geschlossen (Abschnitt 4), trägt Art. 6 Abs. 1 lit. c
   Meldungen angemeldeter Personen ohne Einwilligung (V12), und gibt es eine Altersgrenze für
   Konten (WP 248 Kriterium 7)?

## 7. Vor dem Einschalten der Punkte

Offen:

- DSFA übernommen (Abschnitt 6).

Erledigt:

- Datenschutzerklärung angepasst (#499): Prüfwert und Vermerk der ersten Kopie unter
  „Verwendung von Beiträgen“, eigener Abschnitt „Punkte“ mit Paar-Prüfwert (7 Tage) und
  Muster-Hinweisen (8 Wochen), Startkonten; „kein Pseudonym“ beim Kopieren gestrichen, „kein
  Profiling“ gilt nur, solange Punkte aus sind; „Rückmeldung zur Nutzung“ nennt Muster-Hinweise
  als Ausnahme.
- Umstellung auf #470 und Schlüssel im Speicher aus Risiko 2 (PR #476).
- Im Code Punkte und Muster-Hinweise nur für Konten mit geltender Einwilligung (#559, PR #560):
  Der Zählendpunkt der Nutzung (`ss/api/v1/usage.py`) bildet ohne Einwilligung keinen Prüfwert
  und meldet nichts für Muster-Hinweise, auch nicht, wenn die Autorin nicht eingewilligt hat;
  `GET /users/me/punkte` liefert ohne Einwilligung 0. Gefragt wird je Kopie und je Abruf.
- Login-Einwilligung um die Zwecke aus Abschnitt 4 ergänzt (PR #560, Wortlaut `2026-11-05-b`).

## 8. Übrige Verarbeitungen des Dienstes (#374)

Abschnitt 1 bis 7 prüfen Punkte, Quests und Ranglisten. Dieser Abschnitt nimmt alles auf, was `main`
sonst verarbeitet, mit Belegen als `Datei:Zeile`.

**Ergebnis:** Art. 9 betrifft den Kern: Schon ein Konto, ein Beitrag, eine Stimme oder ein Einwurf
kann auf eine politische Meinung schließen lassen (`DSE:1081-1084`); Rechtsgrundlage der Mitwirkung
ist die Art.-9-Einwilligung (`A9:3-6`, `DSE:1094-1122`). Empfohlen wird eine DSFA für die ganze
Plattform (8.1). Drei Lücken sind offen: Konto und Anzeigename entstehen vor der Einwilligung (V1),
das Tagespseudonym angemeldeter Personen ist mit dem Schlüssel aus der Konfiguration nachrechenbar,
falls er gesetzt ist (V7), Anwendungsprotokolle haben in Produktion keine Frist (V16). **Erst wenn
diese drei geschlossen sind** und die Maßnahmen aus 8.2 und 8.3 stehen, ist das Restrisiko gering
bis mittel und eine Konsultation nach Art. 36 nicht nötig; bis dahin liegt es bei R2 und R5 bei
mittel.

### 8.1 Schwellwert für den Grundbetrieb ohne Punkte

WP 248 rev.01 wie in Abschnitt 2 (Wortlaut für diesen Abschnitt nicht erneut im Original geprüft),
hier für den Grundbetrieb neben dem Stand mit Punkten:

| Kriterium | Grundbetrieb | mit Punkten |
|---|---|---|
| 1 Bewerten, Einstufen | nein | **ja**: Punkte stufen Personen nach ihrem Verhalten ein (`ss/services/punkte_service.py:1-7`) |
| 3 Systematische Überwachung | **offen**: Nutzung ohne Kennung (V9), Suchereignisse mit Tagespseudonym; das der Angemeldeten ist nachrechenbar, falls der Schlüssel gesetzt ist (V7); nein, sobald V7 umgestellt ist | wie links |
| 4 Vertrauliche oder höchstpersönliche Daten | **ja**: politische Meinung (`DSE:1081-1084`) | **ja** |
| 5 Umfangreich | nein (Ausbaustufe 1) | nein |
| 6 Abgleich von Datensätzen | nein | teilweise: Nutzung, Stimmen und Beiträge fließen in den Punktestand |
| 7 Schutzbedürftige Betroffene | **offen**: eine Altersgrenze für Konten steht nirgends | wie links |
| 2, 8, 9 | nein | nein |

**Schluss:** Für den Grundbetrieb ist die Pflicht grenzwertig, solange Kriterium 3 offen ist; Art.
35 Abs. 3 und die DSK-Mussliste ändern daran nichts (Abschnitt 2). Ein begründetes Verwerfen wäre
möglich, aber angreifbar: Die Plattform sammelt genau die Daten, die Art. 9 schützt, und die Punkte
sind gebaut und nur abgeschaltet (`ss/core/config.py:238-244`). Die Datenschutzbeauftragte ist zu
beteiligen (Art. 35 Abs. 2).

### 8.2 Die Verarbeitungen (Art. 35 Abs. 7 lit. a)

Je Verarbeitung: Zweck, Rechtsgrundlage, Daten, Frist, wer es sieht, Risiko, Maßnahmen. Ohne
Personenbezug und deshalb nicht einzeln aufgeführt sind die Tabellen `usage_tracking`,
`nutzung_je_fassung`, `suchen_je_tag`, `varianten` und `aussage_themen` (Zähler bzw. IDs ohne
Kennung; `ss/infrastructure/database/models.py:37,96,287,373,391`, `LK:364-390`). Wo die
Datenschutzerklärung eine Rechtsgrundlage nennt, ist das der heutige Stand; geprüft hat ihn niemand
juristisch (#296). **Empfänger** sind bei allen Verarbeitungen gleich und stehen unter „Für alle:
Empfänger und Ort“.

#### Für alle: Empfänger und Ort

- verdigado eG als Auftragsverarbeiterin, Hetzner als Unterauftragsverarbeiterin, Rechenzentrum in
  Deutschland; sonst keine Empfänger (`DSE:66-75`). **Offen:** ob der AV-Vertrag Gut gesagt abdeckt
  (#506, `docs/FRAGEN_DATENSCHUTZBEAUFTRAGTE.md:38-45`).
- Keine Übermittlung außerhalb der EU, kein KI-Anbieter (`DSE:1048-1051`, `CLAUDE.md`, Abschnitt
  „Datenschutz — keine KI-Anbieter“). Ausnahme: Bilder von fremden Servern lädt der Browser erst
  nach Klick (`DSE:996-1022`).
- Mails (Bestätigung einer Meldung, Entscheidung) gehen über einen SMTP-Server aus der Konfiguration
  (`ss/core/config.py:196-198`); welcher das in Produktion ist, steht nicht im Repo (**offen**,
  gehört zur AV-Frage).
- Admins sehen Kennungen, Meldungen samt Name und E-Mail-Adresse, Sperren und Muster-Hinweise
  (`DSE:268-269`, `DSE:720`, `DSE:759-760`, `DSE:631-632`).

#### V1 Konto, Anmeldung und Anzeigename

- **Zweck:** Anmelden, Mitwirkung zuordnen, Anzeigename an Beiträgen (`DSE:133-134`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. b für das Konto, lit. f für den Anzeigenamen
  (`DSE:135-136`, `DSE:297-300`).
- **Daten:** Kennung, E-Mail-Adresse und Name im verschlüsselten Cookie (`DSE:117-127`); in der
  Datenbank nur Kennung und Anzeigename (`ss/infrastructure/database/models.py:654-675`). Konto im
  eigenen Realm (ADR 0006).
- **Frist:** Cookie 14 Tage nach letzter Nutzung (`DSE:137-139`); Anzeigename bis zur Kontolöschung
  (`DSE:300`); nie benutzte Konten aus Einladungen etwa 33 Tage (`LK:164`).
- **Risiko:** Schon das Konto verrät die Nähe zu einer politischen Richtung (`DSE:1081-1083`). Der
  Anzeigename kommt mit jeder angemeldeten Anfrage an und wird bei der ersten und nach jeder
  Änderung abgelegt, auch **vor und ohne Art.-9-Einwilligung** (`ss/main.py:282-283`,
  `ss/dependencies.py:464-476`, `ss/services/anzeigename_service.py:74-89`); die Einwilligung kommt
  erst nach der ersten Anmeldung (`A9:10-14`). Für Mitglieder der Netzbegrünung käme lit. d in
  Frage, für Konten aus Einladungen nicht (Abschnitt 4, „Lücke vor der Einwilligung“).
- **Maßnahmen:** Besucher sehen weder Anzeigename noch Kennung (`DSE:263-266`); nur Vorname und
  Initial (`DSE:125-127`); E-Mail-Adresse und voller Name nicht in der Plattform (`DSE:123-124`);
  Einladung ohne Zuordnung zum Konto (ADR 0006:9).

#### V2 Art.-9-Einwilligung

- **Zweck:** Rechtsgrundlage der Mitwirkung und ihr Nachweis (Art. 7 Abs. 1, `DSE:1117-1122`).
- **Rechtsgrundlage:** Art. 9 Abs. 2 lit. a; der Nachweis nach Art. 7 Abs. 1 (`DSE:1119-1122`).
- **Daten:** Kennung, Zeitpunkt, Kennung des Wortlauts, Zeitpunkt des Widerrufs
  (`ss/infrastructure/database/models.py:715-721`).
- **Frist:** bis zur Kontolöschung, auch widerrufene (`DSE:1123-1125`, `LK:102-103`).
- **Risiko:** Die Zeile selbst belegt die Mitwirkung. Die Prüfung unterscheidet nicht nach Wortlaut
  (`A9:68-72`): Nennt ein neuer Wortlaut neue Zwecke, gilt eine alte Einwilligung still für sie mit.
- **Maßnahmen:** eigenes Häkchen, nicht vorbelegt, getrennt von den Nutzungsbedingungen
  (`A9:12-14`); Widerruf im Profilmenü (`A9:40-45`); ohne Einwilligung sind die Endpunkte gesperrt,
  die Mitwirkung speichern (Beitragen, Einwerfen, Bewerten); Melden, Feedback und Löschen bleiben
  offen; die Liste ist durch einen Test abgesichert (`A9:17-27`).

#### V3 Beiträge, Herkunft, Änderungsverlauf

- **Zweck:** durchsuchbarer Bestand, Nachvollziehbarkeit (`DSE:286-287`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. b, lit. f für Herkunft und Änderungsverlauf
  (`DSE:288-291`); zusätzlich Art. 9 Abs. 2 lit. a (`A9:22`, `DSE:1119-1121`).
- **Daten:** Text, Kennung von Autor und letzter Änderung, Zeitpunkte, Änderungsverlauf ohne alten
  Wortlaut, Kennung des CC0-Hinweises (`DSE:225-252`); in Qdrant (`docs/ARCHITECTURE.md:115`).
- **Frist:** keine, solange die Plattform läuft (`DSE:292-296`); vom Autor gelöschte nach 30 Tagen
  endgültig (`LK:157`); bei Kontolöschung anonymisiert statt gelöscht (`LK:121-131`).
- **Risiko:** Angemeldete können Beiträge über den Anzeigenamen einer Person zusammenführen
  (`DSE:266-267`), auch Nicht-Mitglieder aus Einladungen. Beiträge nennen oft Dritte, auch deren
  Namen und Profile (`DSE:279-283`); diese Dritten werden nicht informiert (Art. 14, **offen**).
  CC0-Texte bleiben nach der Anonymisierung weiterverwendbar (`DSE:1183-1185`).
- **Maßnahmen:** Kennung nur für Admins und den eigenen Browser (`DSE:267-270`); Anonymisierung mit
  Platzhalter (`LK:121-131`); Einzelfall-Löschung, wenn der Text die Person erkennbar macht
  (`DSE:307-308`); Gegenlesen speichert nichts (`DSE:326-328`).
- **„Gepostet von“ am Post (#622, Stand 09.11.2026 noch nicht gemergt):**
  - *Zweck:* zeigen, woher ein Post stammt.
  - *Daten:* Kontoname des ursprünglichen Posters auf der anderen Plattform („@konto“), Freitext
    im Qdrant-Payload (`ss/domain/models/post.py:26,49-50` auf #622); ist es das Konto einer Person, sind es Daten
    Dritter, oft mit politischer Zuordnung.
  - *Rechtsgrundlage (Vorschlag, nicht juristisch geprüft, #296):* Art. 6 Abs. 1 lit. f;
    berechtigtes Interesse an der Herkunft, abgewogen gegen die Person, die ihr Konto
    öffentlich gepostet hat. Für eine Person, die nicht öffentlich auftritt, trägt die Abwägung
    nicht; Art. 9 Abs. 2 lit. e greift nur, wenn sie ihre Haltung selbst öffentlich gemacht hat. Die
    Erklärung nennt lit. f ohne diesen Vorbehalt; danach in #296 ausdrücklich fragen.
  - *Wer es sieht:* alle, auch Besucher (`PostResponse.author`, `ss/dtos/beitrag.py:96-98` auf #622).
  - *Frist:* wie der Post (keine, solange die Plattform läuft); nicht anonymisiert, wenn das
    Konto der einstellenden Person gelöscht wird.
  - *Minimierung:* Feld freiwillig, leer wird `null` gesendet (#622); Melden und
    Einzelfall-Löschung wie oben (Entscheidung Maintainer 09.11.2026: keine Bitte, nur bestimmte
    Konten einzutragen). Art. 14 (Information der Person) bleibt wie bei R3 **offen**.

#### V4 Einwürfe und Sätze im Fangkorb

- **Zweck:** Rohmaterial sammeln, aus dem Beiträge werden (`DSE:840`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. b, lit. f für die Herkunft (`DSE:841-843`); Art. 9 Abs. 2
  lit. a (`A9:22-23`).
- **Daten:** Hinweis, Link, Zeitpunkt, Weg, Kennung der einwerfenden Person und der Personen mit
  Sätzen (`DSE:814-822`).
- **Frist:** 365 Tage nach der letzten Arbeit, ausformulierte solange der Beitrag (`LK:155-156`).
- **Risiko:** Alle Mitwirkenden sehen, wer was eingeworfen hat (`DSE:825-831`). Links zeigen oft auf
  Profile Dritter (`DSE:835-837`).
- **Maßnahmen:** nur angemeldet erreichbar (`DSE:828`); Kennungen nur für Admins (`DSE:831-832`);
  bei Kontolöschung Platzhalter je Satz (`LK:108-120`).

#### V5 Bewertungen (Stimmen), Güte und Siegel

- **Zweck:** Beiträge nach Brauchbarkeit sortieren (`DSE:668`) und ihre Güte im Siegel zeigen
  (#427, `DSE:663-665`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. b (`DSE:669`); Art. 9 Abs. 2 lit. a (`A9:22-23`).
- **Daten:** Kennung, Beitrag, Richtung, Zeitpunkt (`ss/repositories/vote_repository.py:41-47`).
  Die Güte und die Zähler werden bei jedem Abruf aus diesen Zeilen und dem Gegenlesen berechnet
  und nicht gespeichert (`ss/services/guete_service.py`, `ss/domain/guete.py`); das Ergebnis des
  Gegenlesens liegt nur im Arbeitsspeicher.
- **Empfänger:** alle, die einen Beitrag sehen, auch Besucher: Güte, Siegel und, ab der
  Mindestzahl, die Summen „hilfreich“/„nicht hilfreich“. Einzelstimmen und Kennungen sehen nur
  Admins in der Datenbank, nicht über die Oberfläche.
- **Frist:** solange der Beitrag besteht, oder bis zur Rücknahme bzw. Kontolöschung (`LK:160`,
  `DSE:670-673`).
- **Risiko:** Eine Stimme zu einem politischen Text ist eine Meinungsäußerung. Bei kleinen Zählern
  oder aus einer Änderung der Güte ließe sich eine einzelne Stimme erraten, besonders wer die
  Seite vor und nach einer Stimme vergleicht (R8).
- **Maßnahmen (M5, Entscheidung des Maintainers vom 09.11.2026 in #427):** Gezählt werden nur
  Stimmen anderer, ohne Startkonten und ohne die Stimme der schreibenden Person. Erst ab drei
  verschiedenen Stimmenden (`SEMANTIC_SEARCH_GUETE_STIMMEN_AB`, Standard 3) gehen Stimmen in die
  Güte ein und liefert die Schnittstelle die Summen; darunter enthält die Antwort keine Zahl, nicht
  einmal 0, durchgesetzt im Dienst und nicht erst in der Oberfläche. Das Gewicht der Stimmen in der
  Güte ist gedeckelt (`SEMANTIC_SEARCH_GUETE_STIMMEN_GEWICHT_MAX`), damit sich eine Güte nicht
  allein durch Absprachen bewegen lässt. Die Erklärung am Siegel nennt nur erfüllte Kriterien,
  keine Anmerkungen des Gegenlesens.
- **Restrisiko:** Ab der Schwelle kann, wer eine Seite unmittelbar vor und nach einer Stimme
  sieht, die Richtung dieser einen Stimme ablesen; die Person dahinter bleibt verborgen. Gering.

#### V6 Suchanfragen als Aussage

- **Zweck:** Bestand aufbauen; was gesucht wird, zeigt, welche Antworten fehlen (`DSE:364-367`,
  `DSE:387`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f (`DSE:388`).
- **Daten:** der Suchtext als Aussage mit dem Systemautor `system:suchanfrage`, ohne Kennung
  (`ss/services/search/search_query_statement.py:4,58-63`, `ss/domain/models/content_origin.py:29`).
- **Frist:** keine (`DSE:389`).
- **Risiko:** Suchtexte können Namen, Orte oder Angaben über die suchende Person oder Dritte
  enthalten und werden sichtbar, sobald jemand antwortet oder zwei Personen ohne Treffer danach
  suchten (`DSE:370-374`). Über den Anlagezeitpunkt ließe sich eine Aussage einem Suchereignis
  zuordnen; dagegen trägt das Suchereignis nur den Tag (`LK:322-325`). Zur Zuordnung über das
  Tagespseudonym siehe V7.
- **Maßnahmen:** kein Autor, kein Pseudonym an der Aussage (`DSE:377-379`); Warnhinweis
  (`DSE:382-384`); Rate-Limit ohne Speicherung der Adresse (`DSE:398-403`); keine Suchtexte in
  Protokollen ab INFO (`LK:427-433`).

#### V7 Suchereignisse

- **Zweck:** Personen pro Tag zählen, die suchen (`DSE:448-449`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f (`DSE:450-452`). Für Besucher **offen** mit § 25 TDDDG
  (#495, `docs/FRAGEN_DATENSCHUTZBEAUFTRAGTE.md:18-36`).
- **Daten:** Tag, Trefferzahl, Tagespseudonym; kein Suchtext, keine Kennung
  (`ss/infrastructure/database/models.py:226-264`).
- **Frist:** Einzelzeilen 90 Tage, danach nur Tageszähler ohne Pseudonym (`ss/core/config.py:290`,
  `LK:354-367`).
- **Risiko:** Bei Besuchern liegt der Tagesschlüssel nur im Speicher
  (`ss/utils/besucher_pseudonym.py:15-22`). **Bei Angemeldeten nicht:** Ihr Pseudonym ist ein HMAC
  über Kennung und Datum mit dem Schlüssel `SEMANTIC_SEARCH_ACTOR_HASH_SECRET` aus der Konfiguration
  (`ss/services/search_tracking_service.py:51-62,82-87`, `ss/core/config.py:263-268`); nur wenn er
  nicht gesetzt ist, gilt ein Zufallsschlüssel je Prozess. Ob er in Produktion gesetzt ist, steht
  nicht im Repo (**offen**); die Konfiguration empfiehlt es (`ss/core/config.py:264-265`). Ist er
  gesetzt, kann, wer Datenbank und Konfiguration hat, für eine bekannte Kennung 90 Tage lang
  ausrechnen, an welchen Tagen sie wie oft gesucht hat und wie oft ohne Treffer (`LK:316-317` nennt
  das „tageweise nachrechenbar“). An einem ruhigen Tag mit einer neuen Aussage aus einer Suche ohne
  Treffer könnte das auf den Suchtext dieser Person führen. Die Datenschutzerklärung sagt nur, dass
  die Kennung „nicht zurückrechenbar“ sei (`DSE:427-428`), nicht, dass sie nachrechenbar ist.
- **Maßnahmen:** nur der Tag, keine Uhrzeit (`LK:322-325`); zufällige ID und Mischen abgeschlossener
  Tage (`LK:331-345`). Vorschlag: Schlüssel der Angemeldeten wie bei Besuchern nur im Speicher
  (Abschnitt 9, Punkt 3).

#### V8 Suchen ohne Treffer

- **Zweck:** erkennen, wo Antworten fehlen (`DSE:513-514`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f (`DSE:515-516`).
- **Daten:** je Aussage und Woche Zahl der Suchen und Personen, kein Pseudonym (`LK:368-374`).
- **Frist:** acht Wochen (`DSE:517-518`).
- **Risiko:** gering; der Zähler „n Personen“ ist für alle Angemeldeten sichtbar (`DSE:497-500`).
- **Maßnahmen:** Merkliste nur im Speicher bis Mitternacht (`DSE:469-476`); erst ab zwei Personen
  auf der Liste (`DSE:490-491`).

#### V9 Nutzung (Kopieren, Teilen)

- **Zweck:** erkennen, welche Beiträge gebraucht werden (`DSE:562`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f (`DSE:563`).
- **Daten:** `usage_events` mit Beitrag, Art, Zeitpunkt, Geräteklasse, Fassung und dem Vermerk der
  ersten Kopie des Tages, ohne Kennung (`ss/infrastructure/database/models.py:107-153`); ältere
  Zeilen noch mit Sitzungskennung (`ss/infrastructure/database/models.py:139-142`). Prüfwert für die
  entdoppelte Nutzung in `nutzung_heute` (`ss/infrastructure/database/models.py:165-181`).
- **Frist:** Einzelzeilen 90 Tage, danach nur Zähler je Beitrag (`ss/core/config.py:282`,
  `DSE:564-568`); Prüfwert bis Tagesende (`LK:161`).
- **Risiko:** gering. Der Vermerk „erste Kopie“ zeigt, dass mehrere Kopien am selben Tag von
  derselben Person kamen, nicht von wem (`DSE:537-541`). Besucher haben nicht eingewilligt, ihre
  Kopie bildet trotzdem einen Prüfwert aus dem Besuchermerkmal (`DSE:544-547`).
- **Maßnahmen:** Schlüssel des Prüfwerts nur im Speicher, täglich neu
  (`ss/services/entdoppelung.py:10-20`); angemeldete Konten ohne Einwilligung bekommen keinen
  Prüfwert (`A9:28-36`); Startkonten gar nicht gezählt (`DSE:558-559`).

#### V10 Rückmeldung zur Nutzung

- **Zweck:** Mitwirkenden zeigen, dass ihre Beiträge helfen (`DSE:589`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f (`DSE:590-592`).
- **Daten:** je Kennung eine Zahl, kein Zeitpunkt (`ss/infrastructure/database/models.py:678-696`).
- **Frist:** bis zur Kontolöschung (`DSE:593`).
- **Risiko:** gering. **Offen:** Die Rückmeldung läuft unter lit. f, obwohl sie an der Mitwirkung
  hängt, die sonst unter Art. 9 Abs. 2 lit. a steht.
- **Maßnahmen:** wer genutzt hat, steht nirgends (`DSE:583-584`).

#### V11 Punkte und Muster-Hinweise (gebaut, ausgeschaltet)

- **Zweck:** Wirkung der Mitwirkung zeigen, Punkte gegen Absprachen schützen (`DSE:637-638`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. a und Art. 9 Abs. 2 lit. a (`DSE:639-644`).
- **Daten:** Punktestand nicht gespeichert, bei jedem Abruf berechnet
  (`ss/services/punkte_service.py:1-7`); Paar-Prüfwerte und Muster-Hinweise mit zwei Kennungen
  (`ss/infrastructure/database/models.py:184-223`).
- **Frist:** Paar-Prüfwert 7 Tage, Muster-Hinweis 56 Tage (`LK:162-163`).
- **Risiko und Maßnahmen:** Abschnitt 3 (Sichtbarkeit, Nutzungsnetz, Zweckentfremdung),
  Rechtsgrundlage Abschnitt 4. Schalter `punkte_aktiv`, Standard aus (`ss/core/config.py:238-244`).
- **Meilensteine, nur für die Person selbst (#615, Stand 09.11.2026 noch nicht gemergt):** hinter
  demselben Schalter (ohne `punkte_aktiv` 404, `ss/api/v1/usage.py:450-451` auf #615), gleiche Rechtsgrundlage, nicht gespeichert, bei jedem Abruf berechnet
  (`ss/services/meilensteine_service.py`). Neu gegenüber den Punkten: gezählt wird auch, wie viele
  Einwürfe anderer die Person ausformuliert hat (Ausformulierer an der Verknüpfung,
  `ss/infrastructure/database/models.py:577`, V4), nicht nur
  ihre eigenen Einwürfe, die andere ausformuliert haben. Die Daten liegen schon in V4; neu ist nur
  die Zählung je Person, und die sieht nur sie selbst. Die Erklärung nennt das unter „Punkte“.

#### V12 Meldungen

- **Zweck:** gemeldete Inhalte prüfen, Pflichten nach DSA (`DSE:723-725`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. c mit Art. 16 DSA, lit. f für Rate-Limit und
  Tagespseudonym (`DSE:726-730`). Melden geht ohne Art.-9-Einwilligung (`A9:23-24`).
- **Daten:** Beitrag, Grund, Freitext, Erklärung guten Glaubens, freiwillig Name und E-Mail-Adresse,
  Kennung oder Tagespseudonym, Bearbeitungsvermerk (`ss/infrastructure/database/models.py:400-437`,
  `DSE:687-698`).
- **Frist:** 180 Tage nach Bearbeitung; offene ohne Frist; Tagespseudonym bis zum Abschluss
  (`LK:152-154`, `LK:166-187`).
- **Risiko:** Name und E-Mail-Adresse bei Admins; ein Freitext kann Meinung oder Daten Dritter
  tragen (`DSE:708-709`). **Offen:** Ob eine Meldung einer angemeldeten Person Art. 9 berührt und
  dann ohne Einwilligung auf lit. c allein gestützt werden kann.
- **Maßnahmen:** nur Admins (`DSE:720`); Auskunft und Löschung über „Nach Person“ (`LK:168-184`);
  Rate-Limit ohne gespeicherte Adresse (`DSE:712-717`).

#### V13 Sperren und Widerspruch

- **Zweck:** Entscheidung mitteilen, Widerspruch prüfen (`DSE:763-764`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. c mit Art. 17 und 20 DSA (`DSE:765-766`).
- **Daten:** Sperrgrund, Begründung, Kennung des Autors und der Admins, Widerspruch, Prüfergebnis
  (`ss/infrastructure/database/models.py:440-474`).
- **Frist:** solange gesperrt, danach 180 Tage (`LK:158-159`).
- **Risiko:** gering; nur Admins und die betroffene Person sehen es (`DSE:759-760`).
- **Maßnahmen:** bei Kontolöschung Kennung und Widerspruch auf `NULL` (`LK:96-97`).

#### V14 Feedback

- **Zweck, Rechtsgrundlage:** Plattform verbessern, antworten; Art. 6 Abs. 1 lit. f (`DSE:799-802`).
- **Daten:** Text, freiwillige Kontaktangabe, Tag; keine Kennung (`LK:239-243`).
- **Frist:** 180 Tage (`LK:245-248`).
- **Risiko:** gering; Freitext ungefiltert (`DSE:789-790`).

#### V15 Einladungen

- **Zweck, Rechtsgrundlage:** Konto auf Anfrage einrichten (lit. b), Missbrauch abwehren (lit. f)
  (`DSE:183-188`).
- **Daten:** an der Einladung nur Zähler und Notiz, keine Adresse und keine Kennung (`LK:266-271`);
  E-Mail-Adresse und Passwort-Hash im Realm (`DSE:154-157`).
- **Frist:** Einladung keine (ohne Personenbezug); nie benutzte Konten etwa 33 Tage (`LK:164`).
- **Risiko:** Bei einem persönlichen Link lässt sich die Kontoanlage über Zeitpunkte zuordnen
  (`DSE:162-165`, `LK:278-281`); eine Einladung für eine Gruppe verriete sonst die Zugehörigkeit.
- **Maßnahmen:** keine Zuordnung von Einladung und Konto (ADR 0006:9); Notiz ohne Namen
  (`LK:273-275`).

#### V16 Protokolle

- **Zweck, Rechtsgrundlage:** Betrieb, Fehlersuche, Abwehr; Art. 6 Abs. 1 lit. f (`DSE:870-871`).
- **Daten:** vorgelagerter Webserver mit voller IP (`DSE:863-867`); Anwendung ohne Suchtext und mit
  gekürzter Kennung (`DSE:896-899`, `LK:398-406`).
- **Frist:** vorgelagerter Webserver 14 Tage (`DSE:872-873`); Anwendung und Frontend-nginx **keine**
  (`DSE:889-891`, `DSE:910-911`). Ziel 14 Tage, laut Löschkonzept noch nicht ausgerollt (`LK:511-519`,
  Stand 30.10.2026; ob es inzwischen am Host steht, ist nicht im Repo belegt; #485, #336).
- **Risiko:** Altbestand vor #275 und #284 trägt Suchtexte und Kennungen im Klartext (`DSE:902-905`,
  `LK:491-498`). Der vorgelagerte Webserver protokolliert je Suche eine Zeile mit IP und Uhrzeit,
  die sich mit der Aussage aus der Suche verbinden lässt (`LK:502-507`, **offen**). Das
  Log-Pseudonym ist ungesalzen und bei bekannten Kennungen zurückrechenbar (`LK:402-404`).
- **Maßnahmen:** keine Suchtexte, Pfade und Fehlertexte im Log (`LK:427-464`); Referrer nur Ursprung
  (`LK:499-502`).

#### V17 Sicherungskopien

- **Daten, Frist:** Datenbanken; 7 Tages- und 4 Wochenstände (`mvp/scripts/backup/backup.sh:28-29`),
  Gelöschtes bis zu 28 Tage (`DSE:1031-1034`).
- **Maßnahmen:** nach jeder Wiederherstellung den Löschlauf wiederholen (`DSE:1037-1039`).
  **Offen:** ob die Sicherungen verschlüsselt sind; das steht nicht im Repo.

#### V18 Flüchtige Zähler gegen Missbrauch

Rate-Limits für Suche, Meldungen, Feedback, Einladungen und Gegenlesen verarbeiten die IP-Adresse
oder Kennung nur gekürzt im Arbeitsspeicher, höchstens etwa 16 Minuten, mit Schlüssel je Neustart
(`DSE:175-180`, `DSE:344-348`, `DSE:398-403`, `DSE:712-717`, `DSE:793-796`). Risiko gering.

#### V19 Zugang von Hand (Beta-Zugang)

- **Zweck, Rechtsgrundlage:** Anmeldung für einzelne Personen ohne Netzbegrünung-Konto, ohne den
  Identitätsdienst; Art. 6 Abs. 1 lit. b (`DSE:198-209`).
- **Daten:** E-Mail-Adresse, Anzeigename, Kennung und Prüfsumme des Passworts in einer
  Konfigurationsdatei auf dem Server (`DSE:201-205`, `LK:20`, `LK:55-56`); für Fehlversuche ein
  Zähler im Speicher, 15 Minuten (`DSE:215-217`).
- **Frist:** bis zur Entfernung von Hand, keine automatische Löschung (`DSE:210-212`); der Weg steht
  im Löschkonzept (`LK:55-56`, `LK:133`).
- **Risiko:** Wer die Konfigurationsdatei lesen kann, sieht Adressen und Passwort-Prüfsummen. Wer
  Zugriff darauf hat, steht nicht im Repo (**offen**, R4).
- **Maßnahmen:** Passwort nur als Prüfsumme (`DSE:203-204`); Sperre nach Fehlversuchen
  (`DSE:215-217`).

#### V20 Gegenlesen, Sprachhinweis, Kürzungsvorschlag

- **Zweck, Rechtsgrundlage:** dem Schreibenden Anmerkungen, Sprachhinweis und Kürzungsvorschlag zeigen;
  Art. 6 Abs. 1 lit. b (`DSE:320-361`).
- **Daten:** Titel, Text und die Aussage, auf die geantwortet wird, gehen an den eigenen Server, ohne
  KI und ohne externen Dienst; gespeichert wird nichts, nur ein flüchtiger Zähler gegen Überlastung
  (`DSE:320-361`).
- **Frist:** keine Speicherung; der Zähler höchstens etwa elf Minuten (`DSE:320-361`).
- **Risiko:** gering. Die Entwürfe können politische Haltung enthalten, werden aber nicht abgelegt.
  Die Funktionen sind auch ohne Art.-9-Einwilligung offen (`A9:17-27`).
- **Maßnahmen:** keine Speicherung (`DSE:320-361`).

#### V21 Speicherung auf dem Gerät

- **Zweck, Rechtsgrundlage:** Anmeldung und Bedienkomfort; § 25 TDDDG (`DSE:924-993`).
- **Daten im Browser:** Anmelde-Cookie (V1) und zwei kurzlebige Cookies im Anmeldevorgang;
  nur bis zum Tabschluss Rücksprungseite, Filter im Fangkorb und ein geteilter Link; dauerhaft die
  Wahl des Profilbilds und zwei Vermerke „schon gesehen“; ein Service Worker, der nichts speichert
  (`DSE:924-993`).
- **Frist:** Cookie 14 Tage nach letzter Nutzung, sonst bis der Browser die Websitedaten löscht.
- **Risiko:** gering. Keine Kennung zum Wiedererkennen; die alte Sitzungskennung wird beim nächsten
  Aufruf entfernt (`DSE:951-958`). Ob § 25 Abs. 2 TDDDG die Ausnahme für alle Einträge trägt, ist
  nicht geprüft (**offen**, Frage an die Datenschutzbeauftragte).

#### Geplant, nicht gebaut

Ranglisten, Quests, Level, Meilenstein-Abzeichen am Anzeigenamen, Krone und Wochenthema (`docs/VISION.md:99-103`,
#351, #564). Sie machen sichtbar, wer wie aktiv ist, und brauchen ein eigenes Opt-in
(`docs/VISION.md:101`, Abschnitt 3 Risiko 1). Abschnitt 1 bis 7 prüft sie als Plan; vor dem Bau ist
die Prüfung zu wiederholen; `docs/VISION.md:134` legt die DSFA vor die Ranglisten, Abschnitt 2
empfiehlt sie schon vor dem Einschalten der Punkte.

### 8.3 Risiken über alle Verarbeitungen (Art. 35 Abs. 7 lit. c, d)

| # | Risiko | Maßnahmen | Rest |
|---|---|---|---|
| R1 | **Politische Haltung wird sichtbar**: Anzeigename an Beiträgen, Einwürfen und Sätzen für alle Angemeldeten, darunter Nicht-Mitglieder (V1, V3, V4) | nur Angemeldete, nur Vorname und Initial, Kennung nur für Admins; Einwilligung vor dem Beitragen (V2) | gering |
| R2 | **Zuordnung pseudonymer Daten**: Tagespseudonym der Angemeldeten nachrechenbar, falls der Schlüssel gesetzt ist (V7), Uhrzeiten im vorgelagerten Webserver (V16) | Tag statt Uhrzeit, Mischen, Schlüssel der Besucher nur im Speicher; für Angemeldete **offen** | mittel, bis V7 umgestellt ist |
| R3 | **Daten Dritter** in Beiträgen, Einwürfen und Suchtexten, auch deren politische Zuordnung (V3, V4, V6), darunter „Gepostet von“ am Post | Hinweise im Formular und in der Erklärung; „Gepostet von“ freiwillig; Melden; Einzelfall-Löschung | mittel, hinnehmbar |
| R4 | **Datenpanne oder Zugriff durch Admins**: Kennungen, Meldungen mit Name und E-Mail-Adresse, Muster-Hinweise | Fristen (`LK:150-164`), Kennungen nur gekürzt im Log, keine Weitergabe (`DSE:74-75`); Rollen und Zugriffskonzept stehen nicht im Repo (**offen**) | gering bis mittel |
| R5 | **Unbefristete Protokolle** mit Altbestand aus Suchtexten und Kennungen (V16) | Ziel 14 Tage (`LK:511-519`), nicht ausgerollt | mittel, bis ausgerollt |
| R6 | **Löschung von Hand, nie an echten Daten erprobt** (`LK:3-13`, `DSE:1161-1163`) | Skript getestet gegen Testdaten (`LK:531-532`); Backup und Protokoll beim ersten Lauf | gering bis mittel |
| R7 | **Scoring und Zweckentfremdung** durch Punkte (V11) | Abschnitt 3 | gering bis mittel |
| R8 | **Rückschluss auf einzelne Stimmen** über kleine Zähler oder die Güte (V5) | M5: Summen und Stimmenanteil der Güte erst ab drei verschiedenen Stimmenden, darunter keine Zahl in der Antwort; ohne Startkonten und eigene Stimme; Gewicht der Stimmen gedeckelt (#427) | gering |

## 9. Offene Entscheidungen für den Maintainer

1. **Umfang:** diese DSFA für die ganze Plattform führen (Abschnitt 1 bis 9), statt den Grundbetrieb
   begründet herauszunehmen? Empfehlung: ja.
2. **Lücke vor der Einwilligung** (Abschnitt 4): Anzeigename erst nach der Einwilligung speichern
   (Weg 2)? Empfehlung: ja, als eigenes Ticket.
3. **Tagespseudonym der Angemeldeten** (V7): Schlüssel nur im Speicher wie bei Besuchern? Preis:
   Nach einem Neustart zählt eine Person am selben Tag doppelt. Empfehlung: ja.
4. **Frist für Protokolle** (V16): 14 Tage für Anwendung und Frontend-nginx am Host ausrollen
   (`LK:511-519`, Stand 30.10.2026; Tickets #485 und #336) und den Altbestand mit Suchtexten und
   Kennungen löschen. Das ist Betrieb am Host, nicht Code.
5. **Formales:** Wer übernimmt die DSFA (Vorstand mit Datenschutzbeauftragter, Art. 35 Abs. 2), und
   wo steht das Verzeichnis der Verarbeitungstätigkeiten? Im Repo gibt es keins.
6. **Fragen an die Datenschutzbeauftragte:** Lücke aus Abschnitt 4, Meldungen ohne Einwilligung
   (V12) und Altersgrenze (WP 248 Kriterium 7) zu `docs/FRAGEN_DATENSCHUTZBEAUFTRAGTE.md` hinzufügen
   (vorbereitet als Abschnitt 6, Frage 5)? Empfehlung: ja, gebündelt mit Frage 1 dort.
