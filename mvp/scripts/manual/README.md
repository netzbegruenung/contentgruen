# Manual verification scripts

Ad-hoc scripts for checking a **running** deployment by hand. They are not part of the
automated test suite and are not collected by pytest — the suite lives in
`mvp/backend/semantic-search-service/app/tests/`.

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

Each script requires `requests` and targets `http://localhost:8000` (semantic search) or
`http://localhost:5054` (BFF).

## Bestand in Qdrant (im semantic-search-Container)

Diese beiden Skripte laufen nicht gegen die HTTP-API, sondern per stdin im
semantic-search-Container, mit dessen Qdrant-Umgebung:

- `bestand_pruefen.py` – **nur lesend**. Zaehlt Punkte je Typ und Herkunft,
  Kommentare/Hintergrundinfos ohne verknuepfende Aussage, normalisiert gleiche
  Aussagen, Stand des Felds `text_normalisiert`; mit `--praefix N` zusaetzlich eine
  Stichprobe, mit welchem E5-Praefix die Vektoren eingebettet sind. Gibt nur Zaehler
  aus, keine Texte, IDs oder Autoren.
- `text_normalisiert_nachtragen.py` – traegt das Payload-Feld `text_normalisiert`
  fuer Aussagen und Kommentare nach (exakter Abgleich der Dublettenpruefung) und legt
  den Keyword-Index an. Ohne `--ausfuehren` wird nur gezaehlt; idempotent. Erst nach
  dem Ausrollen der Version laufen lassen, die das Feld schreibt.

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

## Loeschkommando (im PostgreSQL-Container)

`person_loeschen.sql` – **schreibend.** Der PostgreSQL-Teil des Loeschkonzepts
(Schritt 1 und 2): loescht, was an der Kennung einer Person haengt, und ersetzt ihre
Kennung an Saetzen in fremden Einwuerfen durch einen Platzhalter mit dem Anzeigenamen
„ehemalige Person“. Ablauf, Reihenfolge und Fallen stehen in `docs/LOESCHKONZEPT.md`;
dort steht auch der Aufruf. Getestet in `tests/integration/test_loeschkommando.py`.

## Beitraege anonymisieren (im semantic-search-Container)

`beitraege_anonymisieren.py <kennung> [--ausfuehren]` – **schreibend mit
`--ausfuehren`.** Schritt 3 des Loeschkonzepts: ersetzt die Kennung an Beitraegen in
Qdrant durch den Platzhalter `ehemalige-person` (Anzeige „ehemalige Person“) und
listet die Treffer fuer die Einzelfallpruefung. Mit der Kennung `geloeschter-nutzer`
stellt es einmalig den Bestand mit dem alten Platzhalter um. Aufruf in
`docs/LOESCHKONZEPT.md`; getestet in `tests/unit/services/test_beitraege_anonymisieren.py`.
