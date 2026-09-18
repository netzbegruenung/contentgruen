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
docker exec -i contentgruen-semantic-search python - < bestand_pruefen.py

curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/contentgruen/main/mvp/scripts/manual/text_normalisiert_nachtragen.py
docker exec -i contentgruen-semantic-search python - < text_normalisiert_nachtragen.py
docker exec -i contentgruen-semantic-search python - --ausfuehren < text_normalisiert_nachtragen.py
```

`bestand_pruefen.py` nutzt nur qdrant_client und die Standardbibliothek und laeuft
auch gegen aeltere Versionen; `text_normalisiert_nachtragen.py` braucht den
ausgerollten neuen Stand.
