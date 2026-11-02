# Datenschutz-Folgenabschätzung: Punkte, Quests und Ranglisten

> **Entwurf zur Prüfung, nicht beschlossen.** Keine Rechtsberatung. Entscheiden müssen der
> Vorstand der Netzbegrünung als Verantwortlicher und die Datenschutzbeauftragte; Fragen an sie
> stehen in #296. Bis dahin bleiben die Punkte aus (`SEMANTIC_SEARCH_PUNKTE_AKTIV`, Standard aus).

Stand 02.11.2026; Code `main` @ `2c28931a` und PR #476 @ `5b19ef32` (offen). `ss/` =
`mvp/backend/semantic-search-service/app/`, `DSE` = die Datenschutzerklärung
(`mvp/frontend/gutgesagt-frontend/src/app/datenschutz/datenschutz.component.html`), **(#476)** =
Stand auf dem Branch von PR #476. Begriffe wie in [`GLOSSARY.md`](../GLOSSARY.md).

## 1. Worum es geht

- **Gebaut (PR #476, ausgeschaltet):** Entdoppelte Nutzung über einen Prüfwert, der nach seinem
  Tag verworfen wird (`ss/services/entdoppelung.py:1-18` (#476)); ein Punktestand, den nur die
  Person selbst sieht und der nicht gespeichert, sondern bei jedem Abruf berechnet wird
  (`ss/services/punkte_service.py:1-7` (#476), `ss/api/v1/usage.py:387-412` (#476));
  Muster-Hinweise für Admins, wenn zwei Konten sich innerhalb von 7 Tagen gegenseitig nutzen
  (`ss/services/muster_hinweise_service.py:1-24` (#476)).
- **Geplant, nicht gebaut:** Ranglisten (die ersten 10 und der eigene Platz, nur für Angemeldete,
  nur mit Zustimmung), Quests, Meilenstein-Abzeichen, Krone, Wochenthema
  (`docs/VISION.md:99-103`).
- **Fristen** (`docs/LOESCHKONZEPT.md:146-148` (#476)): Prüfwert 1 Tag, Paar-Prüfwert 7 Tage,
  Muster-Hinweis 56 Tage und mit dem Konto gelöscht (`mvp/scripts/manual/person_loeschen.sql:55` (#476)).

## 2. Ist eine DSFA Pflicht?

**Ja.** Art. 35 Abs. 3 trifft nicht zu: Es gibt keine Entscheidung mit Rechtswirkung (lit. a), die
Zahl der Mitwirkenden ist nicht „umfangreich“ (lit. b), und Gut gesagt beobachtet nichts
Öffentliches (lit. c). Auch die DSK-Mussliste (Art. 35 Abs. 4) nennt den Fall nicht ausdrücklich;
sie ist aber nicht abschließend. Nach den Leitlinien WP 248, die der EDSA übernommen hat, reichen
in der Regel zwei von neun Kriterien, und zwei treffen sicher zu:

- **Bewerten oder Einstufen:** Punkte und Rangplatz stufen Personen nach ihrem Verhalten ein
  (`ss/domain/punkte.py:55-73` (#476)).
- **Besondere Kategorien:** Schon die Mitwirkung lässt auf eine politische Meinung schließen
  (Art. 9 Abs. 1; DSE:876-889; `docs/VISION.md:101`).

Die DSFA muss stehen, **bevor die Punkte eingeschaltet werden**, nicht erst vor den Ranglisten.
Neu zu prüfen ist sie vor Ausbaustufe 2 (Grünes Netz), weil dann lit. b anders aussehen kann.

## 3. Die drei wichtigsten Risiken und die Maßnahmen

| Risiko | Maßnahmen | Rest |
|---|---|---|
| **1. Politische Aktivität wird sichtbar.** Rangliste, Abzeichen, Krone und Wochenthema zeigen anderen, wer wie aktiv ist. Unter den Angemeldeten sind auch Nicht-Mitglieder (Beta-Zugänge, Einladungen; `GLOSSARY.md:423-424`), und Screenshots können nach außen gehen. | **Ein eigenes Opt-in** für alles, was andere an der Person sehen. Zwei gleichwertige Knöpfe, nichts vorbelegt, jederzeit widerrufbar (`docs/VISION.md:101`). Gezeigt wird nur der Anzeigename, nur die ersten 10 und der eigene Platz, nur für Angemeldete, keine Linkvorschau. Eine Rangliste erst ab etwa 5 Personen mit Opt-in. Ohne Opt-in sieht nur die Person selbst ihre Punkte. | gering |
| **2. Ein Netz, wer wessen Beiträge nutzt.** PR #476 speichert kein Protokoll, nur Prüfwerte als HMAC. Die werden aber mit dem **konfigurierten** Schlüssel gebildet (`ss/services/entdoppelung.py:37-43,65-67` (#476); `ss/services/search_tracking_service.py:82`). Wer Datenbank und Schlüssel hat, kann für jedes Kontenpaar 7 Tage lang nachrechnen, wer einen Beitrag von wem genutzt hat (#499). | Die Entdoppelung über Prüfwerte statt Protokoll ist **umgesetzt**. **Neu:** Prüfwerte und Paar-Prüfwerte mit einem Schlüssel bilden, der nur im Speicher liegt, wie der Tagesschlüssel der Besucher (`ss/utils/besucher_pseudonym.py:45-73`). Nach einem Neustart beginnt dann ein Muster neu, und eine Nutzung zählt am selben Tag ein zweites Mal; das ist hinnehmbar. Muster-Hinweise lösen nichts automatisch aus; ein Admin prüft und hört die Personen an. | gering (ohne den Speicherschlüssel: mittel) |
| **3. Zweckentfremdung und Druck.** Punkte könnten als Maßstab für Ämter, Listen oder Kampagnen dienen oder Masse und Schärfe belohnen. | Zweckbindung in Datenschutzerklärung und Nutzungsbedingungen: keine Weitergabe, keine Auswahl nach Punkten. Kein Geld und keine Sachleistung (`docs/VISION.md:31`). Punkte vor allem für Wirkung, Tagesdeckel, kein Abzug, keine Punkte fürs Bewerten (`docs/adr/0004-punkte-aus-wirkung-bei-anderen.md:9-19`). | gering bis mittel; in der Acht-Wochen-Bilanz ansehen |

Mit diesen Maßnahmen ist das Restrisiko gering bis mittel. Die Aufsichtsbehörde muss deshalb
nicht konsultiert werden (Art. 36).

## 4. Rechtsgrundlage

**Empfehlung: ausdrückliche Einwilligung, Art. 9 Abs. 2 lit. a, in zwei Stufen.**

1. **Beim ersten Login** gibt es die Art. 9-Einwilligung schon als Entscheidung (Lückenliste
   D-N15, `docs/rechtstexte-luecken/4-fehlende-vorgaenge/D-N15.md`). Sie nennt zusätzlich als
   Zwecke: Punkte, Aufgaben und Meilensteine, und den Schutz der Punkte durch Muster-Hinweise. Für
   die Muster-Hinweise reicht Art. 6 Abs. 1 lit. f allein nicht, weil sie Art. 9-Daten betreffen.
2. **Beim ersten Punkt** fragt die App nach dem Opt-in aus Risiko 1, das ist eine eigene
   Einwilligung für die Sichtbarkeit.

**Warum nicht lit. d** (politisch ausgerichtete Organisation): Die Norm deckt nur Mitglieder und
Personen mit regelmäßigem Kontakt und keine Offenlegung „nach außen“. Beta-Zugänge und
Eingeladene sind keine Mitglieder, und spätestens mit Ausbaustufe 2 geht der Kreis darüber hinaus.
Ob die Netzbegrünung überhaupt unter lit. d fällt, ist offen (`docs/VISION.md:134`). Lit. d bleibt
deshalb höchstens eine interne Hilfsbegründung und gehört nicht in die Datenschutzerklärung.

**Besucher** haben nicht eingewilligt. Ihre Kopie erzeugt nur für einen Tag einen Prüfwert aus
ihrem flüchtigen Tagespseudonym (`ss/utils/besucher_pseudonym.py:15-30`). Dafür trägt Art. 6
Abs. 1 lit. f wie bei der bestehenden Nutzungsmessung (DSE:425-430); zu prüfen mit #495.

## 5. Vor dem Einschalten der Punkte

- Vorstand und Datenschutzbeauftragte übernehmen diese DSFA, gegebenenfalls geändert.
- Die Login-Einwilligung nennt die Zwecke aus Abschnitt 4.
- Die Datenschutzerklärung bekommt einen Abschnitt zu Punkten (#499). Zwei Stellen dort werden
  dann falsch und müssen ersetzt werden: „Ein Profiling … findet nicht statt“ (DSE:864-870) und
  „kein Pseudonym“ beim Kopieren (DSE:419-421).
- PR #476 nutzt das Tagespseudonym aus #470 statt der alten Sitzungskennung
  (`ss/api/v1/usage.py:292` (#476)), und der Schlüssel im Speicher aus Risiko 2 ist umgesetzt
  oder bewusst verschoben.
