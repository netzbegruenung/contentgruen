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
Claim `sub`, ersatzweise `NameIdentifier` (`Program.cs:617`, `IdentityHeaderTransform.cs:50`).
Mit Keycloak ist das die Keycloak-UUID, mit `USE_KEYCLOAK=false` (dev/tst) die
`userId` aus `managed-users.json` (`user-001`). **Vorher prüfen, welche Form die
Umgebung benutzt** — die Kommandos sind identisch, nur der eingesetzte Wert nicht.

## Ablauf

1. **Sitzungskennung sichern.** `content_reports` ist die einzige Zeile im System,
   die `reported_by_user_id` und `reported_by_session_id` nebeneinander führt
   (`api/v1/moderation.py:114`). Nur über sie sind die `usage_events` einer Person
   erreichbar.
2. **PostgreSQL.** `usage_events` (über die Sitzungen aus Schritt 1), `votes` und
   `content_reports` löschen (ein von der Person gemeldeter, inzwischen gesperrter
   Beitrag bleibt über die Moderationsansicht „Gesperrt“ erreichbar);
   `reviewed_by` und `raw_input_content_links.created_by`
   auf `NULL` setzen statt löschen — die Zeilen gehören inhaltlich anderen;
   `raw_inputs` der Person löschen (CASCADE räumt deren Links und die Sätze daran mit
   ab); in **Sätzen an fremden Einwürfen** (`raw_input_drafts`) und in
   `raw_inputs.destilled_by` die Kennung ersetzen (unten); die Zeile in
   `users` (Anzeigename) löschen. Der Anzeigename steht **nur dort** — weder in Qdrant
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
   `mvp/config/managed-users.json` entfernen und das BFF neu starten (Cache 5 min).
   Die Datei ist seit PR #29 **nicht mehr eingecheckt** (`.gitignore:19`); getrackt ist nur
   `managed-users.example.json`. Die Adresse bleibt trotzdem in der Git-Historie, weil die
   Datei dort bis PR #29 lag.

## Vier Fallen

- **Sitzungskennung vor `content_reports`.** Wird Schritt 2 vor Schritt 1 ausgeführt,
  ist der einzige Weg von der UUID zu den `usage_events` dauerhaft weg. Findet
  Schritt 1 nichts, sind die Ereignisse dieser Person nicht bestimmbar — das gehört
  so ins Protokoll, es ist kein Fehler des Laufs.
- **Anonymisieren vor Löschen.** Erst der Payload-Lauf über alle vier Felder, dann
  die Einzelfall-Löschungen. Andersherum fehlen die gelöschten Punkte im
  Anonymisierungslauf, und ein Punkt mit fremden Mitautoren wäre schon weg.
- **Der Anzeigename kommt mit der nächsten Anfrage zurück.** Der Semantic-Service legt
  ihn aus dem Header `X-User-Display-Name` an, sobald er ihn nicht im Prozess-Cache hat
  (`services/anzeigename_service.py`). Solange das Anmelde-Cookie der Person gilt, entsteht
  die Zeile in `users` nach einem Neustart des Dienstes wieder — auch nach Schritt 4, denn
  ein in Keycloak gelöschtes Konto bleibt bis zum Ablauf des Cookies angemeldet (bis zu
  14 Tage, `Program.cs`, Kommentar zur Cookie-Lebensdauer). In der Zeit kann sie auch
  neue Sätze, Stimmen, Einwürfe und Beiträge anlegen. Das Kommando für Schritt 1 und 2
  und den Lauf für Schritt 3 deshalb nach 14 Tagen noch einmal laufen lassen, danach
  auch das `VACUUM FULL`; beide sind wiederholbar.
- **`VACUUM FULL` danach.** `DELETE` markiert in PostgreSQL nur; die alten Kennungen
  stehen bis zum Table-Rewrite physisch auf der Platte.

## Was nicht gelöscht wird

- **`search_events`** trägt seit PR #14 nur `actor_hash`, ein täglich rotierendes
  HMAC-SHA256 über Kennung + UTC-Datum (`services/search_tracking_service.py:33`).
  Ohne Geheimnis nicht umkehrbar, mit Geheimnis nur tageweise nachrechenbar: Löschen
  auf Antrag ist unmöglich und mangels Personenbezug auch nicht geschuldet.
  **Vorher prüfen, ob die Zielumgebung migriert ist** — auf einem Stand ohne
  `actor_hash` stehen dort Klartext-Suchtext, Kennung und IP-Hash, und dann ist
  `DELETE FROM search_events WHERE user_id = …` sehr wohl nötig
  (`mvp/backend/postgres-app/migrations/2026-08-19-search-events-pseudonymisieren.sql`).
- **`suchen_ohne_treffer`** trägt nur Aussage-ID, Montag der Woche, Anzahl der Suchen
  und Anzahl der Personen, weder Kennung noch Pseudonym: nichts, was sich einer Person
  zuordnen ließe. Welche Tagespseudonyme eine Aussage heute schon gezählt haben, liegt nur
  im Arbeitsspeicher (als SHA-256-Prüfwert) und wird um Mitternacht (UTC) verworfen.
  Wochen älter als acht löscht ein täglicher Task von selbst
  (`services/suchen_ohne_treffer_service.py`, `loeschen_im_takt`).
- **Backups** unter `/opt/gutgesagt-backups` halten 7 Tages- und 4 Wochenstände,
  gelöschte Daten leben dort bis zu 28 Tage weiter. Selektives Editieren von
  `pg_dump`-Archiven und Qdrant-Snapshots ist nicht praktikabel: nach jedem
  `restore.sh` ist der Löschlauf zu wiederholen.
- **Logs.** Der Inhalt ist seit PR #29 kleiner, als hier früher stand: **E-Mail-Adressen
  stehen nicht mehr im Log**, Suchtexte seit dem Nachtrag vom 08.09.2026 auch nicht mehr im
  Fehlerzweig, und Nutzerkennungen erscheinen nur noch als achtstelliges Pseudonym
  (`app/core/logging.py`, `log_pseudonym()`). Was bleibt: dieses Pseudonym in den
  Anwendungszeilen und die vollen Client-IPs in den Zugriffsprotokollen des vorgelagerten
  Reverse Proxy. Für Letztere gilt eine Frist — `logrotate` auf dem Prod-Host, 14 Tage;
  alles aus dem `json-file`-Treiber ist unbegrenzt. Einzelne Zeilen daraus zu entfernen ist
  nicht vorgesehen. Einordnung und Belege: `docs/archiv/DATENSCHUTZ_BESTANDSAUFNAHME.md`, 1.10.

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
  "VACUUM FULL votes, content_reports, raw_inputs, raw_input_content_links, raw_input_drafts, usage_events, users;"
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
dieser Punkt einzeln über `DELETE /api/v1/moderation/content/{id}` gelöscht — nicht
direkt gegen Qdrant: nur der Endpunkt räumt verwaiste Antwortvorschläge auf
(`services/moderation_service.py:186`) und schreibt einen Moderationsvermerk.
