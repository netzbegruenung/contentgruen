# Löschkonzept (Art. 17 DSGVO)

> **Vorsorge, keine erprobte Prozedur.** Es gibt heute keine Nutzer und keine
> erhaltenswerten Daten. Die Anlage hat keinen Codepfad, der eine Person löscht;
> was hier steht, sind Handkommandos gegen PostgreSQL und Qdrant. Sie sind aus dem
> Code hergeleitet und gegen ein leeres Dev-System gelesen, der PostgreSQL-Teil
> zusätzlich gegen Testdaten geprüft (`tests/integration/test_loeschkommando.py`), der
> Qdrant-Teil gegen eine Collection im Speicher und gegen einen echten Qdrant
> (`tests/unit/services/test_beitraege_anonymisieren.py`,
> `tests/integration/test_beitraege_anonymisieren_qdrant.py`), aber
> **nie an echten Daten gelaufen**. Wer sie zum ersten Mal ausführt, macht vorher ein Backup und
> protokolliert jede Zeilenzahl mit.

## Ausgangspunkt

Alles hängt am Wert des Headers `X-User`. Das BFF setzt ihn ausschließlich aus dem
Claim `sub`, ersatzweise `NameIdentifier` (`BFF/Program.cs:659`, `ClaimUtilities.GetUserId`,
aufgerufen in `BFF/Proxy/IdentityHeaderTransform.cs:79`).
Mit Keycloak ist das die Keycloak-UUID, mit `USE_KEYCLOAK=false` (dev/tst) die
`userId` aus `managed-users.json` (`user-001`). **Vorher prüfen, welche Form die
Umgebung benutzt** — die Kommandos sind identisch, nur der eingesetzte Wert nicht.

## Zwei Wege, einen Beitrag zu löschen

- **Der Autor löscht** (`DELETE /api/v1/content/{id}`, „Beitrag löschen“ in „Meine
  Beiträge“): Der Beitrag bekommt nur den Zustand „gelöscht“
  (`services/content/beitrag_loeschen_service.py`). Er verschwindet aus Suche, Ansicht,
  Listen, Bestandszählern und „Meine Beiträge“, bleibt aber gespeichert, damit Verknüpfungen und
  Stimmen nicht ins Leere zeigen. Nur die Verweise der Aussagen auf ihn (Antwortvorschläge)
  gehen weg, damit eine Aussage ohne weiteren Beitrag nicht mehr als beantwortet zählt.
  Scheitert das, bleibt der Beitrag sichtbar und der Autor bekommt einen Fehler mit der Bitte,
  es erneut zu versuchen; wie beim Admin-Weg unten räumt erst der zweite Versuch fertig auf.
  Das ist **kein Löschen im Sinne von Art. 17**: Text und
  Kennung stehen weiter in Qdrant, bis die Frist für gelöschte Beiträge (30 Tage, unter
  „Fristen“) abläuft. Ein Löschantrag erfasst gelöschte Beiträge deshalb
  genauso wie sichtbare und gesperrte; der Lauf in Schritt 3 filtert nur nach der Kennung,
  nicht nach dem Zustand.
- **Ein Admin entfernt endgültig**
  (`DELETE /api/v1/moderation/content/{content_type}/{id}`): Der Punkt ist danach aus
  Qdrant weg, mit ihm seine Stimmen (`votes`) und das „ausformuliert in“ der Einwürfe
  zu ihm (`raw_input_content_links`); offene Meldungen zu ihm stehen danach auf
  bearbeitet, bearbeitete und abgewiesene behalten ihre Entscheidung. Das ist der Weg
  für Schritt 3, wenn ein Text die Person erkennbar macht, und sonst für nichts:
  Gemeldete Beiträge sperrt ein Admin, statt sie zu entfernen. Denselben Weg nimmt die
  Frist für gelöschte Beiträge (unten).

## Ablauf

**Vorab: Sitzung beenden.** Vor allem anderen, damit die Person zwischen den Schritten
nichts Neues anlegt. Das BFF prüft bei jeder Anfrage mit Anmelde-Cookie, ob das Konto noch
besteht (`BFF/Services/KontoPruefung.cs`), und weist das Cookie sonst ab und löscht es:

- **Beta-Zugang:** Die `userId` notieren (Schritt 1 bis 3 brauchen sie als Kennung), dann
  den Eintrag aus `mvp/config/managed-users.json` entfernen (Details unter Schritt 4).
- **Netzbegrünung-Login:** Die Kennung als eigene Zeile in `geloeschte-konten.txt` im
  Konfigurationsverzeichnis des BFF eintragen (`GELOESCHTE_KONTEN_PATH`, Standard
  `/config/geloeschte-konten.txt`; im Dev-Stack `mvp/config/`, gitignoriert). Zeilen mit
  `#` und Leerzeilen zählen nicht. Das Cookie trägt keine Tokens, deshalb kann das BFF
  Keycloak nicht selbst fragen; das Löschen in Keycloak (Schritt 4) allein beendet die
  Sitzung nicht.

Beide Dateien liest das BFF spätestens nach fünf Minuten neu
(`BFF/Services/ManagedUserService.cs:16`, `BFF/Services/GeloeschteKontenService.cs`), nach
einem Neustart sofort; also danach das BFF neu starten. Ob es die Liste liest, zeigt die
Zeile „Loaded N deleted accounts from …“ im BFF-Log, eine abgewiesene Sitzung die Zeile
„Session of user … ended“ mit dem Pseudonym der Kennung. Der Eintrag in
`geloeschte-konten.txt` wird überflüssig, sobald zweierlei 14 Tage zurückliegt: der
Neustart, nach dem das BFF ihn gelesen hat, und das Löschen des Keycloak-Kontos
(Schritt 4). Ab dann kann kein Cookie mehr gelten, denn ohne Anfrage läuft es nach 14
Tagen ab, und jede Anfrage seit dem Neustart wurde abgewiesen. Dann wieder entfernen.
Solange das Keycloak-Konto besteht, kann sich die Person neu anmelden; die Liste weist
dann jede folgende Anfrage ab, nach dem Entfernen nicht mehr.

1. **Sitzungskennung sichern.** `content_reports` ist die einzige Zeile im System,
   die `reported_by_user_id` und `reported_by_session_id` nebeneinander führen kann
   (geschrieben bis #446). Nur über sie sind die `usage_events` einer Person
   erreichbar. Seit #446 gibt es keine Sitzungskennung mehr: Neue Meldungen und neue
   `usage_events` tragen keine, der Schritt findet also nur noch ältere Zeilen.
   Anonyme offene Meldungen tragen stattdessen ein Tagespseudonym; es hat keinen
   Bezug zu einem Konto und wird beim Abschluss der Meldung gelöscht.
2. **PostgreSQL.** `usage_events` (über die Sitzungen aus Schritt 1), `votes` und
   `content_reports` löschen (ein von der Person gemeldeter, inzwischen gesperrter
   Beitrag bleibt über die Moderationsansicht „Gesperrt“ erreichbar);
   `reviewed_by` und `raw_input_content_links.created_by`
   auf `NULL` setzen statt löschen — die Zeilen gehören inhaltlich anderen;
   in `sperren` `autor` und `widerspruch` sowie `gesperrt_von` und `geprueft_von` auf
   `NULL` setzen — die Sperre bleibt, solange der Beitrag gesperrt ist (#448);
   `raw_inputs` der Person löschen (CASCADE räumt deren Links und die Sätze daran mit
   ab); in **Sätzen an fremden Einwürfen** (`raw_input_drafts`) und in
   `raw_inputs.destilled_by` die Kennung ersetzen (unten); die Zeile in
   `users` (Anzeigename) und die in `gesehene_nutzung` (Stand der Rückmeldung beim
   Anmelden, nur eine Zahl) löschen. Der Anzeigename steht **nur dort** — weder in Qdrant
   noch in `raw_inputs` noch im Log —, die Karten lesen ihn beim Ausliefern dazu und
   zeigen nach Schritt 3 „ehemalige Person“.

   **Sätze an fremden Einwürfen bleiben stehen**, nur der Personenbezug geht: Jeder
   Satz bekommt statt der Kennung einen eigenen Platzhalter `ehemalige-person-<UUID>`,
   und zu jedem Platzhalter legt das Kommando eine Zeile in `users` mit dem Anzeigenamen
   „ehemalige Person“ an — so steht es im Fangkorb. Ein Platzhalter je Satz statt eines
   gemeinsamen, weil der eindeutige Index `(raw_input_id, user_id)` zwei Sätze mit
   derselben Kennung am selben Einwurf nicht zulässt (zwei gelöschte Personen am selben
   Einwurf) und weil so auch nichts die Sätze einer Person untereinander verbindet.
   `destilled_by` bekommt den Platzhalter des eigenen Satzes; hat die Person ihren Satz
   inzwischen geleert, einen eigenen, ohne Zeile in `users` — kein Codepfad zeigt einen
   Namen zu `destilled_by`. Verknüpfungen auf
   den Satz (`raw_input_content_links.draft_id`) bleiben gültig, weil die Zeile bleibt.
   Platzhalter, deren Satz nicht mehr existiert (Sätze früher Gelöschter an den eben
   gelöschten Einwürfen der Person), räumt das Kommando aus `users` ab.
3. **Qdrant.** Beiträge werden **anonymisiert, nicht gelöscht.** `original_author`,
   `last_modified_by`, `authors[].name` und `edit_history[].editor` bekommen den
   Platzhalter `ehemalige-person`; Karten und Detailansichten zeigen dazu wie im
   Fangkorb „ehemalige Person“. Anders als bei den Sätzen ist es ein gemeinsamer
   Platzhalter für alle Gelöschten und ohne Zeile in `users`: Den Namen setzt der
   Dienst selbst (`services/anzeigename_service.py`), und ein gemeinsamer Wert
   verbindet nichts, was nicht alle Gelöschten teilen. Damit bleiben
   Antwortvorschläge, Referenzen und Nutzungszähler intakt und der Personenbezug ist
   trotzdem weg. **Gelöscht wird nur,
   wo der Text selbst die Person erkennbar macht** — das ist eine Einzelfallprüfung,
   kein Filterlauf.
4. **Konto.** Keycloak-Konto im Realm löschen, bzw. Eintrag aus
   `mvp/config/managed-users.json` entfernen, falls nicht schon vorab geschehen, und das
   BFF neu starten (Cache 5 min, `BFF/Services/ManagedUserService.cs:16`). Die Datei ist
   **nicht mehr eingecheckt** (`.gitignore:19`); getrackt ist nur
   `managed-users.example.json`. Was bis zur Umbenennung in `b993b0c4` darin stand, bleibt in der Git-Historie
   (`git log --follow -- mvp/config/managed-users.example.json`).
   Die Platzhalter sind als `userId` gesperrt: Einen Beta-Zugang mit `ehemalige-person`
   oder `ehemalige-person-…` lässt das BFF nicht zu und protokolliert einen Fehler
   (`BFF/Services/ManagedUserService.cs:128`).

## Fristen

Ein täglicher Task löscht nach festen Fristen, sofort beim Start des Dienstes, dann
täglich und zusätzlich um Mitternacht (UTC). Die Zahlen stehen an einer Stelle im Code,
`services/loeschfristen_service.py`; dort steht auch die Begründung. Wie beim Feedback
hängt der Task nicht am abschaltbaren Usage-Cleanup. Was gelöscht ist, steht in Backups
bis zu 28 Tage weiter (unter „Was nicht gelöscht wird“).

| Datenart | Frist | Gerechnet ab |
|---|---|---|
| Meldungen (`content_reports`), bearbeitet oder abgewiesen | 180 Tage | Bearbeitung (`reviewed_at`; ohne sie, im Altbestand, der Eingang) |
| Tagespseudonym an anonymen Meldungen (`reported_by_session_id`, `besucher:…`) | bis zum Abschluss der Meldung | Bearbeiten oder Abweisen ersetzt es durch einen Zufallswert (`anon:…`), angemeldete Meldungen verlieren den Wert (#446, `repositories/content_report_repository.py`) |
| Meldungen, offen | keine | — sie sind Arbeit und bleiben, bis ein Admin sie bearbeitet oder ihr Beitrag endgültig entfernt wird (dann bearbeitet, Frist wie oben) |
| Einwürfe (`raw_inputs`), die in keinem Beitrag ausformuliert sind, samt Sätzen | 365 Tage | letzte Arbeit daran: Einwerfen oder zuletzt gespeicherter Satz |
| Einwürfe, die in einem Beitrag ausformuliert sind | solange dieser Beitrag besteht | — danach wie die anderen |
| Gelöschte Beiträge (Zustand „gelöscht“, Qdrant) | 30 Tage, dann endgültig entfernt | Tag im Payload-Feld `geloescht_am` |
| Sperren (`sperren`), aufgehoben, samt Widerspruch | 180 Tage | Aufhebung (`aufgehoben_am`) |
| Sperren, aktiv | keine | — der Beitrag ist gesperrt |
| Stimmen (`votes`) | solange der Beitrag besteht | — gehen mit ihm |

- **Meldungen:** Sechs Monate, weil eine Entscheidung über eine Meldung so lange
  angefochten werden kann (Art. 20 Abs. 1 DSA). Danach braucht niemand mehr die
  meldende Person, ihre Sitzungskennung, ihren Namen und ihre E-Mail-Adresse (freiwillig,
  seit #438) oder den Freitext. Verlangt jemand ohne Konto die Löschung dieser Angaben,
  finden sich seine Meldungen nur über `content_reports.melder_email` oder `melder_name`,
  per Hand in der Datenbank; ein Werkzeug dafür gibt es nicht. Die Adresse ohne Rücksicht
  auf Groß- und Kleinschreibung suchen (`ILIKE`): Gespeichert ist sie, wie sie eingegeben
  wurde, nur die Domain klein. Offene Meldungen haben keine
  Frist, Name und E-Mail-Adresse bleiben also, bis die Meldung bearbeitet ist. Der Zähler am Beitrag
  (`report_count`) bleibt; er trägt keinen Personenbezug. Das gilt auch für Meldungen zu
  gesperrten Beiträgen: Die Sperre selbst hat keine Frist, ihr Anlass in der Meldung
  (samt `resolution_notes`) geht nach 180 Tagen.
- **Sperren (#448):** Sperrgrund, Begründung, Kennung des Autors, Widerspruch und
  Ergebnis der erneuten Prüfung gehören zur Entscheidung über die Sperre. Solange der
  Beitrag gesperrt ist, gilt sie; nach dem Entsperren kann sie wie eine Meldung noch sechs
  Monate angefochten werden (Art. 20 Abs. 1 DSA). Wird ein gesperrter Beitrag endgültig
  entfernt, gilt seine Sperre als aufgehoben, und ihre 180 Tage beginnen.
- **Einwürfe:** Verworfene zählen wie offene und destillierte; ein Einwurf, an dem ein
  Jahr niemand gearbeitet hat, ist kein Arbeitsvorrat mehr. Verwerfen selbst setzt
  keinen Zeitpunkt; ein alter Einwurf, der eben verworfen wurde, geht also mit dem
  nächsten Lauf. Auch das Ausformulieren setzt keinen Zeitpunkt am Einwurf: Wird der
  Beitrag endgültig entfernt, zählt für den Einwurf wieder die letzte Arbeit davor; ist
  die älter als 365 Tage, geht er mit dem nächsten Lauf. Platzhalter ehemaliger Personen (`ehemalige-person-<UUID>` in
  `users`), deren Satz dabei mitgeht, räumt der Task ab wie `person_loeschen.sql`.
- **Gelöschte Beiträge:** Der erste Lauf, der einen Beitrag gelöscht findet, schreibt den
  UTC-Tag nach `geloescht_am`; die 30 Tage zählen ab dann, also höchstens einen Tag nach
  dem Löschen. Das gilt auch für Altbestand, der vor #421 gelöscht wurde. Entfernt wird
  über `ModerationService.delete_content`, denselben Weg wie beim Admin: erst Verweise der
  Aussagen, Stimmen und „ausformuliert in“, dann der Punkt. Wie beim Admin stehen offene
  Meldungen zum Beitrag danach auf bearbeitet, hier ohne Admin (`reviewed_by` leer), und
  ihre 180 Tage beginnen. Bearbeitete und abgewiesene behalten Entscheidung und Frist.
  Scheitert ein Schritt, bleibt der Beitrag stehen und der nächste Lauf versucht es erneut. Gesperrte Beiträge
  haben keine Frist: Admins brauchen sie für die Moderation.
- **Stimmen:** Aus ihnen entsteht die Güte; ohne Kennung ließe sich nicht verhindern, dass
  eine Person zweimal stimmt. Sie leben deshalb so lange wie der Beitrag.

## Feedback

Die Tabelle `feedback` (Knopf „Feedback“ im Kopf der App, #343) trägt nur den Freitext,
eine **optionale Kontaktangabe** und den UTC-Tag, keine Kennung und keine Sitzung, auch
bei angemeldeten Personen. Über die Kennung aus „Ausgangspunkt“ ist Feedback deshalb
nicht zu finden, und der Ablauf oben erfasst es nicht.

- **Frist:** Nach 180 Tagen löscht ein täglicher Task die ganze Zeile samt Kontakt
  (`services/feedback_service.py`, `loeschen_im_takt`, `AUFBEWAHRUNG_TAGE`). Er hängt
  nicht am abschaltbaren Usage-Cleanup.
- **Auf Antrag:** Die Person nennt die Kontaktangabe, die sie hinterlassen hat; ein
  Admin löscht die Zeilen mit dieser Angabe, ohne Rücksicht auf Groß- und
  Kleinschreibung und Leerzeichen am Rand
  (`DELETE FROM feedback WHERE lower(btrim(kontakt)) = lower(btrim('<angabe>'));`,
  vorher mit `SELECT` prüfen).
  Ohne Kontaktangabe ist Feedback keiner Person zuzuordnen. Nennt der Freitext selbst
  die Person, ist das wie bei Beiträgen eine Einzelfallprüfung.
- Backups: wie unten unter „Was nicht gelöscht wird“, bis zu 28 Tage.

## Einladungen

Die Tabelle `einladungen` (#429) trägt eine Notiz, die Zahl erlaubter und erfolgter Einlösungen,
den letzten gültigen Tag und ob die Einladung abgeschaltet ist. Sie enthält **keine
Mail-Adresse und keine Kennung**: Wer eine Einladung einlöst, erhöht nur den
Zähler. Die Mail-Adresse geht beim Einlösen an Keycloak und wird in Gut gesagt weder
gespeichert noch geloggt. Über die Kennung aus „Ausgangspunkt“ ist deshalb nichts zu finden,
und der Ablauf oben erfasst die Tabelle nicht.

- **Notiz:** Das Dashboard bittet, keine Namen oder Mail-Adressen einzutragen. Steht doch
  einer darin, ist das eine Einzelfallprüfung; die Notiz lässt sich in der Datenbank
  ändern.
- **Frist:** keine. Einladungen bleiben stehen, auch abgelaufene; sie tragen keinen
  Personenbezug.
- **Konto im Realm:** Löschen wie bisher in Keycloak; dass es über eine Einladung entstand,
  steht nirgends. Wer Keycloak-Admin ist, kann bei einem persönlichen Link aber den
  Zeitpunkt der Kontoanlage (oder einer Anfrage an `/einloesen` im Access-Log) mit dem
  Zähler vergleichen.

## Vier Fallen

- **Sitzungskennung vor `content_reports`.** Wird Schritt 2 vor Schritt 1 ausgeführt,
  ist der einzige Weg von der UUID zu den `usage_events` dauerhaft weg. Findet
  Schritt 1 nichts, sind die Ereignisse dieser Person nicht bestimmbar — das gehört
  so ins Protokoll, es ist kein Fehler des Laufs.
- **Anonymisieren vor Löschen.** Erst der Payload-Lauf über alle vier Felder, dann
  die Einzelfall-Löschungen. Andersherum fehlen die gelöschten Punkte im
  Anonymisierungslauf, und ein Punkt mit fremden Mitautoren wäre schon weg.
- **Erst die Sitzung, dann die Daten.** Der Semantic-Service legt den Anzeigenamen aus
  dem Header `X-User-Display-Name` neu an, sobald er ihn nicht im Prozess-Cache hat
  (`services/anzeigename_service.py`), und solange das Anmelde-Cookie gilt, kann die Person
  neue Sätze, Stimmen, Einwürfe und Beiträge anlegen. Das Cookie läuft **gleitend**: 14 Tage
  ab der letzten Nutzung (`BFF/Program.cs`, `ExpireTimeSpan` und `SlidingExpiration`, in
  beiden Zweigen). Deshalb steht „Sitzung beenden“ vor Schritt 1: Ist das Cookie
  abgewiesen, kommt nichts mehr nach, und ein Lauf genügt. Wer die Reihenfolge vertauscht
  oder die Prüfung im BFF-Log nicht sieht, lässt Schritt 1 bis 3 nach dem Beenden der
  Sitzung noch einmal laufen; alle drei sind wiederholbar.
- **`VACUUM FULL` danach.** `DELETE` markiert in PostgreSQL nur; die alten Kennungen
  stehen bis zum Table-Rewrite physisch auf der Platte.

## Was nicht gelöscht wird

- **`search_events`** trägt seit der Migration vom 19.08.2026 (unten) nur `actor_hash`,
  ein täglich rotierendes HMAC-SHA256 über Kennung + UTC-Datum
  (`services/search_tracking_service.py:35`, `_derive_actor_hash`).
  Ohne Geheimnis nicht umkehrbar, mit Geheimnis nur tageweise nachrechenbar: Löschen
  auf Antrag ist unmöglich und mangels Personenbezug auch nicht geschuldet.
  **Vorher prüfen, ob die Zielumgebung migriert ist** — auf einem Stand ohne
  `actor_hash` stehen dort Suchanfrage im Klartext, Kennung und IP-Hash, und dann ist
  `DELETE FROM search_events WHERE user_id = …` sehr wohl nötig
  (`mvp/backend/postgres-app/migrations/2026-08-19-search-events-pseudonymisieren.sql`).
  Der Zeitstempel trägt nur den UTC-Tag, keine Uhrzeit: Sonst ließe sich eine Aussage,
  die eine Suche angelegt hat, über ihren Anlagezeitpunkt einem Suchereignis und damit
  einem Tagespseudonym zuordnen. Bestandsumgebungen schneiden alte Uhrzeiten mit
  `mvp/backend/postgres-app/migrations/2026-10-26-search-events-nur-tag.sql` ab (samt
  `VACUUM FULL search_events`). In Backups stehen die alten Uhrzeiten, bis diese
  herausrotiert sind; ebenso in Anwendungsprotokollen älterer Stände die Zeilen je
  Suche („Tracking search“, „Search request“, „Statement already exists with ID …“,
  „Successfully created new statement with ID …“, „Found entry with id …“, „Query
  polarity …“ mit Wörtern aus dem Suchtext), die der Dienst auf INFO nicht mehr schreibt.
  Die Spalte `id` ist seit #275 eine zufällige UUID, keine fortlaufende Nummer: Eine
  Nummer ergab die Reihenfolge der Suchen eines Tages, und die ließ sich an ruhigen
  Tagen mit der Reihenfolge der Aussagen aus Suchen abgleichen. Bestandsumgebungen
  stellen mit `mvp/backend/postgres-app/migrations/2026-10-27-suchereignisse-reihenfolge.sql`
  um; dabei wird die Tabelle neu geschrieben, die alten Nummern stehen danach nicht mehr
  in ihr. In Backups und im WAL stehen sie, bis diese herausrotiert sind.
  Auch die physische Reihenfolge der Zeilen (`SELECT` ohne `ORDER BY`, `ctid`, die
  Reihenfolge in `pg_dump`) und die Systemspalte `xmin` folgen dem Einfügen: Jede Suche
  schreibt ihr Suchereignis in einer eigenen Transaktion, deren Nummer mit jeder Suche
  steigt. Seit #337 schreibt der tägliche Bereinigungsjob deshalb jeden abgeschlossenen
  Tag in zufälliger Reihenfolge und in einer Transaktion neu
  (`SearchTrackingRepository.mische_abgeschlossene_tage`), bei jedem Lauf alle
  abgeschlossenen Tage der Frist, auch beim Start des Dienstes. Danach ergeben `xmin`
  und `ctid` für einen abgeschlossenen Tag keine Reihenfolge mehr; ein eingespielter
  älterer Dump ist nach dem nächsten Lauf ebenso gemischt. Mit `ENABLE_USAGE_CLEANUP=false`
  entfällt das Mischen mit dem Job. **Bleibt:** Der laufende Tag ist bis zum nächsten Lauf
  ungemischt. Ebenso eine Suche kurz vor Mitternacht UTC, deren Suchereignis erst
  eingeht, während der Lauf schon mischt (praktisch nur beim Start des Dienstes kurz nach
  Mitternacht): Ihre Zeile trägt bis zum nächsten Lauf ein eigenes `xmin` und ist damit
  als eine der letzten Suchen ihres Tages erkennbar; verloren geht dabei nichts. Die
  alten Zeilenversionen und ihre Einträge im Index auf `timestamp` stehen physisch in
  der Datei, bis ein `VACUUM` ihren Platz freigibt (nur mit Werkzeugen lesbar, die Seiten
  roh auslesen); in Backups und im WAL, bis diese herausrotiert sind.
  **Frist:** Suchereignisse bleiben 90 Tage als Einzelzeilen
  (`SEMANTIC_SEARCH_SEARCH_EVENT_RETENTION_DAYS`, `core/config.py`, nicht unter 90:
  `GET /metrics/searches-per-user` wertet bis zu 90 Tage Einzelzeilen aus). Ältere Tage
  verdichtet der tägliche Bereinigungsjob (`services/cleanup/usage_cleanup_service.py`,
  derselbe wie für die Nutzungsereignisse) zu einem Tageszähler und löscht die
  Einzelzeilen samt Pseudonym und `id` (#289). Der Job läuft nur mit
  `SEMANTIC_SEARCH_ENABLE_USAGE_CLEANUP=true` (Standard); abgeschaltet gilt auch diese
  Frist nicht. Physisch verschwinden die gelöschten Zeilen erst, wenn PostgreSQL den
  Platz wiederverwendet (Autovacuum); in Backups stehen sie bis zu 28 Tage weiter.
- **`suchen_je_tag`** (Tageszähler der Suchen) trägt je UTC-Tag nur die Zahl der Suchen,
  die Zahl der Suchen ohne Treffer (seit #467, für die Bilanz) und die Zahl der Personen
  (verschiedene Tagespseudonyme), kein Pseudonym: nichts, was sich einer Person zuordnen
  ließe. Keine Frist.
- **`suchen_ohne_treffer`** trägt nur Aussage-ID, Montag der Woche, Anzahl der Suchen
  und Anzahl der Personen, weder Kennung noch Pseudonym: nichts, was sich einer Person
  zuordnen ließe. Welche Tagespseudonyme (dieselben wie in `search_events`) eine Aussage
  heute schon gezählt haben, liegt nur im Arbeitsspeicher (als SHA-256-Prüfwert) und wird
  um Mitternacht (UTC) verworfen. Wochen älter als acht löscht ein täglicher Task von
  selbst (`services/suchen_ohne_treffer_service.py`, `loeschen_im_takt`).
- **`aussage_themen`** (#363) trägt je Zuordnung nur Aussage-ID, Thema und
  Zuordnungsart, weder Kennung noch Zeitpunkt: nichts, was sich einer Person zuordnen
  ließe. Keine Frist. Aussagen werden nicht gelöscht; wird eine gesperrt, bleiben ihre
  Zeilen stehen, gehen aber nicht mehr ins Testset. Das **Testset**
  (`GET /statement/themen/testset`, nur Admins, Knopf „Testset herunterladen“ unter
  Admin → Themen) ist eine Datei mit Aussage-ID, Text der Aussage, Themen und
  Zuordnungsart, ohne Aussagen aus Suchanfragen (`services/aussage_themen_service.py`,
  `fuers_testset`). Wer es herunterlädt, verwaltet die Kopie selbst; der Text einer
  vorab angelegten Aussage stammt von einer Person und kann, wie jeder Beitrag, Namen
  enthalten.
- **Backups** unter `/opt/gutgesagt-backups` halten 7 Tages- und 4 Wochenstände
  (`mvp/scripts/backup/backup.sh:12,28-29`), gelöschte Daten leben dort bis zu 28 Tage
  weiter. Selektives Editieren von
  `pg_dump`-Archiven und Qdrant-Snapshots ist nicht praktikabel: nach jedem
  `restore.sh` ist der Löschlauf zu wiederholen.
- **Logs.** Einzelne Zeilen zu entfernen ist nicht vorgesehen. Was darin stehen kann,
  am Code geprüft am 26.10.2026 (Stand nach #284):
  - **Kennungen:** Ab INFO steht in BFF und Semantic-Service keine Kennung im Klartext,
    nur ihr achtstelliges Pseudonym. Beide Dienste rechnen dasselbe (erste acht
    Hex-Zeichen von SHA-256): `log_pseudonym()` in `app/core/logging.py` und
    `LogPseudonym.Of()` in `BFF/Logging/LogPseudonym.cs`; dieselbe Kennung hat also in
    beiden Logs dasselbe Pseudonym. Das Pseudonym ist ein ungesalzener Hash: über Zeilen
    verkettbar und bei bekanntem Kennungsraum zurückrechenbar (Docstring von
    `log_pseudonym()`), bei Kennungen wie `user-001` also kein Schutz. Das gilt auch für
    Admins (manueller Cleanup, `api/v1/usage.py`); die Moderationsaktionen nennen sie seit
    #271 gar nicht mehr, sie steht nur in `content_reports.reviewed_by`.
  - **BFF:** keine E-Mail-Adressen. Beim Beta-Zugang stehen erfolgreiche Anmeldungen und
    Fehlversuche mit falschem Passwort mit dem Pseudonym der `UserId` im Log
    (`BFF/Services/ManagedUserService.cs`, `BFF/Controllers/AuthController.cs`, Level
    Information/Warning), ebenso ein Beta-Zugang mit reservierter Kennung (Error). Über
    `managed-users.json` ist die `UserId` einer Adresse zugeordnet; wer die Datei hat,
    rechnet das Pseudonym durch Ausprobieren der wenigen `UserId`s zurück. Auf
    Debug steht das Pseudonym bei jeder angemeldeten Anfrage
    (`BFF/Proxy/IdentityHeaderTransform.cs`). Warnzeilen nennen den Pfad unverändert
    (Fehlerzeilen seit #422 nicht mehr, `BFF/Program.cs`); seit #284 trägt kein Pfad,
    den das Frontend aufruft, eine Kennung (die
    Nutzungsstatistik unter „Meine Beiträge“ heißt `/api/v1/usage/users/me/usage-stats`,
    die Rückmeldung beim Anmelden `/api/v1/usage/users/me/besuch`, die Person kommt aus
    der Anmeldung). Unabhängig davon sind die Zeilen unterdrückt, in
    denen YARP jede Weiterleitung mit Ziel-URL und ASP.NET Core jede Anfrage mit Pfad
    („Request starting“) protokolliert: Die Kategorien `Yarp` und
    `Microsoft.AspNetCore` stehen im Code auf `Warning` (`BFF/Program.cs`), unabhängig von
    `BFF/appsettings.json`. Ein Log-Level von außen für genau diese Kategorien ändert daran
    nichts. Eines für eine Unterkategorie (etwa `Logging__LogLevel__Yarp.ReverseProxy` oder
    `Logging__LogLevel__Microsoft.AspNetCore.Hosting`) übersteuert die Regel aber und bringt
    die Pfade zurück.
  - **Semantic-Service, Texte:** Ab INFO steht weder die Suchanfrage (`api/v1/search.py`,
    nur `limit`; Fehlerzweig in
    `repositories/implementations/qdrant/statement_repository.py`) noch der Text einer
    Aussage. Auf DEBUG stehen die ersten 50 Zeichen jeder Aussage, die die Suche unter der
    Schwelle aussortiert (`services/search/search_orchestrator.py`); da jede Suchanfrage
    als Aussage gespeichert wird (`api/v1/search.py`), sind das auch frühere Suchanfragen
    anderer, ohne Bezug zu einer Person. Ebenfalls auf DEBUG steht die Suchanfrage selbst,
    wenn sie eine aufgehobene Verneinung enthält (`utils/negation_detector.py`; nur bei
    eingeschaltetem Polaritätsfilter, Default an, `core/config.py`, und wenn die Suche
    Treffer hat, `services/polarity_filter_service.py`). Der Dev-Stack läuft auf DEBUG
    (`mvp/docker-compose.dev.yml`). Auf INFO steht die Herkunft eines neuen Kommentars
    oder einer neuen Hintergrundinfo als eingegebener Text (`reference_string`,
    `api/v1/commentary.py`, `api/v1/generic_text.py`), also meist ein Link oder eine
    Fundstelle, ohne Bezug zu einer Person. Beim Seeding stehen auf INFO die Titel der
    eingespielten Beiträge (`services/orchestration/content_orchestrator.py`), kuratierte
    Daten aus dem Repo. Die Zugriffszeilen von uvicorn sind unterdrückt
    (`uvicorn.access` auf `WARNING`, `app/core/logging.py`).
  - **Fehlerzeilen (BFF und Semantic-Service):** Seit #422 nennen sie von einer Ausnahme
    nur Typ und Stack, nicht ihren Fehlertext, der oft Eingabewerte trägt (eine
    Validierungsmeldung den abgelehnten Wert, ein Datenbankfehler die Parameter der
    Abfrage). Im Semantic-Service schreibt der Formatter Tracebacks so
    (`ausnahme_ohne_fehlertext()` in `app/core/logging.py`, auch für unbehandelte Ausnahmen,
    die uvicorn meldet), und die Log-Aufrufe setzen statt der Ausnahme nur
    `type(e).__name__` in den Text. Für Aufrufe im `except`-Block, die die Ausnahme
    direkt verwenden, prüft das `tests/unit/core/test_kein_fehlertext_im_log.py`
    am Quelltext; einen Fehlertext, der erst über eine Variable ins Log geht, sieht der
    Test nicht. Ebenso seit #422 ohne Eingabe: abgelehnte und bereinigte Herkunfts-Adressen
    (`utils/url_validator.py`, `services/content/reference_service.py`), ein unbekannter
    Meldegrund und ungültige IDs von Beiträgen und Meldungen
    (`services/moderation_service.py`, `services/usage_tracking_service.py`, Test
    `tests/unit/services/test_ungueltige_id_nicht_im_log.py`). Die Skripte für
    Sicherung und Wiederherstellung von Qdrant (`scripts/backup_qdrant.py`,
    `scripts/restore_qdrant.py`) schreiben mit demselben Formatter. Im BFF schreibt die
    Konsole mit `AusnahmeOhneFehlertextFormatter`
    (`BFF/Logging/`), im Code gesetzt, sodass ein `Logging__Console__FormatterName` von
    außen ihn nicht ersetzt; Fehlerzeilen zu einer Anfrage nennen den Pfad nicht.
    **Altbestand:** Zeilen von vor #422 können Fehlertexte samt Eingabewerten tragen,
    bis sie aus dem `json-file`-Strom rotiert sind (Frist unten).
  - **Frontend-nginx:** schreibt seit #275 das Format `ohne_suchtext`
    (`mvp/frontend/gutgesagt-frontend/nginx.protokoll.conf`, für `nginx.conf` und
    `nginx.docker.conf` gemeinsam) nach stdout: Absenderadresse, Zeitpunkt,
    Methode, Pfad ohne Adresszusatz, Status, Größe und User-Agent, aber keinen Adresszusatz und keinen
    Referrer. Beide trugen den Suchtext: die Adresse bei jedem direkten Aufruf von
    `/result?searchQuery=…`, der Referrer bei jeder Anfrage, die diese Seite auslöst. Für
    die Suche selbst (`/api/v1/search/searchByText`, nur im Dev-Stack über dieses nginx)
    und für jeden direkten Aufruf der Ergebnisseite (`/result`, löst eine Suche aus)
    schreibt es keine Zeile: Ihre genaue Uhrzeit ließe sich, je Tag durchgezählt, mit dem
    Anlagezeitpunkt der Aussage aus derselben Suche verbinden. Ins Fehlerprotokoll
    (stderr, im selben `json-file`-Strom) schreibt es für fehlende Dateien keine Zeile
    (`log_not_found off`); die trug Adresse samt Adresszusatz und Referrer. Seit #422
    schreibt es überhaupt keine Fehlerzeile zu einer Anfrage mehr (`error_log … emerg` im
    http-Block): nginx kennt für Fehlerzeilen kein eigenes Format, und jede trüge Adresse,
    Anfrage samt Adresszusatz und Referrer, etwa im Dev-Stack `connect() failed …`, wenn
    das BFF nicht antwortet. Den Ausgang einer solchen Anfrage zeigt das Zugriffsprotokoll
    mit dem Status (413, 502 …). Zeilen außerhalb einer Anfrage (Start, Konfiguration,
    Worker) schreibt nginx weiter. Belegt mit
    `app/tests/integration/test_webserver_protokoll.py` gegen das Image aus
    `mvp/frontend/gutgesagt-frontend/Dockerfile`. **Altbestand:** Bis #275 stehen
    Suchtexte in Adresse und Referrer im `json-file`-Strom (Frist siehe unten). Hinter dem
    vorgelagerten Reverse Proxy steht dort dessen Adresse, nicht die des Besuchers. Eine
    Kennung steht im Pfad nicht: Die Nutzungsstatistik
    unter „Meine Beiträge“ fragt `/api/v1/usage/users/me/usage-stats`, die Rückmeldung
    beim Anmelden `/api/v1/usage/users/me/besuch` (`usage-tracking.service.ts`), und der
    Suchdienst nimmt die Person aus `X-User` (`api/v1/usage.py`). Das gilt ebenso für
    das Zugriffsprotokoll des vorgelagerten Reverse Proxy. **Altbestand:** Bis #284 stand die Kennung in beiden Protokollen im
    Klartext. Beim vorgelagerten Reverse Proxy verschwinden diese Zeilen mit dessen Frist.
    Das Frontend-nginx schreibt dagegen in den `json-file`-Strom, für den in Produktion
    keine Frist gilt (siehe Fristen unten); dort bleiben die alten Zeilen mit Kennung
    stehen, bis jemand den Strom am Host rotiert oder leert. Bei einer Auskunft oder
    Löschung also am Host nach der Kennung im Pfad `/api/v1/usage/users/` suchen; das
    gilt auch für Aufrufe aus einem noch zwischengespeicherten alten Frontend, die die
    alte Adresse weiter anfragen (Antwort 404).
  - **Vorgelagerter Reverse Proxy:** Sein Format steht nicht im Repo. Seit #275 schicken
    Browser als Referrer nur noch den Ursprung (`<meta name="referrer"
    content="strict-origin">` in `src/index.html`), der Suchtext kommt also nicht mehr
    über den Referrer hinein. **Offen:** Direkte Aufrufe von `/result?searchQuery=…`
    stehen dort weiter mit Suchtext, und je Suche steht eine Zeile
    `POST /api/v1/search/searchByText` mit voller IP und genauer Uhrzeit, die sich mit
    dem Anlagezeitpunkt der Aussage aus derselben Suche verbinden lässt. Abhilfe am Host:
    für diesen Pfad kein Zugriffsprotokoll, sonst ein Format ohne Adresszusatz und
    Referrer, wie im Frontend-nginx.
  - **Fristen:** Im Repo begrenzt nur der Dev-Stack die Größe der `json-file`-Logs
    (`mvp/docker-compose.dev.yml`, 20 MB × 3) — eine Größe, keine Frist. Die
    Produktionskonfiguration liegt nicht im Repo.
    - **Ziel (#422): höchstens 14 Tage** für alles im `json-file`-Strom (Anwendung,
      Frontend-nginx) und für die Protokolle des vorgelagerten Reverse Proxy. Der
      `json-file`-Treiber rotiert nur nach Größe; im Betrieb ist dafür eine Grenze von
      10 MB × 3 Dateien je Container vorgesehen, vorläufig, bis das Wachstum je Tag
      gemessen ist. Die Grenze hält die Frist nur, solange drei Dateien höchstens
      14 Tage Protokoll fassen; wächst ein Container langsamer, bleiben seine Zeilen
      länger stehen. **Noch nicht ausgerollt** (Stand 30.10.2026); bis dahin gilt der
      Stand darunter, und die Datenschutzerklärung nennt noch keine Frist
      (`docs/rechtstexte-luecken/pruefliste/P7.md`). Im Repo nicht belegbar, deshalb nur als
    Stand der Bestandsaufnahme (`docs/archiv/DATENSCHUTZ_BESTANDSAUFNAHME.md`, 1.10.4):
    - **Stand 04.09.2026, vom Maintainer am Host geprüft:** Die Zugriffsprotokolle des
      vorgelagerten Reverse Proxy, die als einzige die volle Client-IP enthalten, löscht
      `logrotate` nach 14 Tagen.
    - **Undatierte Auskunft des Maintainers, vor dem 04.09.2026:** Alles aus dem
      `json-file`-Treiber ist in Produktion unbegrenzt.

    Beides vor einer Auskunft am Host nachprüfen.

## Kommandos

Schritt 1 und 2 stehen als Skript in `mvp/scripts/manual/person_loeschen.sql`, getestet
gegen PostgreSQL in `tests/integration/test_loeschkommando.py`. Auf den Hosts liegt kein
Repo-Checkout; das Skript wird wie die anderen in `mvp/scripts/manual/` heruntergeladen.
Die Variable heißt `KENNUNG`, nicht `UID`: `UID` ist in bash schreibgeschützt.

```bash
KENNUNG=a1b2c3d4-0000-0000-0000-000000000000
curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/contentgruen/main/mvp/scripts/manual/person_loeschen.sql
docker exec -i gutgesagt-app-postgres psql -U app_user -d gutgesagt_app \
  -v ON_ERROR_STOP=1 -v uid="$KENNUNG" < person_loeschen.sql   # Ausgabe protokollieren
# Nur auf unmigriertem Schema (Spalte user_id vorhanden):
# echo "DELETE FROM search_events WHERE user_id = :'uid';" | \
#   docker exec -i gutgesagt-app-postgres psql -U app_user -d gutgesagt_app \
#   -v ON_ERROR_STOP=1 -v uid="$KENNUNG"

docker exec -i gutgesagt-app-postgres psql -U app_user -d gutgesagt_app -c \
  "VACUUM FULL votes, content_reports, raw_inputs, raw_input_content_links, raw_input_drafts, usage_events, users, gesehene_nutzung;"
```

```bash
# Schritt 3: Beitraege anonymisieren. Vor jeder Einzelfall-Loeschung.
curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/contentgruen/main/mvp/scripts/manual/beitraege_anonymisieren.py
docker exec -i gutgesagt-semantic-search python - "$KENNUNG" \
  < beitraege_anonymisieren.py                # zeigt nur, aendert nichts
docker exec -i gutgesagt-semantic-search python - "$KENNUNG" --ausfuehren \
  < beitraege_anonymisieren.py                # Ausgabe protokollieren
```

Anders als `person_loeschen.sql` trägt das Skript die Logik nicht selbst: Es kommt von
`main`, importiert sie aber aus dem laufenden Container. Ein Image ohne #236 bricht mit
`ModuleNotFoundError` ab, bevor es etwas schreibt; dann erst das neue Image ausrollen.

Bis #236 hieß der Platzhalter in Qdrant `geloeschter-nutzer`, und die Karten zeigten
dazu „Mitglied“. Bestand mit dem alten Wert stellt derselbe Lauf einmalig um: statt
`"$KENNUNG"` die Kennung `geloeschter-nutzer` übergeben. Er ist wiederholbar; ein
Lauf ohne Treffer zeigt, dass nichts mehr umzustellen ist.

Danach die ausgegebenen Texte durchsehen. Macht ein Text die Person erkennbar, wird
dieser Punkt einzeln über `DELETE /api/v1/moderation/content/{content_type}/{id}` gelöscht — nicht
direkt gegen Qdrant: nur der Endpunkt räumt verwaiste Antwortvorschläge auf
(`repositories/implementations/qdrant/moderation_repository.py`, `aus_aussagen_entfernen`),
für jeden Beitragstyp, und schreibt einen Moderationsvermerk. Scheitert das Aufräumen,
antwortet der Endpunkt mit 500 und lässt den Punkt stehen; den Aufruf dann wiederholen.
Bricht das Aufräumen mitten im Lauf ab, sind manche Aussagen schon ohne Verweis auf den
stehengebliebenen Punkt; erst der wiederholte Aufruf macht das Bild wieder stimmig
(`services/content/verweise_entfernen.py`).
