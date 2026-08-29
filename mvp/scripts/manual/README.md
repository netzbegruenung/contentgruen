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
