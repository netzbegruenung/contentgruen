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
Claim `sub`, ersatzweise `NameIdentifier` (`BFF/Program.cs:647`, `ClaimUtilities.GetUserId`,
aufgerufen in `BFF/Proxy/IdentityHeaderTransform.cs:79`).
Mit Keycloak ist das die Keycloak-UUID, mit `USE_KEYCLOAK=false` (dev/tst) die
`userId` aus `managed-users.json` (`user-001`). **Vorher prüfen, welche Form die
Umgebung benutzt** — die Kommandos sind identisch, nur der eingesetzte Wert nicht.

## Zwei Wege, einen Beitrag zu löschen

- **Der Autor löscht** (`DELETE /api/v1/content/{id}`, „Beitrag löschen“ in „Meine
  Beiträge“): Der Beitrag bekommt nur den Zustand „gelöscht“
  (`services/content/beitrag_loeschen_service.py`). Er verschwindet aus Suche, Ansicht,
  Listen, Bestandszählern und „Meine Beiträge“, bleibt aber gespeichert, damit Verknüpfungen und
  Stimmen nicht ins Leere zeigen. Das ist **kein Löschen im Sinne von Art. 17**: Text und
  Kennung stehen weiter in Qdrant. Ein Löschantrag erfasst gelöschte Beiträge deshalb
  genauso wie sichtbare und gesperrte; der Lauf in Schritt 3 filtert nur nach der Kennung,
  nicht nach dem Zustand.
- **Ein Admin entfernt endgültig**
  (`DELETE /api/v1/moderation/content/{content_type}/{id}`): Der Punkt ist danach aus
  Qdrant weg. Das ist der Weg für Schritt 3, wenn ein Text die Person erkennbar macht,
  und sonst für nichts: Gemeldete Beiträge sperrt ein Admin, statt sie zu entfernen.

## Ablauf

1. **Sitzungskennung sichern.** `content_reports` ist die einzige Zeile im System,
   die `reported_by_user_id` und `reported_by_session_id` nebeneinander führt
   (`api/v1/moderation.py:169-174`). Nur über sie sind die `usage_events` einer Person
   erreichbar.
2. **PostgreSQL.** `usage_events` (über die Sitzungen aus Schritt 1), `votes` und
   `content_reports` löschen (ein von der Person gemeldeter, inzwischen gesperrter
   Beitrag bleibt über die Moderationsansicht „Gesperrt“ erreichbar);
   `reviewed_by` und `raw_input_content_links.created_by`
   auf `NULL` setzen statt löschen — die Zeilen gehören inhaltlich anderen;
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
   `mvp/config/managed-users.json` entfernen und das BFF neu starten (Cache 5 min,
   `BFF/Services/ManagedUserService.cs:14`). Die Datei ist **nicht mehr eingecheckt**
   (`.gitignore:19`); getrackt ist nur `managed-users.example.json`. Was bis zur Umbenennung
   in `b993b0c4` darin stand, bleibt in der Git-Historie
   (`git log --follow -- mvp/config/managed-users.example.json`).
   Die Platzhalter sind als `userId` gesperrt: Einen Beta-Zugang mit `ehemalige-person`
   oder `ehemalige-person-…` lässt das BFF nicht zu und protokolliert einen Fehler
   (`BFF/Services/ManagedUserService.cs:110`).

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
  ein gelöschtes Konto bleibt bis zum Ablauf des Cookies angemeldet. Das Cookie läuft
  **gleitend**: 14 Tage ab der letzten Nutzung (`BFF/Program.cs:92-93`, `ExpireTimeSpan`
  und `SlidingExpiration`, für den Beta-Zugang `:149-150`), und das BFF prüft das Konto bei
  späteren Anfragen nicht mehr. Wer weiter Gut gesagt benutzt, bleibt also ohne Ende
  angemeldet und kann neue Sätze, Stimmen, Einwürfe und Beiträge anlegen. Das Kommando für
  Schritt 1 und 2 und den Lauf für Schritt 3 deshalb nach 14 Tagen noch einmal laufen
  lassen, danach auch das `VACUUM FULL`; beide sind wiederholbar. Findet der zweite Lauf
  noch Zeilen, war die Person in der Zwischenzeit aktiv: nach weiteren 14 Tagen
  wiederholen, bis ein Lauf leer bleibt.
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
  **Offen:** Die fortlaufende `id` verrät weiter die Reihenfolge der Suchen eines Tages.
  An ruhigen Tagen lässt sie sich mit der Reihenfolge der Aussagen aus Suchen abgleichen.
  **Frist:** Suchereignisse bleiben 90 Tage als Einzelzeilen
  (`SEMANTIC_SEARCH_SEARCH_EVENT_RETENTION_DAYS`, `core/config.py`, nicht unter 90:
  `GET /metrics/searches-per-user` wertet bis zu 90 Tage Einzelzeilen aus). Ältere Tage
  verdichtet der tägliche Bereinigungsjob (`services/cleanup/usage_cleanup_service.py`,
  derselbe wie für die Nutzungsereignisse) zu einem Tageszähler und löscht die
  Einzelzeilen samt Pseudonym und `id` (#289). Der Job läuft nur mit
  `SEMANTIC_SEARCH_ENABLE_USAGE_CLEANUP=true` (Standard); abgeschaltet gilt auch diese
  Frist nicht. Physisch verschwinden die gelöschten Zeilen erst, wenn PostgreSQL den
  Platz wiederverwendet (Autovacuum); in Backups stehen sie bis zu 28 Tage weiter.
- **`suchen_je_tag`** (Tageszähler der Suchen) trägt je UTC-Tag nur die Zahl der Suchen
  und die Zahl der Personen (verschiedene Tagespseudonyme), kein Pseudonym: nichts, was
  sich einer Person zuordnen ließe. Keine Frist.
- **`suchen_ohne_treffer`** trägt nur Aussage-ID, Montag der Woche, Anzahl der Suchen
  und Anzahl der Personen, weder Kennung noch Pseudonym: nichts, was sich einer Person
  zuordnen ließe. Welche Tagespseudonyme (dieselben wie in `search_events`) eine Aussage
  heute schon gezählt haben, liegt nur im Arbeitsspeicher (als SHA-256-Prüfwert) und wird
  um Mitternacht (UTC) verworfen. Wochen älter als acht löscht ein täglicher Task von
  selbst (`services/suchen_ohne_treffer_service.py`, `loeschen_im_takt`).
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
    (`BFF/Proxy/IdentityHeaderTransform.cs`). Warn- und Fehlerzeilen nennen den Pfad
    unverändert; seit #284 trägt kein Pfad, den das Frontend aufruft, eine Kennung (die
    Nutzungsstatistik unter „Meine Beiträge“ heißt `/api/v1/usage/users/me/usage-stats`,
    die Person kommt aus der Anmeldung). Unabhängig davon sind die Zeilen unterdrückt, in
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
  - **Nicht abgedeckt:** Fehlerzeilen geben die Meldung der Ausnahme mit aus
    (`logger.error(f"...: {e}", exc_info=True)`). Enthält eine Ausnahme Eingabewerte, etwa
    eine Validierungsmeldung, stehen diese mit darin.
  - **Frontend-nginx:** setzt weder `access_log` noch `log_format` noch `real_ip`
    (`mvp/frontend/gutgesagt-frontend/nginx*.conf`), schreibt also das Standardformat
    des Basis-Images `nginx:alpine` nach stdout
    (`mvp/frontend/gutgesagt-frontend/Dockerfile:31`). Hinter dem vorgelagerten Reverse
    Proxy steht dort dessen Adresse, nicht die des Besuchers; Zeitpunkt, Pfad, Referrer
    und User-Agent stehen darin. Eine Kennung steht im Pfad nicht: Die Nutzungsstatistik
    unter „Meine Beiträge“ fragt `/api/v1/usage/users/me/usage-stats`
    (`usage-tracking.service.ts`), und der Suchdienst nimmt die Person aus `X-User`
    (`api/v1/usage.py`). Das gilt ebenso für das Zugriffsprotokoll des vorgelagerten
    Reverse Proxy. **Altbestand:** Bis #284 stand die Kennung in beiden Protokollen im
    Klartext. Beim vorgelagerten Reverse Proxy verschwinden diese Zeilen mit dessen Frist.
    Das Frontend-nginx schreibt dagegen in den `json-file`-Strom, für den in Produktion
    keine Frist gilt (siehe Fristen unten); dort bleiben die alten Zeilen mit Kennung
    stehen, bis jemand den Strom am Host rotiert oder leert. Bei einer Auskunft oder
    Löschung also am Host nach der Kennung im Pfad `/api/v1/usage/users/` suchen; das
    gilt auch für Aufrufe aus einem noch zwischengespeicherten alten Frontend, die die
    alte Adresse weiter anfragen (Antwort 404).
  - **Fristen:** Im Repo begrenzt nur der Dev-Stack die Größe der `json-file`-Logs
    (`mvp/docker-compose.dev.yml`, 20 MB × 3) — eine Größe, keine Frist. Die
    Produktionskonfiguration liegt nicht im Repo. Im Repo nicht belegbar, deshalb nur als
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
(`repositories/implementations/qdrant/moderation_repository.py:91`, `aus_aussagen_entfernen`)
und schreibt einen Moderationsvermerk.
