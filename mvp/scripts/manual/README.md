# Manual scripts

Ad-hoc scripts for checking or maintaining a **running** deployment by hand. Some of them
write (marked below). They are not part of the automated test suite and are not
collected by pytest — the suite lives in `mvp/backend/semantic-search-service/app/tests/`.

Start the services first (`mvp/run-local.sh` or `mvp/run-docker.sh`), then:

```bash
python mvp/scripts/manual/check_anonymous_access.py
```

Die frueheren `check_similarity_api.py`, `check_polarity_api.py` und
`check_keyword_overlap_api.py` sind entfallen: sie haengten am Debug-Router
`/api/v1/test`, der unauthentifiziert erreichbar war und deshalb entfernt wurde
(`/headers` gab eingehende Header inklusive Auth-Cookie aus, die
Embedding-Endpunkte rechneten ungedrosselt auf beliebigem Eingabetext).
Die dahinterliegende Logik ist ueber die Unit-Tests abgedeckt:
`tests/unit/utils/test_negation_detector.py`, `test_german_stemmer.py` und
`tests/unit/api/test_search_ranking.py`.

The check scripts require `requests` and target `http://localhost:8000` (semantic search) or
`http://localhost:5054` (BFF).

## Einwuerfe importieren (gegen das BFF)

`einwuerfe_importieren.py <liste> --email <konto> [--adresse <url>] [--trockenlauf]` –
**schreibend ohne `--trockenlauf`.** Legt Einwuerfe aus einer CSV- oder Markdown-Liste
in den Fangkorb und ueberspringt Zeilen, deren Link schon im Fangkorb liegt. Nur
Standardbibliothek, laeuft von jedem Rechner mit Python 3. Aufruf, Dateiformat und
Exit-Codes in `mvp/SCRIPTS.md`; Beispiellisten `einwuerfe_beispiel.csv` und
`einwuerfe_beispiel.md`.

## Bestand in Qdrant (im semantic-search-Container)

Diese beiden Skripte laufen nicht gegen die HTTP-API, sondern per stdin im
semantic-search-Container, mit dessen Qdrant-Umgebung:

- `bestand_pruefen.py` – **nur lesend**. Zaehlt Punkte je Typ und Herkunft,
  Kommentare/Hintergrundinfos ohne verknuepfende Aussage, normalisiert gleiche
  Aussagen, Stand des Felds `text_normalisiert`; mit `--praefix N` zusaetzlich eine
  Stichprobe, mit welchem E5-Praefix die Vektoren eingebettet sind. Gibt nur Zaehler
  aus, keine Texte, IDs oder Autoren.
- `text_normalisiert_nachtragen.py` – traegt das Payload-Feld `text_normalisiert`
  fuer Aussagen, Kommentare und Hintergrundinfos nach (exakter Abgleich der
  Dublettenpruefung) und legt den Keyword-Index an. Ohne `--ausfuehren` wird nur gezaehlt; idempotent. Erst nach
  dem Ausrollen der Version laufen lassen, die das Feld schreibt, und erneut nach
  jeder Version, die einen weiteren Typ aufnimmt (zuletzt Hintergrundinfos, #301):
  Bis dahin findet die Pruefung aeltere Beitraege dieses Typs nur ueber die
  Einbettung, eine nur klein geschriebene Kopie also nicht.

Auf Test/Prod liegt kein Repo-Checkout; die Skripte werden heruntergeladen:

```bash
curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/contentgruen/main/mvp/scripts/manual/bestand_pruefen.py
docker exec -i gutgesagt-semantic-search python - < bestand_pruefen.py

curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/contentgruen/main/mvp/scripts/manual/text_normalisiert_nachtragen.py
docker exec -i gutgesagt-semantic-search python - < text_normalisiert_nachtragen.py
docker exec -i gutgesagt-semantic-search python - --ausfuehren < text_normalisiert_nachtragen.py
```

`bestand_pruefen.py` nutzt nur qdrant_client und die Standardbibliothek und laeuft
auch gegen aeltere Versionen; `text_normalisiert_nachtragen.py` braucht den
ausgerollten neuen Stand.

## Vektor benennen (im semantic-search-Container)

`vektor_benennen.py [--ausfuehren]` – **schreibend mit `--ausfuehren`.** Einmalig mit
#395: fuehrt den unbenannten Vektor der Collection als benannten Vektor `e5_base`.
Kopiert alle Punkte samt Vektoren und Payload-Indizes in die neue Collection
`<collection>_e5_base`, loescht die alte und macht ihren Namen zum Alias auf die neue.
Nichts wird neu eingebettet, die Treffer bleiben gleich. Ohne `--ausfuehren` zaehlt es
nur; ein zweiter Lauf meldet `"vorher": "benannt"` und aendert nichts. Aendert sich die
Zahl der Punkte waehrend der Kopie, bricht es ab, ohne umzustellen. Nach dem Rueckweg
(Restore ueber den Alias) kopiert ein neuer Lauf nach `<collection>_e5_base_2` und setzt
den Alias in einem Schritt um.

Reihenfolge, Backup und Rueckweg stehen in `docs/DEPLOYMENT.md`, „Qdrant: named vector
(#395)“. Kurz: Backup, Version mit #395 ausrollen, zaehlen, umstellen und gleich danach
(nicht waehrend des Laufs) den Dienst neu starten; bis dahin schlagen Suchen und
Schreiben fehl.

```bash
curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/contentgruen/main/mvp/scripts/manual/vektor_benennen.py
docker exec -i gutgesagt-semantic-search python - < vektor_benennen.py
docker exec -i gutgesagt-semantic-search python - --ausfuehren < vektor_benennen.py
docker restart gutgesagt-semantic-search
```

Getestet in `tests/unit/services/test_vektor_benennen.py` (Speicher-Modus, Aufruf) und
`tests/integration/test_vektor_benennen_qdrant.py` (echter Qdrant; der Dienst sucht vor
und nach der Umstellung gleich). Ist die Umstellung auf Test und Produktion gelaufen,
entfaellt der Uebergang fuer den unbenannten Vektor im Dienst
(`QdrantEmbeddingsManager._vektorname_aus`).

## Zustaende umstellen (im semantic-search-Container)

`zustaende_umstellen.py [--ausfuehren]` – **schreibend mit `--ausfuehren`.** Einmalig
mit #214: stellt den Status aller Punkte auf die Zustaende sichtbar, gesperrt,
geloescht um (auch `status_vor_sperre` gesperrter Beitraege) und entfernt das Feld
`visibility`. Bisher auffindbare Status (`released_internal`, `approved`, `draft`,
`archived`, `duplicate` u. a., auch Punkte ohne Status) und `pending_review` werden
`visible`; `blocked` und die Bild-Vorstufen bleiben. Unbekannte Werte bleiben stehen,
auch in `status_vor_sperre`, werden gemeldet und das Skript endet mit Exit 1.
Idempotent.

Reihenfolge:

1. Backup ziehen (`mvp/scripts/backup/backup.sh`, enthaelt den Qdrant-Snapshot).
2. Die Version mit den neuen Zustaenden ausrollen. Bis Schritt 4 liest sie Altwerte
   als sichtbar und die Suche findet, was sie vorher fand (Uebergang in
   `domain/models/content_status.py`); gesperrte Beitraege bleiben ausgeblendet.
3. Ohne `--ausfuehren` laufen lassen und die Zaehler pruefen. Vorher ansehen, was
   mit mehr als 0 dasteht bei
   - `pending_review`: heute in der Suche ausgeblendet, wird sichtbar;
   - `rejected`, `archived`, `duplicate`: heute schon in der Suche, aber nicht in der
     Dublettenpruefung und nicht in „Suchen ohne Treffer“; werden voll sichtbar.
     Zwischen Ausrollen und Umstellung zaehlt „Suchen ohne Treffer“ diese Aussagen
     bereits mit (das Modell liest sie als sichtbar).
4. Mit `--ausfuehren` laufen lassen; ein zweiter Lauf meldet `umzustellen: 0`. Die
   Umstellung schreibt nur Punkte, deren Status sich seit dem Lesen nicht geaendert
   hat; was ein Admin waehrend des Laufs sperrt oder entsperrt, bleibt stehen. Meldet
   der zweite Lauf noch etwas, ihn mit `--ausfuehren` wiederholen.

```bash
curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/contentgruen/main/mvp/scripts/manual/zustaende_umstellen.py
docker exec -i gutgesagt-semantic-search python - < zustaende_umstellen.py
docker exec -i gutgesagt-semantic-search python - --ausfuehren < zustaende_umstellen.py
```

Getestet in `tests/unit/services/test_zustaende_umstellen.py` (Logik),
`test_zustaende_umstellen_skript.py` (Aufruf) und `tests/integration/test_zustaende.py`
(echter Qdrant, vor und nach der Umstellung). Ist die Umstellung auf Test und
Produktion gelaufen, entfaellt der Uebergang im Modell. Das fruehere Einmal-Skript
`promote_pending_review_content.py` ist entfallen: Es setzte `released_internal`, einen
Status, den es nicht mehr gibt.

## Loeschkommando (im PostgreSQL-Container)

`person_loeschen.sql` – **schreibend.** Der PostgreSQL-Teil des Loeschkonzepts
(Schritt 1 und 2): loescht, was an der Kennung einer Person haengt, und ersetzt ihre
Kennung an Saetzen in fremden Einwuerfen durch einen Platzhalter mit dem Anzeigenamen
„ehemalige Person“. Ablauf, Reihenfolge und Fallen stehen in `docs/LOESCHKONZEPT.md`;
dort steht auch der Aufruf. Getestet in `tests/integration/test_loeschkommando.py`.

## Kennungen auf den Realm umstellen (im semantic-search-Container)

`kennungen_umstellen.py [--ausfuehren] [--konten-anlegen DATEI] [--liste NAME=K1,K2] [--loeschliste K1,K2]` –
**schreibend mit `--ausfuehren`.** Einmalig vor dem Umstellen der BFF auf den Realm
„gutgesagt“ (#487): schreibt die Kennungen von Mitgliedern der Netzbegruenung in
PostgreSQL und Qdrant auf die ihres Kontos im Realm um, gibt die neuen Werte der
Admin-Listen aus und ergaenzt die Loeschliste; ohne `--ausfuehren` zaehlt es nur. Ablauf und
Aufruf in `docs/KEYCLOAK_REALM.md`, „Kennungen umstellen“; getestet in
`tests/unit/services/test_kennungen_umstellen.py` (Qdrant),
`tests/unit/infrastructure/test_keycloak_kennungen.py` (Realm),
`tests/integration/test_kennungen_umstellen_postgres.py` (PostgreSQL, Ablauf) und
`test_kennungen_umstellen_skript.py` (Aufruf).

## Beitraege anonymisieren (im semantic-search-Container)

`beitraege_anonymisieren.py <kennung> [--ausfuehren]` – **schreibend mit
`--ausfuehren`.** Schritt 3 des Loeschkonzepts: ersetzt die Kennung an Beitraegen in
Qdrant durch den Platzhalter `ehemalige-person` (Anzeige „ehemalige Person“) und
listet die Treffer fuer die Einzelfallpruefung. Mit der Kennung `geloeschter-nutzer`
stellt es einmalig den Bestand mit dem alten Platzhalter um. Aufruf in
`docs/LOESCHKONZEPT.md`; getestet in `tests/unit/services/test_beitraege_anonymisieren.py`
(Speicher-Modus), `test_beitraege_anonymisieren_skript.py` (Aufruf) und
`tests/integration/test_beitraege_anonymisieren_qdrant.py` (echter Qdrant).
