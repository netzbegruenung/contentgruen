# Löschkonzept (Art. 17 DSGVO)

> **Vorsorge, keine erprobte Prozedur.** Es gibt heute keine Nutzer und keine
> erhaltenswerten Daten. Die Anlage hat keinen Codepfad, der eine Person löscht;
> was hier steht, sind Handkommandos gegen PostgreSQL und Qdrant. Sie sind aus dem
> Code hergeleitet und gegen ein leeres Dev-System gelesen, aber **nie an echten
> Daten gelaufen**. Wer sie zum ersten Mal ausführt, macht vorher ein Backup und
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
   `content_reports` löschen; `reviewed_by` und `raw_input_content_links.created_by`
   auf `NULL` setzen statt löschen — die Zeilen gehören inhaltlich anderen;
   `raw_inputs` der Person löschen (CASCADE räumt deren Links mit ab).
3. **Qdrant.** Beiträge werden **anonymisiert, nicht gelöscht.** `original_author`,
   `last_modified_by`, `authors[].name` und `edit_history[].editor` bekommen den Wert
   `geloeschter-nutzer`. Damit bleiben Antwortvorschläge, Referenzen und
   Nutzungszähler intakt und der Personenbezug ist trotzdem weg. **Gelöscht wird nur,
   wo der Text selbst die Person erkennbar macht** — das ist eine Einzelfallprüfung,
   kein Filterlauf.
4. **Konto.** Keycloak-Konto im Realm löschen, bzw. Eintrag aus
   `mvp/config/managed-users.json` entfernen und das BFF neu starten (Cache 5 min).
   Die Datei ist seit PR #29 **nicht mehr eingecheckt** (`.gitignore:19`); getrackt ist nur
   `managed-users.example.json`. Die Adresse bleibt trotzdem in der Git-Historie, weil die
   Datei dort bis PR #29 lag.

## Drei Fallen

- **Sitzungskennung vor `content_reports`.** Wird Schritt 2 vor Schritt 1 ausgeführt,
  ist der einzige Weg von der UUID zu den `usage_events` dauerhaft weg. Findet
  Schritt 1 nichts, sind die Ereignisse dieser Person nicht bestimmbar — das gehört
  so ins Protokoll, es ist kein Fehler des Laufs.
- **Anonymisieren vor Löschen.** Erst der Payload-Lauf über alle vier Felder, dann
  die Einzelfall-Löschungen. Andersherum fehlen die gelöschten Punkte im
  Anonymisierungslauf, und ein Punkt mit fremden Mitautoren wäre schon weg.
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
- **Backups** unter `/opt/contentgruen-backups` halten 7 Tages- und 4 Wochenstände,
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
  nicht vorgesehen. Einordnung und Belege: `docs/DATENSCHUTZ_BESTANDSAUFNAHME.md`, 1.10.

## Kommandos

```bash
UID=a1b2c3d4-0000-0000-0000-000000000000
docker exec -i contentgruen-app-postgres psql -U app_user -d contentgruen_app <<SQL
\set uid '$UID'

-- Schritt 1: Sitzungskennungen sichern. VOR jedem DELETE.
CREATE TEMP TABLE loeschung_sessions AS
SELECT DISTINCT reported_by_session_id AS session_id FROM content_reports
WHERE reported_by_user_id = :'uid' AND reported_by_session_id IS NOT NULL;
SELECT * FROM loeschung_sessions;   -- protokollieren

-- Schritt 2
BEGIN;
DELETE FROM usage_events WHERE session_id IN (SELECT session_id FROM loeschung_sessions);
DELETE FROM votes            WHERE user_id             = :'uid';
DELETE FROM content_reports  WHERE reported_by_user_id = :'uid';
UPDATE content_reports         SET reviewed_by = NULL WHERE reviewed_by = :'uid';
UPDATE raw_input_content_links SET created_by  = NULL WHERE created_by  = :'uid';
DELETE FROM raw_inputs       WHERE submitted_by        = :'uid';
-- Nur auf unmigriertem Schema (Spalte user_id vorhanden):
-- DELETE FROM search_events WHERE user_id = :'uid';
COMMIT;
SQL

docker exec -i contentgruen-app-postgres psql -U app_user -d contentgruen_app -c \
  "VACUUM FULL votes, content_reports, raw_inputs, raw_input_content_links, usage_events;"
```

```bash
# Schritt 3: Beitraege anonymisieren. Vor jeder Einzelfall-Loeschung.
python3 - "$UID" <<'EOF'
import json, sys, urllib.request
Q, UID, ERSATZ = "http://localhost:6333/collections/content_collection/points", sys.argv[1], "geloeschter-nutzer"

def post(pfad, body):
    r = urllib.request.Request(Q + pfad, data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r))["result"]

filt = {"should": [{"key": k, "match": {"value": UID}} for k in
        ("original_author", "last_modified_by", "authors[].name", "edit_history[].editor")]}

off, n = None, 0
while True:
    body = {"limit": 256, "with_payload": True, "with_vector": False, "filter": filt}
    if off: body["offset"] = off
    r = post("/scroll", body)
    for p in r["points"]:
        pl, neu = p["payload"], {}
        for feld in ("original_author", "last_modified_by"):
            if pl.get(feld) == UID: neu[feld] = ERSATZ
        for feld, schluessel in (("authors", "name"), ("edit_history", "editor")):
            eintraege = pl.get(feld) or []
            if any(e.get(schluessel) == UID for e in eintraege):
                neu[feld] = [{**e, schluessel: ERSATZ} if e.get(schluessel) == UID else e
                             for e in eintraege]
        if neu:
            post("/payload", {"payload": neu, "points": [p["id"]], "wait": True})
            n += 1
            print(p["id"], pl.get("content_type"), repr(pl.get("text"))[:80])
    off = r.get("next_page_offset")
    if not off: break
print("anonymisiert:", n)
EOF
```

Danach die ausgegebenen Texte durchsehen. Macht ein Text die Person erkennbar, wird
dieser Punkt einzeln über `DELETE /api/v1/moderation/content/{id}` gelöscht — nicht
direkt gegen Qdrant: nur der Endpunkt räumt verwaiste Antwortvorschläge auf
(`services/moderation_service.py:186`) und schreibt einen Moderationsvermerk.
