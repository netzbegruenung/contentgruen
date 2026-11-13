# Datenschutz-Folgenabschätzung

> **Entwurf, nicht juristisch geprüft, nicht beschlossen.** Keine Rechtsberatung. Entscheiden
> müssen der Vorstand der Netzbegrünung als Verantwortlicher und die Datenschutzbeauftragte, am
> besten in derselben Runde wie #296; die Fragen an sie stehen in Abschnitt 6. Bis dahin bleiben
> die Punkte aus (`SEMANTIC_SEARCH_PUNKTE_AKTIV`, Standard aus). Aussagen ohne Beleg im Repo
> stehen als **offen** da.

Abschnitte 1 bis 7 prüfen Punkte, Quests und Ranglisten, Abschnitte 8 und 9 alle übrigen
Verarbeitungen des Dienstes (#374). Das Verzeichnis der Verarbeitungstätigkeiten (Art. 30)
steht in [`docs/VERARBEITUNGSVERZEICHNIS.md`](./VERARBEITUNGSVERZEICHNIS.md) und verweist je
Tätigkeit hierher.

**Stand 13.11.2026:** Code `main` @ `5816e358`, Tag `v0.8.4` (Release-PR #656);
eingearbeitet sind #622, #643, #651 und #655 (Tagespseudonym
ohne User-Agent, Suchereignisse am Tagesende zu Tageszählern verdichtet). Neu an diesem Stand:
Risikomethode nach DSK-Kurzpapier Nr. 18 (8.4), Verhältnismäßigkeit des Grundbetriebs (8.5),
Widerruf der Art.-9-Einwilligung (V2, R9) und die Liste der offenen Fakten (8.6).
Fundstellen mit Zeilennummer zeigen auf den Stand, an dem sie geprüft wurden: in Abschnitt 1
bis 7 auf `cdb7ec64` mit #476 (Datenschutzerklärung nach #499), in V6, V7 und V9 auf
`c4a95e9c` (nach #655, nachgezogen mit #656), sonst in Abschnitt 8 und 9 auf `c2c9bbe5`, auch
die Zeilen `LK:` laut `c2c9bbe5` (`git show c2c9bbe5:docs/LOESCHKONZEPT.md`).
Was danach dazukam, steht ohne Zeile mit seinem Ticket. Nachgetragen: der Löschauftrag beim
Widerruf (R9b als Löschauftrag, #661; V2, R9, 8.4).
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
- **Gebaut (#351), hinter demselben Schalter:** Meilensteine, die die Person selbst in
  „Meine Beiträge“ sieht, bei jedem Abruf aus denselben Zählern berechnet und nicht gespeichert,
  ohne Startkonten und nur mit Art.-9-Einwilligung (`ss/services/meilensteine_service.py`).
  Dazu, hinter einem zweiten Schalter (`abzeichen_sichtbar_aktiv`, Standard aus), das
  Abzeichen am Anzeigenamen für andere Angemeldete mit eigener Zustimmung; geprüft in
  Abschnitt 8.2, V22.
- **Geplant, nicht gebaut:** Ranglisten (die ersten 10 und der eigene Platz, nur für Angemeldete,
  nur mit Zustimmung), Quests, Krone, Wochenthema
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
| **1. Politische Aktivität wird sichtbar.** Rangliste, Abzeichen, Krone und Wochenthema zeigen anderen, wer wie aktiv ist. Unter den Angemeldeten sind auch Nicht-Mitglieder (Beta-Zugänge, Einladungen; `GLOSSARY.md:489-490`), und Screenshots können nach außen gehen. | **Ein eigenes Opt-in** für alles, was andere an der Person sehen. Zwei gleichwertige Knöpfe, nichts vorbelegt, jederzeit widerrufbar (`docs/VISION.md:101`). Gezeigt wird nur der Anzeigename, nur die ersten 10 und der eigene Platz, nur für Angemeldete. Vorschlag zusätzlich: keine Linkvorschau für Ranglisten und eine Rangliste erst ab etwa 5 Personen mit Opt-in. Ohne Opt-in sieht nur die Person selbst ihre Punkte. | geringes Risiko (8.4) |
| **2. Ein Netz, wer wessen Beiträge nutzt.** PR #476 speichert kein Protokoll, nur Prüfwerte als HMAC. Mit einem Schlüssel aus der Konfiguration könnte, wer Datenbank und Schlüssel hat, für jedes Kontenpaar 7 Tage lang nachrechnen, wer einen Beitrag von wem genutzt hat (#499). | **Umgesetzt** (PR #476): Entdoppelung über Prüfwerte statt Protokoll, und beide Schlüssel liegen nur im Speicher, nach dem Muster des Tagesschlüssels der Besucher (`ss/utils/besucher_pseudonym.py:45-73`): Prüfwerte mit einem eigenen Tagesschlüssel, Paar-Prüfwerte mit einem Fensterschlüssel, der je 7 Tage wechselt und den vorigen einen Block lang zum Vergleich behält (`ss/services/entdoppelung.py:10-30,54-86` (#476)). Kein Bezug mehr zu `SEMANTIC_SEARCH_ACTOR_HASH_SECRET`. Nach einem Neustart beginnt ein Muster neu, und eine Nutzung zählt am selben Tag ein zweites Mal; das ist hinnehmbar. Muster-Hinweise lösen nichts automatisch aus; ein Admin prüft und hört die Personen an. | geringes Risiko (8.4) |
| **3. Zweckentfremdung und Druck.** Punkte könnten als Maßstab für Ämter, Listen oder Kampagnen dienen oder Masse und Schärfe belohnen. | Zweckbindung in Datenschutzerklärung und Nutzungsbedingungen: keine Weitergabe, keine Auswahl nach Punkten. Kein Geld und keine Sachleistung (`docs/VISION.md:31`). Punkte vor allem für Wirkung, Tagesdeckel, kein Abzug, keine Punkte fürs Bewerten (`docs/adr/0004-punkte-aus-wirkung-bei-anderen.md:9-19`). | Risiko (mittlere Klasse, 8.4); in der Acht-Wochen-Bilanz ansehen |

Eingestuft nach DSK-Kurzpapier Nr. 18 (Methode in 8.4): Mit diesen Maßnahmen bleibt für die
Punkte selbst höchstens die mittlere Klasse „Risiko“ (Risiko 3). Ob die Aufsichtsbehörde
konsultiert werden muss (Art. 36 Abs. 1), entscheidet das Gesamtrisiko der Plattform; das
steht in 8.4 und hängt heute an den offenen Fakten (8.6) und an Frage 7 zum Widerruf (R9).

## 4. Rechtsgrundlage

**Empfehlung: ausdrückliche Einwilligung, Art. 9 Abs. 2 lit. a, in zwei Stufen.**

1. **Beim ersten Login** fragt die App seit #489 nach der Art.-9-Einwilligung (Lückenliste
   D-N15, `docs/ART9_EINWILLIGUNG.md`); die DSE nennt sie seit #557. Ihr Wortlaut muss zusätzlich
   als Zwecke nennen: Punktestand, Level, Quests und Meilenstein-Abzeichen (nur für die Person,
   solange sie nicht gesondert zustimmt, sie anderen Angemeldeten zu zeigen; Opt-in aus Risiko 1),
   neue Aktionen, die ein höheres Level freischaltet, und den Schutz der Punkte durch
   Muster-Hinweise; das tut der Wortlaut `2026-11-05-b` (#559), der den ersten vom selben
   Tag ablöst, bevor er in einem Release war. `2026-11-10` (#644) ändert daran nur den Namen
   des Menüpunkts für den Widerruf („Datenschutz-Einstellungen“), redaktionell, ohne neue Frage. Für die Muster-Hinweise
   reicht Art. 6 Abs. 1 lit. f allein nicht, weil sie Art. 9-Daten betreffen.
2. **Beim ersten Punkt** fragt die App nach dem Opt-in aus Risiko 1, das ist eine eigene
   Einwilligung für die Sichtbarkeit. Für Meilenstein-Abzeichen gebaut (#351): gefragt ab dem
   ersten erreichten Meilenstein, `GLOSSARY.md` „Zustimmung zur Sichtbarkeit“, V22.

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
Prüfwert und ohne Meldung für Muster-Hinweise (#559). Mit #658 (Wortlaut `2026-11-12`) werden
beim Widerruf ihre Bewertungen gelöscht; für Beiträge, Einwürfe und Sätze legt der Widerruf seit
#661 einen Löschauftrag an, den ein Admin binnen sieben Tagen ausführt; bis dahin bleiben sie an
ihrem Konto (#489, `docs/ART9_EINWILLIGUNG.md`). Bewertung und Maßnahmen in V2 und R9. Geht das Konto, gehen die
Muster-Hinweise mit, die Paar-Prüfwerte laufen nach 7 Tagen aus. Notwendigkeit und
Verhältnismäßigkeit des Grundbetriebs ohne Punkte: 8.5.

## 6. Fragen an Vorstand und Datenschutzbeauftragte

1. Ist eine DSFA nach Art. 35 Abs. 1 nötig, und genügt dieser Umfang (Abschnitt 2)? Tragen die
   Methode und die Einstufung in 8.4?
2. Trägt Art. 9 Abs. 2 lit. a in zwei Stufen, auch für die Muster-Hinweise (Abschnitt 4)?
3. Trägt Art. 6 Abs. 1 lit. f den Prüfwert und das Tagespseudonym der Besucher, und ist das
   Auswerten der Adresse ohne User-Agent schon ein Zugriff nach § 25 Abs. 1 TDDDG (Abschnitt 4, V7,
   #495)?
4. Erledigt: Der Schlüssel der Prüfwerte liegt nur im Speicher (Risiko 2, PR #476).
5. Ist eine DSFA auch für den Grundbetrieb ohne Punkte zu führen, und genügt Abschnitt 8 dafür?
   Wie wird die Lücke vor der Einwilligung geschlossen (Abschnitt 4), trägt Art. 6 Abs. 1 lit. c
   Meldungen angemeldeter Personen ohne Einwilligung (V12), und gibt es eine Altersgrenze für
   Konten (WP 248 Kriterium 7)?
6. Trägt die gesonderte Einwilligung das Meilenstein-Abzeichen am Anzeigenamen, und genügt die
   Zahl der erreichten Meilensteine als einzige Angabe (8.2, V22, #351)?
7. Widerruf der Art.-9-Einwilligung (V2, R9): Ist ohne Antrag zu löschen oder zu anonymisieren,
   oder erst auf Antrag? Genügt die Anonymisierung wie bei der Kontolöschung? Muss der Wortlaut
   den Verein als Verantwortlichen nennen statt „Gut gesagt“? #658 löscht beim Widerruf die
   Stimmen, #661 legt für Beiträge, Einwürfe und Sätze einen Löschauftrag an, den ein Admin binnen
   sieben Tagen ausführt (R9b): Genügen Frist und Ausführung von Hand, oder ist ohne den
   vollautomatischen Ablauf vor dem Start die Aufsichtsbehörde zu konsultieren (Art. 36, 8.4)?

## 7. Vor dem Einschalten der Punkte

Offen:

- DSFA übernommen (Abschnitt 6).
- Für die Abzeichen am Anzeigenamen zusätzlich (zweiter Schalter `abzeichen_sichtbar_aktiv`):
  Frage 6 beantwortet, Wortlaut der Frage nach der Sichtbarkeit und Absatz der
  Datenschutzerklärung freigegeben (8.2, V22).

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
Plattform (8.1). Vier Lücken sind offen: Konto und Anzeigename entstehen vor der Einwilligung (V1);
nach einem Widerruf der Einwilligung bleiben Beiträge, Einwürfe und Sätze an der Person, bis ein
Admin den Löschauftrag ausführt, höchstens sieben Tage (#658 löscht die Stimmen sofort, #661 legt
den Auftrag an; V2, R9); das
Tagespseudonym angemeldeter Personen ist am laufenden Tag mit dem Schlüssel aus der Konfiguration
nachrechenbar, falls er gesetzt ist (V7); Anwendungsprotokolle haben in Produktion keine Frist
(V16). Nach der Methode in 8.4 liegt R9 mit dem Löschauftrag (#661) in der mittleren Klasse
„Risiko“, ebenso R2, R3, R4, R5 und R6. Ob die Ausführung von Hand binnen sieben Tagen genügt oder
erst der vollautomatische Ablauf, ist eine Frage an die Datenschutzbeauftragte (Frage 7;
Folgerung in 8.4). **Erst wenn die vier Lücken geschlossen
sind**, die Maßnahmen aus 8.2 und 8.3 stehen
und die offenen Fakten (8.6) belegt sind, bleibt außer den Daten Dritter (R3) nur geringes Risiko.

### 8.1 Schwellwert für den Grundbetrieb ohne Punkte

WP 248 rev.01 wie in Abschnitt 2 (Wortlaut für diesen Abschnitt nicht erneut im Original geprüft),
hier für den Grundbetrieb neben dem Stand mit Punkten:

| Kriterium | Grundbetrieb | mit Punkten |
|---|---|---|
| 1 Bewerten, Einstufen | nein | **ja**: Punkte stufen Personen nach ihrem Verhalten ein (`ss/services/punkte_service.py:1-7`) |
| 3 Systematische Überwachung | **offen**: Nutzung ohne Kennung (V9), Suchereignisse mit Tagespseudonym nur am laufenden Tag; das der Angemeldeten ist bis dahin nachrechenbar, falls der Schlüssel gesetzt ist (V7); nein, sobald V7 umgestellt ist | wie links |
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
  Deutschland; sonst keine Empfänger (`DSE:66-75`). **Offen (8.6, F1):** ob es einen
  AV-Vertrag nach Art. 28 Abs. 3 gibt, der Gut gesagt mit Zweck, Datenarten (auch politische
  Meinung, Art. 9) und Kategorien der Betroffenen erfasst, und ob Hetzner als
  Unterauftragsverarbeiterin genehmigt ist oder nur Räume, Strom und Netz stellt
  (#506, `docs/FRAGEN_DATENSCHUTZBEAUFTRAGTE.md:38-45`). Die Datenschutzerklärung sagt, es gebe
  den Vertrag; belegt ist er im Repo nicht. Ohne ihn fehlt die Grundlage für alle Verarbeitungen
  bei verdigado, auch für die Art.-9-Daten.
- Keine Übermittlung außerhalb der EU, kein KI-Anbieter (`DSE:1048-1051`, `CLAUDE.md`, Abschnitt
  „Datenschutz — keine KI-Anbieter“). Ausnahme: Bilder von fremden Servern lädt der Browser erst
  nach Klick (`DSE:996-1022`).
- Mails (Bestätigung einer Meldung, Entscheidung) gehen über einen SMTP-Server aus der Konfiguration
  (`ss/core/config.py:196-198`, auf `c4a95e9c` Zeile 209-214, Standard STARTTLS); welcher das in
  Produktion ist und wer ihn betreibt, steht nicht im Repo (**offen**, 8.6, F2; gehört zur
  AV-Frage). Dasselbe gilt für den Mailversand des Anmeldedienstes (Einladung, Passwort), den die
  Datenschutzerklärung verdigado zuordnet (`DSE:66-75`).
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
- **Widerruf, heute:** Der Widerruf setzt den Zeitpunkt an der Zeile
  (`ss/repositories/art9_einwilligung_repository.py`, `widerrufen`) und nimmt das
  Meilenstein-Abzeichen weg (`ss/api/v1/art9_einwilligung.py`, V22). In derselben Transaktion
  löscht er alle Stimmen der Person (#658, `Art9EinwilligungService.widerrufen`,
  `VoteRepository.loeschen_fuer_person`) und legt einen Löschauftrag an (#661,
  `LoeschauftragRepository.anlegen`): Kennung, Zeitpunkt, Frist sieben Tage, je Person höchstens
  ein offener. Scheitert eins davon, gilt der Widerruf nicht, die API antwortet mit 500, und die
  Person kann erneut widerrufen. Ein Admin führt den Auftrag unter „Moderation“, „Löschaufträge“
  aus (`ss/services/loeschauftrag_service.py`); bis dahin behalten Beiträge, Einwürfe und Sätze
  Kennung und Anzeigenamen (LK „Löschauftrag nach dem Widerruf“). Was die Person nach einer neuen
  Einwilligung beiträgt, bleibt; ohne neue Einwilligung erfasst der Auftrag alles (Entscheidung
  Maintainer, 13.11.2026). Der Wortlaut `2026-11-13`
  (`ss/domain/art9_einwilligung.py`) sagt das: „Innerhalb von sieben Tagen werden auch meine
  Beiträge, Einwürfe und Sätze von mir gelöst: […] Was ich nach einer neuen Einwilligung
  beitrage, bleibt davon unberührt. Mein Konto bleibt.“ Wer einem früheren Wortlaut zugestimmt
  hat, wird neu gefragt, weil die Folgen des Widerrufs weiter gehen (`docs/ART9_EINWILLIGUNG.md`,
  „Wortlaut ändern“). Der Wortlaut nennt als
  Verantwortlichen nur „Gut gesagt“, nicht den Verein (dazu Abschnitt 6, Frage 7).
- **Widerruf, Bewertung (Vorschlag, nicht juristisch geprüft, #296):** Nach Art. 7 Abs. 3 wirkt
  der Widerruf für die Zukunft. Fehlt danach eine andere Rechtsgrundlage, sind die Daten nach
  Art. 17 Abs. 1 lit. b zu löschen, und zwar auch ohne Antrag; still auf eine andere
  Rechtsgrundlage auszuweichen, ist nicht zulässig (EDSA-Leitlinien 05/2020 zur Einwilligung,
  Rn. 117 bis 120; Randnummer am Original prüfen). Als andere Ausnahme nach Art. 9 Abs. 2 käme nur lit. e in Betracht
  („offensichtlich öffentlich gemacht“). Sie setzt voraus, dass die Person ihre Daten bewusst
  einer unbegrenzten Zahl von Personen zugänglich gemacht hat (EuGH C-252/21); der Anzeigename ist
  aber nur für Angemeldete sichtbar, Stimmen sind gar nicht sichtbar. Also trägt „Gespeichertes
  bleibt“ voraussichtlich nicht.
- **Rechtsgrundlage der Beiträge nach dem Widerruf:** Die Datenschutzerklärung stützt Beiträge auf
  Art. 6 Abs. 1 lit. b (Funktion) und lit. f (Herkunft, Änderungsverlauf, Anzeigename)
  (`DSE:299-302`, `DSE:308-310` auf `c4a95e9c`) und für alles, was auf die politische Meinung
  schließen lässt, „zusätzlich“ auf Art. 9 Abs. 2 lit. a (`DSE:1199-1202`); der Wortlaut nennt
  Beiträge, Einwürfe, Sätze und den Anzeigenamen daran ausdrücklich
  (`ss/domain/art9_einwilligung.py:75-77`), ebenso V3 und V4. Lit. e nennen weder Erklärung
  noch DSFA für die eigenen Beiträge, und sie trüge nicht (oben). Art. 6 Abs. 1 lit. b oder f
  heben das Verbot aus Art. 9 Abs. 1 nicht auf. Mit dem Widerruf fällt deshalb für die
  Zuordnung von Beiträgen, Einwürfen und Sätzen zur Person (Kennung, Anzeigename) die
  Art.-9-Grundlage weg; der Text selbst darf als CC0-Beitrag ohne Personenbezug bleiben.
- **Widerruf, Maßnahmen (R9):**
  - **R9a, Stimmen löschen:** gebaut (#658, in `v0.8.5`; Wortlaut `2026-11-12`).
  - **R9b, Mitwirkung anonymisieren:** gebaut als Löschauftrag (#661). Der Widerruf wirkt für
    die Mitwirkung wie die Kontolöschung: Beiträge anonymisieren (`LK` „Ablauf“, Schritt 3), Sätze
    an fremden Einwürfen mit Platzhalter versehen, eigene Einwürfe löschen (Schritt 2); das Konto
    und die Zeile der Einwilligung als Nachweis (Art. 7 Abs. 1) bleiben. Der Widerruf legt den
    Auftrag an, ein Admin führt ihn binnen sieben Tagen mit einem Knopf aus; überfällige stehen
    hervorgehoben (LK „Löschauftrag nach dem Widerruf“). Datenschutzerklärung und Wortlaut
    (`2026-11-13`) sind angepasst; **offen** ist der vollautomatische Ablauf ohne Admin (nach
    dem Freeze).
  - Alternative zu R9b: Löschen erst auf
  Antrag, schwächer, weil die Leitlinien eine Pflicht ohne Antrag sehen; das entscheidet die
  Datenschutzbeauftragte (Abschnitt 6, Frage 7).

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
- **„Gepostet von“ am Post (#622, gemergt am 09.11.2026):**
  - *Zweck:* zeigen, woher ein Post stammt.
  - *Daten:* Kontoname des ursprünglichen Posters auf der anderen Plattform („@konto“), Freitext
    im Qdrant-Payload (`ss/domain/models/post.py:26,49-50`); ist es das Konto einer Person, sind es Daten
    Dritter, oft mit politischer Zuordnung.
  - *Rechtsgrundlage (Vorschlag, nicht juristisch geprüft, #296):* Art. 6 Abs. 1 lit. f;
    berechtigtes Interesse an der Herkunft, abgewogen gegen die Person, die ihr Konto
    öffentlich gepostet hat. Für eine Person, die nicht öffentlich auftritt, trägt die Abwägung
    nicht; Art. 9 Abs. 2 lit. e greift nur, wenn sie ihre Haltung selbst öffentlich gemacht hat. Die
    Erklärung nennt lit. f ohne diesen Vorbehalt; danach in #296 ausdrücklich fragen.
  - *Wer es sieht:* alle, auch Besucher (`PostResponse.author`, `ss/dtos/beitrag.py:111-112`).
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
  `DSE:670-673`). Trifft ein geänderter Titel nach der NLI-Stufe eine andere Behauptung, werden
  die Stimmen zum Beitrag gelöscht (#427, `ss/services/content/beitrag_aendern_service.py`);
  eine Stimme gilt damit nie für eine Aussage, der die Person nicht zugestimmt hat. Ohne
  Entscheidung der Stufe (nicht `an`, kein Modell, keine Antwort) bleiben sie.
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
  zuordnen; dagegen trägt das Suchereignis nur den Tag (`LK:330-332`). Zur Zuordnung über das
  Tagespseudonym siehe V7.
- **Maßnahmen:** kein Autor, kein Pseudonym an der Aussage (`DSE:377-379`); Warnhinweis
  (`DSE:382-384`); Rate-Limit ohne Speicherung der Adresse (`DSE:398-403`); keine Suchtexte in
  Protokollen ab INFO (`LK:427-433`).

#### V7 Suchereignisse

- **Zweck:** Personen pro Tag zählen, die suchen (`DSE:464-465`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f (`DSE:466-468`). Für Besucher **offen** mit § 25 TDDDG
  (#495, `docs/FRAGEN_DATENSCHUTZBEAUFTRAGTE.md:18-36`).
- **§ 25 TDDDG für das Tagespseudonym der Besucher (Vorschlag, nicht juristisch geprüft, #296):**
  Der EDSA legt Art. 5 Abs. 3 der ePrivacy-Richtlinie weit aus: Auch IP-Adressen und Header wie
  der User-Agent können erfasst sein, wenn sie zum Wiedererkennen ausgewertet werden
  (Leitlinien 2/2023, Rn. 42 f. und 55; Randnummer am Original prüfen). Die DSK-Orientierungshilfe Digitale Dienste beschreibt
  Fingerprinting als serverseitige Bildung eines möglichst eindeutigen und langlebigen Werts.
  Das Tagespseudonym ist beides nicht: Es steht für einen Anschluss (IPv6: das /64, der Host-Teil
  geht nicht ein), mehrere Geräte dahinter zählen als einer; der Schlüssel wechselt täglich und
  liegt nur im Speicher, die Zeilen werden am Tagesende verdichtet (#655). Seit #655 geht auch der
  User-Agent nicht mehr ein, also kein Merkmal des Geräts
  (`ss/utils/besucher_pseudonym.py`). Die Geräteklasse an der Nutzung (V9) liest den User-Agent
  weiter, schreibt aber nur eine von vier groben Klassen (`ss/utils/device_category.py`). Ergebnis:
  Lit. f trägt, die Eingriffstiefe ist gering; ob schon das Auswerten der Adresse ein Zugriff im
  Sinne von § 25 Abs. 1 ist, bleibt eine Frage an die Datenschutzbeauftragte (Abschnitt 6,
  Frage 3). Für das Pseudonym an anonymen Meldungen (V12) läge, falls § 25 greift, Abs. 2 Nr. 2
  näher, weil die Meldung von der Person ausgeht. Für Besucher bleibt geringes Risiko; R2 betrifft
  die Angemeldeten.
- **Daten:** Tag, Trefferzahl, Tagespseudonym; kein Suchtext, keine Kennung
  (`ss/infrastructure/database/models.py:258-304`), verdichtet in `suchen_je_tag`
  (`ss/infrastructure/database/models.py:307-326`).
- **Frist:** Einzelzeilen nur bis zum Ende ihres UTC-Tages; kurz nach Mitternacht verdichtet der
  Task der Löschfristen sie zu Tageszählern ohne Pseudonym, ohne Schalter
  (`ss/services/loeschfristen_service.py`, `SearchTrackingRepository.verdichten_vor`, LK „Was nicht
  gelöscht wird“). Vor der Umstellung zu #495 blieben sie 90 Tage.
- **Risiko:** Bei Besuchern liegt der Tagesschlüssel nur im Speicher, und das Besuchermerkmal ist
  nur noch der Anschluss, ohne User-Agent (`ss/utils/besucher_pseudonym.py`); weniger Merkmale des
  Geräts, weniger Nähe zu einem Fingerabdruck (§ 25 TDDDG). **Bei Angemeldeten nicht:** Ihr Pseudonym ist ein HMAC
  über Kennung und Datum mit dem Schlüssel `SEMANTIC_SEARCH_ACTOR_HASH_SECRET` aus der Konfiguration
  (`ss/services/search_tracking_service.py:52-63,77-88`, `ss/core/config.py:300-305`); nur wenn er
  nicht gesetzt ist, gilt ein Zufallsschlüssel je Prozess. Ob er in Produktion gesetzt ist, steht
  nicht im Repo (**offen**); die Konfiguration empfiehlt es (`ss/core/config.py:301-302`). Ist er
  gesetzt, kann, wer Datenbank und Konfiguration hat, für eine bekannte Kennung ausrechnen, ob und
  wie oft sie am laufenden Tag gesucht hat und wie oft ohne Treffer (vor der Umstellung zu #495: 90 Tage lang) (`LK:323` nennt
  das „nur für den laufenden Tag nachrechenbar“). An einem ruhigen Tag mit einer neuen Aussage aus einer Suche ohne
  Treffer könnte das auf den Suchtext dieser Person führen. Die Datenschutzerklärung sagt nur, dass
  sich die Kennung „nicht zurückrechnen“ lasse (`DSE:439-440`), nicht, dass sie nachrechenbar ist.
- **Maßnahmen:** nur der Tag, keine Uhrzeit (`LK:330-332`); zufällige ID; abgeschlossene Tage nur
  noch als Zähler, deshalb auch kein Mischen mehr. Personen pro Tag werden beim Verdichten gezählt,
  die Bilanz bleibt so möglich. Vorschlag: Schlüssel der Angemeldeten wie bei Besuchern nur im Speicher
  (Abschnitt 9, Punkt 3).

#### V8 Suchen ohne Treffer

- **Zweck:** erkennen, wo Antworten fehlen (`DSE:513-514`).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f (`DSE:515-516`).
- **Daten:** je Aussage und Woche Zahl der Suchen und Personen (Summe der Personen je Tag, Besucher
  je Anschluss), kein Pseudonym (`LK:368-374`).
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
- **Frist:** Einzelzeilen 90 Tage, danach nur Zähler je Beitrag (`ss/core/config.py:320`,
  `DSE:585-589`); Prüfwert bis Tagesende (`LK:161`).
- **Risiko:** gering. Der Vermerk „erste Kopie“ zeigt, dass mehrere Kopien am selben Tag von
  derselben Person kamen, nicht von wem (`DSE:537-541`). Besucher haben nicht eingewilligt, ihre
  Kopie bildet trotzdem einen Prüfwert aus dem Besuchermerkmal (`DSE:544-547`).
- **Maßnahmen:** Schlüssel des Prüfwerts nur im Speicher, täglich neu
  (`ss/services/entdoppelung.py:10-20`); angemeldete Konten ohne Einwilligung bekommen keinen
  Prüfwert (`A9:28-36`); Startkonten gar nicht gezählt (`DSE:558-559`).

#### V9a Rückmeldung „Ja, gepostet“ (#643)

- **Stand:** gebaut (#651, gemergt am 10.11.2026); Schalter `gepostet_aktiv`, im Code Standard aus. **Intern an** (Entscheidung
  des Maintainers vom 10.11.2026), **vor dem öffentlichen Start neu prüfen.**
- **Zweck:** messen, wie viele verschiedene Menschen je Woche öffentlich kontern (Nordstern,
  `docs/VISION.md`); der Person danken. Die Person meldet nach dem Kopieren mit einem Klick
  „Ja, gepostet“; das ist eine Selbstauskunft, ein Link zum Post wird nicht abgefragt.
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f für die Zählung, dazu Art. 9 Abs. 2 lit. a über die
  Art.-9-Einwilligung (Wortlaut 2026-11-05-b bzw. redaktionell 2026-11-10). Begründung: Gespeichert wird keine Kennung, nur
  ein Prüfwert, der sich ohne den Wochenschlüssel im Arbeitsspeicher nicht auf die Person
  zurückführen lässt, und nach Wochenende nur die Zahl der Woche; das berechtigte Interesse
  (Wirkung des Angebots messen) überwiegt bei diesem Umfang. Der Klick selbst lässt aber auf
  politische Aktivität schließen, deshalb zählt nur, wer eingewilligt hat. Der Wortlaut nennt
  „meine Mitwirkung … für den Betrieb der Plattform“, nicht ausdrücklich diese Meldung.
  **Offen:** Vor dem öffentlichen Start klären, ob der Wortlaut sie ausdrücklich nennen muss
  (dann ein neuer Wortlaut, `docs/ART9_EINWILLIGUNG.md`).
- **Daten:** je Person und Kalenderwoche (UTC, ab Montag) ein Prüfwert, HMAC über die Kennung mit
  einem Wochenschlüssel nur im Arbeitsspeicher (`ss/services/gepostet_service.py`), mit dem
  Montag der Woche (`gepostet_pruefwerte`); kein Beitrag, kein Zeitpunkt. Nach Wochenende nur die
  Zahl der Personen je Woche (`gepostet_wochen`).
- **Frist:** Prüfwert bis kurz nach Wochenende, verdichtet beim ersten täglichen Lauf danach
  (`docs/LOESCHKONZEPT.md`); die Zahl je Woche ohne Personenbezug unbefristet.
- **Risiko:** gering. Auch mit Datenbank und Konfiguration lässt sich ein Prüfwert nicht
  nachrechnen; die Person sieht nur die Gesamtzahl der Woche, Admins nur die Zahl je Woche.
  Nach einem Neustart zählt eine erneute Meldung derselben Woche doppelt (zu hoch, nie zu
  niedrig).
- **Maßnahmen:** nur angemeldet und mit geltender Art.-9-Einwilligung (sonst 403), keine
  Startkonten, Schalter, keine Weitergabe; der Prüfwert ändert sich jede Woche.

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
- **Meilensteine, nur für die Person selbst (#615, gemergt am 09.11.2026):** hinter
  demselben Schalter (ohne `punkte_aktiv` 404, `ss/api/v1/usage.py:478-479`), gleiche Rechtsgrundlage, nicht gespeichert, bei jedem Abruf berechnet
  (`ss/services/meilensteine_service.py`). Neu gegenüber den Punkten: gezählt wird auch, wie viele
  Einwürfe anderer die Person ausformuliert hat (Ausformulierer an der Verknüpfung,
  `ss/infrastructure/database/models.py:577`, V4), nicht nur
  ihre eigenen Einwürfe, die andere ausformuliert haben. Die Daten liegen schon in V4; neu ist nur
  die Zählung je Person, und die sieht nur sie selbst. Die Erklärung nennt das unter „Punkte“.
- **Wegmarken, Texte und Bilder (#351, gebaut, ausgeschaltet):** vier neue Meilensteine aus gespeicherten Daten,
  die schon unter die Art.-9-Einwilligung fallen: erster Einwurf (eigene, nicht verworfene
  Einwürfe, V4), erster fremder Einwurf ausformuliert (dieselbe Zählung wie oben, Schwelle 1),
  erster Beitrag, der heute sichtbar und mindestens drei Tage alt ist (Alter der sichtbaren
  Beiträge, Regel wie bei den Punkten), erster Kommentar, den eine sichtbare Aussage als Antwort führt (Payload
  `antwort_ids` in Qdrant). Keine neue Speicherung, kein zeitliches Muster, keine Suchen, Kopien,
  Meldungen oder Anmeldetage. Drei davon sind Wegmarken: nur für die Person, nicht in der Zahl am
  Namen und nicht für die Krone (V22 unverändert). Der Hinweis beim Erreichen (nach dem eigenen
  Tun oder beim Anmelden) merkt sich die angezeigten Kennungen nur im Browser (localStorage), je
  Konto unter einem Schlüssel mit einem Prüfwert der Kennung, entfernt beim Abmelden und beim
  Widerruf der Art.-9-Einwilligung; ohne Server-Eintrag, keine Erinnerungen. Das Abzeichen
  rechnet ohne Wegmarken und ohne deren Abfragen. Bis zur juristischen Prüfung nach § 25 TDDDG
  ist der Merker ausgeschaltet (`MEILENSTEIN_MERKER_AKTIV = false` im Frontend): kein Eintrag im
  Browser, keine Hinweise; die Meilensteine stehen nur in „Meine Beiträge“. Ob ein Einwurf der erste ist, liest die Karte nach dem
  Einwurf aus der Zahl der eigenen Einwürfe (`getOwnRawInputs`, vorhanden).
  Die Erklärung nennt die neue Liste unter „Punkte“.

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
  **Offen (8.6, F3):** ob die Sicherungen verschlüsselt sind. Das Skript selbst verschlüsselt
  nicht: Es legt den PostgreSQL-Dump als SQL-Text und den Qdrant-Snapshot im Verzeichnis
  `/opt/gutgesagt-backups` auf demselben Host ab (`mvp/scripts/backup/backup.sh`, auf
  `c4a95e9c`). Ob der Datenträger verschlüsselt ist, ob die Sicherungen den Host verlassen und
  wer sie lesen kann, steht nicht im Repo.

#### V18 Flüchtige Zähler gegen Missbrauch

Rate-Limits für Suche (samt ähnlichen Aussagen unter „Nicht dabei?“, #642), Meldungen, Feedback, Einladungen und Gegenlesen verarbeiten die IP-Adresse
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

#### V22 Meilenstein-Abzeichen am Anzeigenamen (gebaut, ausgeschaltet; #351)

Wiederholte Prüfung von Risiko 1 (Abschnitt 3) für diesen einen Teil, vor dem Bau verlangt
unten unter „Geplant, nicht gebaut“.

- **Zweck:** Anerkennung durch andere sichtbar machen (`docs/VISION.md` „Meilensteine“).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. a und Art. 9 Abs. 2 lit. a, eine eigene Einwilligung
  neben der Art.-9-Einwilligung (`ss/domain/abzeichen_sichtbarkeit.py`, Wortlaut `2026-11-09-b`: kurze Frage, die
  Hinweise auf Nicht-Mitglieder, Screenshots und die Datenschutzerklärung aufklappbar unter
  „Mehr dazu“ direkt darunter).
  Ohne Art.-9-Einwilligung keine Meilensteine und damit kein Abzeichen.
- **Daten:** je Antwort eine Zeile mit Kennung, Ja/Nein, Wortlaut und Zeitpunkt
  (`abzeichen_sichtbarkeit`, Nachweis nach Art. 7 Abs. 1); die Zahl der erreichten
  Meilensteine nur im Arbeitsspeicher, alle 15 Minuten neu berechnet
  (`ss/services/abzeichen_service.py`).
- **Empfänger:** andere Angemeldete, an Beiträgen der Person neben dem Anzeigenamen
  (`ss/services/beitrag_fuer_aufrufer.py`); Besucher nie. Ab 5 erreichten Meilensteinen
  trägt das Siegel ihrer Beiträge außerdem eine Krone; sie kommt aus derselben Zahl, für
  dieselben Empfänger, mit derselben Zustimmung (Frontend, `siegel-auszeichnung.ts`). Glanz am
  Siegel betrifft den Beitrag, nicht die Person, und folgt dem Zähler der Karte, den alle sehen.
- **Frist:** Antworten solange das Konto besteht, mit ihm gelöscht (`LK` Schritt 2,
  `mvp/scripts/manual/person_loeschen.sql`); die Zahl hat keine Speicherung.
- **Risiko:** Das Abzeichen zeigt, dass und wie viel jemand mitmacht; unter den Angemeldeten
  sind Nicht-Mitglieder, Screenshots können nach außen gehen. Mehr als der Anzeigename am
  Beitrag verrät es nur in der Menge: Schon der Name am Beitrag zeigt die Mitwirkung (R1).
- **Maßnahmen:** gesonderte Einwilligung, einmal gefragt ab dem ersten erreichten Meilenstein, der keine Wegmarke ist,
  zwei gleichwertige Knöpfe, nichts vorbelegt; Nein und Widerruf der Art.-9-Einwilligung
  nehmen das Abzeichen sofort weg; gezeigt wird nur eine Zahl, keine Einzelheiten, ohne
  Wegmarken (eigenes Tun, `ss/domain/meilensteine.py`), damit sie Anerkennung durch andere
  zeigt und nicht die Menge des eigenen Tuns; nur für
  Angemeldete; zwei Schalter, Standard aus (`abzeichen_sichtbar_aktiv` und `punkte_aktiv`).
- **Widerruf:** Ein Widerruf der Art.-9-Einwilligung nimmt das Abzeichen sofort weg und hält
  ein früheres Ja als Nein fest; nach einer neuen Art.-9-Einwilligung erscheint es erst nach
  einem neuen Ja.
- **Rest:** gering, wie Risiko 1. **Offen:** Frage 6 an die Datenschutzbeauftragte
  (Abschnitt 6). Die Datenschutzerklärung beschreibt das Abzeichen im Abschnitt „Punkte“
  (Absatz „Abzeichen an deinem Namen“, Fachfrage in PR #634).

#### Geplant, nicht gebaut

Ranglisten, Quests, Level, Krone und Wochenthema (`docs/VISION.md:99-103`,
#351, #564). Sie machen sichtbar, wer wie aktiv ist, und brauchen ein eigenes Opt-in
(`docs/VISION.md:101`, Abschnitt 3 Risiko 1). Abschnitt 1 bis 7 prüft sie als Plan; vor dem Bau ist
die Prüfung zu wiederholen; `docs/VISION.md:134` legt die DSFA vor die Ranglisten, Abschnitt 2
empfiehlt sie schon vor dem Einschalten der Punkte.

### 8.3 Risiken über alle Verarbeitungen (Art. 35 Abs. 7 lit. c, d)

| # | Risiko | Maßnahmen | Rest |
|---|---|---|---|
| R1 | **Politische Haltung wird sichtbar**: Anzeigename an Beiträgen, Einwürfen und Sätzen für alle Angemeldeten, darunter Nicht-Mitglieder (V1, V3, V4) | nur Angemeldete, nur Vorname und Initial, Kennung nur für Admins; Einwilligung vor dem Beitragen (V2) | geringes Risiko |
| R2 | **Zuordnung pseudonymer Daten**: Tagespseudonym der Angemeldeten am laufenden Tag nachrechenbar, falls der Schlüssel gesetzt ist (V7), Uhrzeiten im vorgelagerten Webserver (V16) | Tag statt Uhrzeit, Verdichten am Tagesende, Schlüssel der Besucher nur im Speicher, Besucher ohne User-Agent; für Angemeldete am laufenden Tag **offen** | Risiko; geringes Risiko, sobald V7 umgestellt ist |
| R3 | **Daten Dritter** in Beiträgen, Einwürfen und Suchtexten, auch deren politische Zuordnung (V3, V4, V6), darunter „Gepostet von“ am Post | Hinweise im Formular und in der Erklärung; „Gepostet von“ freiwillig; Melden; Einzelfall-Löschung | Risiko, hinnehmbar |
| R4 | **Datenpanne oder Zugriff durch Admins**: Kennungen, Meldungen mit Name und E-Mail-Adresse, Muster-Hinweise | Fristen (`LK:150-164`), Kennungen nur gekürzt im Log, keine Weitergabe (`DSE:74-75`); Rollen und Zugriffskonzept, AV-Vertrag und Verschlüsselung der Sicherungen stehen nicht im Repo (**offen**, 8.6) | Risiko unter Vorbehalt von 8.6; **hoch**, wenn es keinen AV-Vertrag gibt oder die Sicherungen unverschlüsselt auf demselben Host liegen |
| R5 | **Unbefristete Protokolle** mit Altbestand aus Suchtexten und Kennungen (V16) | Ziel 14 Tage (`LK:511-519`), nicht ausgerollt | Risiko, bis ausgerollt |
| R6 | **Löschung von Hand, nie an echten Daten erprobt** (`LK:3-13`, `DSE:1161-1163`) | Skript getestet gegen Testdaten (`LK:531-532`); Backup und Protokoll beim ersten Lauf | Risiko; geringes Risiko nach dem ersten belegten Lauf |
| R7 | **Scoring und Zweckentfremdung** durch Punkte (V11) | Abschnitt 3 | Risiko (wie Risiko 3) |
| R8 | **Rückschluss auf einzelne Stimmen** über kleine Zähler oder die Güte (V5) | M5: Summen und Stimmenanteil der Güte erst ab drei verschiedenen Stimmenden, darunter keine Zahl in der Antwort; ohne Startkonten und eigene Stimme; Gewicht der Stimmen gedeckelt (#427) | geringes Risiko |
| R9 | **Widerruf ohne volle Folgen**: Beiträge, Einwürfe, Sätze (und ohne #658 auch Stimmen) bleiben nach dem Widerruf der Art.-9-Einwilligung mit Kennung und Anzeigenamen (V2) | R9a (#658, gebaut): Stimmen werden beim Widerruf gelöscht; R9b (#661, gebaut als Löschauftrag): ein Admin anonymisiert Beiträge, Einwürfe und Sätze wie bei der Kontolöschung binnen sieben Tagen (V2) | Risiko; geringes Risiko, wenn der Ablauf ohne Admin läuft |

### 8.4 Risikomethode und Einstufung (DSK-Kurzpapier Nr. 18)

Bis zum 11.11.2026 stufte diese DSFA mit „gering“, „gering bis mittel“ und „mittel“ ohne
benannte Methode ein. Ab hier gilt das Kurzpapier Nr. 18 der Datenschutzkonferenz („Risiko
für die Rechte und Freiheiten natürlicher Personen“):

- Je Risiko werden **Eintrittswahrscheinlichkeit** und **Schwere des möglichen Schadens** für
  die betroffenen Personen geschätzt, je in vier Stufen: geringfügig, überschaubar,
  substanziell, groß.
- Aus beiden ergibt sich eine von drei **Risikoklassen**: geringes Risiko, Risiko, hohes Risiko.
- **Gesamtrisiko** der Verarbeitung ist grundsätzlich die höchste Klasse der Einzelrisiken.
- Bleibt nach den Maßnahmen ein hohes Risiko, ist die Aufsichtsbehörde vorher zu konsultieren
  (Art. 36 Abs. 1).

Matrix, wie sie hier angewendet wird (Zeilen Schwere, Spalten Wahrscheinlichkeit). Die
Zuordnung der Felder folgt der Abbildung im Kurzpapier; vor der Übernahme am Original
abgleichen.

| Schwere \ Wahrscheinlichkeit | geringfügig | überschaubar | substanziell | groß |
|---|---|---|---|---|
| **groß** | Risiko | hoch | hoch | hoch |
| **substanziell** | gering | Risiko | hoch | hoch |
| **überschaubar** | gering | gering | Risiko | hoch |
| **geringfügig** | gering | gering | gering | Risiko |

Die alte Skala bildet sich so ab: „gering“ → geringes Risiko, „mittel“ → Risiko; „gering bis
mittel“ ist je Risiko unten neu entschieden. Die Schätzungen sind die der Verfasser dieses
Entwurfs; sie zu bestätigen oder zu ändern, ist Teil der Beratung (Abschnitt 6, Frage 1).

| Risiko | Wahrscheinlichkeit | Schwere | Klasse heute | nach den offenen Maßnahmen |
|---|---|---|---|---|
| 1 Sichtbarkeit der Aktivität (Punkte, Abschnitt 3) | geringfügig: nur mit Opt-in | substanziell: politische Meinung | gering | gering |
| 2 Netz der Nutzung (Abschnitt 3) | geringfügig: Schlüssel nur im Speicher | überschaubar | gering | gering |
| 3 Zweckentfremdung, Druck (Abschnitt 3, R7) | überschaubar: keine technische Sperre gegen interne Auswertung | substanziell: Auswahl für Ämter oder Listen | **Risiko** | Risiko (Bilanz nach acht Wochen) |
| R1 Haltung sichtbar | überschaubar | überschaubar: Vorname und Initial, nur Angemeldete | gering | gering |
| R2 Zuordnung pseudonymer Daten | überschaubar: braucht Datenbank und Konfiguration, nur der laufende Tag | substanziell: kann auf einen Suchtext führen | **Risiko** | gering (V7 umgestellt) |
| R3 Daten Dritter | substanziell: Beiträge nennen oft Dritte | überschaubar: öffentliche Äußerungen, Melden möglich | **Risiko** | Risiko, hinnehmbar |
| R4 Datenpanne, Zugriff durch Admins | überschaubar, unter Vorbehalt von 8.6; substanziell, wenn es keinen AV-Vertrag gibt oder die Sicherungen unverschlüsselt auf demselben Host liegen | substanziell: Art.-9-Daten, Name und E-Mail in Meldungen | **Risiko**, im genannten Fall **hoch** | gering (8.6 belegt, Zugriff geregelt) |
| R5 Protokolle ohne Frist | überschaubar | substanziell: Altbestand mit Suchtexten und Kennungen | **Risiko** | gering (14 Tage ausgerollt, Altbestand gelöscht) |
| R6 Löschung von Hand | überschaubar: nie an echten Daten gelaufen | substanziell: Art.-9-Daten bleiben | **Risiko** | gering (erster Lauf belegt) |
| R8 Rückschluss auf Stimmen | geringfügig: Schwelle drei | überschaubar | gering | gering |
| R9 Widerruf ohne volle Folgen | überschaubar: mit dem Löschauftrag (#661) bleibt die Zuordnung bis zur Ausführung, höchstens sieben Tage, länger nur, wenn ein Admin die Frist versäumt (überfällige hervorgehoben) | substanziell: in dieser Zeit bleibt die Zuordnung politischer Beiträge zur Person ohne Rechtsgrundlage (wie R6), für alle Angemeldeten sichtbar | **Risiko** (vor #661 **hoch**) | gering, wenn der Ablauf ohne Admin läuft: Wahrscheinlichkeit geringfügig |

**Gesamtrisiko heute: Risiko**, unter dem Vorbehalt der offenen Fakten (8.6): Mit dem
Löschauftrag (#661) liegt R9 in der mittleren Klasse, vorher war es **hoch**. **Folgerung zu
Art. 36:** Nach den Maßnahmen bleibt kein hohes Risiko, solange die offenen Fakten F1 bis F6 (8.6)
R4 nicht auf hoch heben, also ein AV-Vertrag besteht und die Sicherungen nicht unverschlüsselt auf
demselben Host liegen. Ob die Ausführung von Hand binnen sieben Tagen dafür genügt oder erst der
vollautomatische Ablauf, ist Frage 7 an die Datenschutzbeauftragte.
Nach den offenen Maßnahmen bleibt Risiko bei Risiko 3 und R3;
beide sind hinnehmbar, Risiko 3 nur, solange die Punkte aus sind oder die Bilanz nichts
anderes zeigt. Sind die Punkte an, gilt dieselbe Einstufung; neu zu prüfen ist sie vor den
Ranglisten und vor Ausbaustufe 2 (Abschnitt 2).

### 8.5 Notwendigkeit und Verhältnismäßigkeit des Grundbetriebs (Art. 35 Abs. 7 lit. b)

Abschnitt 5 prüft das für die Punkte. Für den Grundbetrieb ohne Punkte:

- **Zweck:** Argumente für die politische Auseinandersetzung sammeln, durchsuchbar machen und
  verbessern (`docs/VISION.md`, `DSE:1081-1084`). Ein legitimer Zweck des Vereins; ohne Konto
  und Zuordnung von Beiträgen, Stimmen und Meldungen lässt er sich nicht erreichen, ohne Namen
  und Kennungen lässt sich weder Doppelstimmen verhindern noch Missbrauch abwehren
  (LK „Stimmen“, V12).
- **Erforderlichkeit, Datenminimierung (Art. 5 Abs. 1 lit. c):**
  - Suchen und Lesen ohne Konto (`DSE` „Was diese Erklärung abdeckt“).
  - In der Datenbank nur Kennung und Anzeigename, kein Name, keine E-Mail-Adresse; gezeigt
    werden Vorname und Initial (V1).
  - Suchtexte ohne Autor und Pseudonym (V6); Suchereignisse nur mit Tag und seit #655 am
    Tagesende zu Zählern verdichtet (V7).
  - Nutzung ohne Kennung, Prüfwerte mit Schlüsseln nur im Speicher (V9, V9a, V11).
  - Summen der Stimmen erst ab drei Stimmenden (V5); Rate-Limits nur flüchtig (V18).
  - Kein KI-Anbieter, keine Übermittlung außerhalb der EU („Für alle“).
- **Speicherbegrenzung (Art. 5 Abs. 1 lit. e):** Fristen je Datenart in LK „Fristen“, gelöscht
  von einem täglichen Task. Ohne Frist und begründet: Beiträge (Zweck ist der Bestand, bei
  Kontolöschung anonymisiert), offene Meldungen und aktive Sperren (laufende Arbeit), der
  Anzeigename (solange das Konto besteht). Ohne Frist und **nicht** begründet: die Protokolle
  der Anwendung und des Frontend-nginx (V16, R5).
- **Angemessenheit:** Mitwirkung, aus der eine politische Meinung folgt, nur mit ausdrücklicher
  Einwilligung (V2), die Sperre ist durch einen Test abgesichert. Unter den Angemeldeten sind
  Nicht-Mitglieder; deshalb sehen auch Angemeldete keine Kennungen, und Besucher sehen keine
  Namen (R1). Wo die Lücken unten offen sind, fällt die Abwägung noch nicht für die Verarbeitung
  aus.
- **Rechte der Betroffenen (Art. 12 bis 22):** Information in der Datenschutzerklärung, in
  Abschnitten je Verarbeitung. Auskunft und Löschung auf Anfrage an die Kontaktadresse, von Hand
  nach dem Löschkonzept (`DSE` „Deine Rechte“, LK „Ablauf“); selbst kann die Person eigene
  Beiträge löschen und die Einwilligung widerrufen. Widerspruch nach Art. 21 steht in der
  Erklärung. **Offen:** Einen Export für die Datenübertragbarkeit (Art. 20) gibt es im Code
  nicht; die Erklärung nennt das Recht. Ob Art. 20 hier greift und wie eine Anfrage bedient
  wird, steht nicht im Repo.
- **Auftragsverarbeitung, Drittland:** Keine Übermittlung außerhalb der EU. Der AV-Vertrag ist
  nicht belegt (8.6, F1).

**Ergebnis:** Der Grundbetrieb ist im Kern notwendig und verhältnismäßig. Nicht verhältnismäßig
sind heute vier Punkte, die Maßnahmen dazu stehen in Abschnitt 9: Anzeigename vor der
Einwilligung (V1), Widerruf ohne volle Folgen (V2, R9; mit dem Löschauftrag aus #661 nur noch bis zur Ausführung, höchstens sieben Tage), nachrechenbares Tagespseudonym der
Angemeldeten (V7), Protokolle ohne Frist (V16).

### 8.6 Offene Fakten

Diese Angaben stehen nicht im Repo. Die DSFA erfindet sie nicht; wer sie belegt, trägt sie hier
und an den genannten Stellen nach.

| # | Offen | Warum es zählt | Stellen |
|---|---|---|---|
| F1 | **AV-Vertrag** mit verdigado: gibt es ihn, erfasst er Gut gesagt mit Zweck, Datenarten (auch Art. 9) und Betroffenen (Art. 28 Abs. 3), und ist Hetzner Unterauftragsverarbeiterin oder nur Rechenzentrum ohne Zugriff? | Ohne Vertrag fehlt die Grundlage für die Verarbeitung bei verdigado, und die Aussage der Datenschutzerklärung stimmt nicht. | „Für alle“, R4, #506 |
| F2 | **SMTP-Server** in Produktion: welcher, wer betreibt ihn, ist er vom AV-Vertrag erfasst? Ebenso der Mailversand des Anmeldedienstes. | Mails tragen E-Mail-Adresse und Anlass (Meldung, Entscheidung). | „Für alle“ |
| F3 | **Verschlüsselung der Sicherungen**: Datenträger, Ablage außerhalb des Hosts, Zugriff. Das Skript selbst verschlüsselt nicht. | Sicherungen halten alles bis zu 28 Tage, auch Gelöschtes. | V17, R4 |
| F4 | **Rollen und Zugriff**: wer Admin ist (Admin-Claim aus dem Realm oder Liste `admin_users` in der Konfiguration, `docs/ARCHITECTURE.md`), wer Zugang zu Host, Datenbank, Konfiguration und der Datei der Beta-Zugänge hat, wie Zugänge vergeben und entzogen werden. | Admins sehen Kennungen, Meldungen mit Name und E-Mail-Adresse, Muster-Hinweise. | R4, V19 |
| F5 | **Schlüssel des Tagespseudonyms** der Angemeldeten (`SEMANTIC_SEARCH_ACTOR_HASH_SECRET`): in Produktion gesetzt? | Davon hängt ab, ob das Pseudonym am laufenden Tag nachrechenbar ist. | V7, R2 |
| F6 | **Frist der Protokolle** am Host: 14 Tage ausgerollt, Altbestand gelöscht? Laut Löschkonzept Stand 30.10.2026 nicht. | Speicherbegrenzung, Altbestand mit Suchtexten. | V16, R5, #485, #336 |

## 9. Offene Entscheidungen für den Maintainer

1. **Umfang:** diese DSFA für die ganze Plattform führen (Abschnitt 1 bis 9), statt den Grundbetrieb
   begründet herauszunehmen? Empfehlung: ja.
2. **Lücke vor der Einwilligung** (Abschnitt 4): Anzeigename erst nach der Einwilligung speichern
   (Weg 2)? Empfehlung: ja, als eigenes Ticket.
3. **Tagespseudonym der Angemeldeten** (V7): Schlüssel nur im Speicher wie bei Besuchern? Preis:
   Nach einem Neustart zählt eine Person am selben Tag doppelt. Empfehlung: ja. Seit dem Verdichten
   am Tagesende (Umstellung zu #495) betrifft es nur noch den laufenden Tag.
4. **Frist für Protokolle** (V16): 14 Tage für Anwendung und Frontend-nginx am Host ausrollen
   (`LK:511-519`, Stand 30.10.2026; Tickets #485 und #336) und den Altbestand mit Suchtexten und
   Kennungen löschen. Das ist Betrieb am Host, nicht Code.
5. **Formales:** Wer übernimmt die DSFA (Vorstand mit Datenschutzbeauftragter, Art. 35 Abs. 2)?
   Das Verzeichnis der Verarbeitungstätigkeiten steht als Entwurf in
   `docs/VERARBEITUNGSVERZEICHNIS.md`; führen muss es der Verein (Art. 30 Abs. 1).
6. **Fragen an die Datenschutzbeauftragte:** Lücke aus Abschnitt 4, Meldungen ohne Einwilligung
   (V12) und Altersgrenze (WP 248 Kriterium 7) zu `docs/FRAGEN_DATENSCHUTZBEAUFTRAGTE.md` hinzufügen
   (vorbereitet als Abschnitt 6, Frage 5)? Empfehlung: ja, gebündelt mit Frage 1 dort.
7. **Widerruf der Art.-9-Einwilligung** (V2, R9): Stimmen löschen ist gebaut (R9a, #658), R9b
   als Löschauftrag (#661): Der Widerruf legt ihn an, ein Admin führt binnen sieben Tagen den
   Löschablauf aus; der Widerrufstext der Datenschutzerklärung und der Wortlaut `2026-11-13` sind
   angepasst. Offen ist der vollautomatische Ablauf nach dem Freeze, mit dem R9 gering wird.
   Empfehlung: eigenes Ticket.
8. **Offene Fakten** (8.6): F1 bis F6 belegen, vor allem den AV-Vertrag (F1), bevor Art.-9-Daten
   echter Personen verarbeitet werden.
